from sqlalchemy import literal, select, union_all
from sqlalchemy.orm import Session

from models.course import Course
from models.course_prerequisite import CoursePrerequisite
from models.event import Event
from models.quiz_attempt import QuizAttempt
from models.skill_profile import SkillProfile
from services.skill_graph_service import (
    get_prerequisites,
    get_next_skills,
    is_skill_unlocked,
    is_skill_completed
)

def get_root_nodes(roadmap_id: str, db: Session) -> list[Course]:
    """
    Identify root nodes (courses with no prerequisites).
    A root node is a course that never appears as `course_id` (a dependent) in course_prerequisites.
    """
    # Query all courses for roadmap
    courses = db.query(Course).filter(Course.roadmap_id == roadmap_id).all()
    
    # Get all course_ids that have prerequisites
    dependent_course_ids = {
        cp.course_id for cp in db.query(CoursePrerequisite).all()
    }
    
    # Filter root nodes
    root_nodes = [c for c in courses if c.id not in dependent_course_ids]
    return root_nodes

def get_unlocked_courses(user_id: str, roadmap_id: str, db: Session) -> list[Course]:
    """
    Identify properly unlocked (and not yet completed) courses for a given user.
    """
    courses = db.query(Course).filter(Course.roadmap_id == roadmap_id).all()
    unlocked_courses = []
    
    for course in courses:
        # Ensure it's unlocked by prerequisite completion, and not already completed
        if is_skill_unlocked(user_id, course.id, db) and not is_skill_completed(user_id, course.id, db):
            unlocked_courses.append(course)
            
    return unlocked_courses

def compute_graph_depth(course_id: str, db: Session) -> int:
    """
    Compute depth of a node from the root.
    Root nodes = depth 0. Depth increases recursively by following prerequisite chains backward.
    """
    prereqs = get_prerequisites(course_id, db)
    if not prereqs:
        return 0
        
    depths = []
    for edge in prereqs:
        depths.append(1 + compute_graph_depth(edge.prerequisite_id, db))
        
    return max(depths)

def count_descendants(course_id: str, db: Session) -> int:
    """
    Count the total number of downstream reachable nodes.
    Uses BFS graph traversal.
    """
    visited = set()
    queue = [course_id]
    
    while queue:
        current = queue.pop(0)
        next_skills = get_next_skills(current, db)
        for edge in next_skills:
            if edge.course_id not in visited:
                visited.add(edge.course_id)
                queue.append(edge.course_id)
                
    return len(visited)

def compute_importance_score(course_id: str, db: Session) -> float:
    """
    Compute an importance score based on the network topology.
    Formula: descendants_count * 3 + out_degree * 2 + (10 - graph_depth)
    """
    next_skills = get_next_skills(course_id, db)
    out_degree = len(next_skills)
    descendants_count = count_descendants(course_id, db)
    graph_depth = compute_graph_depth(course_id, db)
    
    importance_score = (descendants_count * 3) + (out_degree * 2) + (10 - graph_depth)
    return float(importance_score)

def compute_confidence_adjustment(user_id: str, course_id: str, db: Session) -> float:
    """
    Returns a score adjustment based on the user's existing skill confidence for this course.
    Low confidence → positive boost (needs attention).
    High confidence → negative adjustment (already strong, de-prioritise).
    """
    profile = db.query(SkillProfile).filter(
        SkillProfile.user_id == user_id,
        SkillProfile.skill_id == course_id
    ).first()

    if not profile:
        return 0.0  # No data — no adjustment

    confidence = profile.confidence or 0.0
    if confidence < 0.4:
        return 5.0   # Low confidence: needs attention, boost priority
    elif confidence > 0.7:
        return -3.0  # High confidence: already strong, de-prioritise
    return 0.0


def get_recommended_start_courses(user_id: str, roadmap_id: str, db: Session) -> dict:
    """
    Returns the top recommended starting courses based on topological importance
    adjusted by the user's skill confidence.
    """
    unlocked_courses = get_unlocked_courses(user_id, roadmap_id, db)

    course_scores = []
    for course in unlocked_courses:
        base_score = compute_importance_score(course.id, db)
        confidence_adj = compute_confidence_adjustment(user_id, str(course.id), db)
        score = base_score + confidence_adj
        course_scores.append((score, course))
        
    # Sort descending
    course_scores.sort(key=lambda x: x[0], reverse=True)
    
    if not course_scores:
        return {
            "recommended": None,
            "alternatives": []
        }
        
    top_course = course_scores[0][1]
    
    recommended = {
        "id": top_course.id,
        "title": top_course.title
    }
    
    alternatives = [
        {"id": course.id, "title": course.title}
        for _, course in course_scores[1:3]
    ]
    
    return {
        "recommended": recommended,
        "alternatives": alternatives
    }


