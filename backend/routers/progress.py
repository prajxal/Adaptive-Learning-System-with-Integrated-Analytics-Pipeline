from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from db.database import get_db
from models.course import Course
from models.event import Event
from models.user import User
from models.user_skill import UserSkill
from core.clerk_auth import get_current_user

router = APIRouter()


@router.get("/roadmap/{roadmap_id}")
def get_roadmap_course_progress(
    roadmap_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = str(current_user.id)

    # 1) Fetch all courses for the roadmap in one query
    courses = db.query(Course).filter(Course.roadmap_id == roadmap_id).all()
    course_slugs = [course.id for course in courses]

    if not course_slugs:
        return {"course_progress": {}}

    # 2) Fetch completed progress rows for these courses in one query
    completed_rows = (
        db.query(Event.course_id)
        .filter(
            Event.user_id == user_id,
            Event.event_type == "course_completed",
            Event.course_id.in_(course_slugs),
        )
        .distinct()
        .all()
    )

    # Build default map (0 = not completed, 1 = completed)
    progress_map = {course_slug: 0 for course_slug in course_slugs}
    for (course_slug,) in completed_rows:
        if course_slug in progress_map:
            progress_map[course_slug] = 1

    return {"course_progress": progress_map}


@router.get("/{roadmap_id}")
def get_progress(roadmap_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user_id = str(current_user.id)
    # total courses in roadmap
    total_courses = (
        db.query(func.count(Course.id))
        .filter(Course.roadmap_id == roadmap_id)
        .scalar()
    )
    total_courses = total_courses or 0

    # completed courses
    completed_courses = (
        db.query(func.count(func.distinct(Event.course_id)))
        .filter(
            Event.user_id == user_id,
            Event.event_type == "course_completed",
            Event.roadmap_id == roadmap_id
        )
        .scalar()
    )
    completed_courses = completed_courses or 0

    # skill data
    skill = (
        db.query(UserSkill)
        .filter(
            UserSkill.user_id == user_id,
            UserSkill.skill_name == roadmap_id
        )
        .first()
    )

    trust_score = skill.trust_score if skill and skill.trust_score is not None else 800.0
    proficiency_level = skill.proficiency_level if skill and skill.proficiency_level is not None else 0.0

    progress_percent = (
        (completed_courses / total_courses) * 100
        if total_courses > 0 else 0.0
    )
    
    # Clamp progress_percent to 100%
    progress_percent = min(100.0, progress_percent)

    return {
        "roadmap_id": roadmap_id,
        "total_courses": total_courses,
        "completed_courses": completed_courses,
        "progress_percent": round(progress_percent, 2),
        "trust_score": float(trust_score),
        "proficiency_level": float(proficiency_level)
    }
