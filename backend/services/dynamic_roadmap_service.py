"""
Dynamic Roadmap Service

Computes a personalized 5-state course status map for a given user and roadmap.
States: completed | skippable | fast_tracked | unlocked | locked

Uses exactly 4 batch DB queries — no N+1.
"""

import logging
import os
import time
from typing import Any

from sqlalchemy import func, literal, select, union_all
from sqlalchemy.orm import Session

from models.course import Course
from models.course_prerequisite import CoursePrerequisite
from models.event import Event
from models.quiz_attempt import QuizAttempt
from models.skill_profile import SkillProfile

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# State constants
# ---------------------------------------------------------------------------
STATE_COMPLETED = "completed"
STATE_SKIPPABLE = "skippable"
STATE_FAST_TRACKED = "fast_tracked"
STATE_UNLOCKED = "unlocked"
STATE_LOCKED = "locked"


def _get_skip_threshold() -> float:
    """Read threshold at call-time so env changes are picked up without restart."""
    return float(os.environ.get("SKIP_CONFIDENCE_THRESHOLD", "0.75"))


def _get_fast_track_threshold() -> float:
    """Read threshold at call-time so env changes are picked up without restart."""
    return float(os.environ.get("FAST_TRACK_CONFIDENCE_THRESHOLD", "0.50"))


def get_skip_threshold() -> float:
    """Public accessor — import this instead of duplicating the env var read."""
    return _get_skip_threshold()


def get_fast_track_threshold() -> float:
    """Public accessor — import this instead of duplicating the env var read."""
    return _get_fast_track_threshold()


def _build_reason(
    status: str,
    course_id: str,
    profile: "SkillProfile | None",
    prereq_ids: set,
    satisfied_ids: set,
    completed_event_ids: set,
    skipped_event_ids: set,
    quiz_passed_ids: set,
    quiz_scores: dict,
    skip_threshold: float,
    fast_track_threshold: float,
    is_force_unlocked: bool = False,
) -> str:
    """Return a deterministic <=60-char reason string for a course node's current state."""

    if status == STATE_COMPLETED:
        # Priority: quiz > skip > event
        if course_id in quiz_passed_ids:
            score = quiz_scores.get(course_id)
            if score is not None:
                pct = int(round(score * 100))
                return f"Passed quiz ({pct}%)"
            return "Passed quiz"
        if course_id in skipped_event_ids:
            if profile is None:
                return "Skipped — prior expertise confirmed"
            confidence = float(profile.confidence or 0.0)
            pct = int(round(min(1.0, max(0.0, confidence)) * 100))
            return f"Skipped — high confidence ({pct}%)"
        return "Completed"

    if status in (STATE_SKIPPABLE, STATE_FAST_TRACKED):
        prefix = "Skip available" if status == STATE_SKIPPABLE else "Fast-track"
        action_verb = "strong" if status == STATE_SKIPPABLE else "some"

        if profile is None:
            confidence = 0.0
            github_conf = resume_conf = 0.0
        else:
            confidence = float(profile.confidence or 0.0)
            github_conf = float(getattr(profile, "github_confidence", None) or 0.0)
            resume_conf = float(getattr(profile, "resume_confidence", None) or 0.0)

        attr_threshold = skip_threshold if status == STATE_SKIPPABLE else fast_track_threshold
        github_meets = github_conf >= attr_threshold
        resume_meets = resume_conf >= attr_threshold

        if github_meets and resume_meets:
            return f"{prefix} — GitHub + resume signal"
        if github_meets:
            return f"{prefix} — GitHub shows {action_verb} experience"
        if resume_meets:
            return f"{prefix} — resume mentions this skill"
        # Fallback: composite confidence is high even if sources are individually below threshold
        pct = int(round(min(1.0, max(0.0, confidence)) * 100))
        return f"{prefix} — high confidence ({pct}%)"

    if status == STATE_UNLOCKED:
        if is_force_unlocked:
            return "Entry point — start here"
        n = len(prereq_ids)
        if n == 0:
            return "No prerequisites — ready to start"
        return f"Unlocked — all {n} prerequisite{'s' if n != 1 else ''} complete"

    if status == STATE_LOCKED:
        unsatisfied = [p for p in prereq_ids if p not in satisfied_ids]
        n = len(unsatisfied)
        return f"Locked — {n} prerequisite{'s' if n != 1 else ''} remaining"

    return ""


