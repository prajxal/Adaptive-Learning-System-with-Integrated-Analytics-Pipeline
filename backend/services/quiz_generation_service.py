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
    Strictly validates the schema of the generated quiz JSON.
    Returns the list of question dicts if valid, raises ValueError if not.
    """
    try:
        validated = QuizSchema(**quiz_data)
        if len(validated.questions) != 4:
            raise ValueError(f"Expected exactly 4 questions, got {len(validated.questions)}")
        
        for q in validated.questions:
            if len(q.options) != 4:
                raise ValueError("Each question must have exactly 4 options")
                
        return [q.model_dump() for q in validated.questions]
    except ValidationError as e:
        raise ValueError(f"Invalid quiz schema: {str(e)}")

async def get_or_generate_quiz(skill_id: str, db: Session) -> SkillQuiz:
    """
    Returns an existing quiz if available, otherwise generates one idempotenly 
    using the Gemini API and saves it. Handles race conditions safely.
    """
    # Step 1: Check cache
    quiz = db.query(SkillQuiz).filter(SkillQuiz.skill_id == skill_id).first()
    
    # Ensure questions is a list for the length check (SQLite returns string for JSON)
    if quiz and isinstance(quiz.questions, str):
        try:
            quiz.questions = json.loads(quiz.questions)
        except json.JSONDecodeError:
            pass

    if quiz and quiz.questions and len(quiz.questions) == 4:
        return quiz
        
    # Step 2: Fetch required context
    course = db.query(Course).filter(Course.id == skill_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Skill (course) not found")
        
    skill_title = course.title
    skill_description = course.description or ""
    roadmap_id = course.roadmap_id
    roadmap_title = roadmap_id.replace('-', ' ').title() # simple fallback for roadmap title
    
    # Step 3: Trigger Generation
    if not GEMINI_API_KEY:
        raise HTTPException(
            status_code=404,
            detail="Quiz not found and Gemini generation unavailable"
        )
        
    prompt = f"""You are an expert technical instructor.

Generate a quiz to assess understanding of the following skill.

Skill title: {skill_title}

Skill description: {skill_description}

Roadmap context: {roadmap_title}

Requirements:

• Generate exactly 4 questions
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
                raise HTTPException(status_code=502, detail="Quiz generation failed. Please try again.")
            
    except (httpx.RequestError, httpx.HTTPStatusError) as e:
        logger.error(f"Gemini API request failed: {e}")
        raise HTTPException(status_code=503, detail="Quiz generation temporarily unavailable")
        
    # Validate JSON schema and exact length
    try:
        questions = validate_quiz_json({"questions": questions})
    except ValueError as e:
        logger.error(f"Quiz validation failed: {e}")
        raise HTTPException(status_code=502, detail="Quiz generation failed. Please try again.")
        
    # Step 5: Safely persist with race-condition handling
    new_quiz = SkillQuiz(
        skill_id=skill_id,
        questions=json.dumps(questions),
        passing_score=100  # Enforce 100% since there are only 4 questions
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
                pass

        if quiz and quiz.questions and len(quiz.questions) == 4:
            return quiz
        else:
            # Should theoretically never happen unless deleted immediately after insertion
            raise HTTPException(status_code=503, detail="Quiz generation temporarily unavailable")
