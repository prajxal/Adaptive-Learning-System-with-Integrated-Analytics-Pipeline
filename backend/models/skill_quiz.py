from sqlalchemy import Column, String, ForeignKey, DateTime, Integer, JSON, Text, UniqueConstraint
from datetime import datetime
import uuid
from db.database import Base

class SkillQuiz(Base):
    __tablename__ = "skill_quizzes"
    __table_args__ = (UniqueConstraint("skill_id", name="uq_skill_quiz_skill_id"),)

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    skill_id = Column(String, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    questions = Column(JSON(), nullable=False, default=list) # [{ question: "...", options: ["A", "B", ...], correct_answer: "A" }]
    passing_score = Column(Integer, nullable=False, default=80) # Default to 80%
    created_at = Column(DateTime, default=datetime.utcnow)
