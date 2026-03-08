from sqlalchemy.orm import Session
from models.skill_quiz import SkillQuiz
from models.quiz_attempt import QuizAttempt
from models.event import Event
from models.course import Course
from services.skill_profile_service import update_skill_profile_from_quiz
import logging

logger = logging.getLogger(__name__)

def get_quiz_for_skill(skill_id: str, db: Session) -> SkillQuiz | None:
    return db.query(SkillQuiz).filter(SkillQuiz.skill_id == skill_id).first()

def evaluate_quiz_attempt(user_id: str, skill_id: str, answers: dict, db: Session) -> QuizAttempt:
    """
    Evaluates a user's quiz attempt, calculates score, and saves the attempt.
    If passed, emits a 'course_completed' event.
    """
    quiz = get_quiz_for_skill(skill_id, db)
    if not quiz:
        raise ValueError(f"Quiz not found for skill: {skill_id}")

    # Assuming quiz.questions is a list of dicts: {"id": "q1", "correct_answer": "A"}
    # And answers is a dict mapping question ids to user's answer: {"q1": "A"}
    import json
    questions = quiz.questions if quiz.questions else []
    if isinstance(questions, str):
        try:
            questions = json.loads(questions)
        except json.JSONDecodeError:
            questions = []
            
    total_questions = len(questions)
    
    if total_questions == 0:
        score = 100.0
        passed = True
    else:
        correct_count = 0
        for idx, q in enumerate(questions):
            q_id = str(q.get("id", f"q{idx}"))
            user_ans = str(answers.get(q_id, "")).strip().lower()
            correct_ans = str(q.get("correct_answer", "")).strip().lower()
            if user_ans == correct_ans:
                correct_count += 1
                
        score = (correct_count / total_questions) * 100.0
        passed = score >= quiz.passing_score
        
    attempt = QuizAttempt(
        user_id=user_id,
        skill_id=skill_id,
        score=score,
        passed=passed,
        answers=json.dumps(answers) if isinstance(answers, dict) else answers
    )
    db.add(attempt)
    db.flush() # Flush to get attempt.id if needed
    
    # We need the course to get roadmap_id
    course = db.query(Course).filter(Course.id == skill_id).first()
    if course:
        # As per integration instructions, update adaptive profile securely
        update_skill_profile_from_quiz(
            user_id=user_id,
            skill_id=skill_id,
            quiz_score=score,
            roadmap_id=course.roadmap_id,
            db=db
        )
    
    if passed:
        # Check if they already have a completed event to avoid duplicates
        existing_event = db.query(Event).filter(
            Event.user_id == user_id,
            Event.event_type == "course_completed",
            Event.course_id == skill_id
        ).first()
        
        if not existing_event and course:
            event = Event(
                user_id=user_id,
                event_type="course_completed",
                course_id=skill_id,
                roadmap_id=course.roadmap_id,
                payload=json.dumps({"score": score, "attempt_id": attempt.id})
            )
            db.add(event)
                
    db.commit()
    db.refresh(attempt)
    return attempt
