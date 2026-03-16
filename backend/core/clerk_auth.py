import os
import uuid
import logging
import requests
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import jwt

from db.database import get_db
from models.user import User

logger = logging.getLogger(__name__)

security = HTTPBearer()

CLERK_JWKS_URL = os.getenv("CLERK_JWKS_URL", "https://clerk.dev/.well-known/jwks.json")

try:
    jwks = requests.get(CLERK_JWKS_URL).json()
except Exception as e:
    logger.warning(f"Failed to fetch JWKS from {CLERK_JWKS_URL}: {e}")
    jwks = {}

async def verify_clerk_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    Validates the Bearer token using Clerk JWKS and returns the clerk_user_id (sub).
    """
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            jwks,
            algorithms=["RS256"],
            options={"verify_aud": False}
        )
        clerk_user_id = payload.get("sub")
        if not clerk_user_id:
            raise ValueError("Token missing 'sub' claim")
        return clerk_user_id
    except Exception as e:
        print("Clerk auth failed:", e)
        logger.warning(f"Clerk auth failed: {e}")
        raise HTTPException(
            status_code=401,
            detail="Invalid Clerk token"
        )

async def get_current_user(
    clerk_user_id: str = Depends(verify_clerk_token),
    db: Session = Depends(get_db)
) -> User:
    """
    Returns the User from the DB corresponding to the clerk_user_id.
    Auto-provisions the user if they do not exist.
    """
    user = db.query(User).filter(User.clerk_user_id == clerk_user_id).first()

    if not user:
        logger.info(f"Auto-provisioning new user for Clerk ID: {clerk_user_id}")
        user = User(
            id=str(uuid.uuid4()),
            clerk_user_id=clerk_user_id,
            email=f"{clerk_user_id}@placeholder.com", # Needs a placeholder if clerk does not pass email inside standard token
            password_hash="clerk_managed", 
            global_elo_rating=800.0,
            resume_status="not_uploaded",
            github_status="disconnected",
            github_sync_status="idle"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    return user
