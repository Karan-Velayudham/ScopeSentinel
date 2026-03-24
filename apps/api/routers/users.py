"""
routers/users.py — User and role management endpoints (Epic 5.2)

Endpoints:
  GET    /api/users              — List users in the caller's org
  POST   /api/users/invite       — Invite a user (ORG_ADMIN only)
  PATCH  /api/users/{id}/role    — Change a user's role (ORG_ADMIN only)
  DELETE /api/users/{id}         — Remove a user from the org (ORG_ADMIN only)
  POST   /api/users/api-keys     — Generate a new scoped API key for yourself
  DELETE /api/users/api-keys     — Revoke your current API key
"""

import hashlib
import os
import secrets
from typing import Optional

import structlog
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlmodel import select

from auth.rbac import CurrentUserDep, assert_can_manage_users, require_role
from db.models import User, UserRole
from db.session import SessionDep

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/users", tags=["users"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class UserOut(BaseModel):
    id: str
    email: str
    role: str
    has_api_key: bool
    org_id: str


class InviteUserRequest(BaseModel):
    email: str
    role: UserRole = UserRole.DEVELOPER


class UpdateRoleRequest(BaseModel):
    role: UserRole


class ApiKeyResponse(BaseModel):
    api_key: str
    message: str = "Store this key securely — it will not be shown again."


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=list[UserOut])
async def list_users(current_user: CurrentUserDep, session: SessionDep):
    """List all users in the caller's organisation."""
    if current_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    result = await session.exec(select(User).where(User.org_id == current_user.org_id))
    users = result.all()
    return [
        UserOut(
            id=u.id,
            email=u.email,
            role=u.role.value,
            has_api_key=u.hashed_api_key is not None,
            org_id=u.org_id,
        )
        for u in users
    ]


@router.post("/invite", response_model=UserOut, status_code=201)
async def invite_user(
    body: InviteUserRequest,
    current_user: CurrentUserDep,
    session: SessionDep,
):
    """Invite a new user to the org. Only ORG_ADMIN can do this."""
    if current_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    assert_can_manage_users(current_user)

    # Check if user already exists
    result = await session.exec(select(User).where(User.email == body.email))
    if result.first():
        raise HTTPException(status_code=409, detail=f"User '{body.email}' already exists")

    user = User(org_id=current_user.org_id, email=body.email, role=body.role)
    session.add(user)
    await session.commit()
    await session.refresh(user)

    logger.info("users.invited", invited_email=body.email, by=current_user.email, role=body.role)
    return UserOut(id=user.id, email=user.email, role=user.role.value, has_api_key=False, org_id=user.org_id)


@router.patch("/{user_id}/role", response_model=UserOut)
async def update_user_role(
    user_id: str,
    body: UpdateRoleRequest,
    current_user: CurrentUserDep,
    session: SessionDep,
):
    """Change a user's role. Only ORG_ADMIN can do this."""
    if current_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    assert_can_manage_users(current_user)

    result = await session.exec(
        select(User).where(User.id == user_id, User.org_id == current_user.org_id)
    )
    target = result.first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found in this org")

    old_role = target.role
    target.role = body.role
    session.add(target)
    await session.commit()

    logger.info("users.role_changed", target_id=user_id, old=old_role, new=body.role, by=current_user.email)
    return UserOut(id=target.id, email=target.email, role=target.role.value, has_api_key=target.hashed_api_key is not None, org_id=target.org_id)


@router.delete("/{user_id}", status_code=204)
async def remove_user(
    user_id: str,
    current_user: CurrentUserDep,
    session: SessionDep,
):
    """Remove a user from the org. Only ORG_ADMIN can do this."""
    if current_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    assert_can_manage_users(current_user)

    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot remove yourself")

    result = await session.exec(
        select(User).where(User.id == user_id, User.org_id == current_user.org_id)
    )
    target = result.first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found in this org")

    await session.delete(target)
    await session.commit()
    logger.info("users.removed", target_id=user_id, by=current_user.email)


@router.post("/api-keys", response_model=ApiKeyResponse, status_code=201)
async def generate_api_key(current_user: CurrentUserDep, session: SessionDep):
    """Generate a new API key for yourself. Replaces any existing key."""
    if current_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    raw_key = f"sk-{secrets.token_urlsafe(32)}"
    result = await session.exec(select(User).where(User.id == current_user.id))
    user = result.first()
    user.hashed_api_key = User.hash_api_key(raw_key)
    session.add(user)
    await session.commit()

    logger.info("users.api_key_generated", user_id=user.id)
    return ApiKeyResponse(api_key=raw_key)


@router.delete("/api-keys", status_code=204)
async def revoke_api_key(current_user: CurrentUserDep, session: SessionDep):
    """Revoke your current API key."""
    if current_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    result = await session.exec(select(User).where(User.id == current_user.id))
    user = result.first()
    user.hashed_api_key = None
    session.add(user)
    await session.commit()
    logger.info("users.api_key_revoked", user_id=user.id)
