import os
import re
from typing import Dict, Optional
import structlog
from agentscope.mcp import StdIOStatefulClient

logger = structlog.get_logger(__name__)
_ENV_VAR_PATTERN = re.compile(r"\$\{([^}]+)\}")

def _substitute_env_vars(value: str) -> str:
    def _replace(match: re.Match) -> str:
        return os.environ.get(match.group(1), "")
    return _ENV_VAR_PATTERN.sub(_replace, value)

class ConnectionManager:
    def __init__(self):
        self.clients: Dict[str, StdIOStatefulClient] = {}

    async def connect_stdio(self, server_name: str, command: str, args: list, env: dict) -> StdIOStatefulClient:
        resolved_env = {k: _substitute_env_vars(v) for k, v in (env or {}).items()}
        try:
            client = StdIOStatefulClient(server_name, command=command, args=args, env=resolved_env or None)
            await client.connect()
            self.clients[server_name] = client
            logger.info("connection_manager.connected", server=server_name)
            return client
        except Exception as exc:
            logger.error("connection_manager.connection_failed", server=server_name, error=str(exc))
            raise

    def get_client(self, server_name: str) -> Optional[StdIOStatefulClient]:
        return self.clients.get(server_name)

    async def close_all(self):
        for server_name, client in self.clients.items():
            await client.close()
            logger.info("connection_manager.closed", server=server_name)

connection_manager = ConnectionManager()
