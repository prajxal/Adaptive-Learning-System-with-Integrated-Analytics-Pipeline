from sqlalchemy import Column, String, Float, DateTime, UniqueConstraint, ForeignKey
from datetime import datetime
import uuid
from db.database import Base

class SkillProfile(Base):
    __tablename__ = "skill_profiles"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    skill_id = Column(String, nullable=False, index=True)  # roadmap/skill identifier; no FK constraint
    roadmap_id = Column(String, nullable=False, index=True)
    
    proficiency_level = Column(Float, default=0.0)
    confidence = Column(Float, default=0.0)
    
    quiz_proficiency = Column(Float, default=0.0)
    quiz_confidence = Column(Float, default=0.0)
    
    github_proficiency = Column(Float, default=0.0)
    github_confidence = Column(Float, default=0.0)
    
    resume_proficiency = Column(Float, default=0.0)
    resume_confidence = Column(Float, default=0.0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "skill_id", name="uix_user_skill_profile"),
    )
