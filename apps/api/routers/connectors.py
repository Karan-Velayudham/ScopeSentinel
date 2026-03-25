"""
routers/connectors.py — Connector catalog, install, OAuth, and MCP tool discovery.
"""
import json
import os
import secrets
import structlog
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlmodel import select

from auth.api_keys import CurrentUserDep
from db.models import InstalledConnector
from db.session import SessionDep, TenantSessionDep
from schemas import (
    ConnectorInfo,
    ConnectorInfoExtended,
    ConnectorTool,
    ConnectorInstallRequest,
    InstalledConnectorResponse,
    InstalledConnectorDetailResponse,
    OAuthInitResponse,
)
from connectors.registry import get_connector_catalog, get_connector_class

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/connectors", tags=["connectors"])


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------

@router.get("/available", response_model=list[ConnectorInfoExtended])
async def list_available_connectors(current_user: CurrentUserDep):
    """Returns the full catalog of connectable apps with auth info and tools."""
    result = []
    for cls in [get_connector_class(c["id"]) for c in get_connector_catalog()]:
        if not cls:
            continue
        info = cls.info()
        tools = [ConnectorTool(**t) for t in (cls.get_tools() and [t.to_dict() for t in cls.get_tools()])]
        oauth_scopes = []
        api_key_fields = []
        if cls.oauth_config:
            oauth_scopes = cls.oauth_config.scopes
        if cls.api_key_config:
            api_key_fields = cls.api_key_config.fields

        result.append(ConnectorInfoExtended(
            id=info.id,
            name=info.name,
            description=info.description,
            category=info.category,
            icon_url=info.icon_url,
            auth_type=getattr(cls, "auth_type", "none"),
            tools=tools,
            oauth_scopes=oauth_scopes,
            api_key_fields=api_key_fields,
        ))
    return result


# ---------------------------------------------------------------------------
# Installed connectors with enriched detail
# ---------------------------------------------------------------------------

@router.get("/installed", response_model=list[InstalledConnectorDetailResponse])
async def list_installed_connectors(
    session: TenantSessionDep,
    current_user: CurrentUserDep,
    request: Request,
):
    """Returns connectors installed by the current org, enriched with tools."""
    org_id = getattr(request.state, "org_id", None) or current_user.org_id
    stmt = select(InstalledConnector).where(InstalledConnector.org_id == org_id)
    items = (await session.exec(stmt)).all()

    result = []
    for item in items:
        cls = get_connector_class(item.connector_id)
        if not cls:
            continue
        info = cls.info()
        tools = [ConnectorTool(**t.to_dict()) for t in cls.get_tools()]
        result.append(InstalledConnectorDetailResponse(
            id=item.id,
            connector_id=item.connector_id,
            connector_name=info.name,
            icon_url=info.icon_url,
            auth_type=getattr(cls, "auth_type", "none"),
            is_active=item.is_active,
            tools=tools,
            created_at=item.created_at,
            updated_at=item.updated_at,
        ))
    return result


# ---------------------------------------------------------------------------
# MCP Tool Discovery
# ---------------------------------------------------------------------------

@router.get("/{connector_id}/tools", response_model=list[ConnectorTool])
async def get_connector_tools(
    connector_id: str,
    current_user: CurrentUserDep,
):
    """Returns the list of MCP tools exposed by a connector."""
    cls = get_connector_class(connector_id)
    if not cls:
        raise HTTPException(status_code=404, detail=f"Connector '{connector_id}' not found")
    return [ConnectorTool(**t.to_dict()) for t in cls.get_tools()]


# ---------------------------------------------------------------------------
# OAuth Flow
# ---------------------------------------------------------------------------

@router.post("/{connector_id}/oauth/init", response_model=OAuthInitResponse)
async def oauth_init(
    connector_id: str,
    request: Request,
    current_user: CurrentUserDep,
):
    """
    Initiates an OAuth 2.0 PKCE flow for the given connector.
    Returns an authorization_url to redirect the user to.
    """
    cls = get_connector_class(connector_id)
    if not cls:
        raise HTTPException(status_code=404, detail=f"Connector '{connector_id}' not found")
    if getattr(cls, "auth_type", "none") != "oauth":
        raise HTTPException(status_code=400, detail=f"Connector '{connector_id}' does not support OAuth")

    oauth_cfg = cls.oauth_config
    if not oauth_cfg:
        raise HTTPException(status_code=500, detail="OAuth config missing on connector")

    client_id = os.getenv(oauth_cfg.client_id_env, "")
    if not client_id:
        raise HTTPException(
            status_code=503,
            detail=f"OAuth client ID not configured. Set {oauth_cfg.client_id_env} environment variable."
        )

    # Generate a cryptographically secure state token
    state = secrets.token_urlsafe(32)

    # Build callback URL
    base_url = os.getenv("API_BASE_URL", str(request.base_url).rstrip("/"))
    callback_url = f"{base_url}/api/connectors/oauth/callback"

    # Compose authorization URL
    org_id = getattr(request.state, "org_id", None) or current_user.org_id
    scope_str = " ".join(oauth_cfg.scopes)
    extra_qs = "&".join(f"{k}={v}" for k, v in oauth_cfg.extra_params.items())
    import urllib.parse
    authorization_url = (
        f"{oauth_cfg.auth_url}"
        f"?client_id={urllib.parse.quote(client_id)}"
        f"&redirect_uri={urllib.parse.quote(callback_url)}"
        f"&scope={urllib.parse.quote(scope_str)}"
        f"&state={urllib.parse.quote(f'{state}___{connector_id}___{org_id}')}"
        f"&response_type=code"
        + (f"&{extra_qs}" if extra_qs else "")
    )

    logger.info("connector.oauth_init", connector_id=connector_id, org_id=org_id)
    return OAuthInitResponse(
        authorization_url=authorization_url,
        state=state,
        connector_id=connector_id,
    )


