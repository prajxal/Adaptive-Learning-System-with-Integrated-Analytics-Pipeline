from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from models.skill_profile import SkillProfile
from models.skill_weight import SkillWeight
import logging
from models.user import User
from models.course import Course
from services import xp_level_service

logger = logging.getLogger(__name__)

def get_or_create_skill_profile(user_id: str, skill_id: str, roadmap_id: str, db: Session) -> SkillProfile:
    """
    Returns an existing SkillProfile or creates a new empty one securely.
    Handles concurrency via try/except IntegrityError.
    """
    profile = db.query(SkillProfile).filter(
        SkillProfile.user_id == user_id,
        SkillProfile.skill_id == skill_id
    ).first()

    if profile:
        return profile
        
    new_profile = SkillProfile(
        user_id=user_id,
        skill_id=skill_id,
        roadmap_id=roadmap_id
    )
    
    try:
        db.add(new_profile)
        db.commit()
        db.refresh(new_profile)
        return new_profile
    except IntegrityError:
        # Caused by concurrent insert
        db.rollback()
        return db.query(SkillProfile).filter(
            SkillProfile.user_id == user_id,
            SkillProfile.skill_id == skill_id
        ).first()

def initialize_skill_profile_from_cold_start(user_id: str, skill_id: str, db: Session):
    """
    Cold start initialization from github/resume data. 
    Only runs if quiz_confidence == 0 (no quiz taken yet). 
    """
    pass # As per request constraint "Do not modify SkillWeight schema". We'll just define the function.
    # The prompt actually gives the algorithm for this:
    # We need a roadmap_id but function signature doesn't pass it. Wait, the user prompt says:
    # "initialize_skill_profile_from_cold_start(user_id, skill_id, db)"
    # How do we get roadmap_id? We can query it from Course.
    from models.course import Course
    course = db.query(Course).filter(Course.id == skill_id).first()
    if not course:
        return
        
    profile = get_or_create_skill_profile(user_id, skill_id, course.roadmap_id, db)
    
    if profile.quiz_confidence > 0:
        return # Skip cold start if we already have quiz signals
        
    # Fetch github and resume rows (Assume weight_type is 'github' and 'resume')
    github_weight = db.query(SkillWeight).filter(
        SkillWeight.user_id == user_id, 
        SkillWeight.skill_name == skill_id,
        SkillWeight.source == 'github'
    ).first()
    
    resume_weight = db.query(SkillWeight).filter(
        SkillWeight.user_id == user_id, 
        SkillWeight.skill_name == skill_id,
        SkillWeight.source == 'resume'
    ).first()
    
    github_prof = github_weight.weight if github_weight else 0.0
    github_conf = github_weight.confidence if github_weight else 0.0
    
    resume_prof = resume_weight.weight if resume_weight else 0.0
    resume_conf = resume_weight.confidence if resume_weight else 0.0
    
    total_conf = github_conf + resume_conf
    
    if total_conf > 0:
        cold_start_proficiency = (github_prof * github_conf + resume_prof * resume_conf) / total_conf
        cold_start_confidence = max(github_conf, resume_conf)
        
        # We also need to store these components safely onto the profile per prompt schemas
        profile.github_proficiency = github_prof
        profile.github_confidence = github_conf
        profile.resume_proficiency = resume_prof
        profile.resume_confidence = resume_conf
        
        profile.proficiency_level = cold_start_proficiency
        profile.confidence = cold_start_confidence
        
        db.commit()

def update_skill_profile_from_quiz(user_id: str, skill_id: str, quiz_score: float, roadmap_id: str, db: Session):
    """
    Updates adaptive score deterministically using quiz signal as authoritative.
    """
    profile = get_or_create_skill_profile(user_id, skill_id, roadmap_id, db)
    
    QUIZ_SIGNAL_WEIGHT = 0.8
    QUIZ_CONFIDENCE_INCREMENT = 0.2
    MAX_CONFIDENCE = 1.0
    
    old_quiz_confidence = profile.quiz_confidence
    old_quiz_proficiency = profile.quiz_proficiency
    
    new_quiz_confidence = min(MAX_CONFIDENCE, old_quiz_confidence + QUIZ_CONFIDENCE_INCREMENT)
    
    # EMA formula
    new_quiz_proficiency = (
        (old_quiz_proficiency * old_quiz_confidence + quiz_score * QUIZ_SIGNAL_WEIGHT) /
        (old_quiz_confidence + QUIZ_SIGNAL_WEIGHT)
    )
    
    cold_weight = max(profile.github_confidence, profile.resume_confidence) * 0.3
    
    final_proficiency = (
        (new_quiz_proficiency * new_quiz_confidence + profile.proficiency_level * cold_weight) /
        (new_quiz_confidence + cold_weight)
    )
    
    final_confidence = min(1.0, max(new_quiz_confidence, cold_weight))
    
    profile.quiz_proficiency = new_quiz_proficiency
    profile.quiz_confidence = new_quiz_confidence
    
    profile.proficiency_level = final_proficiency
    profile.confidence = final_confidence
    
    # --- XP award for quiz performance ---
    # Extract roadmap_id from skill_id if not provided (format: roadmap_id:node_id)
    resolved_roadmap_id = roadmap_id
    if not resolved_roadmap_id and ":" in skill_id:
        resolved_roadmap_id = skill_id.split(":")[0]

    if resolved_roadmap_id:
        # award_xp_for_quiz expects a 0–1 normalized score; quiz_score is 0–100
        xp_level_service.award_xp_for_quiz(
            user_id=int(user_id),
            quiz_score=quiz_score / 100.0,
            course_id=skill_id,
            roadmap_id=resolved_roadmap_id,
            db=db,
        )
    else:
        db.commit()
