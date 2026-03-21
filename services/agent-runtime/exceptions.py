"""
exceptions — Typed exception hierarchy for ScopeSentinel (Story 0.1.3)

Provides structured error types so callers can handle each failure
mode precisely instead of catching bare `Exception`.
"""


class ScopeSentinelError(Exception):
    """Base class for all ScopeSentinel runtime errors."""


# --- MCP Errors ---

class MCPConnectionError(ScopeSentinelError):
    """Raised when a connection to an MCP server cannot be established."""


class MCPToolCallError(ScopeSentinelError):
    """Raised when a tool call to an MCP server fails."""


# --- LLM Errors ---

class LLMTimeoutError(ScopeSentinelError):
    """Raised when an LLM request exceeds the allowed timeout."""


class LLMResponseError(ScopeSentinelError):
    """Raised when the LLM returns an unexpected or unparseable response."""


# --- Infrastructure Errors ---

class DockerUnavailableError(ScopeSentinelError):
    """Raised when the Docker daemon is unreachable or unavailable."""


class ConfigurationError(ScopeSentinelError):
    """Raised when a required configuration value is missing or invalid."""
