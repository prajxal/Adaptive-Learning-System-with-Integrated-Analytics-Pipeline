import sys
import uuid
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend'))
sys.path.insert(0, project_root)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.database import Base
from models.user import User
from models.skill_weight import SkillWeight
from models.skill_profile import SkillProfile
from routers.skill_graph import read_roadmap_skill_status
from routers.users import get_user_skills

engine = create_engine("sqlite:///backend/app.db")
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

test_id = str(uuid.uuid4())
new_user = User(
    id=test_id,
    email=f"test{test_id}@example.com"
)
db.add(new_user)
db.commit()

weight = SkillWeight(
    user_id=test_id,
    skill_name="ai-agents:VPI89s-m885r2YrXjYxdd",
    source="github",
    weight=0.8,
    confidence=0.9
)
db.add(weight)
db.commit()

status_response = read_roadmap_skill_status("ai-agents", new_user, db)

unlocked_nodes = [s for s in status_response["skills"] if s["status"] == "unlocked"]
print(f"Total unlocked nodes: {len(unlocked_nodes)}")
if len(unlocked_nodes) > 0:
    print(f"First Unlocked Node: {unlocked_nodes[0]['skill_id']}")

profiles = db.query(SkillProfile).filter(SkillProfile.user_id == test_id).all()
print(f"SkillProfile rows generated automatically by API: {len(profiles)}")

dashboard_skills = get_user_skills(new_user, db)
print(f"Dashboard aggregated skillset count: {len(dashboard_skills['skills'])}")
for skill in dashboard_skills['skills']:
    print(f"  Roadmap: {skill['roadmap_id']}, Proficiency: {skill['proficiency_level']}")

