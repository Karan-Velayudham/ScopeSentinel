import json
import structlog
from fastapi import APIRouter, HTTPException, status
from sqlmodel import select

from auth.api_keys import CurrentUserDep
from db.models import InstalledConnector
from db.session import SessionDep
from schemas import (
    ConnectorInfo,
    ConnectorInstallRequest,
    InstalledConnectorResponse,
)
from connectors.registry import get_connector_catalog, get_connector_class

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/connectors", tags=["connectors"])


@router.get("/available", response_model=list[ConnectorInfo])
async def list_available_connectors(current_user: CurrentUserDep):
    """Returns the static catalog of connectable apps."""
    return get_connector_catalog()


@router.get("/installed", response_model=list[InstalledConnectorResponse])
async def list_installed_connectors(
    session: SessionDep,
    current_user: CurrentUserDep,
):
    """Returns connectors installed by the current org."""
    stmt = select(InstalledConnector).where(InstalledConnector.org_id == current_user.org_id)
    items = (await session.exec(stmt)).all()  # FIX C-2: added await

    return [
        InstalledConnectorResponse(
            id=item.id,
            connector_id=item.connector_id,
            is_active=item.is_active,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
        for item in items
    ]


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
):
    """Mocks an OAuth install by persisting config into DB."""
    cls = get_connector_class(connector_id)
    if not cls:
        raise HTTPException(status_code=404, detail="Connector not found")

    stmt = select(InstalledConnector).where(
        InstalledConnector.org_id == current_user.org_id,
        InstalledConnector.connector_id == connector_id,
    )
    existing = (await session.exec(stmt)).first()  # FIX C-2: added await
    if existing:
        raise HTTPException(status_code=400, detail="Connector already installed")

    new_connector = InstalledConnector(
        org_id=current_user.org_id,
        connector_id=connector_id,
        config_json=json.dumps(body.config),
    )
    session.add(new_connector)
    await session.commit()
    await session.refresh(new_connector)

    logger.info("connector.installed", connector_id=connector_id, org_id=current_user.org_id)
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
    session: SessionDep,
    current_user: CurrentUserDep,
) -> None:
    """FIX M-6: Removes an installed connector from the org."""
    stmt = select(InstalledConnector).where(
        InstalledConnector.org_id == current_user.org_id,
        InstalledConnector.connector_id == connector_id,
    )
    existing = (await session.exec(stmt)).first()
    if not existing:
        raise HTTPException(status_code=404, detail="Connector not installed")

    await session.delete(existing)
    await session.commit()
    logger.info("connector.uninstalled", connector_id=connector_id, org_id=current_user.org_id)
