import structlog
from typing import Annotated, List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import select

from auth.api_keys import CurrentUserDep
from db.models import OAuthConnection
from db.session import SessionDep
from schemas import (
    OAuthConnectionResponse,
    OAuthConnectionCreate
)
from auth.crypto import encrypt_token, decrypt_token

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/oauth-connections", tags=["oauth-connections"])

def _conn_to_response(conn: OAuthConnection) -> OAuthConnectionResponse:
    return OAuthConnectionResponse(
        id=conn.id,
        org_id=conn.org_id,
        user_id=conn.user_id,
        provider=conn.provider,
        expires_at=conn.expires_at,
        scopes=conn.scopes,
        created_at=conn.created_at,
        updated_at=conn.updated_at,
    )

@router.get("/", response_model=List[OAuthConnectionResponse])
async def list_connections(
    session: SessionDep,
    current_user: CurrentUserDep,
) -> List[OAuthConnectionResponse]:
    query = select(OAuthConnection).where(OAuthConnection.org_id == current_user.org_id)
    conns = (await session.exec(query)).all()
    return [_conn_to_response(c) for c in conns]

@router.post("/", response_model=OAuthConnectionResponse, status_code=status.HTTP_201_CREATED)
async def upsert_connection(
    body: OAuthConnectionCreate,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> OAuthConnectionResponse:
    """Creates or updates an OAuth connection for the user & provider."""
    query = select(OAuthConnection).where(
        OAuthConnection.org_id == current_user.org_id,
        OAuthConnection.user_id == current_user.id,
        OAuthConnection.provider == body.provider
    )
    existing = (await session.exec(query)).first()
    
    enc_access = encrypt_token(body.access_token)
    enc_refresh = encrypt_token(body.refresh_token)

    if existing:
        existing.access_token_encrypted = enc_access
        existing.refresh_token_encrypted = enc_refresh
        existing.expires_at = body.expires_at
        existing.scopes = body.scopes
        existing.updated_at = datetime.now(timezone.utc)
        session.add(existing)
        await session.commit()
        await session.refresh(existing)
        logger.info("api.oauth_connection_updated", provider=body.provider, user=current_user.id)
        return _conn_to_response(existing)
    else:
        new_conn = OAuthConnection(
            org_id=current_user.org_id,
            user_id=current_user.id,
            provider=body.provider,
            access_token_encrypted=enc_access,
            refresh_token_encrypted=enc_refresh,
            expires_at=body.expires_at,
            scopes=body.scopes,
        )
        session.add(new_conn)
        await session.commit()
        await session.refresh(new_conn)
        logger.info("api.oauth_connection_created", provider=body.provider, user=current_user.id)
        return _conn_to_response(new_conn)

@router.get("/{provider}/token")
async def get_connection_token(
    provider: str,
    session: SessionDep,
    current_user: CurrentUserDep,
):
    query = select(OAuthConnection).where(
        OAuthConnection.org_id == current_user.org_id,
        OAuthConnection.provider == provider
    )
    conn = (await session.exec(query)).first()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
        
    return {
        "access_token": decrypt_token(conn.access_token_encrypted),
        "refresh_token": decrypt_token(conn.refresh_token_encrypted),
        "expires_at": conn.expires_at,
        "scopes": conn.scopes
    }

@router.delete("/{provider}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_connection(
    provider: str,
    session: SessionDep,
    current_user: CurrentUserDep,
):
    query = select(OAuthConnection).where(
        OAuthConnection.org_id == current_user.org_id,
        OAuthConnection.user_id == current_user.id,
        OAuthConnection.provider == provider
    )
    conn = (await session.exec(query)).first()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
        
    await session.delete(conn)
    await session.commit()
    logger.info("api.oauth_connection_deleted", provider=provider, user=current_user.id)

@router.post("/internal/save")
async def internal_save_connection(
    body: OAuthConnectionCreate,
    session: SessionDep,
    org_id: str = Query(...),
    user_id: str = Query(...)
):
    """Internal endpoint for adapter-service to save a token."""
    query = select(OAuthConnection).where(
        OAuthConnection.org_id == org_id,
        OAuthConnection.user_id == user_id,
        OAuthConnection.provider == body.provider
    )
    existing = (await session.exec(query)).first()
    
    enc_access = encrypt_token(body.access_token)
    enc_refresh = encrypt_token(body.refresh_token)

    if existing:
        existing.access_token_encrypted = enc_access
        existing.refresh_token_encrypted = enc_refresh
        existing.expires_at = body.expires_at
        existing.scopes = body.scopes
        existing.updated_at = datetime.now(timezone.utc)
        session.add(existing)
        await session.commit()
    else:
        new_conn = OAuthConnection(
            org_id=org_id,
            user_id=user_id,
            provider=body.provider,
            access_token_encrypted=enc_access,
            refresh_token_encrypted=enc_refresh,
            expires_at=body.expires_at,
            scopes=body.scopes,
        )
        session.add(new_conn)
        await session.commit()
    return {"status": "ok"}

@router.get("/internal/{provider}/token")
async def internal_get_connection_token(
    provider: str,
    org_id: str,
    session: SessionDep,
):
    """Internal endpoint for adapter-service to fetch an active token."""
    query = select(OAuthConnection).where(
        OAuthConnection.org_id == org_id,
        OAuthConnection.provider == provider
    )
    # Get the latest or first connection for this org/provider
    conn = (await session.exec(query)).first()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
        
    return {
        "access_token": decrypt_token(conn.access_token_encrypted),
        "refresh_token": decrypt_token(conn.refresh_token_encrypted),
        "expires_at": conn.expires_at,
        "scopes": conn.scopes
    }


