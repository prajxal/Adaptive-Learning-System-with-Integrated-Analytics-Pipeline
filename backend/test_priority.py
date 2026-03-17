import sys
import os
import json

# Ensure we can import from backend dir
sys.path.append(os.path.dirname(__file__))

from db.database import SessionLocal
from models.user import User
from services.learning_priority_service import get_recommended_start_courses

def run_test():
    db = SessionLocal()
    try:
        # Get a real user ID from the database
        user = db.query(User).first()
        if not user:
            print("No user found in the database. Cannot run test.")
            return
            
        user_id = str(user.id)
        print(f"Running test for user_id: '{user_id}' with roadmap_id: 'blockchain'")
        print("-" * 50)
        
        result = get_recommended_start_courses(user_id, "blockchain", db)
        
        print("\nOutput:")
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    run_test()
