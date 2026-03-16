from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.database import get_db
from models import Event, UserSkill
from models.user import User
from core.clerk_auth import get_current_user

router = APIRouter()


class EventPayload(BaseModel):
    event_type: str
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
        user_skill = (
            db.query(UserSkill)
            .filter(
                UserSkill.user_id == str(current_user.id), UserSkill.skill_name == roadmap_id
            )
            .first()
        )

        if user_skill:
            user_skill.trust_score = min(user_skill.trust_score + 50, 2000)
            user_skill.proficiency_level = min(user_skill.proficiency_level + 0.05, 1.0)
            new_skill = UserSkill(
                user_id=str(current_user.id),
                skill_name=roadmap_id,
                trust_score=850,
                proficiency_level=0.1,
            )
            db.add(new_skill)

    elif payload.event_type == "quiz_failed" and roadmap_id:
        user_skill = (
            db.query(UserSkill)
            .filter(
                UserSkill.user_id == str(current_user.id), UserSkill.skill_name == roadmap_id
            )
            .first()
        )
        if user_skill:
            user_skill.trust_score = max(user_skill.trust_score - 25, 0)

    db.commit()
    return {"status": "event received"}