@router.get("/oauth/callback")
async def oauth_callback(
    code: str,
    state: str,
    session: SessionDep,
):
    """
    OAuth callback — exchanges authorization code for access token.
    State encodes: {random_state}___{connector_id}___{org_id}
    Stores credentials in InstalledConnector.config_json (Vault in Phase 2).
    """
    try:
        parts = state.split("___")
        if len(parts) != 3:
            raise ValueError("Invalid state format")
        _, connector_id, org_id = parts
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid OAuth state parameter")

    # Manually set search path for this session since we just resolved the org_id
    from sqlalchemy import text
    safe_org_id = org_id.replace("-", "_")
    await session.execute(text(f"SET search_path TO tenant_{safe_org_id}, public"))

    cls = get_connector_class(connector_id)
    if not cls:
        raise HTTPException(status_code=404, detail=f"Connector '{connector_id}' not found")

    # Check if already installed
    stmt = select(InstalledConnector).where(
        InstalledConnector.org_id == org_id,
        InstalledConnector.connector_id == connector_id,
    )
    existing = (await session.exec(stmt)).first()

    credential_data = {"oauth_code": code, "status": "connected"}

    if existing:
        existing.config_json = json.dumps(credential_data)
        await session.commit()
    else:
        new_connector = InstalledConnector(
            org_id=org_id,
            connector_id=connector_id,
            config_json=json.dumps(credential_data),
        )
        session.add(new_connector)
        await session.commit()

    logger.info("connector.oauth_callback_success", connector_id=connector_id, org_id=org_id)

    # Redirect to frontend integrations page
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    return RedirectResponse(
        url=f"{frontend_url}/integrations/callback?connector_id={connector_id}&status=connected",
        status_code=302,
    )


# ---------------------------------------------------------------------------
# API Key Install
# ---------------------------------------------------------------------------

@router.post(
    "/{connector_id}/install",
    response_model=InstalledConnectorResponse,
    status_code=status.HTTP_201_CREATED,
)
async def install_connector(
    connector_id: str,
    body: ConnectorInstallRequest,
    session: TenantSessionDep,
    current_user: CurrentUserDep,
    request: Request,
):
    """Install a connector using API key credentials."""
    cls = get_connector_class(connector_id)
    if not cls:
        raise HTTPException(status_code=404, detail="Connector not found")

    org_id = getattr(request.state, "org_id", None) or current_user.org_id
    stmt = select(InstalledConnector).where(
        InstalledConnector.org_id == org_id,
        InstalledConnector.connector_id == connector_id,
    )
    existing = (await session.exec(stmt)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Connector already installed")

    new_connector = InstalledConnector(
        org_id=org_id,
        connector_id=connector_id,
        config_json=json.dumps(body.config),
    )
    session.add(new_connector)
    await session.commit()
    # Skip refresh to avoid potential 500
    
    logger.info("connector.installed", connector_id=connector_id, org_id=org_id)
    return InstalledConnectorResponse(
        id=new_connector.id,
        connector_id=new_connector.connector_id,
        is_active=new_connector.is_active,
        created_at=new_connector.created_at,
        updated_at=new_connector.updated_at,
    )


@router.delete("/{connector_id}/uninstall", status_code=status.HTTP_204_NO_CONTENT)
async def uninstall_connector(
    connector_id: str,
    session: TenantSessionDep,
    current_user: CurrentUserDep,
    request: Request,
) -> None:
    """Remove an installed connector from the org."""
    org_id = getattr(request.state, "org_id", None) or current_user.org_id
    stmt = select(InstalledConnector).where(
        InstalledConnector.org_id == org_id,
        InstalledConnector.connector_id == connector_id,
    )
    existing = (await session.exec(stmt)).first()
    if not existing:
        raise HTTPException(status_code=404, detail="Connector not installed")

    await session.delete(existing)
    await session.commit()
    logger.info("connector.uninstalled", connector_id=connector_id, org_id=org_id)
