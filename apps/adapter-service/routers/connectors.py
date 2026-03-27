from fastapi import APIRouter
from adapters.factory import adapter_factory
from typing import List, Dict, Any

router = APIRouter(prefix="/api/connectors", tags=["connectors"])

@router.get("/catalog", response_model=List[Dict[str, Any]])
async def get_connector_catalog():
    """Returns metadata for all supported connectors/adapters."""
    return adapter_factory.get_all_adapters_info()
