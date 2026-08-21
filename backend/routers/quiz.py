from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from db.database import get_db
from models.user import User
from core.clerk_auth import get_current_user
from services.quiz_service import evaluate_quiz_attempt
from services.quiz_generation_service import get_or_generate_quiz
from services.xp_level_service import get_user_global_xp, get_user_level

router = APIRouter()

@router.get("/{skill_id}")
async def read_quiz_for_skill(skill_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    quiz = await get_or_generate_quiz(skill_id, db)
    if not quiz or not quiz.questions:
        raise HTTPException(status_code=404, detail="Quiz not found")
        
    # Return questions without correct answers to prevent cheating
    import json
    sanitized_questions = []
    questions = quiz.questions if quiz.questions else []
    if isinstance(questions, str):
        try:
            questions = json.loads(questions)
        except json.JSONDecodeError:
            questions = []
            
    for q in questions:
        # Strip answer fields — they are sent back only on the results screen
        sq = {k: v for k, v in dict(q).items() if k not in ("correct_answer", "explanation")}
        sanitized_questions.append(sq)
        
    return {
        "id": quiz.id,
        "skill_id": quiz.skill_id,
        "questions": sanitized_questions,
        "passing_score": quiz.passing_score
    }

class QuizSubmission(BaseModel):
    answers: dict

@router.post("/{skill_id}/submit")
async def submit_quiz_attempt(
    skill_id: str, 
    submission: QuizSubmission,
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    try:
        # Ensure first-time submissions and incomplete persisted rows have a valid quiz.
        await get_or_generate_quiz(skill_id, db)

        user_id = str(current_user.id)
        xp_before = get_user_global_xp(user_id, db)
        level_before = get_user_level(user_id, db)
        attempt = evaluate_quiz_attempt(user_id, skill_id, submission.answers, db)

        xp_after = get_user_global_xp(user_id, db)
        level_after = get_user_level(user_id, db)
        return {
            "attempt_id": attempt.id,
            "skill_id": attempt.skill_id,
            "score": attempt.score,
            "passed": attempt.passed,
            "message": "Quiz passed successfully! Course completed." if attempt.passed else "Keep studying and try again.",
            "xp_awarded": xp_after - xp_before,
            "total_xp": xp_after,
            "current_level": level_after,
            "leveled_up": level_after > level_before,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
