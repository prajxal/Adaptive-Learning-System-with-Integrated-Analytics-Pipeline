from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Boolean
from sqlalchemy.orm import relationship

from db.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    clerk_user_id = Column(String, unique=True, index=True, nullable=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    skill_level = Column(String, nullable=True)
    engagement_score = Column(Float, default=0.0, nullable=False)
    global_elo_rating = Column(Float, default=1000.0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    resume_status = Column(String, default="none", nullable=False)
    
    github_id = Column(String, unique=True, nullable=True, index=True)
    github_username = Column(String, nullable=True)
    github_access_token = Column(String, nullable=True)
    github_status = Column(String, default="disconnected", nullable=False)
    github_connected_at = Column(DateTime, nullable=True)
    github_sync_status = Column(String, default="idle", nullable=False)
    last_github_sync = Column(DateTime, nullable=True)

    google_id = Column(String, unique=True, nullable=True, index=True)
    google_connected = Column(Boolean, default=False)
    avatar_url = Column(String, nullable=True)

    # XP / Level system (added in migration 20260330_add_xp_level_columns)
    total_xp = Column(Integer, default=0, nullable=False)
    current_level = Column(Integer, default=1, nullable=False)

    # Onboarding (added in migration 20260331_add_onboarding_completed)
    onboarding_completed = Column(Boolean, default=False, nullable=False)

    user_skills = relationship("UserSkill", back_populates="user", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="user", cascade="all, delete-orphan")
