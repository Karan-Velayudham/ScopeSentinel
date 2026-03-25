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
    
    # 2. Derive slug from email (e.g., karan-gmail-com)
    slug = body.email.replace("@", "-").replace(".", "-").lower()

    if user:
        # Check if org is active
        org_result = await session.exec(select(Org).where(Org.id == user.org_id))
        org = org_result.first()
        
        if org and org.status == "ACTIVE":
            logger.info("auth.sync_existing_user_active", email=body.email, org_id=org.id)
            return {"status": "ok", "user_id": user.id, "org_id": user.org_id, "new_user": False}
        
        logger.info("auth.sync_existing_user_inactive", email=body.email, org_id=user.org_id, status=org.status if org else "missing")
        # Proceed to trigger/retry provisioning

    # 3. Trigger/Retry tenant creation
    logger.info("auth.trigger_provisioning", email=body.email)
    
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
            # 201 Created or 200 OK or 409 if already active (but we checked)
            if res.status_code not in [200, 201, 202]:
                res.raise_for_status()
            
            tenant_data = res.json()
            org_id = tenant_data["id"]
    except Exception as e:
        logger.error("auth.tenant_creation_failed", email=body.email, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to provision tenant"
        )

    if not user:
        # 4. Create User in API DB
        user = User(
            org_id=org_id,
            email=body.email,
            role=UserRole.ADMIN
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        logger.info("auth.sync_new_user_complete", user_id=user.id, org_id=org_id)
        return {"status": "ok", "user_id": user.id, "org_id": org_id, "new_user": True}
    
    logger.info("auth.sync_existing_user_retry_complete", user_id=user.id, org_id=org_id)
    return {"status": "ok", "user_id": user.id, "org_id": org_id, "new_user": False}
