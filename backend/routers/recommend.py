from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from db.database import get_db
from models.user import User
from models.course import Course
from core.security import get_current_user
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

    # Stage 2 — Suggest new roadmaps
    roadmap_ids = db.query(Course.roadmap_id).distinct().all()

    roadmap_scores = []

    for (rid,) in roadmap_ids:

        if rid == current_roadmap_id:
            continue

        ready = get_next_ready_nodes(
            user_id,
            rid,
            db,
            limit=3
        )

        roadmap_scores.append((rid, len(ready)))

    roadmap_scores.sort(
        key=lambda x: x[1],
        reverse=True
    )

    suggested_roadmaps = [
        r[0]
        for r in roadmap_scores[:3]
    ]

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
