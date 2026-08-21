import logging
import os
import secrets
from datetime import datetime, timedelta

import httpx
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from core.clerk_auth import get_current_user
from db.database import get_db
from models.oauth_state import OAuthState
from models.user import User
from models.skill_weight import SkillWeight
from services.github_skill_extractor import extract_github_skills
from core.rate_limit import RateLimiter

load_dotenv()
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/github", tags=["github-auth"])
rate_limiter = RateLimiter(calls=5, period=60)

_STATE_TTL_MINUTES = 10


def _purge_expired_states(db: Session) -> None:
    """Delete expired OAuth state rows (best-effort, called on connect)."""
    try:
        db.query(OAuthState).filter(OAuthState.expires_at < datetime.utcnow()).delete()
        db.commit()
    except Exception as exc:
        logger.warning("Failed to purge expired OAuth states: %s", exc)
        db.rollback()


@router.get("/connect", dependencies=[Depends(rate_limiter)])
def github_connect(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
    REDIRECT_URI = os.getenv("GITHUB_REDIRECT_URI")

    if not CLIENT_ID or not REDIRECT_URI:
        raise HTTPException(status_code=500, detail="GitHub OAuth not configured properly.")

    _purge_expired_states(db)

    state = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(minutes=_STATE_TTL_MINUTES)
    db.add(OAuthState(state=state, user_id=str(current_user.id), expires_at=expires_at))
    db.commit()

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
    db: Session = Depends(get_db),
):
    state_row = (
        db.query(OAuthState)
        .filter(OAuthState.state == state, OAuthState.expires_at > datetime.utcnow())
        .first()
    )
    if not state_row:
        raise HTTPException(status_code=400, detail="Invalid or expired state")

    user_id = state_row.user_id
    # Consume (delete) the state — single-use
    db.delete(state_row)
    db.commit()

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

    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
    return RedirectResponse(url=f"{FRONTEND_URL}/profile?github=connected")

@router.get("/status")
def github_status(current_user: User = Depends(get_current_user)):
    return {
        "connected": current_user.github_status == "connected",
        "username": current_user.github_username,
        "sync_status": current_user.github_sync_status
    }


@router.post("/sync", dependencies=[Depends(rate_limiter)])
async def github_sync(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user_id = str(current_user.id)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.github_access_token:
        raise HTTPException(status_code=400, detail="GitHub account is not connected")

    user.github_sync_status = "syncing"
    db.commit()

    access_token = user.github_access_token
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github.v3+json"
    }

    repositories_analyzed = 0

    try:
        # Count active repositories that will be analyzed.
        async with httpx.AsyncClient() as client:
            page = 1
            while True:
                resp = await client.get(
                    f"https://api.github.com/user/repos?per_page=100&page={page}",
                    headers=headers,
                )
                if resp.status_code != 200:
                    raise HTTPException(status_code=502, detail="Failed to fetch repositories from GitHub")

                page_rows = resp.json()
                if not isinstance(page_rows, list) or not page_rows:
                    break

                repositories_analyzed += len(
                    [repo for repo in page_rows if not repo.get("fork") and not repo.get("archived")]
                )
                page += 1

        # Recompute analysis from scratch to avoid stale language rows.
        db.query(SkillWeight).filter(
            SkillWeight.user_id == user_id,
            SkillWeight.source == "github"
        ).delete(synchronize_session=False)
        db.commit()

        await extract_github_skills(user_id=user_id, access_token=access_token)
        db.refresh(user)

        if user.github_sync_status == "failed":
            raise HTTPException(status_code=502, detail="GitHub sync failed")

        return {
            "status": "synced",
            "repositories_analyzed": repositories_analyzed
        }
    except HTTPException:
        user.github_sync_status = "failed"
        db.commit()
        raise
    except Exception:
        db.rollback()
        try:
            user.github_sync_status = "failed"
            db.commit()
        except Exception:
            pass
        raise HTTPException(status_code=502, detail="Failed to sync GitHub data")


@router.delete("/disconnect")
def github_disconnect(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user_id = str(current_user.id)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        db.query(SkillWeight).filter(
            SkillWeight.user_id == user_id,
            SkillWeight.source == "github"
        ).delete(synchronize_session=False)

        user.github_access_token = None
        user.github_username = None
        user.github_status = "disconnected"
        user.github_sync_status = "idle"
        user.last_github_sync = None
        user.github_connected_at = None

        db.commit()
        return {"status": "disconnected"}
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to disconnect GitHub")
