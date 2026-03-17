import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from sqlalchemy import text
from db.database import engine

def run_queries():
    with engine.connect() as conn:
        print("\n--- Blockchain Course Prerequisites Analysis ---")
        query = text("""
            SELECT c.id, c.title,
                   COUNT(cp.prerequisite_id) as num_prereqs,
                   STRING_AGG(cp.prerequisite_id, ', ') as prereq_ids
            FROM courses c
            LEFT JOIN course_prerequisites cp ON c.id = cp.course_id
            WHERE c.roadmap_id = 'blockchain' 
              AND c.title IN ('Frontend Frameworks', 'Applicability', 'Node as a Service', 'Management Platforms', 'Security')
            GROUP BY c.id, c.title
        """)
        result = conn.execute(query)
        for row in result:
            print(f"course_id: {row[0]} | Title: {row[1]}")
            print(f"number_of_prerequisites: {row[2]}")
            print(f"list_of_prerequisite_ids: {row[3]}")
            print("-" * 40)

if __name__ == "__main__":
    run_queries()
