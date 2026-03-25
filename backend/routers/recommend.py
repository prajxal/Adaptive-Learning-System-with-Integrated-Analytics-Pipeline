from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from db.database import get_db
from models.user import User
from models.course import Course
from models.skill_profile import SkillProfile
from core.clerk_auth import get_current_user
from routers.learning_path import get_next_ready_nodes

router = APIRouter()

@router.get("/recommend")
def recommend(
    current_roadmap_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user_id = current_user.id

    # Stage 1 — Continue current roadmap
    next_nodes = get_next_ready_nodes(
        user_id,
        current_roadmap_id,
        db,
        limit=5
    )

    # Cold start fallback
    if not next_nodes:
        next_nodes = db.query(Course).filter(
            Course.roadmap_id == current_roadmap_id
        ).order_by(
            Course.difficulty_level.asc()
        ).limit(5).all()

    # Stage 2 — Suggest new roadmaps, weighted by user skill confidence
    roadmap_ids = db.query(Course.roadmap_id).distinct().all()

    # Build a map of roadmap_id → sum of skill confidence from SkillProfile
    skill_profiles = db.query(SkillProfile).filter(
        SkillProfile.user_id == str(user_id)
    ).all()
    confidence_by_roadmap: dict[str, float] = {}
    for sp in skill_profiles:
        rid_key = str(sp.roadmap_id)
        confidence_by_roadmap[rid_key] = confidence_by_roadmap.get(rid_key, 0.0) + float(sp.confidence or 0.0)

    roadmap_scores = []

    for (rid,) in roadmap_ids:
        rid_str = str(rid)
        if rid_str == current_roadmap_id:
            continue

        ready = get_next_ready_nodes(user_id, rid_str, db, limit=3)
        unlocked_count = len(ready)

        # Skill-confidence boost: roadmaps where user has relevant confidence rank higher
        skill_boost = confidence_by_roadmap.get(rid_str, 0.0)

        # Combined score: unlocked node count + skill affinity signal
        combined_score = unlocked_count + (skill_boost * 2.0)
        roadmap_scores.append((rid_str, combined_score))

    roadmap_scores.sort(key=lambda x: x[1], reverse=True)

    suggested_roadmaps = [r[0] for r in roadmap_scores[:3]]

    return {
        "user_elo": current_user.global_elo_rating,
        "next_in_current_roadmap": [
            {
                "id": c.id,
                "title": c.title,
                "difficulty": c.difficulty_level,
                "roadmap_id": c.roadmap_id
            }
            for c in next_nodes
        ],
        "suggested_new_roadmaps": suggested_roadmaps
    }
