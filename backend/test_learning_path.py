import sys
import os

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
# Import app and database
from main import app
from db.database import Base, get_db
from models import User, UserSkill
from models.course import Course

# Setup test DB
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_learning_path.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

from core.security import get_current_user

def override_get_current_user():
    user = User(id="test_user_id", email="test@example.com", password_hash="pw")
    return user

app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user

client = TestClient(app)

def test_learning_path_logic():
    # Reset DB
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()

    # 1. Create User
    import uuid
    user_id = str(uuid.uuid4())
    user = User(id=user_id, email="learner@example.com", password_hash="pw")
    db.add(user)
    db.commit()
    db.refresh(user)
    print(f"Created user: {user_id}")
    print(f"Created user: {user_id}")

    # 2. Create UserSkills
    # Target skill (high trust)
    skill_terraform = UserSkill(
        user_id=user_id,
        skill_name="terraform",
        trust_score=900.0,
        proficiency_level=0.5
    )
    # Irrelevant skill (low trust)
    skill_python = UserSkill(
        user_id=user_id,
        skill_name="python",
        trust_score=100.0,
        proficiency_level=0.1
    )
    db.add(skill_terraform)
    db.add(skill_python)
    db.commit()

    # 3. Create Course
    course = Course(
        id="terraform:basics",
        roadmap_id="terraform",
        node_id="basics",
        title="Terraform Basics",
        difficulty_level=900
    )
    db.add(course)
    db.commit()

    # 4. Request Learning Path
    print("Requesting learning path for terraform:basics...")
    response = client.get(f"/learning-path/{user_id}/terraform:basics")
    
    if response.status_code != 200:
        print(f"Error: {response.status_code} - {response.text}")
        exit(1)

    data = response.json()
    print(f"Response: {data}")

    # 5. Verify user_elo matches terraform trust_score (900), not average (500)
    user_elo = data["user_elo"]
    print(f"Returned user_elo: {user_elo}")
    
    assert user_elo == 900.0, f"Expected 900.0, got {user_elo}"
    
    # 6. Verify status logic (difficulty 900 vs elo 900 -> ready)
    # abs(900 - 900) <= 100 -> ready
    path_item = data["path"][0]
    print(f"Course status: {path_item['status']}")
    assert path_item["status"] == "ready"

    print("\nVerification Passed! Logic uses roadmap-specific trust score.")

    db.close()
    if os.path.exists("./test_learning_path.db"):
        os.remove("./test_learning_path.db")

if __name__ == "__main__":
    test_learning_path_logic()
