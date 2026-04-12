"""
auth/api_keys.py — JWT session authentication dependency (Epic 1.4.3)

Verifies the Authorization: Bearer <token> header (signed by Auth.js/jose)
using the shared AUTH_SECRET.
"""

import os
from dotenv import load_dotenv
load_dotenv()  # Ensure .env is loaded before reading AUTH_SECRET
from typing import Annotated, Optional

import structlog
from fastapi import Depends, HTTPException, Security, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

from db.models import User
from db.session import SessionDep
from sqlmodel import select

logger = structlog.get_logger(__name__)

# Use AUTH_SECRET from environment, matching the frontend
AUTH_SECRET = os.environ.get("AUTH_SECRET", "dev-secret-123")
ALGORITHM = "HS256"

security = HTTPBearer()

async def get_current_user(
    request: Request,
    auth: Annotated[HTTPAuthorizationCredentials, Security(security)],
    session: SessionDep,
) -> User:
    """
    FastAPI dependency — resolves the current user from the JWT Bearer token.
    Raises HTTP 401 if no valid token is provided.
    """
    token = auth.credentials
    try:
        # Decode and verify the JWT
        payload = jwt.decode(token, AUTH_SECRET, algorithms=[ALGORITHM])
        email: str = payload.get("email")
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload: missing email",
            )
    except JWTError as e:
        logger.error("auth.jwt_validation_failed", error=str(e), token_preview=token[:10] + "...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Resolve user from DB by email
    result = await session.exec(select(User).where(User.email == email))
    user = result.first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    # Set request state for downstream use
    request.state.user_id = user.id
    if not getattr(request.state, "org_id", None):
        request.state.org_id = user.org_id
        request.state.tenant_id = user.org_id.replace("-", "_")

    logger.bind(user_id=user.id, email=user.email, auth_method="jwt")
    return user


# Annotated type alias — use in route handlers for clean, reusable injection
CurrentUserDep = Annotated[User, Depends(get_current_user)]
