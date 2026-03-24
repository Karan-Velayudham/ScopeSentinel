"""
db/seed.py — Seed the database with default org + admin user (Epic 1.1.3)

Called on FastAPI startup (idempotent — safe to run multiple times).
Creates:
  - Org(name="default", slug="default")
  - User(email="admin@scopesentinel.local", role=admin) with a fixed dev API key

The raw dev API key is: "dev-admin-api-key-1" — NEVER use this in production.
"""

import os

import structlog
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from db.models import HitlAction, Org, RunStatus, User, UserRole  # noqa: F401

logger = structlog.get_logger(__name__)

_DEFAULT_ORG_NAME = "default"
_DEFAULT_ORG_SLUG = "default"
_ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@scopesentinel.local")
_ADMIN_RAW_API_KEY = os.environ.get("ADMIN_API_KEY", "dev-admin-api-key-1")


async def run_seed(session: AsyncSession) -> None:
    """Create the default org and admin user if they don't already exist."""
    log = logger.bind(step="seed")

    # --- Org ---
    result = await session.exec(select(Org).where(Org.slug == _DEFAULT_ORG_SLUG))
    org = result.first()
    if not org:
        org = Org(name=_DEFAULT_ORG_NAME, slug=_DEFAULT_ORG_SLUG)
        session.add(org)
        await session.commit()
        await session.refresh(org)
        log.info("seed.org_created", org_id=org.id)
    else:
        log.info("seed.org_exists", org_id=org.id)

    # --- Admin user ---
    result = await session.exec(select(User).where(User.email == _ADMIN_EMAIL))
    user = result.first()
    if not user:
        user = User(
            org_id=org.id,
            email=_ADMIN_EMAIL,
            role=UserRole.ADMIN,
            hashed_api_key=User.hash_api_key(_ADMIN_RAW_API_KEY),
        )
        session.add(user)
        await session.commit()
        log.info("seed.admin_user_created", email=_ADMIN_EMAIL)
        log.warning(
            "seed.dev_api_key",
            message="Default dev API key active — override ADMIN_API_KEY in production!",
            key=_ADMIN_RAW_API_KEY,
        )
    else:
        log.info("seed.admin_user_exists", email=_ADMIN_EMAIL)
