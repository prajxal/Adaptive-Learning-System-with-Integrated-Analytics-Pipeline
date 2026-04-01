from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.database import get_db
from models.course import Course
from models.course_prerequisite import CoursePrerequisite
from models.user import User
from core.clerk_auth import get_current_user
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
    user_level: int | None = None,
):
    if user_level is None:
        user = db.query(User).filter(User.id == user_id).first()
        user_level = (getattr(user, "current_level", None) or 1) if user else 1

    if completed_ids is None:
        completed_ids = get_completed_course_ids(user_id, db)

    courses = db.query(Course).filter(
        Course.roadmap_id == roadmap_id
    ).all()

    # Filter by level band (accessible within one level above user) and not-completed
    candidates = [
        c for c in courses
        if c.id not in completed_ids
        and (getattr(c, "required_level", None) or 1) <= user_level + 1
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

    # Sort by required_level ascending (easiest first), then by importance score proxy
    ready_nodes.sort(key=lambda c: (getattr(c, "required_level", None) or 1, c.id))

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



@router.get("/{course_id}")
def get_learning_path(course_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user_id = str(current_user.id)
    target = db.query(Course).filter(Course.id == course_id).first()

    if not target:
        raise HTTPException(status_code=404, detail="Course not found")

    prereqs = collect_prerequisites(course_id, db)
    full_path = prereqs + [target]
    full_path.sort(key=lambda c: getattr(c, "required_level", None) or 1)

    user_level = getattr(current_user, "current_level", None) or 1
    user_xp = getattr(current_user, "total_xp", None) or 0

    completed_ids = get_completed_course_ids(user_id, db)

    path = []
    for course in full_path:
        required_level = getattr(course, "required_level", None) or 1

        if course.id in completed_ids:
            status = "completed"
        elif required_level <= user_level:
            status = "ready"
        else:
            status = "locked"

        path.append(
            {
                "id": course.id,
                "title": course.title,
                "required_level": required_level,
                "status": status,
            }
        )

    return {
        "user_level": user_level,
        "user_xp": user_xp,
        "target_course": target.title,
        "path": path,
    }
