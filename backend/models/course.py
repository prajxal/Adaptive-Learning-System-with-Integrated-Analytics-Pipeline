from sqlalchemy import Column, String, Integer, DateTime, Float
from datetime import datetime
from db.database import Base

class Course(Base):
    __tablename__ = "courses"

    id = Column(String, primary_key=True, index=True)
    roadmap_id = Column(String, nullable=False, index=True)
    node_id = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    difficulty_level = Column(Float, nullable=False, default=1000.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # XP / Level system (added in migration 20260330_add_xp_level_columns)
    required_level = Column(Integer, default=1, nullable=False)
