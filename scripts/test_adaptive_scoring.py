import sqlite3
import requests
import json
import uuid
from datetime import datetime
import subprocess
import time
import os

env = os.environ.copy()
env["DATABASE_URL"] = "sqlite:///backend/app.db"
env["PYTHONPATH"] = os.path.abspath("backend")
# Add a dummy api key to trigger a 503 if real one isn't present
if "GEMINI_API_KEY" not in env:
    env["GEMINI_API_KEY"] = "dummy"

base_url = "http://localhost:8000"
roadmap_id = "ai-agents"
skill_id_1 = "ai-agents:VPI89s-m885r2YrXjYxdd"

def clear_db_for_test():
    import sys
    sys.path.append(os.path.abspath("backend"))
    from sqlalchemy import create_engine
    from db.database import Base
    import main # imports all models so create_all works
    engine = create_engine("sqlite:///backend/app.db")
    Base.metadata.create_all(bind=engine)
    
    conn = sqlite3.connect('backend/app.db')
    c = conn.cursor()
    c.execute("DELETE FROM events")
    c.execute("DELETE FROM quiz_attempts")
    c.execute("DELETE FROM skill_quizzes")
    c.execute("DELETE FROM skill_profiles")
    c.execute("DELETE FROM skill_weights")
    conn.commit()
    conn.close()

clear_db_for_test()

server = subprocess.Popen(["python", "-m", "uvicorn", "backend.main:app", "--port", "8000"], env=env)
time.sleep(3)

try:
    # 1. Login to get token
    user_data = {"email": "testgraph_adaptive@example.com", "password": "password123"}
    login_res = requests.post(f"{base_url}/auth/login", json=user_data)
    if login_res.status_code != 200:
        requests.post(f"{base_url}/auth/signup", json=user_data)
        login_res = requests.post(f"{base_url}/auth/login", json=user_data)

    token = login_res.json().get("access_token")
    user_id = login_res.json().get("user_id")
    headers = {"Authorization": f"Bearer {token}"}

    print("--- Step 1: Submit first quiz attempt via API ---")
    quiz_score = 60.0 # user gets 60%
    # We first need to manually insert a quiz for the skill
    conn = sqlite3.connect('backend/app.db')
    c = conn.cursor()
    questions = json.dumps([
        {"id": "q1", "text": "Q1", "options": ["A", "B", "C", "D"], "correct_answer": "A"},
        {"id": "q2", "text": "Q2", "options": ["A", "B", "C", "D"], "correct_answer": "B"},
        {"id": "q3", "text": "Q3", "options": ["A", "B", "C", "D"], "correct_answer": "C"},
        {"id": "q4", "text": "Q4", "options": ["A", "B", "C", "D"], "correct_answer": "D"},
        {"id": "q5", "text": "Q5", "options": ["A", "B", "C", "D"], "correct_answer": "A"}
    ])
    c.execute(f"INSERT INTO skill_quizzes (id, skill_id, questions, passing_score, created_at) VALUES ('q_adaptive', '{skill_id_1}', '{questions}', 80, '{datetime.utcnow().isoformat()}')")
    
    # Let's insert some mock SkillWeight records to simulate cold-start (GitHub, Resume)
    # The system shouldn't overwrite quiz fields with these
    c.execute(f"INSERT INTO skill_weights (user_id, skill_name, weight, confidence, source, last_updated) VALUES ('{user_id}', '{skill_id_1}', 90.0, 0.5, 'github', '{datetime.utcnow().isoformat()}')")
    conn.commit()

    # Wait, we need to initialize cold start first to see if it works, before the quiz
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from backend.services.skill_profile_service import initialize_skill_profile_from_cold_start
    import os
    engine = create_engine("sqlite:///backend/app.db")
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    initialize_skill_profile_from_cold_start(user_id, skill_id_1, db)
    db.close()

    c.execute(f"SELECT proficiency_level, confidence, quiz_confidence, github_proficiency, github_confidence FROM skill_profiles WHERE user_id='{user_id}' AND skill_id='{skill_id_1}'")
    initial_profile = c.fetchone()
    print(f"Initial Cold Start Profile: Proficiency={initial_profile[0]:.2f}, Conf={initial_profile[1]:.2f}, QuizConf={initial_profile[2]}")

    # Submit quiz attempt 1
    # 3 correct out of 5 = 60%
    fail_res = requests.post(f"{base_url}/quiz/{skill_id_1}/submit", json={"answers": {"q1": "A", "q2": "B", "q3": "C", "q4": "Wrong", "q5": "Wrong"}}, headers=headers)
    
    c.execute(f"SELECT proficiency_level, confidence, quiz_confidence, quiz_proficiency FROM skill_profiles WHERE user_id='{user_id}' AND skill_id='{skill_id_1}'")
    profile1 = c.fetchone()
    print(f"\nAfter Quiz 1 (Score 60%):")
    print(f"Proficiency Level: {profile1[0]:.2f}")
    print(f"Overall Confidence: {profile1[1]:.2f}")
    print(f"Quiz Proficiency: {profile1[3]:.2f}")
    print(f"Quiz Confidence: {profile1[2]:.2f}")

    print("\n--- Step 2: Submit second quiz attempt ---")
    # 5 correct out of 5 = 100%
    pass_res = requests.post(f"{base_url}/quiz/{skill_id_1}/submit", json={"answers": {"q1": "A", "q2": "B", "q3": "C", "q4": "D", "q5": "A"}}, headers=headers)
    
    c.execute(f"SELECT proficiency_level, confidence, quiz_confidence, quiz_proficiency FROM skill_profiles WHERE user_id='{user_id}' AND skill_id='{skill_id_1}'")
    profile2 = c.fetchone()
    print(f"\nAfter Quiz 2 (Score 100%):")
    print(f"Proficiency Level: {profile2[0]:.2f}")
    print(f"Overall Confidence: {profile2[1]:.2f}")
    print(f"Quiz Proficiency: {profile2[3]:.2f}")
    print(f"Quiz Confidence: {profile2[2]:.2f}")
    
    print("\n--- Verification Summary ---")
    print(f"Confidence Increased? {profile2[2] > profile1[2]}")
    print(f"Confidence <= 1.0? {profile2[2] <= 1.0 and profile2[1] <= 1.0}")
    
    c.execute(f"SELECT count(*) FROM skill_profiles WHERE user_id='{user_id}' AND skill_id='{skill_id_1}'")
    profile_count = c.fetchone()[0]
    print(f"Duplicate Profiles Created? {'Yes' if profile_count > 1 else 'No'}")
    
    conn.close()

finally:
    server.terminate()
