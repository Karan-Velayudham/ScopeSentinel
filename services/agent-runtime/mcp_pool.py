"""
mcp_pool — Dynamic MCP Server Registry (Story 7.2)

Reads mcp_servers.yaml to build a pool of StdIOStatefulClient connections
and a flat `tool_registry` mapping tool names to their async callables.

Usage:
    clients, tool_registry = await load_client_pool("mcp_servers.yaml")
    try:
        result = await tool_registry["fetch_jira_ticket"](ticket_id="SCRUM-1")
    finally:
        for client in clients:
            await client.close()
"""

import os
import re
from typing import Any, Callable

import yaml
import structlog
from agentscope.mcp import StdIOStatefulClient

from exceptions import MCPConnectionError, MCPToolCallError

logger = structlog.get_logger(__name__)

# Matches ${SOME_VAR} in YAML values
_ENV_VAR_PATTERN = re.compile(r"\$\{([^}]+)\}")


def _substitute_env_vars(value: str) -> str:
    """Replace ${VAR} tokens in a string with the corresponding env var value."""

    def _replace(match: re.Match) -> str:
        var_name = match.group(1)
        result = os.environ.get(var_name, "")
        if not result:
            logger.warning("mcp_pool.env_var_missing", var=var_name)
        return result

    return _ENV_VAR_PATTERN.sub(_replace, value)


def _resolve_env(raw_env: dict[str, str]) -> dict[str, str]:
    """Resolve all env-var substitutions in an env dict."""
    return {k: _substitute_env_vars(v) for k, v in (raw_env or {}).items()}


async def load_client_pool(
    config_path: str = "mcp_servers.yaml",
) -> tuple[list[StdIOStatefulClient], dict[str, Callable[..., Any]]]:
    """
    Load the MCP server registry from *config_path*, connect each server,
    and return a pool of live clients plus a flat tool_registry.

    Args:
        config_path: Path to the YAML registry file (relative to cwd or absolute).

    Returns:
        clients      -- ordered list of connected StdIOStatefulClient instances.
                        Callers are responsible for closing them when done.
        tool_registry -- flat dict mapping ``tool_name → async callable``.
                        If two servers expose the same tool name, the last one wins
                        (a warning is logged).

    Raises:
        FileNotFoundError: if *config_path* does not exist.
        KeyError:          if a server entry is missing ``command``.
        MCPConnectionError: if a server fails to establish a connection.
    """
    with open(config_path, "r") as fh:
        config = yaml.safe_load(fh)

    servers: dict[str, dict] = config.get("mcp_servers", {})
    if not servers:
        logger.warning("mcp_pool.no_servers_found", config=config_path)
        return [], {}

    clients: list[StdIOStatefulClient] = []
    tool_registry: dict[str, Callable[..., Any]] = {}

    for name, server_cfg in servers.items():
        command: str = server_cfg["command"]
        args: list[str] = server_cfg.get("args", [])
        env: dict[str, str] = _resolve_env(server_cfg.get("env", {}))

        log = logger.bind(server=name)
        log.info("mcp_pool.connecting", command=command, args=args)

        try:
            client = StdIOStatefulClient(name, command=command, args=args, env=env or None)
            await client.connect()
        except Exception as exc:
            raise MCPConnectionError(
                f"Failed to connect to MCP server '{name}': {exc}"
            ) from exc

        clients.append(client)
        log.info("mcp_pool.connected")

        # Discover tools and register callables
        try:
            tool_list = await client.list_tools()
            tool_names = [t.name if hasattr(t, "name") else str(t) for t in tool_list]
        except Exception:
            log.warning("mcp_pool.list_tools_failed")
            tool_names = []

        for tool_name in tool_names:
            if tool_name in tool_registry:
                log.warning("mcp_pool.tool_name_collision", tool=tool_name)
            try:
                callable_fn = await client.get_callable_function(tool_name)
                tool_registry[tool_name] = callable_fn
                log.debug("mcp_pool.tool_registered", tool=tool_name)
            except Exception as exc:
                log.error("mcp_pool.tool_registration_failed", tool=tool_name, error=str(exc))

        log.info("mcp_pool.server_ready", tool_count=len(tool_names))

    logger.info(
        "mcp_pool.pool_ready",
        server_count=len(clients),
        tool_count=len(tool_registry),
        tools=list(tool_registry.keys()),
    )
    return clients, tool_registry
