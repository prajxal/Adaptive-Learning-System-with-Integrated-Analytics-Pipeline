import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.models.user import User
from backend.services.skill_graph_service import get_roadmap_skill_status

engine = create_engine("sqlite:///backend/app.db")
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

user = db.query(User).first()
if not user:
    print("No user found")
    sys.exit(1)

status = get_roadmap_skill_status(str(user.id), "ai-agents", db)
print(status)
