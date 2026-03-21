"""
auth/api_keys.py — API key authentication dependency (Epic 1.4.3)

Verifies the X-Api-Key header against SHA-256-hashed keys stored in the DB.
"""

from typing import Annotated, Optional

import structlog
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from db.models import User
from db.session import SessionDep
from sqlmodel import select

logger = structlog.get_logger(__name__)

_api_key_header = APIKeyHeader(name="X-Api-Key", auto_error=False)


async def _get_user_by_api_key(
    raw_key: str,
    session: SessionDep,
) -> Optional[User]:
    """Look up a user by their hashed API key. Returns None if not found."""
    hashed = User.hash_api_key(raw_key)
    result = await session.exec(select(User).where(User.hashed_api_key == hashed))
    return result.first()


async def get_current_user(
    api_key: Annotated[Optional[str], Security(_api_key_header)],
    session: SessionDep,
) -> User:
    """
    FastAPI dependency — resolves the current user from the X-Api-Key header.

    Phase 1: API key only.
    Phase 2+: add JWT fallback from Keycloak.

    Raises HTTP 401 if no valid credential is provided.
    """
    if api_key:
        user = await _get_user_by_api_key(api_key, session)
        if user:
            logger.bind(user_id=user.id, auth_method="api_key")
            return user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing API key. Pass X-Api-Key header.",
        headers={"WWW-Authenticate": "ApiKey"},
    )


# Annotated type alias — use in route handlers for clean, reusable injection
CurrentUserDep = Annotated[User, Depends(get_current_user)]
