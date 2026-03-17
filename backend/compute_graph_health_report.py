import sys
import os

sys.path.append(os.path.dirname(__file__))

from db.database import SessionLocal
from models.course import Course
from models.course_prerequisite import CoursePrerequisite
from services.learning_priority_service import get_root_nodes, compute_graph_depth
from services.skill_graph_service import get_next_skills

def run_diagnostic():
    db = SessionLocal()
    try:
        # Get all distinct roadmap_ids
        roadmaps = db.query(Course.roadmap_id).distinct().all()
        roadmap_ids = [r[0] for r in roadmaps]
        
        report = []
        
        print("Calculating diagnostics for all roadmaps (this may take a minute)...")
        for r_id in roadmap_ids:
            num_nodes = db.query(Course).filter(Course.roadmap_id == r_id).count()
            if num_nodes == 0:
                continue
                
            num_edges = db.query(CoursePrerequisite).join(Course, Course.id == CoursePrerequisite.course_id).filter(Course.roadmap_id == r_id).count()
            
            root_nodes = get_root_nodes(r_id, db)
            num_root_nodes = len(root_nodes)
            
            courses = db.query(Course).filter(Course.roadmap_id == r_id).all()
            
            max_depth = 0
            total_out_degree = 0
            for c in courses:
                depth = compute_graph_depth(c.id, db)
                if depth > max_depth:
                    max_depth = depth
                
                next_skills = get_next_skills(c.id, db)
                total_out_degree += len(next_skills)
                
            avg_out_degree = total_out_degree / num_nodes if num_nodes > 0 else 0
            
            # Flags logic
            flags = []
            if num_root_nodes > (num_nodes / 2.0):
                flags.append("root_nodes > 50%")
            if num_edges < (num_nodes - 1):
                flags.append("edges < nodes - 1")
            if max_depth < 3:
                flags.append("max_depth < 3")
                
            health_score = len(flags)
            
            report.append({
                "roadmap_id": r_id,
                "nodes": num_nodes,
                "edges": num_edges,
                "roots": num_root_nodes,
                "max_depth": max_depth,
                "avg_out": avg_out_degree,
                "flags": flags,
                "health_score": health_score # Lower is better
            })
            
        # Rank: Sort by health_score (asc), then max_depth (desc)
        report.sort(key=lambda x: (x["health_score"], -x["max_depth"]))
        
        print("\n=== GRAPH HEALTH REPORT ===")
        print(f"{'Roadmap ID':<30} | {'Nodes':<5} | {'Edges':<5} | {'Roots':<5} | {'Max D':<5} | {'Avg Out':<7} | {'Health Flags'}")
        print("-" * 120)
        for r in report:
            flags_str = ", ".join(r["flags"]) if r["flags"] else "HEALTHY"
            print(f"{r['roadmap_id']:<30} | {r['nodes']:<5} | {r['edges']:<5} | {r['roots']:<5} | {r['max_depth']:<5} | {r['avg_out']:<7.2f} | {flags_str}")
            
    finally:
        db.close()

if __name__ == "__main__":
    run_diagnostic()
