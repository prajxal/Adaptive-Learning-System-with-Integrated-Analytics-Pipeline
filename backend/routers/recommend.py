import time

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from db.database import get_db
from models.user import User
from models.course import Course
from models.course_prerequisite import CoursePrerequisite
from models.skill_profile import SkillProfile
from core.clerk_auth import get_current_user
from routers.learning_path import get_completed_course_ids

router = APIRouter()


@router.get("/recommend")
def recommend(
    current_roadmap_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    _t0 = time.perf_counter()
    user_id = current_user.id
    user_level = getattr(current_user, "current_level", None) or 1
    user_xp = getattr(current_user, "total_xp", None) or 0

    # Query 1 — completed course IDs for this user
    completed_ids = get_completed_course_ids(str(user_id), db)

    # Query 2 — all courses across all roadmaps
    all_courses = db.query(Course).all()

    # Group by roadmap and identify candidates (level band + not completed)
    courses_by_roadmap: dict[str, list[Course]] = {}
    candidate_ids: list[str] = []
    for c in all_courses:
        courses_by_roadmap.setdefault(c.roadmap_id, []).append(c)
        if (
            c.id not in completed_ids
            and (getattr(c, "required_level", None) or 1) <= user_level + 1
        ):
            candidate_ids.append(c.id)

    # Query 3 — prerequisites for ALL candidates in one shot
    all_prereqs = db.query(
        CoursePrerequisite.course_id,
        CoursePrerequisite.prerequisite_id,
    ).filter(CoursePrerequisite.course_id.in_(candidate_ids)).all()

    prereq_map: dict[str, set[str]] = {c_id: set() for c_id in candidate_ids}
    for p in all_prereqs:
        prereq_map[p.course_id].add(p.prerequisite_id)

    def get_ready_for_roadmap(roadmap_id: str, limit: int) -> list[Course]:
        """Pure Python — no DB calls."""
        ready = [
            c for c in courses_by_roadmap.get(roadmap_id, [])
            if c.id in prereq_map and prereq_map[c.id].issubset(completed_ids)
        ]
        # Sort by required_level ascending (lower required level first)
        ready.sort(key=lambda c: (getattr(c, "required_level", None) or 1, c.id))
        return ready[:limit]

    # Stage 1 — next steps in the current roadmap
    next_nodes = get_ready_for_roadmap(current_roadmap_id, 5)

    # Cold start fallback: no ready nodes → return lowest-level courses
    if not next_nodes:
        next_nodes = sorted(
            courses_by_roadmap.get(current_roadmap_id, []),
            key=lambda c: (getattr(c, "required_level", None) or 1, c.id),
        )[:5]

    # Query 4 — skill profile confidence for roadmap suggestions
    skill_profiles = db.query(SkillProfile).filter(
        SkillProfile.user_id == str(user_id)
    ).all()
    confidence_by_roadmap: dict[str, float] = {}
    for sp in skill_profiles:
        rid_key = str(sp.roadmap_id)
        confidence_by_roadmap[rid_key] = confidence_by_roadmap.get(rid_key, 0.0) + float(sp.confidence or 0.0)

    # Stage 2 — suggest other roadmaps (pure Python, no more DB calls)
    roadmap_scores = []
    for rid in courses_by_roadmap:
        if rid == current_roadmap_id:
            continue
        unlocked_count = len(get_ready_for_roadmap(rid, 3))
        skill_boost = confidence_by_roadmap.get(rid, 0.0)
        roadmap_scores.append((rid, unlocked_count + (skill_boost * 2.0)))

    roadmap_scores.sort(key=lambda x: x[1], reverse=True)
    suggested_roadmaps = [r[0] for r in roadmap_scores[:3]]

    print(f"[PERF] GET /recommend/recommend took {(time.perf_counter() - _t0) * 1000:.0f}ms (roadmaps checked: {len(courses_by_roadmap)})")
    return {
        "user_level": user_level,
        "user_xp": user_xp,
        "next_in_current_roadmap": [
            {
                "id": c.id,
                "title": c.title,
                "required_level": getattr(c, "required_level", None) or 1,
                "roadmap_id": c.roadmap_id,
            }
            for c in next_nodes
        ],
        "suggested_new_roadmaps": suggested_roadmaps,
    }
