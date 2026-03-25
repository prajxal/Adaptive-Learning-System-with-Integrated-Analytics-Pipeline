import subprocess
import time
import os

env = os.environ.copy()
env["DATABASE_URL"] = "sqlite:///backend/app.db"
env["PYTHONPATH"] = os.path.abspath("backend")

server = subprocess.Popen(["python", "-m", "uvicorn", "backend.main:app", "--port", "8000"], env=env)
time.sleep(4)

print("Starting test...")
test = subprocess.run(["python", "test_quiz_flow.py"], env=env)

server.terminate()
