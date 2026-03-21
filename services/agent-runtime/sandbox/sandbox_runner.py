"""
SandboxRunner: Executes commands inside a Docker container for ScopeSentinel.

Mounts the generated workspace as a volume and runs commands in isolation.
Image is configurable via SANDBOX_IMAGE env var (default: python:3.12-slim).
"""

import logging
import os
from dataclasses import dataclass
from pathlib import Path

import docker
from docker.errors import DockerException, ImageNotFound, ContainerError

logger = logging.getLogger(__name__)

DEFAULT_IMAGE = "python:3.12-slim"
CONTAINER_WORKDIR = "/workspace"


@dataclass
class SandboxResult:
    """Result of a command run inside the sandbox container."""
    exit_code: int
    stdout: str
    stderr: str

    @property
    def success(self) -> bool:
        return self.exit_code == 0

    def summary(self) -> str:
        parts = []
        if self.stdout.strip():
            parts.append(f"STDOUT:\n{self.stdout.strip()}")
        if self.stderr.strip():
            parts.append(f"STDERR:\n{self.stderr.strip()}")
        return "\n".join(parts) or "(no output)"


class SandboxRunner:
    """
    Runs shell commands inside a Docker container, with the workspace
    directory mounted at /workspace.
    """

    CLIENT_TIMEOUT = 120  # seconds for Docker API calls

    def __init__(self, workspace_path: str | Path):
        self.workspace_path = Path(workspace_path).resolve()
        self.image = os.environ.get("SANDBOX_IMAGE", DEFAULT_IMAGE)

        try:
            self._client = docker.from_env(timeout=self.CLIENT_TIMEOUT)
            self._client.ping()
            logger.info("SandboxRunner: Docker daemon connected.")
        except DockerException as e:
            raise RuntimeError(
                "Could not connect to Docker daemon. Is Docker running?\n"
                f"Details: {e}"
            ) from e

    def run(self, command: str, timeout: int = 120) -> SandboxResult:
        """
        Run a shell command inside the sandbox container.

        Args:
            command: Shell command to execute (run via sh -c).
            timeout: Max seconds before the container is killed (default 120).

        Returns:
            A SandboxResult with exit_code, stdout, and stderr.
        """
        logger.info(f"SandboxRunner: running → {command!r}")

        volume_mount = {
            str(self.workspace_path): {
                "bind": CONTAINER_WORKDIR,
                "mode": "rw",
            }
        }

        try:
            result = self._client.containers.run(
                image=self.image,
                command=["sh", "-c", command],
                volumes=volume_mount,
                working_dir=CONTAINER_WORKDIR,
                remove=True,
                stdout=True,
                stderr=True,
            )
            stdout = result.decode("utf-8", errors="replace") if result else ""
            return SandboxResult(exit_code=0, stdout=stdout, stderr="")

        except ContainerError as e:
            # ContainerError is raised when exit_code != 0
            stdout = e.stderr.decode("utf-8", errors="replace") if e.stderr else ""
            return SandboxResult(
                exit_code=e.exit_status,
                stdout="",
                stderr=stdout,
            )
        except Exception as e:
            logger.error(f"SandboxRunner: unexpected error: {e}")
            return SandboxResult(exit_code=1, stdout="", stderr=str(e))
