from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict

from db.database import get_db
from models.course import Course
from models.course_resource import CourseResource
from models.user import User
from core.clerk_auth import get_current_user
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
    Primary resources are surfaced first, then sorted by quality score.
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    logger.info(f"[Resource Fetch API] course_id={course_id} course_title='{course.title}'")

    # Fetch all resources tied strictly to this course
    resources = db.query(CourseResource).filter(
        CourseResource.course_id == course_id
    ).all()

    if not resources:
        logger.info(f"[Resource Fetch API] No static resources found for course_id={course_id}.")
        return {"primary": None, "additional": []}

    # Rank resources: primary flag first, then by quality_score descending
    def _sort_key(r: CourseResource) -> tuple:
        is_primary = int(bool(getattr(r, "is_primary", False)))
        quality = float(r.quality_score or 0)
        return (-is_primary, -quality)

    sorted_resources = sorted(resources, key=_sort_key)

    primary = sorted_resources[0]
    additional = sorted_resources[1:]

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
    }
