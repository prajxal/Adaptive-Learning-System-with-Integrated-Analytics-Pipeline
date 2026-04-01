"""XP and Level service.

Replaces the Elo logistic formula for progression tracking.
XP is awarded on course completion and quiz performance.
Levels are derived deterministically from total XP.

Level thresholds (mirrors frontend xpUtils.ts):
    Level 1:  0 – 149 XP
    Level 2:  150 – 399 XP
    Level 3:  400 – 649 XP
    Level 4:  650 – 849 XP
    Level 5:  850 – 999 XP
    Level 6:  1000+ XP
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from models.course import Course
from models.user import User
from models.user_skill import UserSkill

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Each index i holds the minimum XP required to be at level (i+1).
# Level 6 has no upper cap.
_LEVEL_THRESHOLDS: list[int] = [0, 150, 400, 650, 850, 1000]


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def compute_level_from_xp(xp: int) -> int:
    """Return the level (1–6) that corresponds to the given total XP value."""
    level = 1
    for threshold in _LEVEL_THRESHOLDS:
        if xp >= threshold:
            level += 1
        else:
            break
    # _LEVEL_THRESHOLDS has 6 entries; the loop can increment level up to 6 times.
    # Subtract 1 because we start at 1 and increment on the first (0 >= 0) check.
    return min(6, max(1, level - 1))


def compute_xp_for_course(topological_depth: int) -> int:
    """Return the XP awarded for completing a course at the given topological depth.

    Formula: depth * 20 + 10
    Minimum XP is 10 (depth 0), maximum is uncapped but naturally bounded by
    the depth of the deepest course in the graph.
    """
    return max(0, topological_depth) * 20 + 10


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_course_depth(course_id: str, db: Session) -> int:
    """Look up the topological depth for a course.

    Uses ``Course.required_level`` when available (post-migration), otherwise
    falls back to deriving depth from ``Course.difficulty_level`` using the
    formula  depth = (difficulty_level - 800) / 100.
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if course is None:
        logger.warning("course %s not found; defaulting depth to 0", course_id)
        return 0

    # Post-migration: required_level is a 1-based level so depth = level - 1.
    required_level = getattr(course, "required_level", None)
    if required_level is not None:
        return max(0, int(required_level) - 1)

    # Pre-migration fallback: difficulty_level = 800 + depth * 100
    difficulty = float(getattr(course, "difficulty_level", 1000.0))
    return max(0, int((difficulty - 800) / 100))


def _apply_xp(
    user: User,
    user_skill: UserSkill | None,
    xp_award: int,
) -> None:
    """Mutate *user* and *user_skill* in-place, adding XP and recalculating levels.

    Uses ``getattr``/``setattr`` with safe fallbacks so the function works both
    before and after the Phase-2 schema migration.
    """
    # --- User global XP ---
    current_total = getattr(user, "total_xp", 0) or 0
    new_total = current_total + xp_award
    setattr(user, "total_xp", new_total)
    setattr(user, "current_level", compute_level_from_xp(new_total))

    # --- UserSkill XP (roadmap-scoped) ---
    if user_skill is not None:
        current_skill_xp = getattr(user_skill, "xp", 0) or 0
        new_skill_xp = current_skill_xp + xp_award
        setattr(user_skill, "xp", new_skill_xp)
        setattr(user_skill, "level", compute_level_from_xp(new_skill_xp))


def _get_or_create_user_skill(
    user_id: str,
    roadmap_id: str,
    db: Session,
) -> UserSkill:
    """Fetch the UserSkill row for (user_id, roadmap_id), creating it if absent."""
    user_skill = (
        db.query(UserSkill)
        .filter(
            UserSkill.user_id == str(user_id),
            UserSkill.skill_name == roadmap_id,
        )
        .first()
    )
    if user_skill is None:
        user_skill = UserSkill(
            user_id=str(user_id),
            skill_name=roadmap_id,
            proficiency_level=0.0,
            elo_rating=1000.0,
            trust_score=0.0,
        )
        db.add(user_skill)
        db.flush()
    return user_skill


