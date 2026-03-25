import requests
import json
import sqlite3
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

base_url = "http://localhost:8000"

# 1. Login to get token
user_data = {"email": "testgraph2@example.com", "password": "password123"}
login_res = requests.post(f"{base_url}/auth/login", json=user_data)
if login_res.status_code != 200:
    print("Login missing - recreating user")
    requests.post(f"{base_url}/auth/signup", json=user_data)
    login_res = requests.post(f"{base_url}/auth/login", json=user_data)

token = login_res.json().get("access_token")
headers = {"Authorization": f"Bearer {token}"}

# Get User ID
me_res = requests.get(f"{base_url}/auth/me", headers=headers)
user_id = me_res.json().get("id")

roadmap_id = "ai-agents"

# Step 1: Clean up any previous events and quizzes to test fresh
conn = sqlite3.connect('backend/app.db')
c = conn.cursor()
c.execute(f"DELETE FROM events WHERE user_id='{user_id}' AND roadmap_id='{roadmap_id}'")
c.execute(f"DELETE FROM quiz_attempts WHERE user_id='{user_id}'")
c.execute("DELETE FROM skill_quizzes")
conn.commit()

# Step 2: Query initial state
res = requests.get(f"{base_url}/skill-graph/{roadmap_id}/status", headers=headers)
data = res.json()
first_skill = data['skills'][0]['skill_id']
second_skill = data['skills'][1]['skill_id']

print("INITIAL STATUS:")
print(f"1. {first_skill}: {data['skills'][0]['status']}")
print(f"2. {second_skill}: {data['skills'][1]['status']}")

# Step 3: Insert a Quiz for the first skill
questions = json.dumps([
    {"id": "q1", "text": "What is AI?", "options": ["A", "B", "C"], "correct_answer": "A"},
    {"id": "q2", "text": "What is an Agent?", "options": ["X", "Y", "Z"], "correct_answer": "Y"}
])
c.execute(f"INSERT INTO skill_quizzes (id, skill_id, questions, passing_score, created_at) VALUES ('q_test', '{first_skill}', '{questions}', 100, '{datetime.utcnow().isoformat()}')")
conn.commit()
conn.close()

# Step 4: Fetch Quiz (Verify correct_answer is stripped)
quiz_res = requests.get(f"{base_url}/quiz/{first_skill}", headers=headers)
print("\nFETCH QUIZ RESPONSE:")
print(json.dumps(quiz_res.json(), indent=2))

# Step 5: Submit Failure Quiz
print("\nSUBMITTING FAILED QUIZ:")
fail_res = requests.post(f"{base_url}/quiz/{first_skill}/submit", json={"answers": {"q1": "A", "q2": "Z"}}, headers=headers)
print(fail_res.json())

# Step 6: Query status (should still be unlocked/locked)
res = requests.get(f"{base_url}/skill-graph/{roadmap_id}/status", headers=headers)
data = res.json()
print("\nSTATUS AFTER FAILURE:")
print(f"1. {first_skill}: {data['skills'][0]['status']}")
print(f"2. {second_skill}: {data['skills'][1]['status']}")

# Step 7: Submit Winning Quiz
print("\nSUBMITTING PASSING QUIZ:")
pass_res = requests.post(f"{base_url}/quiz/{first_skill}/submit", json={"answers": {"q1": "A", "q2": "Y"}}, headers=headers)
print(pass_res.json())

# Step 8: Query status (should now be completed/unlocked)
res = requests.get(f"{base_url}/skill-graph/{roadmap_id}/status", headers=headers)
data = res.json()
print("\nSTATUS AFTER PASSING:")
print(f"1. {first_skill}: {data['skills'][0]['status']}")
print(f"2. {second_skill}: {data['skills'][1]['status']}")

