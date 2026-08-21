import os
import json
import re
import httpx
import logging
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from pydantic import BaseModel, ValidationError

from models.skill_quiz import SkillQuiz
from models.course import Course
from core.config import DATABASE_URL # We don't have GEMINI_API_KEY in config yet, let's just use os.getenv

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent"

class QuizQuestion(BaseModel):
    question: str
    options: list[str]
    correct_answer: str
    explanation: str

class QuizSchema(BaseModel):
    questions: list[QuizQuestion]

def extract_json_from_text(text: str) -> dict | None:
    """
    Extracts the first valid JSON object from a given text, 
    even if it's wrapped in markdown code blocks or extra commentary.
    """
    # Try to find something that looks like complete JSON
    # It might be in a ```json ... ``` block
    json_blocks = re.findall(r'```(?:json)?\s*(.*?)\s*```', text, re.DOTALL)
    if json_blocks:
        for block in json_blocks:
            try:
                return json.loads(block)
            except json.JSONDecodeError:
                continue
                
    # If no markdown blocks, try finding the first '{' and last '}'
    start_idx = text.find('{')
    end_idx = text.rfind('}')
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        potential_json = text[start_idx:end_idx+1]
        try:
            return json.loads(potential_json)
        except json.JSONDecodeError:
            pass
            
    return None

def validate_quiz_json(quiz_data: dict) -> list[dict]:
    """
    Validates the schema of the generated quiz JSON.
    Accepts 4-6 questions to handle minor Gemini variation.
    Returns the list of question dicts if valid, raises ValueError if not.
    """
    try:
        validated = QuizSchema(**quiz_data)
        if not (4 <= len(validated.questions) <= 6):
            raise ValueError(f"Expected 4-6 questions, got {len(validated.questions)}")

        for q in validated.questions:
            if len(q.options) != 4:
                raise ValueError("Each question must have exactly 4 options")

        # Cap at 5 questions to keep quiz length consistent
        return [q.model_dump() for q in validated.questions[:5]]
    except ValidationError as e:
        raise ValueError(f"Invalid quiz schema: {str(e)}")

def generate_fallback_quiz(skill_title: str, skill_description: str) -> list[dict]:
    """
    Returns a minimal static quiz when Gemini is unavailable.
    Questions are generic but contextually titled so the quiz page always renders.
    """
    desc_snippet = (skill_description[:80] + "...") if len(skill_description) > 80 else skill_description
    return [
        {
            "question": f"What is the primary purpose of {skill_title}?",
            "options": [
                f"To provide a foundation for {skill_title} concepts",
                f"To replace all other tools in the {skill_title} ecosystem",
                f"To act as a database for {skill_title} data",
                f"None of the above"
            ],
            "correct_answer": f"To provide a foundation for {skill_title} concepts",
            "explanation": f"{skill_title} is a core topic in its domain. {desc_snippet}"
        },
        {
            "question": f"Which of the following best describes {skill_title}?",
            "options": [
                f"A tool used in the context of {skill_title}",
                f"An unrelated technology",
                f"A deprecated standard",
                f"A hardware component"
            ],
            "correct_answer": f"A tool used in the context of {skill_title}",
            "explanation": f"{skill_title} is relevant in its specific domain and roadmap context."
        },
        {
            "question": f"When learning {skill_title}, which approach is most effective?",
            "options": [
                "Practice with real projects and examples",
                "Memorise documentation without applying it",
                "Skip fundamentals and jump to advanced topics",
                "Avoid reading any documentation"
            ],
            "correct_answer": "Practice with real projects and examples",
            "explanation": "Hands-on practice is the most effective way to build proficiency in any technical skill."
        },
        {
            "question": f"What is a common use case for {skill_title}?",
            "options": [
                f"Building or improving systems related to {skill_title}",
                "Managing physical hardware directly",
                "Replacing network protocols",
                "None of the above"
            ],
            "correct_answer": f"Building or improving systems related to {skill_title}",
            "explanation": f"{skill_title} is commonly applied in software development and related disciplines."
        },
        {
            "question": f"Which resource type is most helpful when learning {skill_title}?",
            "options": [
                "Official documentation and guided tutorials",
                "Unrelated blog posts",
                "Marketing materials",
                "Social media threads only"
            ],
            "correct_answer": "Official documentation and guided tutorials",
            "explanation": "Official documentation provides accurate, up-to-date information for any technical topic."
        },
    ]


