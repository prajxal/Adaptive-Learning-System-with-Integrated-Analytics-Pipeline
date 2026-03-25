import sys
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.models.user import User
from backend.models.skill_weight import SkillWeight
from backend.routers.skill_graph import read_roadmap_skill_status
from backend.routers.users import get_user_skills
from passlib.context import CryptContext

engine = create_engine("sqlite:///backend/app.db")
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

# 1. Create brand new test user
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
test_id = str(uuid.uuid4())
new_user = User(
    id=test_id,
    email=f"test{test_id}@example.com",
    hashed_password=pwd_context.hash("password"),
    name="Test User"
)
db.add(new_user)
db.commit()

user_id = test_id

# 2 & 3. Connect GitHub / Upload Resume (simulate by adding SkillWeight)
weight = SkillWeight(
    user_id=user_id,
    skill_name="ai-agents:VPI89s-m885r2YrXjYxdd",  # Assuming first node
    source="github",
    weight=0.8,
    confidence=0.9
)
db.add(weight)
db.commit()

# 4. Open roadmap (This triggers GET /skill-graph/ai-agents/status)
# We can call the router function directly. It expects a User object.
try:
    status_response = read_roadmap_skill_status("ai-agents", new_user, db)
    
    # Verify first skill unlocked
    first_skill = status_response["skills"][0]
    print(f"First Skill Status: {first_skill['status']} (Expected: unlocked or completed)")

    # Verify Dashboard shows skill profile
    dashboard_skills = get_user_skills(new_user, db)
    print(f"Dashboard Skills: {len(dashboard_skills['skills'])} roadmap(s) found.")
    for skill in dashboard_skills['skills']:
        print(f"  Roadmap: {skill['roadmap_id']}, Proficiency: {skill['proficiency_level']}")

except Exception as e:
    print(f"Error during verification: {e}")