def compute_dynamic_roadmap(user_id: str, roadmap_id: str, db: Session) -> dict[str, Any]:
    """
    Compute the dynamic status for every course in a roadmap for a given user.

    Performs exactly 4 DB queries:
      Q1 — All Course rows for roadmap_id
      Q2 — All satisfied course_ids (completed events + skipped events + passed quiz attempts)
      Q3 — All CoursePrerequisite edges whose course_id is in Q1 courses
      Q4 — All SkillProfile rows for (user_id, skill_id in Q1 courses)

    Returns a structured dict with per-course status and a summary block.
    Each course dict includes a `reason` field.
    """
    t_total_start = time.perf_counter()
    skip_threshold = _get_skip_threshold()
    fast_track_threshold = _get_fast_track_threshold()

    # ------------------------------------------------------------------
    # Q1 — All courses for this roadmap
    # ------------------------------------------------------------------
    t_q1_start = time.perf_counter()
    courses: list[Course] = (
        db.query(Course)
        .filter(Course.roadmap_id == roadmap_id)
        .all()
    )
    t_q1_ms = (time.perf_counter() - t_q1_start) * 1000

    if not courses:
        # Caller should translate this into a 404; return empty sentinel.
        return {}

    course_ids: list[str] = [c.id for c in courses]
    course_map: dict[str, Course] = {c.id: c for c in courses}

    # ------------------------------------------------------------------
    # Q2 — Satisfied course_ids (single DB roundtrip via union_all):
    #       (a) course_completed events for this user
    #       (b) course_skipped events for this user
    #       (c) passed QuizAttempts for this user
    # All filtered to course_ids from Q1 to avoid pulling irrelevant rows.
    # ------------------------------------------------------------------
    t_q2_start = time.perf_counter()

    events_subq = select(
        Event.course_id.label("course_id"),
        Event.event_type.label("source"),          # "course_completed" or "course_skipped"
        literal(None).label("score"),
    ).where(
        Event.user_id == user_id,
        Event.course_id.in_(course_ids),
        Event.event_type.in_(["course_completed", "course_skipped"]),
    )
    quiz_subq = select(
        QuizAttempt.skill_id.label("course_id"),
        literal("quiz_passed").label("source"),
        QuizAttempt.score.label("score"),
    ).where(
        QuizAttempt.user_id == user_id,
        QuizAttempt.skill_id.in_(course_ids),
        QuizAttempt.passed.is_(True),
    )
    union_stmt = union_all(events_subq, quiz_subq)
    satisfied_rows = db.execute(union_stmt).fetchall()

    satisfied_ids: set[str] = set()
    completed_event_ids: set[str] = set()
    skipped_event_ids: set[str] = set()
    quiz_passed_ids: set[str] = set()
    quiz_scores: dict[str, float] = {}

    for row in satisfied_rows:
        cid, source, score = row[0], row[1], row[2]
        if cid is None:
            continue
        satisfied_ids.add(cid)
        if source == "course_completed":
            completed_event_ids.add(cid)
        elif source == "course_skipped":
            skipped_event_ids.add(cid)
        elif source == "quiz_passed":
            quiz_passed_ids.add(cid)
            if score is not None and cid not in quiz_scores:
                quiz_scores[cid] = float(score)

    t_q2_ms = (time.perf_counter() - t_q2_start) * 1000

    # ------------------------------------------------------------------
    # Q3 — All prerequisite edges whose dependent course is in Q1
    # ------------------------------------------------------------------
    t_q3_start = time.perf_counter()
    prereq_edges: list[CoursePrerequisite] = (
        db.query(CoursePrerequisite)
        .filter(CoursePrerequisite.course_id.in_(course_ids))
        .all()
    )
    t_q3_ms = (time.perf_counter() - t_q3_start) * 1000

    # Build prerequisite map: course_id -> set of prerequisite_ids
    prereq_map: dict[str, set[str]] = {cid: set() for cid in course_ids}
    for edge in prereq_edges:
        if edge.course_id in prereq_map:
            prereq_map[edge.course_id].add(edge.prerequisite_id)

    # ------------------------------------------------------------------
    # Q4 — SkillProfile rows for (user_id, skill_id in Q1 courses)
    # ------------------------------------------------------------------
    t_q4_start = time.perf_counter()
    skill_profiles: list[SkillProfile] = (
        db.query(SkillProfile)
        .filter(
            SkillProfile.user_id == user_id,
            SkillProfile.skill_id.in_(course_ids),
        )
        .all()
    )
    t_q4_ms = (time.perf_counter() - t_q4_start) * 1000

    # Build profile lookup: skill_id -> SkillProfile (or None — do NOT create)
    profile_map: dict[str, SkillProfile] = {sp.skill_id: sp for sp in skill_profiles}

    # ------------------------------------------------------------------
    # State resolution (in priority order per spec)
    # ------------------------------------------------------------------
    t_resolution_start = time.perf_counter()

    resolved_courses: list[dict[str, Any]] = []

    for course_id in course_ids:
        course = course_map[course_id]
        profile = profile_map.get(course_id)  # May be None

        confidence: float = float(profile.confidence) if profile is not None else 0.0
        proficiency: float = float(profile.proficiency_level) if profile is not None else 0.0

        prereqs = prereq_map.get(course_id, set())
        all_prereqs_satisfied = all(p in satisfied_ids for p in prereqs) if prereqs else True

        # Priority 1 — COMPLETED
        if course_id in satisfied_ids:
            status = STATE_COMPLETED
        # Priority 2 — SKIPPABLE
        elif all_prereqs_satisfied and confidence >= skip_threshold:
            status = STATE_SKIPPABLE
        # Priority 3 — FAST_TRACKED
        elif all_prereqs_satisfied and confidence >= fast_track_threshold:
            status = STATE_FAST_TRACKED
        # Priority 4 — UNLOCKED
        elif all_prereqs_satisfied:
            status = STATE_UNLOCKED
        # Priority 5 — LOCKED
        else:
            status = STATE_LOCKED

        reason = _build_reason(
            status=status,
            course_id=course_id,
            profile=profile,
            prereq_ids=prereqs,
            satisfied_ids=satisfied_ids,
            completed_event_ids=completed_event_ids,
            skipped_event_ids=skipped_event_ids,
            quiz_passed_ids=quiz_passed_ids,
            quiz_scores=quiz_scores,
            skip_threshold=skip_threshold,
            fast_track_threshold=fast_track_threshold,
            is_force_unlocked=False,
        )

        resolved_courses.append({
            "skill_id": course_id,
            "title": course.title,
            "status": status,
            "reason": reason,
            "confidence": confidence,
            "proficiency": proficiency,
            "difficulty_level": int(course.difficulty_level) if course.difficulty_level is not None else 0,
            "can_skip": status == STATE_SKIPPABLE,
            "can_fast_track": status == STATE_FAST_TRACKED,
        })

    # ------------------------------------------------------------------
    # Entry-point guarantee:
    # If zero courses are in a non-locked active state, force-unlock
    # the lowest-difficulty course so users can always start.
    # ------------------------------------------------------------------
    active_states = {STATE_UNLOCKED, STATE_SKIPPABLE, STATE_FAST_TRACKED, STATE_COMPLETED}
    has_active = any(rc["status"] in active_states for rc in resolved_courses)

    if not has_active and resolved_courses:
        # Find the lowest-difficulty course from the in-memory list
        lowest = min(courses, key=lambda c: (c.difficulty_level if c.difficulty_level is not None else 0, c.id))
        for rc in resolved_courses:
            if rc["skill_id"] == lowest.id:
                rc["status"] = STATE_UNLOCKED
                rc["reason"] = "Entry point — start here"
                rc["can_skip"] = False
                rc["can_fast_track"] = False
                break

    t_resolution_ms = (time.perf_counter() - t_resolution_start) * 1000

    # ------------------------------------------------------------------
    # Summary counts
    # ------------------------------------------------------------------
    summary = {
        STATE_COMPLETED: 0,
        STATE_SKIPPABLE: 0,
        STATE_FAST_TRACKED: 0,
        STATE_UNLOCKED: 0,
        STATE_LOCKED: 0,
    }
    for rc in resolved_courses:
        summary[rc["status"]] += 1

    t_total_ms = (time.perf_counter() - t_total_start) * 1000

    logger.info(
        "[DynamicRoadmap] roadmap=%s user=%s | Q1(courses)=%.1fms Q2(satisfied)=%.1fms "
        "Q3(prereqs)=%.1fms Q4(profiles)=%.1fms | resolution=%.1fms | TOTAL=%.1fms courses=%d",
        roadmap_id,
        user_id,
        t_q1_ms,
        t_q2_ms,
        t_q3_ms,
        t_q4_ms,
        t_resolution_ms,
        t_total_ms,
        len(resolved_courses),
    )

    return {
        "roadmap_id": roadmap_id,
        "courses": resolved_courses,
        "summary": {
            "total": len(resolved_courses),
            "completed": summary[STATE_COMPLETED],
            "skippable": summary[STATE_SKIPPABLE],
            "fast_tracked": summary[STATE_FAST_TRACKED],
            "unlocked": summary[STATE_UNLOCKED],
            "locked": summary[STATE_LOCKED],
        },
        "thresholds": {
            "skip": skip_threshold,
            "fast_track": fast_track_threshold,
        },
        "computed_in_ms": round(t_total_ms, 2),
    }
