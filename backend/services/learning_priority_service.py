from sqlalchemy.orm import Session
from models.course import Course
from models.course_prerequisite import CoursePrerequisite
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
