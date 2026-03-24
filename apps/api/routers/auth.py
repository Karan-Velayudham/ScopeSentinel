import os
import httpx
import structlog
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from sqlmodel import select
from db.models import User, Org, UserRole
from db.session import SessionDep

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

TENANT_MGMT_URL = os.environ.get("TENANT_MGMT_URL", "http://tenant-mgmt:8002")

class AuthSyncRequest(BaseModel):
    email: str
    name: str

@router.post("/sync")
async def auth_sync(body: AuthSyncRequest, session: SessionDep):
    """
    Synchronizes social login data with the local database.
    Creates a new Org and User if they don't exist.
    """
    # 1. Check if user already exists
    result = await session.exec(select(User).where(User.email == body.email))
    user = result.first()
    
    if user:
        logger.info("auth.sync_existing_user", email=body.email, user_id=user.id)
        return {"status": "ok", "user_id": user.id, "org_id": user.org_id, "new_user": False}

    # 2. User doesn't exist — trigger tenant creation
    logger.info("auth.sync_new_user", email=body.email)
    
    # Derive slug from email (e.g., karan-gmail-com)
    slug = body.email.replace("@", "-").replace(".", "-").lower()
    
    # 3. Call tenant-mgmt to create and provision Org
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                f"{TENANT_MGMT_URL}/tenants",
                json={
                    "name": f"{body.name}'s Org",
                    "slug": slug,
                    "tenant_config": {"llm_model": "gpt-4o"}
                },
                timeout=10.0
            )
            res.raise_for_status()
            tenant_data = res.json()
            org_id = tenant_data["id"]
    except Exception as e:
        logger.error("auth.tenant_creation_failed", email=body.email, error=str(e))
        # Fallback: if tenant-mgmt is down or fails, we might want to fail the sync
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to provision tenant"
        )

    # 4. Create User in API DB
    # Note: Even though tenant-mgmt and api share the DB, api needs its own User record.
    # The Org was created by tenant-mgmt in the 'orgs' table (shared).
    new_user = User(
        org_id=org_id,
        email=body.email,
        role=UserRole.ADMIN # First user is admin
    )
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    
    logger.info("auth.sync_complete", user_id=new_user.id, org_id=org_id)
    return {"status": "ok", "user_id": new_user.id, "org_id": org_id, "new_user": True}
