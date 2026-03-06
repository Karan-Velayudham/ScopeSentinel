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
import logging
from typing import Any, Callable

import yaml
from agentscope.mcp import StdIOStatefulClient

logger = logging.getLogger(__name__)

# Matches ${SOME_VAR} in YAML values
_ENV_VAR_PATTERN = re.compile(r"\$\{([^}]+)\}")


def _substitute_env_vars(value: str) -> str:
    """Replace ${VAR} tokens in a string with the corresponding env var value."""

    def _replace(match: re.Match) -> str:
        var_name = match.group(1)
        result = os.environ.get(var_name, "")
        if not result:
            logger.warning(
                "mcp_pool: env var '${%s}' referenced in mcp_servers.yaml is not set.",
                var_name,
            )
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
    """
    with open(config_path, "r") as fh:
        config = yaml.safe_load(fh)

    servers: dict[str, dict] = config.get("mcp_servers", {})
    if not servers:
        logger.warning("mcp_pool: no servers found in '%s'.", config_path)
        return [], {}

    clients: list[StdIOStatefulClient] = []
    tool_registry: dict[str, Callable[..., Any]] = {}

    for name, server_cfg in servers.items():
        command: str = server_cfg["command"]
        args: list[str] = server_cfg.get("args", [])
        env: dict[str, str] = _resolve_env(server_cfg.get("env", {}))

        logger.info("mcp_pool: connecting to server '%s' via '%s %s' ...", name, command, " ".join(args))

        client = StdIOStatefulClient(name, command=command, args=args, env=env or None)
        await client.connect()
        clients.append(client)
        logger.info("mcp_pool: connected to '%s'.", name)

        # Discover tools and register callables
        try:
            tool_list = await client.list_tools()
            tool_names = [t.name if hasattr(t, "name") else str(t) for t in tool_list]
        except Exception:
            # Older AgentScope versions may not expose list_tools(); fall back gracefully.
            logger.warning(
                "mcp_pool: could not list tools for '%s' — attempting registration by name lookup.",
                name,
            )
            tool_names = []

        for tool_name in tool_names:
            if tool_name in tool_registry:
                logger.warning(
                    "mcp_pool: tool '%s' already registered; server '%s' will override it.",
                    tool_name,
                    name,
                )
            try:
                callable_fn = await client.get_callable_function(tool_name)
                tool_registry[tool_name] = callable_fn
                logger.debug("mcp_pool: registered tool '%s' from server '%s'.", tool_name, name)
            except Exception as exc:
                logger.error(
                    "mcp_pool: failed to get callable for tool '%s' from '%s': %s",
                    tool_name,
                    name,
                    exc,
                )

        logger.info("mcp_pool: server '%s' contributed %d tool(s).", name, len(tool_names))

    logger.info(
        "mcp_pool: pool ready — %d server(s), %d total tool(s): %s",
        len(clients),
        len(tool_registry),
        list(tool_registry.keys()),
    )
    return clients, tool_registry
