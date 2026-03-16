from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db.database import get_db
from models.user import User
from core.clerk_auth import get_current_user
from services.skill_profile_service import get_or_create_skill_profile, initialize_skill_profile_from_cold_start
from models.course import Course

router = APIRouter()

@router.get("/{skill_id}")
def read_skill_profile(
    skill_id: str, 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    user_id = str(current_user.id)
    
    # Need roadmap_id to get/create profile properly
    course = db.query(Course).filter(Course.id == skill_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Skill not found")
        
    # Get or create profile
    profile = get_or_create_skill_profile(user_id, skill_id, course.roadmap_id, db)
    
    # Trigger cold-start initialization if it's completely empty
    if profile.quiz_confidence == 0:
        initialize_skill_profile_from_cold_start(user_id, skill_id, db)
        
        # We need to requery to get the updated DB values since initialize commits
        # and doesn't return the instance
        db.refresh(profile)
        
    return {
        "skill_id": profile.skill_id,
        "proficiency_level": profile.proficiency_level,
        "confidence": profile.confidence,
        "github_proficiency": profile.github_proficiency,
        "resume_proficiency": profile.resume_proficiency,
        "quiz_proficiency": profile.quiz_proficiency
    }
