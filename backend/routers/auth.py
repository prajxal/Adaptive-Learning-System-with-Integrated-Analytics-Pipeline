import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session
import os
import httpx
from fastapi.responses import RedirectResponse

from core.security import create_access_token, get_current_user, hash_password, verify_password
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

@router.get("/google")
def google_auth():
    supabase_url = os.getenv("SUPABASE_URL")
    redirect_url = os.getenv("FRONTEND_URL") + "/auth/callback"
    auth_url = f"{supabase_url}/auth/v1/authorize?provider=google&redirect_to={redirect_url}"
    return RedirectResponse(auth_url)

@router.get("/callback")
async def google_callback(code: str, db: Session = Depends(get_db)):
    supabase_url = os.getenv("SUPABASE_URL")
    anon_key = os.getenv("SUPABASE_ANON_KEY")
    
    async with httpx.AsyncClient() as client:
        # Exchange code
        res = await client.post(
            f"{supabase_url}/auth/v1/token?grant_type=pkce",
            json={"auth_code": code},
            headers={"apikey": anon_key, "Content-Type": "application/json"}
        )
        token_data = res.json()
        supa_access_token = token_data.get("access_token")

        if not supa_access_token:
            raise HTTPException(status_code=400, detail="Failed to retrieve access token from Supabase")

        # Fetch user profile
        user_res = await client.get(
            f"{supabase_url}/auth/v1/user",
            headers={"apikey": anon_key, "Authorization": f"Bearer {supa_access_token}"}
        )
        user_data = user_res.json()
    
    email = user_data.get("email")
    google_id = user_data.get("id")
    user_metadata = user_data.get("user_metadata", {})
    avatar_url = user_metadata.get("avatar_url")

    if not email:
        raise HTTPException(status_code=400, detail="Could not retrieve email from Google")

    # Link or create user
    user = db.query(User).filter(User.email == email).first()
    if user:
        user.google_connected = True
        if not user.google_id:
            user.google_id = google_id
        if avatar_url and not getattr(user, "avatar_url", None):
            user.avatar_url = avatar_url
        db.commit()
    else:
        user_id = str(uuid.uuid4())
        hashed_pw = hash_password("google-oauth-" + str(uuid.uuid4()))
        user = User(
            id=user_id,
            email=email,
            password_hash=hashed_pw,
            google_id=google_id,
            google_connected=True,
            avatar_url=avatar_url,
            created_at=datetime.utcnow()
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # Issue our own JWT
    access_token = create_access_token(user_id=user.id)
    frontend_url = os.getenv("FRONTEND_URL")
    return RedirectResponse(url=f"{frontend_url}/auth/callback?token={access_token}")