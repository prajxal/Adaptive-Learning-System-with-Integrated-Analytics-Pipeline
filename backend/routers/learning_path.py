from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.database import get_db
from models.course import Course
from models.course_prerequisite import CoursePrerequisite
from models.skill_profile import SkillProfile
from models.skill_weight import SkillWeight
from models.user import User
from models.user_skill import UserSkill
from core.clerk_auth import get_current_user
from services.skill_synthesizer import get_skill_profile
from models.event import Event

router = APIRouter()

def get_completed_course_ids(user_id: str, db: Session) -> set[str]:
    completed_events = db.query(Event.course_id).filter(
        Event.user_id == user_id,
        Event.event_type == "course_completed"
    ).all()

    return {
        event.course_id
        for event in completed_events
        if event.course_id is not None
    }

def get_next_ready_nodes(
    user_id: str,
    roadmap_id: str,
    db: Session,
    limit: int = 5,
    completed_ids: set[str] | None = None,
    user_elo: float | None = None,
):
    if user_elo is None:
        user = db.query(User).filter(User.id == user_id).first()
        user_elo = (user.global_elo_rating or 1000.0) if user else 1000.0

    if completed_ids is None:
        completed_ids = get_completed_course_ids(user_id, db)

    elo = user_elo

    courses = db.query(Course).filter(
        Course.roadmap_id == roadmap_id
    ).all()

    # Filter by elo band and not-completed before touching the prereq table
    candidates = [
        c for c in courses
        if c.id not in completed_ids
        and (elo - 150 <= (c.difficulty_level or 1000.0) <= elo + 150)
    ]

    if not candidates:
        return []

    # Batch-load all prerequisites for candidate courses in one query
    candidate_ids = [c.id for c in candidates]
    all_prereqs = db.query(
        CoursePrerequisite.course_id,
        CoursePrerequisite.prerequisite_id,
    ).filter(CoursePrerequisite.course_id.in_(candidate_ids)).all()

    prereq_map: dict[str, set[str]] = {c_id: set() for c_id in candidate_ids}
    for p in all_prereqs:
        prereq_map[p.course_id].add(p.prerequisite_id)

    ready_nodes = [
        c for c in candidates
        if prereq_map[c.id].issubset(completed_ids)
    ]

    ready_nodes.sort(key=lambda c: abs((c.difficulty_level or 1000.0) - elo))

    return ready_nodes[:limit]


def collect_prerequisites(course_id: str, db: Session):
    visited = set()
    stack = [course_id]
    result = []

    while stack:
        current = stack.pop()

        prereqs = (
            db.query(CoursePrerequisite)
            .filter(CoursePrerequisite.course_id == current)
            .all()
        )

        for prereq in prereqs:
            if prereq.prerequisite_id not in visited:
                visited.add(prereq.prerequisite_id)

                course = (
                    db.query(Course)
                    .filter(Course.id == prereq.prerequisite_id)
                    .first()
                )

                if course:
                    result.append(course)

                stack.append(prereq.prerequisite_id)

    return result


def get_adaptive_skill_score(user_id: str, roadmap_id: str, db: Session) -> float:
    # Default baseline
    BASELINE_SCORE = 800.0

    # Fetch trust_score
    skill = db.query(UserSkill).filter(
        UserSkill.user_id == user_id,
        UserSkill.skill_name == roadmap_id
    ).first()

    trust_score = float(skill.trust_score) if skill and skill.trust_score is not None else BASELINE_SCORE

    # Fetch synthesized skill profiles for roadmap
    profiles = db.query(SkillProfile).filter(
        SkillProfile.user_id == user_id,
        SkillProfile.roadmap_id == roadmap_id
    ).all()

    if profiles:
        avg_confidence = sum(p.confidence for p in profiles) / len(profiles)
        normalized_skill_score = 800 + (avg_confidence * 1200)
    else:
        normalized_skill_score = BASELINE_SCORE

    # Blend trust_score and skill_weight_score
    adaptive_score = (0.7 * trust_score) + (0.3 * normalized_skill_score)

    print(f"[AdaptiveScore] user={user_id} roadmap={roadmap_id} score={adaptive_score}")

    return adaptive_score

def get_user_elo(user_id: str, roadmap_id: str, db: Session) -> float:
    skill = (
        db.query(UserSkill)
        .filter(UserSkill.user_id == user_id, UserSkill.skill_name == roadmap_id)
        .first()
    )

    if skill and skill.trust_score is not None:
        return float(skill.trust_score)

    return 800.0  # default starting ELO


@router.get("/{course_id}")
def get_learning_path(course_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user_id = str(current_user.id)
    target = db.query(Course).filter(Course.id == course_id).first()

    if not target:
        raise HTTPException(status_code=404, detail="Course not found")

    prereqs = collect_prerequisites(course_id, db)
    full_path = prereqs + [target]
    full_path.sort(key=lambda c: c.difficulty_level or 0)

    # Extract roadmap_id safely - use roadmap_id from target course or fallback to parsing ID
    roadmap_id = target.roadmap_id or (target.id.split(":")[0] if ":" in target.id else target.id)
    user_elo = get_adaptive_skill_score(user_id, roadmap_id, db)

    path = []
    for course in full_path:
        difficulty = course.difficulty_level or 0

        if difficulty < user_elo - 100:
            status = "completed"
        elif abs(difficulty - user_elo) <= 100:
            status = "ready"
        else:
            status = "locked"

        path.append(
            {
                "id": course.id,
                "title": course.title,
                "difficulty": course.difficulty_level,
                "status": status,
            }
        )

    return {
        "user_elo": user_elo,
        "target_course": target.title,
        "path": path,
    }
