"""
tests/test_auth.py — Tests for the API key authentication dependency (Epic 1.4.3)
"""

import pytest
from httpx import ASGITransport, AsyncClient

from db.session import get_session
from main import app


@pytest.mark.asyncio
async def test_auth_missing_header(client):
    """Missing X-Api-Key header returns 401."""
    response = await client.get("/api/runs/")
    assert response.status_code == 401
    assert "missing API key" in response.json()["detail"]


@pytest.mark.asyncio
async def test_auth_invalid_header(client):
    """Invalid X-Api-Key header returns 401."""
    response = await client.get("/api/runs/", headers={"X-Api-Key": "invalid-key"})
    assert response.status_code == 401
    assert "Invalid or missing" in response.json()["detail"]


@pytest.mark.asyncio
async def test_auth_valid_header(client, test_user):
    """Valid X-Api-Key header succeeds."""
    user, raw_key = test_user
    # Endpoint returns 200, proving auth succeeded
    response = await client.get("/api/runs/", headers={"X-Api-Key": raw_key})
    assert response.status_code == 200
