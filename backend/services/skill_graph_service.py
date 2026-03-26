from sqlalchemy.orm import Session
from models.course import Course
from models.skill_edge import SkillEdge
from models.course_prerequisite import CoursePrerequisite
from models.event import Event
import logging

logger = logging.getLogger(__name__)

def generate_graph_for_roadmap(roadmap_id: str, db: Session):
    """
    Generates a linear prerequisite graph for all courses sequentially ordered within a roadmap.
    Assumes the courses are ordered by node_id based on original roadmap format ingestion.
    """
    try:
        # Fetch all courses for the valid roadmap ordered by sequence.
        # Based on extract_roadmaps.py, it sorts primarily sequentially or node_id when inserted.
        # The prompt instructed to order by original ingestion sequencing (e.g. node_id lexicographically/numerically, since JSON parse preserves array order but DB doesn't inherently without order_by). 
        # If node_id is an integer representation as a string, casting might be needed, but we'll try sorting strings or relying on insertion ID if they are chronological. Wait, extract_roadmaps.py didn't store a explicit sequence number. Let's look at `node_id`. The prompt: "You must order by the original roadmap ordering field used during ingestion. That is usually: position, sequence, node_order, created index".
        # Since extract_roadmaps iterates linearly through JSON, insertion order (rowid in SQLite) guarantees the sequence and created_at timestamps can be identical.
        from sqlalchemy.sql import text
        courses = db.query(Course).filter(Course.roadmap_id == roadmap_id).order_by(Course.id).all()

        if len(courses) < 2:
            return # Skip if less than 2 courses

        existing_edges = set(
            (e.from_skill_id, e.to_skill_id)
            for e in db.query(SkillEdge).filter_by(roadmap_id=roadmap_id)
        )

        new_edges = []
        for i in range(len(courses) - 1):
            from_course = courses[i]
            to_course = courses[i+1]
            
            if (from_course.id, to_course.id) not in existing_edges:
                edge = SkillEdge(
                    roadmap_id=roadmap_id,
                    from_skill_id=from_course.id,
                    to_skill_id=to_course.id
                )
                db.add(edge)
                new_edges.append(edge)
        
        db.commit()
        logger.info(f"Generated {len(new_edges)} new edges for roadmap {roadmap_id}")

    except Exception as e:
        db.rollback()
        logger.error(f"Error generating graph for roadmap {roadmap_id}: {e}")

def get_edges_for_roadmap(roadmap_id: str, db: Session):
    # This might not be easily filtered by roadmap_id without a join, 
    # but returning all for course_ids in roadmap_id is better.
    # Leaving it to return dummy if not used, or re-implement using join:
    from models.course import Course
    return db.query(CoursePrerequisite).join(Course, Course.id == CoursePrerequisite.course_id).filter(Course.roadmap_id == roadmap_id).all()

def get_prerequisites(skill_id: str, db: Session):
    return db.query(CoursePrerequisite).filter(CoursePrerequisite.course_id == skill_id).all()

def get_next_skills(skill_id: str, db: Session):
    return db.query(CoursePrerequisite).filter(CoursePrerequisite.prerequisite_id == skill_id).all()

def is_skill_completed(user_id: str, skill_id: str, db: Session) -> bool:
    """
    Checks if a given skill is completed by the user
    by finding if they have a 'course_completed' or 'course_skipped' event.
    """
    event = db.query(Event).filter(
        Event.event_type.in_(["course_completed", "course_skipped"]),
        Event.user_id == user_id,
        Event.course_id == skill_id
    ).first()
    return event is not None

def is_skill_unlocked(user_id: str, skill_id: str, db: Session) -> bool:
    """
    A skill is unlocked if ALL its prerequisites are completed.
    If it has no prerequisites, it is considered unlocked by default.
    """
    prereqs = get_prerequisites(skill_id, db)
    if not prereqs:
        return True # No prerequisites -> Unlocked
    
    # Check if all prerequisites are completed
    for edge in prereqs:
        if not is_skill_completed(user_id, edge.prerequisite_id, db):
            return False # Found a locked prerequisite
            
    return True

def get_skill_status(user_id: str, skill_id: str, db: Session) -> str:
    """
    Resolves the skill status: 'completed', 'unlocked', or 'locked'.
    Priority: completed > unlocked > locked.
    """
    if is_skill_completed(user_id, skill_id, db):
        return "completed"
    elif is_skill_unlocked(user_id, skill_id, db):
        return "unlocked"
    else:
        return "locked"

def get_roadmap_skill_status(user_id: str, roadmap_id: str, db: Session) -> dict:
    """
    Retrieves the unlock/completed status for all courses within a roadmap
    for a specific user efficiently.
    Returns: {"roadmap_id": ..., "skills": [{"skill_id": ..., "status": ...}]}
    """
    # 1. Fetch all courses in the roadmap
    courses = db.query(Course.id).filter(Course.roadmap_id == roadmap_id).all()
    if not courses:
        return {"roadmap_id": roadmap_id, "skills": []}
        
    course_ids = [c[0] for c in courses]
    
    # 2. Fetch all completed/skipped courses for this user in this roadmap
    completed_events = db.query(Event.course_id).filter(
        Event.user_id == user_id,
        Event.roadmap_id == roadmap_id,
        Event.event_type.in_(["course_completed", "course_skipped"])
    ).all()

    completed_set = {e[0] for e in completed_events}
    
    # 3. Fetch all skill edges for this roadmap to reconstruct prerequisite map
    # mapping: course_id -> list of prerequisite_ids
    edges = db.query(CoursePrerequisite).filter(CoursePrerequisite.course_id.in_(course_ids)).all()
    
    # Validation check for Phase 5
    if len(edges) == 0:
        logger.warning(f"Validation: 0 edges loaded from course_prerequisites for roadmap {roadmap_id}")
    else:
        logger.info(f"Validation: {len(edges)} edges loaded from course_prerequisites for roadmap {roadmap_id}")

    prereq_map = {cid: [] for cid in course_ids}
    for edge in edges:
        # edge.course_id depends on edge.prerequisite_id
        if edge.course_id in prereq_map:
            prereq_map[edge.course_id].append(edge.prerequisite_id)
            
    # 4. Resolve status for all courses
    skills_status = []
    
    for course_id in course_ids:
        if course_id in completed_set:
            status = "completed"
        else:
            # Check if all prerequisites are completed
            prereqs = prereq_map.get(course_id, [])
            if not prereqs:
                status = "unlocked"
            else:
                # All prereqs must be in completed_set
                all_prereqs_met = all(p in completed_set for p in prereqs)
                status = "unlocked" if all_prereqs_met else "locked"
                
        skills_status.append({
            "skill_id": course_id,
            "status": status
        })
        
    # FIX: Add entry point guarantee
    unlocked_count = sum(1 for s in skills_status if s["status"] == "unlocked")

    if unlocked_count == 0:
        # Find lowest difficulty course and force unlock it
        entry_course = db.query(Course.id).filter(
            Course.roadmap_id == roadmap_id
        ).order_by(Course.difficulty_level.asc()).first()
        
        if entry_course:
            for s in skills_status:
                if s["skill_id"] == entry_course[0]:
                    s["status"] = "unlocked"
                    break

    return {
        "roadmap_id": roadmap_id,
        "skills": skills_status
    }