async def get_or_generate_quiz(skill_id: str, db: Session) -> SkillQuiz:
    """
    Returns an existing quiz if available, otherwise generates one idempotenly 
    using the Gemini API and saves it. Handles race conditions safely.
    """
    # Step 1: Check cache
    quiz = db.query(SkillQuiz).filter(SkillQuiz.skill_id == skill_id).first()
    
    # Ensure questions is a list for the length check (SQLite returns string for JSON)
    if quiz:
        questions = quiz.questions
        if isinstance(questions, str):
            try:
                questions = json.loads(questions)
            except json.JSONDecodeError:
                questions = []

        if isinstance(questions, list) and questions:
            try:
                quiz.questions = validate_quiz_json({"questions": questions})
                return quiz
            except ValueError:
                questions = []

        quiz.questions = []

    # Step 2: Fetch required context
    course = db.query(Course).filter(Course.id == skill_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Skill (course) not found")
        
    skill_title = str(course.title)
    skill_description = str(course.description or "")
    roadmap_id = course.roadmap_id
    roadmap_title = roadmap_id.replace('-', ' ').title() # simple fallback for roadmap title
    
    # Step 3: Trigger Generation
    if not GEMINI_API_KEY:
        logger.warning(f"GEMINI_API_KEY not set — using fallback quiz for skill {skill_id}")
        fallback_questions = generate_fallback_quiz(skill_title, skill_description)
        if quiz:
            quiz.questions = json.dumps(fallback_questions)
            quiz.passing_score = 75
            db.commit()
            db.refresh(quiz)
            quiz.questions = fallback_questions
            return quiz

        fallback_quiz = SkillQuiz(
            skill_id=skill_id,
            questions=json.dumps(fallback_questions),
            passing_score=75
        )
        try:
            db.add(fallback_quiz)
            db.commit()
            db.refresh(fallback_quiz)
        except IntegrityError:
            db.rollback()
            fallback_quiz = db.query(SkillQuiz).filter(SkillQuiz.skill_id == skill_id).first()
        if not fallback_quiz:
            raise HTTPException(status_code=503, detail="Quiz generation temporarily unavailable")
        if isinstance(fallback_quiz.questions, str):
            try:
                fallback_quiz.questions = json.loads(fallback_quiz.questions)
            except json.JSONDecodeError:
                raise HTTPException(status_code=503, detail="Quiz generation temporarily unavailable")
        if not isinstance(fallback_quiz.questions, list):
            raise HTTPException(status_code=503, detail="Quiz generation temporarily unavailable")
        try:
            fallback_quiz.questions = validate_quiz_json({"questions": fallback_quiz.questions})
        except ValueError:
            raise HTTPException(status_code=503, detail="Quiz generation temporarily unavailable")
        return fallback_quiz
        
    prompt = f"""You are an expert technical instructor.

Generate a quiz to assess understanding of the following skill.

Skill title: {skill_title}

Skill description: {skill_description}

Roadmap context: {roadmap_title}

Requirements:

• Generate exactly 5 questions
• Difficulty level: intermediate
• Each question must test conceptual understanding, not trivia
• Each question must have exactly 4 options
• Only one correct answer
• Include explanation for correct answer
• Questions must be clear, unambiguous, and technically accurate

Response format requirements:

• Return strictly valid JSON
• Do NOT include markdown
• Do NOT include code blocks
• Do NOT include extra text
• Only return JSON

Required JSON format:

{{
"questions": [
{{
"question": "string",
"options": ["A", "B", "C", "D"],
"correct_answer": "string",
"explanation": "string"
}}
]
}}
"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{GEMINI_API_URL}?key={GEMINI_API_KEY}",
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.4}
                },
                headers={"Content-Type": "application/json"},
                timeout=30.0
            )
            response.raise_for_status()
            
            try:
                response_data = response.json()
                content = response_data["candidates"][0]["content"]["parts"][0]["text"]
                
                # First try our robust extractor, fallback to standard json.loads
                quiz_data = extract_json_from_text(content)
                if not quiz_data:
                    quiz_data = json.loads(content)
                    
                questions = quiz_data["questions"]
            except (KeyError, IndexError, json.JSONDecodeError) as e:
                logger.error(f"Gemini response parsing failed: {e}, raw: {response.text}")
                questions = None

    except (httpx.RequestError, httpx.HTTPStatusError) as e:
        logger.error(f"Gemini API request failed: {e}")
        questions = None

    # Validate JSON schema; fall back to static quiz on failure
    if questions is not None:
        try:
            questions = validate_quiz_json({"questions": questions})
        except ValueError as e:
            logger.error(f"Quiz validation failed: {e}")
            questions = None

    if questions is None:
        logger.warning(f"Falling back to static quiz for skill {skill_id}")
        questions = generate_fallback_quiz(skill_title, skill_description)
        
    # Step 5: Safely persist with race-condition handling
    if quiz:
        quiz.questions = json.dumps(questions)
        quiz.passing_score = 75  # 4/5 correct needed to pass
        try:
            db.commit()
            db.refresh(quiz)
            quiz.questions = json.loads(quiz.questions)
            return quiz
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=503, detail="Quiz generation temporarily unavailable")

    new_quiz = SkillQuiz(
        skill_id=skill_id,
        questions=json.dumps(questions),
        passing_score=75  # 4/5 correct needed to pass
    )
    
    try:
        db.add(new_quiz)
        db.commit()
        db.refresh(new_quiz)
        
        # Ensure returned object has list instead of string
        if isinstance(new_quiz.questions, str):
            new_quiz.questions = json.loads(new_quiz.questions)
            
        return new_quiz
    except IntegrityError:
        # Race condition: someone else generated and inserted the quiz 
        # while we were also generating it
        db.rollback()
        quiz = db.query(SkillQuiz).filter(SkillQuiz.skill_id == skill_id).first()
        
        if quiz and isinstance(quiz.questions, str):
            try:
                quiz.questions = json.loads(quiz.questions)
            except json.JSONDecodeError:
                quiz.questions = []

        if quiz and isinstance(quiz.questions, list) and quiz.questions:
            try:
                quiz.questions = validate_quiz_json({"questions": quiz.questions})
                return quiz
            except ValueError:
                pass

        raise HTTPException(status_code=503, detail="Quiz generation temporarily unavailable")
