"""One-time data migration: populate XP / Level columns from existing progress data.

Run after applying migration 20260330_add_xp_level_columns:

    cd backend
    python scripts/migrate_elo_to_xp.py

The script is idempotent — it resets and recomputes all XP / Level values on
each run, so it can be safely re-executed if data changes or the script is
interrupted.

What it does:
1.  For every Course: derive topological depth from the CoursePrerequisite graph
    (BFS from roots) and set course.required_level.
2.  For every User: collect their completed courses (event_type = 'course_completed'
    or 'course_skipped'), sum XP awards, set user.total_xp and user.current_level.
3.  For every UserSkill (roadmap-scoped): filter completions to that roadmap,
    sum XP, set user_skill.xp and user_skill.level.
"""

from __future__ import annotations

import sys
import os
from collections import defaultdict, deque

# ---------------------------------------------------------------------------
# Ensure the backend package is on sys.path when running from repo root or
# from the backend/ directory.
# ---------------------------------------------------------------------------
_script_dir = os.path.dirname(os.path.abspath(__file__))
_backend_dir = os.path.dirname(_script_dir)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from db.database import SessionLocal
from models.course import Course
from models.course_prerequisite import CoursePrerequisite
from models.event import Event
from models.user import User
from models.user_skill import UserSkill
from services.course_level_service import compute_required_level
from services.xp_level_service import compute_level_from_xp, compute_xp_for_course


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _compute_topological_depths(
    course_ids: list[str],
    prereq_pairs: list[tuple[str, str]],
) -> dict[str, int]:
    """Return a mapping of course_id → topological depth (0-based) within one roadmap.

    Uses BFS from root nodes (courses with no prerequisites).
    In the prerequisites graph:
        course_id  depends on  prerequisite_id
    So the edges go:  prerequisite_id → course_id  (prerequisite before dependent).

    Args:
        course_ids: All course IDs in the roadmap.
        prereq_pairs: List of (course_id, prerequisite_id) pairs.

    Returns:
        Dict mapping each course_id to its depth. Root nodes have depth 0.
    """
    # Build adjacency: prerequisite_id → [course_ids that depend on it]
    children: dict[str, list[str]] = defaultdict(list)
    in_degree: dict[str, int] = {cid: 0 for cid in course_ids}

    for course_id, prereq_id in prereq_pairs:
        if course_id in in_degree and prereq_id in in_degree:
            children[prereq_id].append(course_id)
            in_degree[course_id] += 1

    # BFS from roots (in_degree == 0)
    depth: dict[str, int] = {}
    queue: deque[str] = deque()

    for cid in course_ids:
        if in_degree[cid] == 0:
            depth[cid] = 0
            queue.append(cid)

    while queue:
        node = queue.popleft()
        for child in children[node]:
            candidate = depth[node] + 1
            if child not in depth or depth[child] < candidate:
                depth[child] = candidate
            in_degree[child] -= 1
            if in_degree[child] == 0:
                queue.append(child)

    # Any node not reached (cycle or isolated) defaults to depth 0
    for cid in course_ids:
        if cid not in depth:
            depth[cid] = 0

    return depth


# ---------------------------------------------------------------------------
# Migration steps
# ---------------------------------------------------------------------------


def migrate_course_required_levels(db) -> dict[str, int]:
    """Step 1: Set required_level on every Course.

    Returns a mapping of course_id → xp_award for use in subsequent steps.
    """
    print("Step 1: Computing and setting course.required_level ...")

    # Load all courses grouped by roadmap
    all_courses = db.query(Course).all()
    roadmap_courses: dict[str, list[Course]] = defaultdict(list)
    for course in all_courses:
        roadmap_courses[course.roadmap_id].append(course)

    # Load all prerequisite pairs
    all_prereqs = db.query(
        CoursePrerequisite.course_id, CoursePrerequisite.prerequisite_id
    ).all()
    prereq_pairs: list[tuple[str, str]] = [(row[0], row[1]) for row in all_prereqs]

    course_xp_map: dict[str, int] = {}
    updated = 0

    for roadmap_id, courses in roadmap_courses.items():
        course_ids = [c.id for c in courses]
        roadmap_pairs = [
            (cid, pid) for cid, pid in prereq_pairs if cid in set(course_ids)
        ]
        depths = _compute_topological_depths(course_ids, roadmap_pairs)

        for course in courses:
            depth = depths.get(course.id, 0)
            new_level = compute_required_level(depth)
            course.required_level = new_level
            course_xp_map[course.id] = compute_xp_for_course(depth)
            updated += 1

    db.flush()
    print(f"  Updated required_level for {updated} courses across {len(roadmap_courses)} roadmaps.")
    return course_xp_map


def migrate_user_xp(db, course_xp_map: dict[str, int]) -> None:
    """Step 2 & 3: Set total_xp / current_level on Users and xp / level on UserSkills."""
    print("Step 2 & 3: Computing and setting user XP / levels ...")

    # Load all completed/skipped events
    completion_events = (
        db.query(Event.user_id, Event.course_id, Event.roadmap_id)
        .filter(Event.event_type.in_(["course_completed", "course_skipped"]))
        .all()
    )

    # Index by user: user_id → list of (course_id, roadmap_id)
    user_completions: dict[str, list[tuple[str, str | None]]] = defaultdict(list)
    for user_id, course_id, roadmap_id in completion_events:
        user_completions[user_id].append((course_id, roadmap_id))

    all_users = db.query(User).all()
    user_count = 0

    for user in all_users:
        completions = user_completions.get(str(user.id), [])

        # Deduplicate: a course may have multiple events; count it once.
        seen_courses: set[str] = set()
        # roadmap_id → total XP for that roadmap
        roadmap_xp: dict[str, int] = defaultdict(int)
        total_xp = 0

        for course_id, roadmap_id in completions:
            if course_id in seen_courses:
                continue
            seen_courses.add(course_id)

            xp = course_xp_map.get(course_id, 10)  # fallback 10 XP if course unknown
            total_xp += xp
            if roadmap_id:
                roadmap_xp[roadmap_id] += xp

        user.total_xp = total_xp
        user.current_level = compute_level_from_xp(total_xp)

        # Update UserSkill rows for this user
        user_skills = (
            db.query(UserSkill).filter(UserSkill.user_id == str(user.id)).all()
        )
        for user_skill in user_skills:
            skill_xp = roadmap_xp.get(user_skill.skill_name, 0)
            user_skill.xp = skill_xp
            user_skill.level = compute_level_from_xp(skill_xp)

        user_count += 1
        if user_count % 100 == 0:
            print(f"  Processed {user_count} users ...")

    db.flush()
    print(f"  Updated XP / level for {user_count} users.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    print("=== Elo → XP data migration ===")
    print("This script is idempotent and can be run multiple times safely.\n")

    db = SessionLocal()
    try:
        course_xp_map = migrate_course_required_levels(db)
        migrate_user_xp(db, course_xp_map)
        db.commit()
        print("\nMigration committed successfully.")
    except Exception:
        db.rollback()
        print("\nMigration FAILED — transaction rolled back.")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