def _build_result(user: User, xp_awarded: int) -> dict:
    return {
        "xp_awarded": xp_awarded,
        "total_xp": getattr(user, "total_xp", 0) or 0,
        "current_level": getattr(user, "current_level", 1) or 1,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def award_xp_for_completion(
    user_id: str,
    course_id: str,
    roadmap_id: str,
    db: Session,
) -> dict:
    """Award XP to *user_id* for completing *course_id*.

    - Derives the course's topological depth, computes XP, increments
      ``User.total_xp``, recomputes ``User.current_level``, and does the same
      for the matching ``UserSkill`` row (keyed on *roadmap_id*).
    - All column access uses ``getattr``/``setattr`` with 0/1 fallbacks so the
      function is safe before and after the Phase-2 migration.
    - Commits the session before returning.

    Returns a dict with keys ``xp_awarded``, ``total_xp``, ``current_level``.
    """
    user = db.query(User).filter(User.id == str(user_id)).first()
    if user is None:
        logger.error("award_xp_for_completion: user %s not found", user_id)
        return {"xp_awarded": 0, "total_xp": 0, "current_level": 1}

    depth = _get_course_depth(course_id, db)
    xp_award = compute_xp_for_course(depth)

    user_skill = _get_or_create_user_skill(user_id, roadmap_id, db)
    _apply_xp(user, user_skill, xp_award)

    db.commit()
    logger.info(
        "Awarded %d XP to user %s for completing course %s (depth=%d)",
        xp_award,
        user_id,
        course_id,
        depth,
    )
    return _build_result(user, xp_award)


def award_xp_for_quiz(
    user_id: str,
    quiz_score: float,
    course_id: str,
    roadmap_id: str,
    db: Session,
) -> dict:
    """Award XP to *user_id* based on *quiz_score* for *course_id*.

    Score thresholds:
        >= 0.8  → full XP
        >= 0.5  → half XP (rounded down)
        < 0.5   → 0 XP

    Same update pattern as ``award_xp_for_completion``.
    Returns a dict with keys ``xp_awarded``, ``total_xp``, ``current_level``.
    """
    user = db.query(User).filter(User.id == str(user_id)).first()
    if user is None:
        logger.error("award_xp_for_quiz: user %s not found", user_id)
        return {"xp_awarded": 0, "total_xp": 0, "current_level": 1}

    depth = _get_course_depth(course_id, db)
    full_xp = compute_xp_for_course(depth)

    if quiz_score >= 0.8:
        xp_award = full_xp
    elif quiz_score >= 0.5:
        xp_award = full_xp // 2
    else:
        xp_award = 0

    if xp_award == 0:
        logger.info(
            "No XP awarded to user %s for quiz on course %s (score=%.2f)",
            user_id,
            course_id,
            quiz_score,
        )
        return _build_result(user, 0)

    user_skill = _get_or_create_user_skill(user_id, roadmap_id, db)
    _apply_xp(user, user_skill, xp_award)

    db.commit()
    logger.info(
        "Awarded %d XP to user %s for quiz on course %s (score=%.2f, depth=%d)",
        xp_award,
        user_id,
        course_id,
        quiz_score,
        depth,
    )
    return _build_result(user, xp_award)


def get_user_global_xp(user_id: str, db: Session) -> int:
    """Return the user's total accumulated XP, or 0 if the user is not found."""
    user = db.query(User).filter(User.id == str(user_id)).first()
    if user is None:
        return 0
    return getattr(user, "total_xp", 0) or 0


def get_user_level(user_id: str, db: Session) -> int:
    """Return the user's current level (1–6), or 1 if the user is not found."""
    user = db.query(User).filter(User.id == str(user_id)).first()
    if user is None:
        return 1
    return getattr(user, "current_level", 1) or 1
