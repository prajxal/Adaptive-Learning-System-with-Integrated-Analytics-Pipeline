import logging
import os
import threading
import time
import uuid

import requests
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt
from sqlalchemy.orm import Session

from db.database import get_db
from models.user import User

logger = logging.getLogger(__name__)

security = HTTPBearer()

CLERK_JWKS_URL = os.getenv("CLERK_JWKS_URL")
# Audience is optional — set CLERK_JWT_AUDIENCE to your frontend URL if your
# Clerk instance uses audience claims (some setups do not).
CLERK_JWT_AUDIENCE = os.getenv("CLERK_JWT_AUDIENCE")

# ---------------------------------------------------------------------------
# JWKS cache — thread-safe, supports key rotation
# ---------------------------------------------------------------------------

_jwks_lock = threading.Lock()
_jwks_keys: dict[str, dict] = {}   # kid → key dict
_jwks_fetched_at: float = 0.0
_JWKS_TTL_SECONDS = 3600           # re-fetch once per hour (background refresh)


def _fetch_jwks() -> None:
    """Fetch the JWKS endpoint and rebuild the kid-keyed cache."""
    global _jwks_keys, _jwks_fetched_at
    if not CLERK_JWKS_URL:
        logger.error("CLERK_JWKS_URL is not set — JWT verification will always fail")
        return
    try:
        resp = requests.get(CLERK_JWKS_URL, timeout=10)
        resp.raise_for_status()
        keys = resp.json().get("keys", [])
        with _jwks_lock:
            _jwks_keys = {k["kid"]: k for k in keys if "kid" in k}
            _jwks_fetched_at = time.monotonic()
        logger.info("JWKS refreshed — loaded %d keys", len(_jwks_keys))
    except Exception as exc:
        logger.error("Failed to fetch JWKS from %s: %s", CLERK_JWKS_URL, exc)


def _get_key_by_kid(kid: str, *, force_refresh: bool = False) -> dict | None:
    """Return the JWK for the given `kid`, re-fetching if stale or unknown."""
    with _jwks_lock:
        age = time.monotonic() - _jwks_fetched_at
        cached_key = _jwks_keys.get(kid)

    if cached_key and not force_refresh and age < _JWKS_TTL_SECONDS:
        return cached_key

    # Cache miss, TTL expired, or forced refresh — fetch now
    _fetch_jwks()

    with _jwks_lock:
        return _jwks_keys.get(kid)


# Warm up the cache at import time (non-fatal if it fails)
_fetch_jwks()


# ---------------------------------------------------------------------------
# Token verification
# ---------------------------------------------------------------------------


def verify_clerk_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    token = credentials.credentials

    try:
        headers = jwt.get_unverified_header(token)
        kid = headers.get("kid")
        if not kid:
            raise ValueError("JWT is missing the 'kid' header")

        rsa_key = _get_key_by_kid(kid)
        if rsa_key is None:
            # One retry after a forced JWKS refresh (handles key rotation)
            rsa_key = _get_key_by_kid(kid, force_refresh=True)
        if rsa_key is None:
            raise ValueError(f"RSA key not found for kid={kid!r}")

        decode_kwargs: dict = {
            "algorithms": ["RS256"],
            "options": {"verify_aud": False},  # Clerk does not set aud by default
        }
        # If the operator has configured an audience, verify it
        if CLERK_JWT_AUDIENCE:
            decode_kwargs["audience"] = CLERK_JWT_AUDIENCE
            decode_kwargs["options"] = {"verify_aud": True}

        payload = jwt.decode(token, rsa_key, **decode_kwargs)
        return payload["sub"]

    except Exception as exc:
        logger.warning("Clerk auth failed: %s", exc)
        raise HTTPException(status_code=401, detail="Invalid authentication")


# ---------------------------------------------------------------------------
# User resolution
# ---------------------------------------------------------------------------


def get_current_user(
    clerk_user_id: str = Depends(verify_clerk_token),
    db: Session = Depends(get_db),
) -> User:
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
            github_sync_status="idle",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    return user
