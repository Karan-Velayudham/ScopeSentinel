import base64
import json
import os
import httpx
import datetime
import urllib.parse
from fastapi import APIRouter, Query, Request, HTTPException
from fastapi.responses import RedirectResponse
import structlog
from core.registry import tool_registry
from adapters.factory import adapter_factory

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/connections/oauth", tags=["oauth"])

@router.get("/{provider}/authorize")
async def authorize(
    provider: str,
    org_id: str = Query(...),
    user_id: str = Query(...)
):
    try:
        adapter = adapter_factory.get_adapter(provider)
    except ValueError:
        raise HTTPException(status_code=400, detail="Provider not found")
    state_dict = {"org_id": org_id, "user_id": user_id, "provider": provider}
    state = base64.urlsafe_b64encode(json.dumps(state_dict).encode()).decode()
    
    redirect_uri = os.environ.get("OAUTH_CALLBACK_URL", "http://localhost:8005/api/connections/oauth/callback")
    url = await adapter.get_authorization_url(state, redirect_uri)
    return RedirectResponse(url)

@router.get("/callback")
async def callback(request: Request):
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    
    if not code or not state:
        raise HTTPException(400, "Missing code or state")
        
    try:
        state_dict = json.loads(base64.urlsafe_b64decode(state).decode())
        provider = state_dict["provider"]
        org_id = state_dict["org_id"]
        user_id = state_dict["user_id"]
        logger.info("oauth.callback_received", provider=provider, org_id=org_id, user_id=user_id)
    except Exception:
        raise HTTPException(400, "Invalid state format")
        
    try:
        adapter = adapter_factory.get_adapter(provider)
    except ValueError:
        raise HTTPException(400, "Invalid provider in state")
        
    redirect_uri = os.environ.get("OAUTH_CALLBACK_URL", "http://localhost:8005/api/connections/oauth/callback")
    
    try:
        token_data = await adapter.exchange_code(code, redirect_uri)
    except Exception as e:
        logger.error("oauth.exchange_failed", error=str(e))
        raise HTTPException(500, f"Token exchange failed: {e}")
        
    # Save token via api internal endpoint
    api_url = os.environ.get("API_URL", "http://localhost:8000")
    internal_save_url = f"{api_url}/api/oauth-connections/internal/save?org_id={urllib.parse.quote(org_id)}&user_id={urllib.parse.quote(user_id)}"
    
    expires_at = token_data.get("expires_at")
    if not expires_at:
        expires_at = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=token_data.get("expires_in", 3600))).isoformat()
        
    async with httpx.AsyncClient() as client:
        payload = {
            "provider": provider,
            "access_token": token_data["access_token"],
            "refresh_token": token_data.get("refresh_token", ""),
            "expires_at": expires_at,
            "scopes": json.dumps(token_data.get("scopes", [])),
            "provider_metadata": token_data.get("provider_metadata", "{}")
        }
        res = await client.post(internal_save_url, json=payload)
        res.raise_for_status()

    # Redirect back to frontend
    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
    return RedirectResponse(f"{frontend_url}/integrations?status=success&provider={provider}")
