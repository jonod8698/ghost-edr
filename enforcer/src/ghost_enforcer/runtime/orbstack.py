"""OrbStack runtime implementation."""
from __future__ import annotations

import os

import docker
import structlog

from ghost_enforcer.runtime.docker_desktop import DockerDesktopRuntime


class OrbStackRuntime(DockerDesktopRuntime):
    """OrbStack for macOS runtime.

    OrbStack is Docker-compatible, so we inherit from DockerDesktopRuntime
    and override only what's necessary.
    """

    name = "orbstack"

    def __init__(self, socket_path: str | None = None) -> None:
        self.logger = structlog.get_logger()
        self.socket_path = socket_path or self._find_socket()
        self._client: docker.DockerClient | None = None

    def _find_socket(self) -> str:
        """Find the OrbStack Docker socket."""
        paths = [
            os.path.expanduser("~/.orbstack/run/docker.sock"),
            "/var/run/docker.sock",
        ]

        for path in paths:
            if os.path.exists(path):
                return path

        return os.path.expanduser("~/.orbstack/run/docker.sock")

    def get_client(self) -> docker.DockerClient:
        """Get Docker client for OrbStack."""
        if not self._client:
            # OrbStack may set DOCKER_HOST
            docker_host = os.environ.get("DOCKER_HOST")

            if docker_host:
                self._client = docker.DockerClient(base_url=docker_host)
            else:
                self._client = docker.DockerClient(
                    base_url=f"unix://{self.socket_path}"
                )

        return self._client
