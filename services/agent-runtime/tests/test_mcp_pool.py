"""
Unit tests for mcp_pool.load_client_pool()
"""
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, mock_open

import yaml

pytestmark = pytest.mark.asyncio

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_yaml(servers: dict) -> str:
    return yaml.dump({"mcp_servers": servers})


def _make_mock_client(tool_names: list[str]):
    """Return an AsyncMock that behaves like a connected StdIOStatefulClient."""
    client = AsyncMock()

    # list_tools() returns objects with a .name attribute
    tools = [MagicMock(name=t) for t in tool_names]
    # MagicMock(name=…) sets the mock's NAME not a .name attribute, so fix:
    for tool, tname in zip(tools, tool_names):
        tool.name = tname
    client.list_tools = AsyncMock(return_value=tools)

    # get_callable_function(tool_name) returns an AsyncMock coroutine
    async def _get_callable(tool_name):
        fn = AsyncMock(name=f"call_{tool_name}")
        return fn

    client.get_callable_function = AsyncMock(side_effect=_get_callable)
    return client


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

async def test_load_client_pool_single_server(tmp_path):
    """Single server: clients list has one entry, registry contains its tools."""
    config_file = tmp_path / "mcp_servers.yaml"
    config_file.write_text(_make_yaml({
        "my_server": {"command": "python", "args": ["server.py"], "env": {}}
    }))

    mock_client = _make_mock_client(["fetch_jira_ticket", "update_jira_ticket"])

    with patch("mcp_pool.StdIOStatefulClient", return_value=mock_client):
        from mcp_pool import load_client_pool
        clients, registry = await load_client_pool(str(config_file))

    assert len(clients) == 1
    assert clients[0] is mock_client
    mock_client.connect.assert_called_once()

    assert "fetch_jira_ticket" in registry
    assert "update_jira_ticket" in registry


async def test_load_client_pool_multiple_servers(tmp_path):
    """Two servers: pool has two clients and combined tool registry."""
    config_file = tmp_path / "mcp_servers.yaml"
    config_file.write_text(_make_yaml({
        "server_a": {"command": "python", "args": ["a.py"], "env": {}},
        "server_b": {"command": "python", "args": ["b.py"], "env": {}},
    }))

    client_a = _make_mock_client(["tool_alpha"])
    client_b = _make_mock_client(["tool_beta"])

    call_count = 0
    def _make_client(name, **kwargs):
        nonlocal call_count
        call_count += 1
        return client_a if call_count == 1 else client_b

    with patch("mcp_pool.StdIOStatefulClient", side_effect=_make_client):
        from mcp_pool import load_client_pool
        clients, registry = await load_client_pool(str(config_file))

    assert len(clients) == 2
    assert "tool_alpha" in registry
    assert "tool_beta" in registry


async def test_load_client_pool_env_substitution(tmp_path, monkeypatch):
    """${VAR} tokens in env dict are replaced with actual env var values."""
    monkeypatch.setenv("MY_SECRET", "supersecret")

    config_file = tmp_path / "mcp_servers.yaml"
    config_file.write_text(_make_yaml({
        "secret_server": {
            "command": "npx",
            "args": ["-y", "my-mcp"],
            "env": {"API_KEY": "${MY_SECRET}"}
        }
    }))

    captured_kwargs = {}
    mock_client = _make_mock_client([])

    def _make_client(name, **kwargs):
        captured_kwargs.update(kwargs)
        return mock_client

    with patch("mcp_pool.StdIOStatefulClient", side_effect=_make_client):
        from mcp_pool import load_client_pool
        await load_client_pool(str(config_file))

    # The resolved env should have been passed into the client constructor
    assert captured_kwargs.get("env", {}).get("API_KEY") == "supersecret"


async def test_load_client_pool_empty_config(tmp_path):
    """Empty mcp_servers block returns empty pool."""
    config_file = tmp_path / "mcp_servers.yaml"
    config_file.write_text("mcp_servers: {}\n")

    from mcp_pool import load_client_pool
    clients, registry = await load_client_pool(str(config_file))

    assert clients == []
    assert registry == {}


async def test_load_client_pool_missing_file():
    """FileNotFoundError raised for a non-existent config."""
    from mcp_pool import load_client_pool
    with pytest.raises(FileNotFoundError):
        await load_client_pool("/nonexistent/path/mcp_servers.yaml")
