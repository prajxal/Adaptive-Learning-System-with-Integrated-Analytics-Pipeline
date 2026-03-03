import os
import sys
import uuid

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db.database import SessionLocal, Base, engine
from models.user import User
from models.course import Course
from models.skill_profile import SkillProfile
from services.skill_profile_service import update_skill_profile_from_quiz
from routers.recommend import recommend

def run_tests():
    db = SessionLocal()
    
    print("\n--- TEST SETUP ---")
    user_id = str(uuid.uuid4())
    user = User(id=user_id, email=f"test_{user_id}@example.com", password_hash="pw", global_elo_rating=1000.0)
    db.add(user)
    
    # Create some mock courses
    roadmap1 = "python-developer"
    roadmap2 = "backend-developer"
    
    courses = [
        Course(id="c1", roadmap_id=roadmap1, title="Intro to Python", difficulty_level=900.0, node_id="n1"),
        Course(id="c2", roadmap_id=roadmap1, title="Variables", difficulty_level=1000.0, node_id="n2"),
        Course(id="c3", roadmap_id=roadmap1, title="Control Flow", difficulty_level=1050.0, node_id="n3"),
        Course(id="c4", roadmap_id=roadmap1, title="Functions", difficulty_level=1100.0, node_id="n4"),
        Course(id="c5", roadmap_id=roadmap1, title="Advanced Classes", difficulty_level=1300.0, node_id="n5"),
        Course(id="c6", roadmap_id=roadmap1, title="Asyncio", difficulty_level=1600.0, node_id="n6"),
        Course(id="c7", roadmap_id=roadmap2, title="Intro to Node", difficulty_level=1000.0, node_id="n7"),
    ]
    
    for c in courses:
        # Check if course exists first
        existing_course = db.query(Course).filter(Course.id == c.id).first()
        if not existing_course:
            db.add(c)
    
    db.commit()
    db.refresh(user)
    
    print(f"Created Test User: {user.id}")
    
    try:
        # ==========================================
        print("\n--- TEST 1: Cold start user ---")
        res1 = recommend(current_roadmap_id=roadmap1, db=db, current_user=user)
        print(f"User Elo: {res1['user_elo']}")
        print(f"Next in current roadmap (Count): {len(res1['next_in_current_roadmap'])}")
        print(f"Easiest courses returned: {[c['title'] for c in res1['next_in_current_roadmap']]}")
        print(f"Suggested new roadmaps: {res1['suggested_new_roadmaps']}")
        
        assert res1['user_elo'] == 1000.0
        # ==========================================
        
        # ==========================================
        print("\n--- TEST 2: Elo recalibration after quiz (Pass high difficulty) ---")
        # Pass a 1300 difficulty course
        update_skill_profile_from_quiz(user_id=user.id, skill_id="c5", quiz_score=100, roadmap_id=roadmap1, db=db)
        
        db.refresh(user)
        res2 = recommend(current_roadmap_id=roadmap1, db=db, current_user=user)
        print(f"New User Elo: {res2['user_elo']}")
        print(f"Next in current roadmap (Count): {len(res2['next_in_current_roadmap'])}")
        print(f"Nodes in target band returned: {[c['title'] for c in res2['next_in_current_roadmap']]}")
        
        assert res2['user_elo'] > 1000.0
        # ==========================================
        
        # ==========================================
        print("\n--- TEST 3: Elo recalibration on fail ---")
        # Fail a 1600 difficulty course
        update_skill_profile_from_quiz(user_id=user.id, skill_id="c6", quiz_score=0, roadmap_id=roadmap1, db=db)
        
        db.refresh(user)
        print(f"New User Elo after fail: {user.global_elo_rating}")
        
        assert user.global_elo_rating >= 800.0
        assert user.global_elo_rating < res2['user_elo']
        # ==========================================
        
        # ==========================================
        print("\n--- TEST 4: Stage 2 roadmap suggestions exclude current ---")
        # Ensure 'backend-developer' is in stage 2, but 'python-developer' is NOT.
        print(f"Suggested new roadmaps: {res2['suggested_new_roadmaps']}")
        
        assert roadmap1 not in res2['suggested_new_roadmaps']
        # ==========================================
        
        print("\n✅ ALL TESTS PASSED.")

    finally:
        # Cleanup
        db.delete(user)
        db.query(SkillProfile).filter(SkillProfile.user_id == user_id).delete()
        for c in courses:
            db.query(Course).filter(Course.id == c.id).delete()
        db.commit()
        db.close()

if __name__ == "__main__":
    run_tests()
