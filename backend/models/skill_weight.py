from sqlalchemy import Column, String, Float, DateTime, ForeignKey
from datetime import datetime
from db.database import Base

class SkillWeight(Base):
    __tablename__ = "skill_weights"

    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    skill_name = Column(String, primary_key=True)
    source = Column(String, primary_key=True)  # "github" | "resume" | "quiz"

    weight = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)

    last_updated = Column(DateTime, default=datetime.utcnow, nullable=False)
