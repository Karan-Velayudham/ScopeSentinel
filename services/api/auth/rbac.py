"""
auth/rbac.py — Role-Based Access Control enforcement for ScopeSentinel API (Epic 5.2)

Provides:
  - require_role(*roles) — FastAPI dependency that enforces minimum role level
  - get_current_user    — Resolves JWT or API key from the request → User record
  - Resource-level checks for workflow trigger/approve permissions

Role hierarchy (lowest to highest):
  VIEWER < REVIEWER < DEVELOPER < ORG_ADMIN
"""

import hashlib
import os
from typing import Annotated, Optional

import structlog
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from db.models import User, UserRole
from db.session import get_session

logger = structlog.get_logger(__name__)

# Security schemes
_bearer = HTTPBearer(auto_error=False)
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Role hierarchy — higher index = more privilege
_ROLE_HIERARCHY = [UserRole.VIEWER, UserRole.REVIEWER, UserRole.DEVELOPER, UserRole.ADMIN]


def _role_level(role: UserRole) -> int:
    try:
        return _ROLE_HIERARCHY.index(role)
    except ValueError:
        return -1


# ---------------------------------------------------------------------------
# User resolution (JWT or API key)
# ---------------------------------------------------------------------------

async def get_current_user(
    bearer: Optional[HTTPAuthorizationCredentials] = Security(_bearer),
    api_key: Optional[str] = Security(_api_key_header),
    session: AsyncSession = Depends(get_session),
) -> Optional[User]:
    """
    Resolves the current authenticated user from either:
      1. Bearer token (Keycloak JWT) — extracts `email` claim from token
      2. X-API-Key header            — SHA-256 hash lookup against `users.hashed_api_key`

    Returns None if no credentials provided (allows anonymous access to public endpoints).
    Raises 401 if credentials are invalid.
    """
    # --- API Key auth ---
    if api_key:
        hashed = hashlib.sha256(api_key.encode()).hexdigest()
        result = await session.exec(select(User).where(User.hashed_api_key == hashed))
        user = result.first()
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
        logger.debug("rbac.api_key_auth", user_id=user.id, email=user.email)
        return user

    # --- JWT Bearer auth ---
    if bearer and bearer.credentials:
        try:
            email = _extract_email_from_jwt(bearer.credentials)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid bearer token",
            ) from exc

        result = await session.exec(select(User).where(User.email == email))
        user = result.first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"User '{email}' not found",
            )
        logger.debug("rbac.jwt_auth", user_id=user.id, email=user.email)
        return user

    return None  # Anonymous


def _extract_email_from_jwt(token: str) -> str:
    """
    Decode the JWT payload (no signature verification here — Kong gateway
    validates signatures before requests reach the API).
    Extracts the `email` claim.
    """
    import base64
    import json

    try:
        # JWT = header.payload.signature
        payload_b64 = token.split(".")[1]
        # Add padding if needed
        payload_b64 += "=" * (-len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        email = payload.get("email") or payload.get("preferred_username")
        if not email:
            raise ValueError("No email claim in token")
        return email
    except Exception as exc:
        raise ValueError(f"Failed to decode JWT: {exc}") from exc


# ---------------------------------------------------------------------------
# Role enforcement dependencies
# ---------------------------------------------------------------------------

def require_role(*roles: UserRole):
    """
    Factory that returns a FastAPI dependency enforcing minimum role.

    Usage:
        @router.post("/runs")
        async def create_run(user: Annotated[User, Depends(require_role(UserRole.DEVELOPER))]):
            ...
    """
    min_level = min(_role_level(r) for r in roles)

    async def _check(
        current_user: Optional[User] = Depends(get_current_user),
    ) -> User:
        if current_user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )
        if _role_level(current_user.role) < min_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of: {[r.value for r in roles]}",
            )
        return current_user

    return _check


# Convenience aliases
RequireViewer = Depends(require_role(UserRole.VIEWER))
RequireReviewer = Depends(require_role(UserRole.REVIEWER))
RequireDeveloper = Depends(require_role(UserRole.DEVELOPER))
RequireAdmin = Depends(require_role(UserRole.ADMIN))

# Type aliases for use in route signatures
CurrentUserDep = Annotated[Optional[User], Depends(get_current_user)]


# ---------------------------------------------------------------------------
# Resource-level permission checks
# ---------------------------------------------------------------------------

def can_trigger_workflow(user: User) -> bool:
    """Only developers and above can trigger workflow runs."""
    return _role_level(user.role) >= _role_level(UserRole.DEVELOPER)


def can_approve_hitl(user: User) -> bool:
    """Reviewers and above can approve/reject HITL gates."""
    return _role_level(user.role) >= _role_level(UserRole.REVIEWER)


def can_manage_users(user: User) -> bool:
    """Only org admins can invite/remove users or change roles."""
    return user.role == UserRole.ADMIN


def assert_can_trigger(user: User) -> None:
    if not can_trigger_workflow(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires DEVELOPER role or above to trigger workflows",
        )


def assert_can_approve_hitl(user: User) -> None:
    if not can_approve_hitl(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires REVIEWER role or above to approve HITL decisions",
        )


def assert_can_manage_users(user: User) -> None:
    if not can_manage_users(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires ORG_ADMIN role to manage users",
        )
