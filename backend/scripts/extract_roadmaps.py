import sys
import json
import os
from pathlib import Path
from sqlalchemy.orm import Session

# Add parent directory to sys.path to allow importing from backend modules
file_path = Path(__file__).resolve()
sys.path.append(str(file_path.parent.parent))

from db.database import SessionLocal, engine
from models.course import Course
from models.course_prerequisite import CoursePrerequisite
from create_tables import create_tables

ROADMAPS_DIR = "/Users/prajwal/Documents/Roadmap/developer-roadmap/src/data/roadmaps"

def extract_roadmaps():
    # Ensure tables exist
    create_tables()

    session = SessionLocal()
    total_courses = 0
    total_prereqs = 0
    scanned_files = 0
    processed_roadmaps = set()
    
    print(f"Scanning for roadmaps in: {ROADMAPS_DIR}")

    try:
        for root, dirs, files in os.walk(ROADMAPS_DIR):
            for filename in files:
                if not filename.endswith(".json"):
                    continue

                # Skip meta files if any (e.g. package.json, tsconfig.json if they exist in that tree)
                # The user requirement says "roadmap_id = filename without .json"
                # We will assume all JSONs in this structure are relevant unless they lack "nodes" or "edges"
                
                filepath = os.path.join(root, filename)
                roadmap_id = filename[:-5] # Remove .json
                
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Basic validation to ensure it's a roadmap file
                    if not isinstance(data, dict):
                         # Some files might be metadata
                        continue
                        
                    # Some roadmap.sh files might wrap content in "json" key or be direct arrays?
                    # But the prompt says "Each JSON file represents a roadmap graph containing nodes and edges."
                    # Structure: { "nodes": [], "edges": [] } usually.
                    # Or check for keys.
                    
                    # User sample:
                    # Nodes: { "id": "...", ... }
                    # Edges: { "source": "...", ... }
                    # Usually these are lists under keys "nodes" and "edges" or the root is the object.
                    # Let's assume the root object has "nodes" and "edges" keys based on standard graph formats, 
                    # OR check if the user prompt implies a specific structure.
                    # "Each JSON file represents a roadmap graph containing nodes and edges."
                    
                    nodes = data.get("nodes", [])
                    edges = data.get("edges", [])

                    if not nodes and not edges:
                        # Might not be a roadmap file (e.g. migration-mapping.json saw earlier)
                        # print(f"Skipping {filename}: No nodes/edges found.")
                        continue
                        
                    print(f"Processing {filename} (ID: {roadmap_id})...")
                    scanned_files += 1
                    processed_roadmaps.add(roadmap_id)
                    
                    # 1. Extract Nodes
                    file_courses_count = 0
                    current_course_ids = set()
                    all_nodes = {}
                    
                    for node in nodes:
                        node_type = node.get("type", "unknown")
                        node_id = node.get("id")
                        if not node_id:
                            continue
                            
                        all_nodes[node_id] = node_type
                        
                        if node_type not in ["topic"]:
                            continue
                        
                        # Use label as title if title is missing
                        node_data = node.get("data", {})
                        title = node_data.get("title")
                        if not title:
                            title = node_data.get("label")
                        
                        if not title:
                            # Skip nodes without titles
                            continue
                            
                        description = node_data.get("description")
                        
                        course_id = f"{roadmap_id}:{node_id}"
                        current_course_ids.add(course_id)
                        
                        # Upsert Course
                        existing = session.query(Course).filter_by(id=course_id).first()
                        if existing:
                            existing.title = title
                            existing.description = description
                            # Don't touch difficulty or other fields
                        else:
                            new_course = Course(
                                id=course_id,
                                roadmap_id=roadmap_id,
                                node_id=node_id,
                                title=title,
                                description=description,
                                difficulty_level=None
                            )
                            session.add(new_course)
                        
                        file_courses_count += 1
                    
                    session.flush() # Flush to ensure foreign keys are valid for prerequisites
                    total_courses += file_courses_count

                    # 2. Extract Prerequisites (Edges)
                    # Build adjacency list from JSON
                    adj_list = {}
                    for edge in edges:
                        src = edge.get("source")
                        tgt = edge.get("target")
                        if src and tgt:
                            adj_list.setdefault(src, []).append(tgt)
                            
                    file_prereqs_count = 0
                    
                    # For each topic (source), find reachable topics
                    for source_topic in current_course_ids:
                        raw_source = source_topic.split(":", 1)[1]
                        
                        visited = set()
                        queue = [raw_source]
                        
                        while queue:
                            curr_node = queue.pop(0)
                            
                            for next_node in adj_list.get(curr_node, []):
                                if next_node not in visited:
                                    visited.add(next_node)
                                    
                                    next_topic_id = f"{roadmap_id}:{next_node}"
                                    if next_topic_id in current_course_ids:
                                        # Reached a topic node, create edge and STOP traversing this path
                                        existing_prereq = session.query(CoursePrerequisite).filter_by(
                                            course_id=next_topic_id, 
                                            prerequisite_id=source_topic
                                        ).first()
                                        
                                        if not existing_prereq:
                                            new_prereq = CoursePrerequisite(
                                                course_id=next_topic_id,
                                                prerequisite_id=source_topic
                                            )
                                            session.add(new_prereq)
                                            file_prereqs_count += 1
                                    else:
                                        # Reached a non-topic node, CONTINUE traversing its children
                                        queue.append(next_node)
                                        
                    total_prereqs += file_prereqs_count
                    
                except Exception as e:
                    print(f"Error processing file {filename}: {e}")
                    # Continue to next file
                    continue

        session.commit()
        
        print("\nGenerating Skill Graphs... (DISABLED)")
        # from services.skill_graph_service import generate_graph_for_roadmap
        # for r_id in processed_roadmaps:
        #     generate_graph_for_roadmap(r_id, session)
        print("Skill Graphs Generated. (DISABLED)")

        print("\nExtraction Complete.")
        print(f"Scanned {scanned_files} files.")
        print(f"Inserted/Updated {total_courses} courses.")
        print(f"Inserted {total_prereqs} prerequisite relationships.")
        
        print("\n--- Graph Statistics ---")
        from services.learning_priority_service import get_root_nodes, compute_graph_depth
        for r_id in processed_roadmaps:
            nodes_count = session.query(Course).filter(Course.roadmap_id == r_id).count()
            edges_count = session.query(CoursePrerequisite).join(Course, Course.id == CoursePrerequisite.course_id).filter(Course.roadmap_id == r_id).count()
            
            root_nodes = get_root_nodes(r_id, session)
            
            courses = session.query(Course).filter(Course.roadmap_id == r_id).all()
            max_depth = 0
            for c in courses:
                depth = compute_graph_depth(c.id, session)
                if depth > max_depth:
                    max_depth = depth
                    
            print(f"\nRoadmap: {r_id}")
            print(f"  - nodes: {nodes_count}")
            print(f"  - edges: {edges_count}")
            print(f"  - root nodes: {len(root_nodes)}")
            print(f"  - max depth: {max_depth}")

    except Exception as e:
        session.rollback()
        print(f"CRITICAL ERROR: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    extract_roadmaps()