import pytest
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException
from core.router import ToolRouter

pytestmark = pytest.mark.asyncio

@patch("core.router.connection_manager")
async def test_router_execution(mock_cm):
    router = ToolRouter()
    
    mock_client = AsyncMock()
    mock_callable = AsyncMock()
    mock_callable.return_value = "Success"
    mock_client.get_callable_function.return_value = mock_callable
    
    mock_cm.get_client.return_value = mock_client
    
    result = await router.execute_tool("test_server", "test_tool", {"arg1": "val1"})
    
    assert result == "Success"
    mock_cm.get_client.assert_called_once_with("test_server")
    mock_client.get_callable_function.assert_called_once_with("test_tool")
    mock_callable.assert_called_once_with(arg1="val1")

@patch("core.router.connection_manager")
async def test_router_execution_server_not_found(mock_cm):
    router = ToolRouter()
    mock_cm.get_client.return_value = None
    
    with pytest.raises(HTTPException) as exc:
        await router.execute_tool("missing_server", "test_tool", {})
        
    assert exc.value.status_code == 404
