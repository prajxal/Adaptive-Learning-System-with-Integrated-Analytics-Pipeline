import os
import uuid
import requests
from jose import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from db.database import get_db
from models.user import User

security = HTTPBearer()

CLERK_JWKS_URL = os.getenv("CLERK_JWKS_URL")

jwks = {"keys": []}
if CLERK_JWKS_URL:
    try:
        jwks = requests.get(CLERK_JWKS_URL).json()
    except Exception as e:
        print(f"Failed to fetch JWKS from {CLERK_JWKS_URL}:", e)
else:
    print("Warning: CLERK_JWKS_URL environment variable is not set. Token verification will fail.")


def get_rsa_key(token):
    headers = jwt.get_unverified_header(token)
    kid = headers.get("kid")

    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key

    raise Exception("RSA key not found")


def verify_clerk_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials

    try:
        rsa_key = get_rsa_key(token)

        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )

        return payload["sub"]

    except Exception as e:
        print("Clerk auth failed:", e)
        raise HTTPException(status_code=401, detail="Invalid authentication")


def get_current_user(
    clerk_user_id: str = Depends(verify_clerk_token),
    db: Session = Depends(get_db)
) -> User:
    print(f"[get_current_user] Authenticated Clerk User ID: {clerk_user_id}")
    user = db.query(User).filter(User.clerk_user_id == clerk_user_id).first()

    if not user:
        user = User(
            id=str(uuid.uuid4()),
            clerk_user_id=clerk_user_id,
            email=f"{clerk_user_id}@placeholder.com",
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