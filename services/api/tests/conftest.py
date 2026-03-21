"""
tests/conftest.py — Shared fixtures for the ScopeSentinel API tests
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from db.models import Org, User, UserRole
from db.session import get_session
from main import app


# ---------------------------------------------------------------------------
# In-memory SQLite engine for tests (no real PostgreSQL needed)
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_session(test_engine):
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def test_org(test_session) -> Org:
    """A default test organisation."""
    org = Org(name="Test Org", slug="test-org")
    test_session.add(org)
    await test_session.commit()
    await test_session.refresh(org)
    return org


@pytest_asyncio.fixture(scope="function")
async def test_user(test_session, test_org) -> tuple[User, str]:
    """A test admin user with a raw API key. Returns (user, raw_key)."""
    raw_key = "test-api-key-abc123"
    user = User(
        org_id=test_org.id,
        email="testadmin@scopesentinel.local",
        role=UserRole.ADMIN,
        hashed_api_key=User.hash_api_key(raw_key),
    )
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)
    return user, raw_key


@pytest_asyncio.fixture(scope="function")
async def client(test_session):
    """AsyncClient with DB overridden to the in-memory test session."""
    async def _override_session():
        yield test_session

    app.dependency_overrides[get_session] = _override_session
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()
