import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session
import os
import httpx

from core.security import create_access_token, hash_password, verify_password
from core.clerk_auth import get_current_user
from db.database import get_db
from models.user import User
from core.rate_limit import RateLimiter

router = APIRouter()
rate_limiter = RateLimiter(calls=5, period=60)

# Request models
class AuthRequest(BaseModel):
    email: str
    password: str

# Signup endpoint
@router.post("/signup", dependencies=[Depends(rate_limiter)])
def signup(request: AuthRequest, db: Session = Depends(get_db)):
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create new user
    user_id = str(uuid.uuid4())
    try:
        hashed_pw = hash_password(request.password)
    except Exception as e:
        print(f"Password hashing failed: {e}")
        raise HTTPException(status_code=500, detail="Password hashing failed")
        
    new_user = User(
        id=user_id,
        email=request.email,
        password_hash=hashed_pw,
        created_at=datetime.utcnow()
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Generate token
    access_token = create_access_token(user_id=new_user.id)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": new_user.id
    }

# Login endpoint
@router.post("/login", dependencies=[Depends(rate_limiter)])
def login(request: AuthRequest, db: Session = Depends(get_db)):
    # Find user
    user = db.query(User).filter(User.email == request.email).first()
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Generate token
    access_token = create_access_token(user_id=user.id)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id
    }

# Protected user details endpoint
@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "avatar_url": getattr(current_user, "avatar_url", None)
    }


@router.post("/google/exchange")
async def google_exchange(
    payload: dict,
    db: Session = Depends(get_db)
):
    access_token = payload.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="No access token provided")
    
    # Get user info from Supabase
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{os.getenv('SUPABASE_URL')}/auth/v1/user",
            headers={
                "Authorization": f"Bearer {access_token}",
                "apikey": os.getenv("SUPABASE_ANON_KEY")
            }
        )
    
    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Invalid Supabase token")
    
    supabase_user = response.json()
    email = supabase_user.get("email")
    google_id = supabase_user.get("id")
    avatar_url = supabase_user.get("user_metadata", {}).get("avatar_url", "")

    if not email:
        raise HTTPException(status_code=400, detail="No email from Google")

    # Find or create user
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            password_hash="google-oauth-" + str(uuid.uuid4()),
            google_id=google_id,
            google_connected=True,
            avatar_url=avatar_url,
            created_at=datetime.utcnow()
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        user.google_connected = True
        user.google_id = google_id
        if avatar_url:
            user.avatar_url = avatar_url
        db.commit()

    # Issue our JWT
    our_token = create_access_token(user_id=user.id)
    return {"token": our_token}