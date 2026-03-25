import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from sqlalchemy import text
from db.database import engine

def fetch_samples():
    with engine.connect() as conn:
        print("\n--- Blockchain Course Samples ---")
        # Querying all columns of a course mapping to the model
        query = text("""
            SELECT *
            FROM courses
            WHERE roadmap_id = 'blockchain'
            LIMIT 10
        """)
        result = conn.execute(query)
        keys = result.keys()
        
        for row in result:
            row_dict = dict(zip(keys, row))
            for k, v in row_dict.items():
                print(f"{k}: {v}")
            print("-" * 40)

if __name__ == "__main__":
    fetch_samples()
