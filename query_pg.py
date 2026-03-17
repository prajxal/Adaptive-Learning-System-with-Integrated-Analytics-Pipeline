import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from sqlalchemy import text
from db.database import engine

def run_queries():
    with engine.connect() as conn:
        print("\n--- Courses with 'Applicability' in title ---")
        result = conn.execute(text("SELECT id, title, roadmap_id, node_id, difficulty_level FROM courses WHERE title ILIKE '%Applicability%'"))
        for row in result:
            print(row)

        print("\n--- CoursePrerequisite for 'Applicability' ---")
        result = conn.execute(text("SELECT * FROM course_prerequisites WHERE course_id IN (SELECT id FROM courses WHERE title ILIKE '%Applicability%')"))
        for row in result:
            print(row)

        print("\n--- SkillEdge where 'Applicability' is the target ---")
        result = conn.execute(text("SELECT * FROM skill_edges WHERE to_skill_id IN (SELECT id FROM courses WHERE title ILIKE '%Applicability%')"))
        for row in result:
            print(row)

        print("\n--- SkillEdge where 'Applicability' is the source ---")
        result = conn.execute(text("SELECT * FROM skill_edges WHERE from_skill_id IN (SELECT id FROM courses WHERE title ILIKE '%Applicability%')"))
        for row in result:
            print(row)

        print("\n--- First 10 Blockchain Roadmap Courses ---")
        result = conn.execute(text("SELECT id, title, roadmap_id, node_id, difficulty_level FROM courses WHERE roadmap_id = 'blockchain' ORDER BY id LIMIT 10"))
        for row in result:
            print(row)

if __name__ == "__main__":
    run_queries()
