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
from db.session import SessionDep
from schemas import (
    ConnectorInfo,
    ConnectorInfoExtended,
    ConnectorTool,
    ConnectorInstallRequest,
    InstalledConnectorResponse,
    InstalledConnectorDetailResponse,
    OAuthInitResponse,
)
import httpx

ADAPTER_SERVICE_URL = os.getenv("ADAPTER_SERVICE_URL", "http://localhost:8005")

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/connectors", tags=["connectors"])

# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------

@router.get("/available", response_model=list[ConnectorInfoExtended])
async def list_available_connectors(current_user: CurrentUserDep):
    """Returns the full catalog from adapter-service."""
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(f"{ADAPTER_SERVICE_URL}/api/connectors/catalog")
            res.raise_for_status()
            catalog = res.json()
            
            result = []
            for item in catalog:
                result.append(ConnectorInfoExtended(
                    id=item["id"],
                    name=item["name"],
                    description=item["description"],
                    category=item["category"],
                    icon_url=item["icon_url"],
                    auth_type=item.get("auth_type", "none"),
                    tools=[],
                    oauth_scopes=[], # Scopes can be fetched if needed, or kept simple
                    api_key_fields=[],
                ))
            return result
    except Exception as e:
        logger.error("connectors.list_available_failed", error=str(e))
        return []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _map_mcp_schema_to_inputs(input_schema: dict) -> list[dict]:
    """Map MCP JSON schema properties to frontend ToolInputField format."""
    if not input_schema:
        return []
    properties = input_schema.get("properties", {})
    required_fields = set(input_schema.get("required", []))
    inputs = []
    for prop_name, prop_data in properties.items():
        if not isinstance(prop_data, dict):
            continue
        inputs.append({
            "name": prop_name,
            "type": prop_data.get("type", "string"),
            "description": prop_data.get("description", ""),
            "required": prop_name in required_fields,
            "default": prop_data.get("default", None)
        })
    return inputs


# ---------------------------------------------------------------------------
# Installed connectors with enriched detail
# ---------------------------------------------------------------------------

