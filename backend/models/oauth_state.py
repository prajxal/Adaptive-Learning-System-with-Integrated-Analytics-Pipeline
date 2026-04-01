from datetime import datetime

from sqlalchemy import Column, DateTime, String

from db.database import Base


class OAuthState(Base):
    """Short-lived OAuth CSRF state tokens.

    Created when a user initiates GitHub OAuth (/github/connect).
    Consumed (deleted) on callback (/github/callback).
    Expires after 10 minutes — a background cleanup job or the
    callback itself handles deletion.
    """

    __tablename__ = "oauth_states"

    state = Column(String, primary_key=True, index=True)
    user_id = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
