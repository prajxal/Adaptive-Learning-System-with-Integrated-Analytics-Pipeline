import subprocess
import time
import os
import sqlite3
import requests
import json
from dotenv import load_dotenv

load_dotenv("backend/.env")

env = os.environ.copy()
env["DATABASE_URL"] = "sqlite:///backend/app.db"
env["PYTHONPATH"] = os.path.abspath("backend")
# Add a dummy api key to trigger a 503 if real one isn't present
if "GEMINI_API_KEY" not in env:
    print("Warning: GEMINI_API_KEY not found in backend/.env, setting dummy key to test 503 fallback")
    env["GEMINI_API_KEY"] = "dummy_key_to_trigger_fallback"

def clear_db():
    conn = sqlite3.connect('backend/app.db')
    c = conn.cursor()
    c.execute("DELETE FROM skill_quizzes")
    conn.commit()
    conn.close()

clear_db()

server = subprocess.Popen(["python", "-m", "uvicorn", "backend.main:app", "--port", "8000"], env=env)
time.sleep(3)

base_url = "http://localhost:8000"
roadmap_id = "ai-agents"
skill_id_1 = "ai-agents:VPI89s-m885r2YrXjYxdd"

try:
    print("\n--- Test 1: Fetch Quiz (Should trigger Generation) ---")
    start = time.time()
    res1 = requests.get(f"{base_url}/quiz/{skill_id_1}")
    print(f"Status Code: {res1.status_code}")
    print(f"Time taken: {time.time() - start:.2f}s")
    if res1.status_code == 200:
        print("Success! Response:")
        print(json.dumps(res1.json(), indent=2))
        
        print("\n--- Test 2: Fetch Quiz Again (Should be instant via cache) ---")
        start = time.time()
        res2 = requests.get(f"{base_url}/quiz/{skill_id_1}")
        print(f"Status Code: {res2.status_code}")
        print(f"Time taken: {time.time() - start:.2f}s")
        assert res2.json()["id"] == res1.json()["id"], "IDs should match exactly"
        print("Cache success - returned identical quiz instantly.")
    elif res1.status_code == 503:
        print("Received expected 503 error due to invalid API key or service unavailability.")
        print(res1.json())
    else:
        print(f"Unexpected status: {res1.status_code}")
        print(res1.text)

finally:
    server.terminate()