@router.get("/installed", response_model=list[InstalledConnectorDetailResponse])
async def list_installed_connectors(
    session: SessionDep,
    current_user: CurrentUserDep,
    request: Request,
):
    """Returns connectors installed by the current org, enriched with DYNAMIC tools."""
    org_id = getattr(request.state, "org_id", None) or current_user.org_id
    stmt = select(InstalledConnector).where(InstalledConnector.org_id == org_id)
    items = (await session.exec(stmt)).all()

    # 1. Fetch the absolute catalog from adapter-service to get metadata (names, icons)
    catalog_map = {}
    try:
        async with httpx.AsyncClient() as client:
            cat_res = await client.get(f"{ADAPTER_SERVICE_URL}/api/connectors/catalog")
            if cat_res.is_success:
                for c in cat_res.json():
                    catalog_map[c["id"]] = c
    except Exception:
        pass

    # 2. Fetch discovered tools from adapter-service
    tools_by_provider = {}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            tools_res = await client.get(f"{ADAPTER_SERVICE_URL}/api/tools?org_id={org_id}")
            if tools_res.is_success:
                all_discovered = tools_res.json().get("tools", [])
                for t in all_discovered:
                    # In adapter-service, tools are named "provider.tool_name"
                    if "." in t["name"]:
                        provider, tool_name = t["name"].split(".", 1)
                        if provider not in tools_by_provider:
                            tools_by_provider[provider] = []
                        
                        # Map internal ToolSchema to ConnectorTool
                        mapped_inputs = _map_mcp_schema_to_inputs(t.get("input_schema", {}))
                        tools_by_provider[provider].append(ConnectorTool(
                            name=tool_name,
                            description=t.get("description", ""),
                            inputs=mapped_inputs
                        ))
    except Exception as e:
        logger.error("connectors.fetch_dynamic_tools_failed", error=str(e))

    result = []
    for item in items:
        meta = catalog_map.get(item.connector_id, {})
        connector_tools = tools_by_provider.get(item.connector_id, [])
        
        result.append(InstalledConnectorDetailResponse(
            id=item.id,
            connector_id=item.connector_id,
            connector_name=meta.get("name", item.connector_id.capitalize()),
            icon_url=meta.get("icon_url", ""),
            auth_type=meta.get("auth_type", "none"),
            is_active=item.is_active,
            tools=connector_tools,
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
    request: Request,
):
    """Returns the list of dynamic MCP tools exposed by a connector."""
    org_id = getattr(request.state, "org_id", None) or current_user.org_id
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            tools_res = await client.get(f"{ADAPTER_SERVICE_URL}/api/tools?org_id={org_id}")
            if tools_res.is_success:
                all_tools = tools_res.json().get("tools", [])
                connector_tools = [
                    ConnectorTool(
                        name=t["name"].split(".", 1)[1] if "." in t["name"] else t["name"],
                        description=t.get("description", ""),
                        inputs=_map_mcp_schema_to_inputs(t.get("input_schema", {}))
                    )
                    for t in all_tools 
                    if t["name"].startswith(f"{connector_id}.")
                ]
                return connector_tools
    except Exception:
        pass
    return []


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
    Initiates an OAuth 2.0 PKCE flow.
    M-5 Fix: Dynamically handles Jira via adapter-service proxy.
    """
    # Jira is special as it's our first full MCP integration
    if connector_id == "jira":
        client_id = os.getenv("JIRA_CLIENT_ID", "")
        if not client_id:
            raise HTTPException(status_code=503, detail="JIRA_CLIENT_ID not set")
        
        state = secrets.token_urlsafe(32)
        base_url = os.getenv("API_BASE_URL", str(request.base_url).rstrip("/"))
        callback_url = f"{base_url}/api/connectors/oauth/callback"
        org_id = getattr(request.state, "org_id", None) or current_user.org_id
        
        # Hardcoding the Jira OAuth URL for now purely as the gatekeeper, 
        # but the discovery will be dynamic.
        import urllib.parse
        scopes = "read:jira-work write:jira-work read:jira-user offline_access"
        authorization_url = (
            f"https://auth.atlassian.com/authorize"
            f"?audience=api.atlassian.com"
            f"&client_id={urllib.parse.quote(client_id)}"
            f"&scope={urllib.parse.quote(scopes)}"
            f"&redirect_uri={urllib.parse.quote(callback_url)}"
            f"&state={urllib.parse.quote(f'{state}___{connector_id}___{org_id}')}"
            f"&response_type=code"
            f"&prompt=consent"
        )
        return OAuthInitResponse(
            authorization_url=authorization_url,
            state=state,
            connector_id=connector_id,
        )

    raise HTTPException(status_code=400, detail="Only Jira OAuth is currently supported in dynamic mode.")


@router.get("/oauth/callback")
async def oauth_callback(
    code: str,
    state: str,
    session: SessionDep,
):
    """
    OAuth callback — exchanges authorization code for access token.
    Stores credentials in public.oauth_connections.
    """
    try:
        parts = state.split("___")
        if len(parts) != 3:
            raise ValueError("Invalid state format")
        _, connector_id, org_id = parts
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid OAuth state parameter")

    # Manually set search path for this session
    from sqlalchemy import text
    safe_org_id = org_id.replace("-", "_")
    await session.execute(text(f"SET search_path TO public, tenant_{safe_org_id}"))

    # Jira uses the adapter-service to exchange tokens
    if connector_id == "jira":
        # we still create the entry in InstalledConnector to mark it active
        stmt = select(InstalledConnector).where(
            InstalledConnector.org_id == org_id,
            InstalledConnector.connector_id == connector_id,
        )
        existing = (await session.exec(stmt)).first()
        if not existing:
            new_connector = InstalledConnector(
                org_id=org_id,
                connector_id=connector_id,
                config_json=json.dumps({"status": "oauth_initiated"}),
                is_active=True
            )
            session.add(new_connector)
            await session.commit()
    
    # The actual token exchange and storage happens in the adapter-service or via our hook
    # For now, we redirect to a special frontend route that will trigger the adapter-service discovery
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    return RedirectResponse(
        url=f"{frontend_url}/integrations/callback?connector_id={connector_id}&status=connected&code={code}&org_id={org_id}",
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
    session: SessionDep,
    current_user: CurrentUserDep,
    request: Request,
):
    """Install a connector using API key credentials."""
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


@router.delete("/{connector_id}", status_code=status.HTTP_204_NO_CONTENT)
@router.delete("/{connector_id}/uninstall", status_code=status.HTTP_204_NO_CONTENT)
async def uninstall_connector(
    connector_id: str,
    session: SessionDep,
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
    
    # Also check if there's an OAuth connection to remove
    from db.models import OAuthConnection
    from db.session import SessionDep
    
    # We need a plain SessionDep for OAuthConnection if it's in public schema,
    # but TenantSessionDep is already scoped. Assuming OAuth is in the same schema or accessible.
    oauth_stmt = select(OAuthConnection).where(
        OAuthConnection.org_id == org_id,
        OAuthConnection.provider == connector_id
    )
    # Note: TenantSessionDep is an AsyncSession, we can use it.
    oauth_conn = (await session.exec(oauth_stmt)).first()
    if oauth_conn:
        await session.delete(oauth_conn)

    if existing:
        await session.delete(existing)
    
    if not existing and not oauth_conn:
        # If neither exists, still return 204 to be idempotent
        return

    await session.commit()
    logger.info("connector.uninstalled", connector_id=connector_id, org_id=org_id)
