import time

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, text

from db.database import get_db
from models.course import Course
from models.event import Event
from models.quiz_attempt import QuizAttempt
from models.user import User
from models.user_skill import UserSkill
from core.clerk_auth import get_current_user

router = APIRouter()


@router.get("/roadmap/{roadmap_id}")
def get_roadmap_course_progress(
    roadmap_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = str(current_user.id)

    # 1) Fetch all courses for the roadmap in one query
    courses = db.query(Course).filter(Course.roadmap_id == roadmap_id).all()
    course_slugs = [str(course.id) for course in courses]

    if not course_slugs:
        return {"course_progress": {}}

    # 2) Completed via event log
    completed_via_event = {
        course_id
        for (course_id,) in db.query(Event.course_id)
        .filter(
            Event.user_id == user_id,
            Event.event_type == "course_completed",
            Event.course_id.in_(course_slugs),
        )
        .distinct()
        .all()
    }

    # 3) Completed via quiz attempt (passed=True) — catches missed events
    completed_via_quiz = {
        skill_id
        for (skill_id,) in db.query(QuizAttempt.skill_id)
        .filter(
            QuizAttempt.user_id == user_id,
            QuizAttempt.passed == True,
            QuizAttempt.skill_id.in_(course_slugs),
        )
        .distinct()
        .all()
    }

    # 4) Attempted but not passed (in-progress signal)
    attempted_skill_ids = {
        skill_id
        for (skill_id,) in db.query(QuizAttempt.skill_id)
        .filter(
            QuizAttempt.user_id == user_id,
            QuizAttempt.skill_id.in_(course_slugs),
        )
        .distinct()
        .all()
    }

    completed_ids = completed_via_event | completed_via_quiz

    # Build progress map:
    # 1   = completed
    # 0.5 = attempted quiz but not yet passed (in-progress)
    # 0   = not started
    progress_map: dict[str, float] = {}
    for course_slug in course_slugs:
        if course_slug in completed_ids:
            progress_map[course_slug] = 1.0
        elif course_slug in attempted_skill_ids:
            progress_map[course_slug] = 0.5
        else:
            progress_map[course_slug] = 0.0

    return {"course_progress": progress_map}


@router.get("/{roadmap_id}")
def get_progress(roadmap_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user_id = str(current_user.id)
    # total courses in roadmap
    total_courses = (
        db.query(func.count(Course.id))
        .filter(Course.roadmap_id == roadmap_id)
        .scalar()
    )
    total_courses = total_courses or 0

    # Completed via event log
    event_completed_ids = {
        course_id
        for (course_id,) in db.query(Event.course_id)
        .filter(
            Event.user_id == user_id,
            Event.event_type == "course_completed",
            Event.roadmap_id == roadmap_id
        )
        .distinct()
        .all()
    }

    # Completed via passed quiz attempt (catches missed events)
    course_ids_in_roadmap = [
        c.id for c in db.query(Course.id).filter(Course.roadmap_id == roadmap_id).all()
    ]
    quiz_completed_ids = {
        skill_id
        for (skill_id,) in db.query(QuizAttempt.skill_id)
        .filter(
            QuizAttempt.user_id == user_id,
            QuizAttempt.passed == True,
            QuizAttempt.skill_id.in_(course_ids_in_roadmap),
        )
        .distinct()
        .all()
    }

    completed_courses = len(event_completed_ids | quiz_completed_ids)

    # skill data
    skill = (
        db.query(UserSkill)
        .filter(
            UserSkill.user_id == user_id,
            UserSkill.skill_name == roadmap_id
        )
        .first()
    )

    xp = getattr(skill, "xp", None) if skill else None
    xp = int(xp) if xp is not None else 0
    level = getattr(skill, "level", None) if skill else None
    level = int(level) if level is not None else 1
    proficiency_level = skill.proficiency_level if skill and skill.proficiency_level is not None else 0.0

    progress_percent = (
        (completed_courses / total_courses) * 100
        if total_courses > 0 else 0.0
    )

    # Clamp progress_percent to 100%
    progress_percent = min(100.0, progress_percent)

    return {
        "roadmap_id": roadmap_id,
        "total_courses": total_courses,
        "completed_courses": completed_courses,
        "progress_percent": round(progress_percent, 2),
        "xp": xp,
        "level": level,
        "proficiency_level": float(proficiency_level)
    }


@router.get("/all")
def get_all_progress(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _t0 = time.perf_counter()
    user_id = str(current_user.id)

    # 1. Total courses per roadmap (one query)
    total_rows = (
        db.query(Course.roadmap_id, func.count(Course.id).label("total"))
        .group_by(Course.roadmap_id)
        .all()
    )
    totals: dict[str, int] = {str(row.roadmap_id): int(row.total) for row in total_rows}

    # 2. Completed per roadmap — UNION of Event + QuizAttempt, DISTINCT at DB level
    # quiz_attempts uses skill_id (FK to courses.id), events uses course_id
    completed_sql = text("""
        SELECT roadmap_id, COUNT(DISTINCT course_id) AS completed
        FROM (
            SELECT roadmap_id, course_id
            FROM events
            WHERE user_id = :uid AND event_type = 'course_completed'
            UNION
            SELECT c.roadmap_id, qa.skill_id AS course_id
            FROM quiz_attempts qa
            JOIN courses c ON c.id = qa.skill_id
            WHERE qa.user_id = :uid AND qa.passed = TRUE
        ) combined
        GROUP BY roadmap_id
    """)
    completed_rows = db.execute(completed_sql, {"uid": user_id}).fetchall()
    completed: dict[str, int] = {str(row.roadmap_id): int(row.completed) for row in completed_rows}

    # 3. UserSkill stats for all roadmaps this user has data for (one query)
    skill_rows = (
        db.query(UserSkill.skill_name, UserSkill.xp, UserSkill.level, UserSkill.proficiency_level)
        .filter(UserSkill.user_id == user_id)
        .all()
    )
    skills: dict[str, tuple[int, int, float]] = {
        str(row.skill_name): (
            int(row.xp or 0),
            int(row.level or 1),
            float(row.proficiency_level or 0.0),
        )
        for row in skill_rows
    }

    # 4. Union roadmap IDs from courses AND user_skills so roadmaps with skill data
    # but no courses in DB are still represented (check 2)
    all_roadmap_ids = set(totals.keys()) | set(skills.keys())

    # 5. Build response
    result = []
    for rid in sorted(all_roadmap_ids):
        total = totals.get(rid, 0)
        done = completed.get(rid, 0)
        xp, level, proficiency_level = skills.get(rid, (0, 1, 0.0))
        progress_percent = min(100.0, round((done / total) * 100, 2)) if total > 0 else 0.0
        result.append({
            "roadmap_id": rid,
            "total_courses": total,
            "completed_courses": done,
            "progress_percent": progress_percent,
            "xp": xp,
            "level": level,
            "proficiency_level": proficiency_level,
        })

    print(f"[PERF] GET /progress/all took {(time.perf_counter() - _t0) * 1000:.0f}ms")
    return {"roadmaps": result}
