"""
MCP tool implementations for the AI Mentor.

Each function opens and closes its own DB session so it can be called
from the Gemini function-calling loop without a FastAPI request context.
"""
import logging

from db.database import SessionLocal
from models.course import Course
from models.event import Event
from models.user import User
from models.user_skill import UserSkill
from services.learning_priority_service import get_recommended_start_courses_batched
from services.skill_graph_service import get_edges_for_roadmap, get_roadmap_skill_status

logger = logging.getLogger(__name__)


def get_user_profile(user_id: str) -> dict:
    """Fetch user profile: skills, Elo rating, XP, level, GitHub status."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"error": "User not found"}
        skills = db.query(UserSkill).filter(UserSkill.user_id == user_id).all()
        return {
            "user_id": user_id,
            "email": user.email,
            "global_elo_rating": user.global_elo_rating,
            "total_xp": user.total_xp,
            "current_level": user.current_level,
            "github_connected": user.github_status == "connected",
            "github_username": user.github_username,
            "skills": [
                {
                    "name": s.skill_name,
                    "proficiency": round(s.proficiency_level, 2),
                    "elo": round(s.elo_rating, 1),
                }
                for s in skills
            ],
        }
    finally:
        db.close()


def get_user_progress(user_id: str) -> dict:
    """Fetch learning progress across all roadmaps the user has engaged with."""
    db = SessionLocal()
    try:
        completed_events = (
            db.query(Event)
            .filter(
                Event.user_id == user_id,
                Event.event_type.in_(["course_completed", "course_skipped"]),
            )
            .all()
        )
        completed_ids: set[str] = set()
        roadmap_ids: set[str] = set()
        for e in completed_events:
            cid = e.course_id or (e.payload or {}).get("course_id")
            if cid:
                completed_ids.add(cid)
                roadmap_ids.add(cid.split(":")[0])

        roadmap_progress = []
        for rid in roadmap_ids:
            total = db.query(Course).filter(Course.roadmap_id == rid).count()
            completed = (
                db.query(Course)
                .filter(Course.roadmap_id == rid, Course.id.in_(completed_ids))
                .count()
            )
            roadmap_progress.append(
                {
                    "roadmap_id": rid,
                    "total_courses": total,
                    "completed_courses": completed,
                    "progress_percent": round(completed / total * 100, 1) if total > 0 else 0.0,
                }
            )

        return {
            "user_id": user_id,
            "total_completed": len(completed_ids),
            "roadmaps": roadmap_progress,
        }
    finally:
        db.close()


def get_next_course(user_id: str, roadmap_id: str) -> dict:
    """Get the recommended next course for a user in a given roadmap."""
    db = SessionLocal()
    try:
        return get_recommended_start_courses_batched(user_id, roadmap_id, db)
    except Exception as exc:
        logger.warning("get_next_course failed user=%s roadmap=%s: %s", user_id, roadmap_id, exc)
        return {"error": str(exc)}
    finally:
        db.close()


def get_roadmap_courses(roadmap_id: str) -> dict:
    """List all courses in a roadmap ordered by difficulty."""
    db = SessionLocal()
    try:
        courses = (
            db.query(Course)
            .filter(Course.roadmap_id == roadmap_id)
            .order_by(Course.difficulty_level)
            .all()
        )
        return {
            "roadmap_id": roadmap_id,
            "courses": [
                {
                    "id": c.id,
                    "title": c.title,
                    "difficulty_level": round(c.difficulty_level, 1),
                    "required_level": c.required_level,
                }
                for c in courses
            ],
        }
    finally:
        db.close()


_LEVEL_LABELS: dict[int, str] = {
    1: "Novice",
    2: "Apprentice",
    3: "Practitioner",
    4: "Expert",
    5: "Master",
    6: "Grandmaster",
}


def build_user_context(user_id: str) -> str:
    """
    Return a compact plain-text snapshot of the user's learning state.

    Injected into the AI Mentor system prompt at the start of every chat request
    so the model can answer common questions ("What should I study?") without
    needing tool-call round-trips.

    Queries (single session):
    - User row         → level, XP, GitHub
    - UserSkill rows   → top 5 skills by proficiency
    - Events           → active roadmap (most recent event with roadmap/course)
                       → total completed courses
    - get_recommended_start_courses_batched → next course in active roadmap
    """
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return ""

        # Top 5 skills by proficiency
        skills = (
            db.query(UserSkill)
            .filter(UserSkill.user_id == user_id)
            .order_by(UserSkill.proficiency_level.desc())
            .limit(5)
            .all()
        )

        # Active roadmap — most recent event that has a roadmap or course reference
        recent_event = (
            db.query(Event)
            .filter(
                Event.user_id == user_id,
                (Event.roadmap_id.isnot(None)) | (Event.course_id.isnot(None)),
            )
            .order_by(Event.created_at.desc())
            .first()
        )

        active_roadmap_id: str | None = None
        if recent_event:
            active_roadmap_id = recent_event.roadmap_id or (
                recent_event.course_id.split(":")[0] if recent_event.course_id else None
            )

        # Total completed / skipped courses
        completed_count = (
            db.query(Event)
            .filter(
                Event.user_id == user_id,
                Event.event_type.in_(["course_completed", "course_skipped"]),
            )
            .count()
        )

        # Next recommended course for active roadmap
        next_course: dict | None = None
        alternatives: list[str] = []
        if active_roadmap_id:
            try:
                rec = get_recommended_start_courses_batched(user_id, active_roadmap_id, db)
                if rec.get("recommended"):
                    next_course = rec["recommended"]
                alternatives = [a["title"] for a in rec.get("alternatives", [])]
            except Exception as exc:
                logger.debug("build_user_context: recommendation lookup failed: %s", exc)

        # Assemble context block
        level_label = _LEVEL_LABELS.get(user.current_level, "Learner")
        lines = [
            "## Learner Context (live data — do not ask the user to confirm these details)",
            f"- Level: {user.current_level} ({level_label}) | XP: {user.total_xp}",
        ]

        if active_roadmap_id:
            lines.append(f"- Active roadmap: {active_roadmap_id}")
            if next_course:
                lines.append(
                    f"- Next recommended course: {next_course['title']} [{next_course['id']}]"
                )
                if alternatives:
                    lines.append(f"- Alternatives: {', '.join(alternatives)}")
            else:
                lines.append(
                    "- Next recommended course: none available "
                    "(roadmap may be complete or all courses locked)"
                )
        else:
            lines.append(
                "- Active roadmap: none — user has not started any roadmap yet "
                "(suggest browsing /roadmaps to pick one)"
            )

        lines.append(f"- Total courses completed: {completed_count}")

        if skills:
            skill_str = ", ".join(
                f"{s.skill_name} ({s.proficiency_level:.2f})" for s in skills
            )
            lines.append(f"- Top skills: {skill_str}")
        else:
            lines.append(
                "- Top skills: none yet "
                "(user has not connected GitHub or uploaded a resume)"
            )

        github_str = (
            f"connected (@{user.github_username})"
            if user.github_status == "connected"
            else "not connected"
        )
        lines.append(f"- GitHub: {github_str}")

        return "\n".join(lines)
    finally:
        db.close()


def get_skill_graph(roadmap_id: str, user_id: str | None = None) -> dict:
    """Get skill dependency graph. If user_id given, includes per-skill completion status."""
    db = SessionLocal()
    try:
        if user_id:
            return get_roadmap_skill_status(user_id, roadmap_id, db)
        edges = get_edges_for_roadmap(roadmap_id, db)
        return {
            "roadmap_id": roadmap_id,
            "edges": [{"from": e.prerequisite_id, "to": e.course_id} for e in edges],
        }
    finally:
        db.close()
