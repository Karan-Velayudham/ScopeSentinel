"""
tests/test_health.py — Tests for GET /api/health (Epic 1.2.7)
"""

import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_health_check_ok(client):
    """Health endpoint returns 200 with all services connected."""
    with (
        patch("routers.health.engine") as mock_engine,
        patch("routers.health.aioredis.from_url") as mock_redis_cls,
    ):
        # Mock successful DB ping
        mock_conn = AsyncMock()
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=False)
        mock_conn.execute = AsyncMock()
        mock_engine.connect.return_value = mock_conn

        # Mock successful Redis ping
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis.aclose = AsyncMock()
        mock_redis_cls.return_value = mock_redis

        response = await client.get("/api/health/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["postgres"] == "connected"
        assert data["redis"] == "connected"


@pytest.mark.asyncio
async def test_health_check_degraded_postgres(client):
    """Health returns degraded when PostgreSQL is unreachable."""
    with (
        patch("routers.health.engine") as mock_engine,
        patch("routers.health.aioredis.from_url") as mock_redis_cls,
    ):
        # Simulate DB connection failure
        mock_engine.connect.side_effect = Exception("connection refused")

        # Redis succeeds
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis.aclose = AsyncMock()
        mock_redis_cls.return_value = mock_redis

        response = await client.get("/api/health/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["postgres"] == "unreachable"
        assert data["redis"] == "connected"


@pytest.mark.asyncio
async def test_health_check_degraded_redis(client):
    """Health returns degraded when Redis is unreachable."""
    with (
        patch("routers.health.engine") as mock_engine,
        patch("routers.health.aioredis.from_url") as mock_redis_cls,
    ):
        mock_conn = AsyncMock()
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=False)
        mock_conn.execute = AsyncMock()
        mock_engine.connect.return_value = mock_conn

        # Redis fails
        mock_redis = AsyncMock()
        mock_redis.ping.side_effect = Exception("connection refused")
        mock_redis_cls.return_value = mock_redis

        response = await client.get("/api/health/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["redis"] == "unreachable"
