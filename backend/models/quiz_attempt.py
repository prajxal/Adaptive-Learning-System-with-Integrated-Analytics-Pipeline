from sqlalchemy import Column, String, ForeignKey, DateTime, Integer, Float, Boolean, JSON, Text
from datetime import datetime
import uuid
from db.database import Base

class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    skill_id = Column(String, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    score = Column(Float, nullable=False)
    passed = Column(Boolean, nullable=False)
    answers = Column(JSON(), nullable=True) # User's submitted answers
    created_at = Column(DateTime, default=datetime.utcnow)
