from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict

from db.database import get_db
from models.course import Course
from models.course_resource import CourseResource
from models.user import User
from core.clerk_auth import get_current_user
from routers.learning_path import get_adaptive_skill_score
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/{course_id}/resources")
def get_course_resources(
    course_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Fetches resources specifically bound to this course_id.
    Filters and ranks them based on the user's adaptive_score.
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # Get roadmap_id to compute adaptive score
    roadmap_id = course.roadmap_id or (course.id.split(":")[0] if ":" in course.id else course.id)
    adaptive_score = get_adaptive_skill_score(str(current_user.id), roadmap_id, db)

    logger.info(f"[Resource Fetch API] course_id={course_id} course_title='{course.title}' adaptive_score={adaptive_score}")

    # Fetch all resources tied strictly to this course
    resources = db.query(CourseResource).filter(
        CourseResource.course_id == course_id
    ).all()

    if not resources:
        logger.info(f"[Resource Fetch API] No static resources found for course_id={course_id}.")
        return {"primary": None, "additional": []}

    # Rank resources by how close their difficulty_level is to the adaptive_score
    # If the resource has no difficulty, we treat it as neutral distance (e.g. 0 or infinity)
    # We prioritize 'is_primary' if it exists, or the closest match.
    
    scored_resources = []
    for r in resources:
        diff = r.difficulty_level if r.difficulty_level is not None else 800
        distance = abs(diff - adaptive_score)
        scored_resources.append((distance, r))

    # Sort by distance (closest first), then by quality
    scored_resources.sort(key=lambda x: (x[0], -(x[1].quality_score or 0)))

    # Select the primary resource based on the best fit
    primary = scored_resources[0][1]
    additional = [item[1] for item in scored_resources[1:]]
    
    logger.info(f"[Resource Fetch API Result] Returning Primary: '{primary.title}' URL: '{primary.url}'")
    for a in additional:
        logger.info(f"[Resource Fetch API Result] Returning Additional: '{a.title}' URL: '{a.url}'")

    return {
        "primary": {
            "id": primary.id,
            "title": primary.title,
            "url": primary.url,
            "platform": primary.platform,
            "duration_seconds": primary.duration_seconds,
            "difficulty_level": primary.difficulty_level,
            "quality_score": primary.quality_score,
            "resource_type": primary.resource_type
        },
        "additional": [
            {
                "id": a.id,
                "title": a.title,
                "url": a.url,
                "platform": a.platform,
                "duration_seconds": a.duration_seconds,
                "difficulty_level": a.difficulty_level,
                "quality_score": a.quality_score,
                "resource_type": a.resource_type
            } for a in additional
        ],
        "adaptive_score": adaptive_score
    }