def get_recommended_start_courses_batched(user_id: str, roadmap_id: str, db: Session) -> dict:
    """
    Batched drop-in replacement for get_recommended_start_courses.

    Executes exactly 4 SQL queries regardless of roadmap size, then resolves
    unlock status, graph metrics, and confidence adjustments entirely in memory.

    Q1 — All Course rows for roadmap_id
    Q2 — All CoursePrerequisite edges for those course IDs
    Q3 — All satisfied course IDs for this user (events + passed quiz attempts)
    Q4 — All SkillProfile rows for (user_id, skill_ids in Q1)
    """
    # Q1 — courses
    courses: list[Course] = (
        db.query(Course)
        .filter(Course.roadmap_id == roadmap_id)
        .all()
    )
    if not courses:
        return {"recommended": None, "alternatives": []}

    course_ids = [c.id for c in courses]
    course_map: dict[str, Course] = {c.id: c for c in courses}

    # Q2 — prerequisite edges
    prereq_edges: list[CoursePrerequisite] = (
        db.query(CoursePrerequisite)
        .filter(CoursePrerequisite.course_id.in_(course_ids))
        .all()
    )
    # prereq_map: course_id -> set of prerequisite_ids (what must be done first)
    prereq_map: dict[str, set[str]] = {cid: set() for cid in course_ids}
    # forward_map: prerequisite_id -> set of dependent course_ids (for BFS descendants)
    forward_map: dict[str, set[str]] = {cid: set() for cid in course_ids}
    for edge in prereq_edges:
        if edge.course_id in prereq_map:
            prereq_map[edge.course_id].add(edge.prerequisite_id)
        if edge.prerequisite_id in forward_map:
            forward_map[edge.prerequisite_id].add(edge.course_id)

    # Q3 — satisfied course IDs (completed events + skipped events + passed quizzes)
    events_subq = select(Event.course_id.label("course_id")).where(
        Event.user_id == user_id,
        Event.course_id.in_(course_ids),
        Event.event_type.in_(["course_completed", "course_skipped"]),
    )
    quiz_subq = select(QuizAttempt.skill_id.label("course_id")).where(
        QuizAttempt.user_id == user_id,
        QuizAttempt.skill_id.in_(course_ids),
        QuizAttempt.passed.is_(True),
    )
    completed_rows = db.execute(union_all(events_subq, quiz_subq)).fetchall()
    completed_ids: set[str] = {row[0] for row in completed_rows if row[0] is not None}

    # Q4 — skill profiles
    skill_profiles: list[SkillProfile] = (
        db.query(SkillProfile)
        .filter(
            SkillProfile.user_id == user_id,
            SkillProfile.skill_id.in_(course_ids),
        )
        .all()
    )
    profile_map: dict[str, SkillProfile] = {sp.skill_id: sp for sp in skill_profiles}

    # --- In-memory unlock resolution ---
    def is_unlocked(cid: str) -> bool:
        if cid in completed_ids:
            return False
        prereqs = prereq_map.get(cid, set())
        return all(p in completed_ids for p in prereqs)

    unlocked_ids = [cid for cid in course_ids if is_unlocked(cid)]

    if not unlocked_ids:
        return {"recommended": None, "alternatives": []}

    # --- In-memory graph metrics ---

    # BFS descendants count (how many nodes downstream of cid)
    def count_descendants(cid: str) -> int:
        visited: set[str] = set()
        queue = [cid]
        while queue:
            current = queue.pop(0)
            for dep in forward_map.get(current, set()):
                if dep not in visited:
                    visited.add(dep)
                    queue.append(dep)
        return len(visited)

    # Memoised recursive depth (longest path from any root to cid)
    depth_memo: dict[str, int] = {}

    def compute_depth(node: str) -> int:
        if node in depth_memo:
            return depth_memo[node]
        prereqs = prereq_map.get(node, set())
        if not prereqs:
            depth_memo[node] = 0
            return 0
        d = max(compute_depth(p) + 1 for p in prereqs)
        depth_memo[node] = d
        return d

    # --- Score each unlocked course ---
    course_scores = []
    for cid in unlocked_ids:
        course = course_map[cid]
        out_degree = len(forward_map.get(cid, set()))
        descendants = count_descendants(cid)
        depth = compute_depth(cid)
        base_score = float((descendants * 3) + (out_degree * 2) + (10 - depth))

        profile = profile_map.get(cid)
        confidence_adj = 0.0
        if profile:
            confidence = float(profile.confidence or 0.0)
            if confidence < 0.4:
                confidence_adj = 5.0
            elif confidence > 0.7:
                confidence_adj = -3.0

        course_scores.append((base_score + confidence_adj, course))

    course_scores.sort(key=lambda x: x[0], reverse=True)

    top = course_scores[0][1]
    return {
        "recommended": {"id": top.id, "title": top.title},
        "alternatives": [
            {"id": c.id, "title": c.title}
            for _, c in course_scores[1:3]
        ],
    }
