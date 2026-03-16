import os
import secrets
import httpx
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from core.clerk_auth import get_current_user
from db.database import get_db
from models.user import User
from services.github_skill_extractor import extract_github_skills
from core.rate_limit import RateLimiter

load_dotenv()

router = APIRouter(prefix="/github", tags=["github-auth"])
rate_limiter = RateLimiter(calls=5, period=60)

# In-memory state store (production should use Redis)
oauth_state_store = {}

@router.get("/connect", dependencies=[Depends(rate_limiter)])
def github_connect(current_user: User = Depends(get_current_user)):
    CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
    REDIRECT_URI = os.getenv("GITHUB_REDIRECT_URI")
    
    if not CLIENT_ID or not REDIRECT_URI:
        raise HTTPException(status_code=500, detail="GitHub OAuth not configured properly.")

    state = secrets.token_urlsafe(32)
    oauth_state_store[state] = str(current_user.id)
    
    github_auth_url = (
        f"https://github.com/login/oauth/authorize?"
        f"client_id={CLIENT_ID}&"
        f"redirect_uri={REDIRECT_URI}&"
        f"scope=read:user,repo&"
        f"state={state}"
    )
    return {"url": github_auth_url}

@router.get("/callback")
async def github_callback(
    code: str,
    state: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    user_id = oauth_state_store.pop(state, None)
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid or expired state")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
    CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
    REDIRECT_URI = os.getenv("GITHUB_REDIRECT_URI")

    # Exchange code for access_token
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "code": code,
                "redirect_uri": REDIRECT_URI
            },
            headers={"Accept": "application/json"}
        )
        token_data = token_resp.json()
        
    access_token = token_data.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="GitHub authentication failed")

    # Fetch GitHub user profile
    async with httpx.AsyncClient() as client:
        user_resp = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github.v3+json"
            }
        )
        if user_resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to fetch GitHub profile")
        
        profile_data = user_resp.json()

    github_username = profile_data.get("login")

    user.github_username = github_username
    user.github_access_token = access_token
    user.github_status = "connected"
    user.github_sync_status = "syncing"

    db.commit()

    background_tasks.add_task(
        extract_github_skills,
        user_id=user_id,
        access_token=access_token
    )

    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5174")
    return RedirectResponse(url=f"{FRONTEND_URL}/dashboard?github=connected")

@router.get("/status")
def github_status(current_user: User = Depends(get_current_user)):
    return {
        "connected": current_user.github_status == "connected",
        "username": current_user.github_username,
        "sync_status": current_user.github_sync_status
    }
