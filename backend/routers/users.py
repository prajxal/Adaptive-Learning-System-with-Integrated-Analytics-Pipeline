from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct

from db.database import get_db
from models.skill_profile import SkillProfile
from models.course import Course
from models.event import Event
from models.user import User
from core.clerk_auth import get_current_user
from services.github_skill_extractor import synthesize_all_skills_for_user

router = APIRouter()

@router.get("/me")
def get_user_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "clerk_user_id": current_user.clerk_user_id,
        "email": current_user.email,
        "global_elo_rating": current_user.global_elo_rating,
        "resume_status": current_user.resume_status,
        "github_sync_status": current_user.github_sync_status
    }

@router.get("/me/profile")
def get_user_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user_id = str(current_user.id)
    
    # Get total completed courses
    completed_courses = db.query(func.count(distinct(Event.course_id))) \
        .filter(
            Event.user_id == user_id,
            Event.event_type == "course_completed"
        ).scalar() or 0

    # Get top 3 skills
    profiles = db.query(SkillProfile).filter(SkillProfile.user_id == user_id).all()
    skill_list = []
    
    if profiles:
        roadmap_ids = list(set(p.roadmap_id for p in profiles))
        for roadmap_id in roadmap_ids:
            roadmap_profiles = [p for p in profiles if p.roadmap_id == roadmap_id]
            avg_confidence = sum(p.confidence for p in roadmap_profiles) / len(roadmap_profiles)
            skill_list.append({
                "roadmap_id": roadmap_id,
                "confidence": avg_confidence
            })
            
        skill_list.sort(key=lambda x: x["confidence"], reverse=True)
        top_skills = [s["roadmap_id"] for s in skill_list[:3]]
    else:
        top_skills = []

    return {
        "global_elo_rating": current_user.global_elo_rating,
        "resume_status": current_user.resume_status,
        "github_sync_status": current_user.github_sync_status,
        "last_github_sync": current_user.last_github_sync,
        "completed_courses": completed_courses,
        "top_skills": top_skills
    }

@router.get("/me/skills")
def get_user_skills(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user_id = str(current_user.id)
    # Query all synthesized skills for the user
    profiles = db.query(SkillProfile).filter(SkillProfile.user_id == user_id).all()

    print(f"[UsersRouter] Fetching skills for {user_id}: found {len(profiles)} profiles")

    if not profiles:
        return {
            "user_id": user_id,
            "skills": []
        }

    skill_list = []
    
    # Get distinct roadmaps from the user's profiles
    roadmap_ids = list(set(p.roadmap_id for p in profiles))

    for roadmap_id in roadmap_ids:
        roadmap_profiles = [p for p in profiles if p.roadmap_id == roadmap_id]
        avg_confidence = sum(p.confidence for p in roadmap_profiles) / len(roadmap_profiles)
        avg_proficiency = sum(p.proficiency_level for p in roadmap_profiles) / len(roadmap_profiles)

        # Count total courses in roadmap
        total_courses = db.query(func.count(Course.id)) \
            .filter(Course.roadmap_id == roadmap_id) \
            .scalar() or 0

        # Count completed courses
        completed_courses = db.query(func.count(distinct(Event.course_id))) \
            .filter(
                Event.user_id == user_id,
                Event.event_type == "course_completed",
                Event.roadmap_id == roadmap_id
            ) \
            .scalar() or 0

        # Calculate progress percent safely
        progress_percent = round((completed_courses / total_courses) * 100, 2) if total_courses > 0 else 0.0

        skill_list.append({
            "roadmap_id": roadmap_id,
            "trust_score": float(avg_confidence * 1000) if avg_confidence else 800.0,
            "proficiency_level": float(avg_proficiency) if avg_proficiency else 0.0,
            "completed_courses": completed_courses,
            "total_courses": total_courses,
            "progress_percent": progress_percent,
            "last_updated": roadmap_profiles[0].updated_at if roadmap_profiles else None
        })

    return {
        "user_id": user_id,
        "skills": skill_list
    }

@router.post("/me/skills/rebuild")
def rebuild_skills(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user_id = str(current_user.id)
    synthesize_all_skills_for_user(user_id, db)
    return {"status": "success", "message": "Skills recalculated successfully"}
