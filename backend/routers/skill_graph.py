from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from db.database import get_db
from models.user import User
from core.clerk_auth import get_current_user
from services.skill_graph_service import get_roadmap_skill_status
from services.dynamic_roadmap_service import compute_dynamic_roadmap
from models.course import Course
from services.skill_profile_service import get_or_create_skill_profile, initialize_skill_profile_from_cold_start

router = APIRouter()

@router.get("/{roadmap_id}/dynamic-status")
def read_dynamic_roadmap_status(
    roadmap_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns a personalized 5-state status map for all courses in the roadmap.
    States: completed | skippable | fast_tracked | unlocked | locked
    """
    result = compute_dynamic_roadmap(current_user.id, roadmap_id, db)
    if not result:
        raise HTTPException(status_code=404, detail=f"Roadmap '{roadmap_id}' not found or has no courses")
    return result


@router.get("/{roadmap_id}/status")
def read_roadmap_skill_status(
    roadmap_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    response: Response = None,
):
    """
    Returns the unlock status (completed, unlocked, locked)
    for all skills in the given roadmap for the active user.
    """
    response.headers["Deprecation"] = "true"
    response.headers["Sunset"] = "2026-06-01"
    response.headers["Link"] = f'</skill-graph/{roadmap_id}/dynamic-status>; rel="successor-version"'
    user_id = str(current_user.id)
    
    # 1. Fetch all skills for roadmap
    courses = db.query(Course.id).filter(Course.roadmap_id == roadmap_id).all()
    
    # 2. & 3. For each skill, get/create profile and initialize cold start if needed
    for course in courses:
        skill_id = course[0]
        profile = get_or_create_skill_profile(user_id, skill_id, roadmap_id, db)
        if profile.quiz_confidence == 0:
            initialize_skill_profile_from_cold_start(user_id, skill_id, db)
            
    return get_roadmap_skill_status(user_id, roadmap_id, db)
