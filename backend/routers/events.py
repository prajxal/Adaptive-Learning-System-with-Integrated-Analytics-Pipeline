from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.clerk_auth import get_current_user
from db.database import get_db
from models import Event, UserSkill
from models.course_prerequisite import CoursePrerequisite
from models.skill_profile import SkillProfile
from models.user import User
from services.dynamic_roadmap_service import get_skip_threshold
from services.skill_graph_service import is_skill_completed
from services import xp_level_service

router = APIRouter()


class EventPayload(BaseModel):
    event_type: Literal["course_completed", "course_skipped", "quiz_started", "quiz_failed", "resource_viewed", "resource_completed"]
    course_id: str
    payload: dict | None = None


@router.post("")
def create_event(payload: EventPayload, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, str]:
    roadmap_id = None
    if payload.event_type == "course_completed":
        if not payload.course_id or ":" not in payload.course_id:
            raise HTTPException(
                status_code=400,
                detail="Invalid course_id format for course_completed event. Expected 'roadmap_id:course_code'",
            )
        roadmap_id = payload.course_id.split(":")[0]
    elif payload.course_id and ":" in payload.course_id:
        roadmap_id = payload.course_id.split(":")[0]

    if payload.event_type == "course_skipped":
        skip_threshold = get_skip_threshold()
        user_id_str = str(current_user.id)

        # Verify a SkillProfile exists — do NOT create one
        profile = (
            db.query(SkillProfile)
            .filter(
                SkillProfile.user_id == user_id_str,
                SkillProfile.skill_id == payload.course_id,
            )
            .first()
        )

        if profile is None:
            raise HTTPException(
                status_code=403,
                detail="No skill profile found for this course — cannot verify skip eligibility",
            )

        if float(profile.confidence) < skip_threshold:
            raise HTTPException(
                status_code=403,
                detail=f"Course confidence too low to skip (confidence={profile.confidence:.2f}, required={skip_threshold:.2f})",
            )

        # Verify course is not locked (all prerequisites must be satisfied)
        prereqs = (
            db.query(CoursePrerequisite)
            .filter(CoursePrerequisite.course_id == payload.course_id)
            .all()
        )
        for prereq in prereqs:
            if not is_skill_completed(user_id_str, prereq.prerequisite_id, db):
                raise HTTPException(
                    status_code=403,
                    detail=f"Cannot skip a locked course — prerequisite '{prereq.prerequisite_id}' is not completed",
                )

        # Reject if already completed or skipped
        existing = (
            db.query(Event)
            .filter(
                Event.user_id == user_id_str,
                Event.course_id == payload.course_id,
                Event.event_type.in_(["course_completed", "course_skipped"]),
            )
            .first()
        )
        if existing is not None:
            raise HTTPException(
                status_code=409,
                detail="Course already completed or skipped",
            )

    event = Event(
        user_id=str(current_user.id),
        event_type=payload.event_type,
        course_id=payload.course_id,
        roadmap_id=roadmap_id,
        payload=payload.payload,
    )
    db.add(event)
    db.flush()

    if payload.event_type == "course_completed" and roadmap_id:
        xp_level_service.award_xp_for_completion(
            user_id=str(current_user.id),
            course_id=payload.course_id,
            roadmap_id=roadmap_id,
            db=db,
        )
        # award_xp_for_completion commits internally; also ensure proficiency update
        user_skill = (
            db.query(UserSkill)
            .filter(
                UserSkill.user_id == str(current_user.id), UserSkill.skill_name == roadmap_id
            )
            .first()
        )
        if user_skill:
            user_skill.proficiency_level = min(user_skill.proficiency_level + 0.05, 1.0)
        else:
            new_skill = UserSkill(
                user_id=str(current_user.id),
                skill_name=roadmap_id,
                xp=0,
                level=1,
                proficiency_level=0.1,
            )
            db.add(new_skill)
        db.commit()
    else:
        # quiz_failed: XP never goes down — no trust_score penalty
        db.commit()
    return {"status": "event received"}


@router.delete("/skip/{course_id}")
def unskip_course(course_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, str]:
    skip_event = (
        db.query(Event)
        .filter(
            Event.user_id == str(current_user.id),
            Event.course_id == course_id,
            Event.event_type == "course_skipped",
        )
        .first()
    )

    if skip_event is None:
        raise HTTPException(status_code=404, detail="No skip event found for this course")

    db.delete(skip_event)
    db.commit()
    return {"status": "course un-skipped"}
