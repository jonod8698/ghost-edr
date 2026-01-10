"""Docker Desktop runtime implementation."""
from __future__ import annotations

import os

import docker
import docker.errors
import structlog

from ghost_enforcer.runtime.base import ContainerInfo, ContainerRuntime


class DockerDesktopRuntime(ContainerRuntime):
    """Docker Desktop for macOS runtime."""

    name = "docker_desktop"

    def __init__(self, socket_path: str | None = None) -> None:
        self.logger = structlog.get_logger()
        self.socket_path = socket_path or self._find_socket()
        self._client: docker.DockerClient | None = None

    def _find_socket(self) -> str:
        """Find the Docker socket path."""
        paths = [
            "/var/run/docker.sock",
            os.path.expanduser("~/.docker/run/docker.sock"),
            os.path.expanduser(
                "~/Library/Containers/com.docker.docker/Data/docker.sock"
            ),
        ]

        for path in paths:
            if os.path.exists(path):
                return path

        return "/var/run/docker.sock"

    def get_client(self) -> docker.DockerClient:
        """Get or create Docker client."""
        if not self._client:
            self._client = docker.DockerClient(base_url=f"unix://{self.socket_path}")
        return self._client

    def kill_container(self, container_id: str, signal: str = "SIGKILL") -> bool:
        """Kill a container."""
        try:
            client = self.get_client()
            container = client.containers.get(container_id)
            container.kill(signal=signal)
            self.logger.info(
                "Container killed",
                container_id=container_id[:12],
                signal=signal,
            )
            return True
        except docker.errors.NotFound:
            self.logger.warning("Container not found", container_id=container_id[:12])
            return False
        except docker.errors.APIError as e:
            self.logger.error(
                "Failed to kill container",
                container_id=container_id[:12],
                error=str(e),
            )
            return False

    def pause_container(self, container_id: str) -> bool:
        """Pause a container."""
        try:
            client = self.get_client()
            container = client.containers.get(container_id)
            container.pause()
            self.logger.info("Container paused", container_id=container_id[:12])
            return True
        except docker.errors.NotFound:
            self.logger.warning("Container not found", container_id=container_id[:12])
            return False
        except docker.errors.APIError as e:
            self.logger.error(
                "Failed to pause container",
                container_id=container_id[:12],
                error=str(e),
            )
            return False

    def disconnect_network(
        self, container_id: str, network: str | None = None
    ) -> bool:
        """Disconnect container from network(s)."""
        try:
            client = self.get_client()
            container = client.containers.get(container_id)

            # Get container's networks
            networks = container.attrs.get("NetworkSettings", {}).get("Networks", {})
            disconnected = False

            for net_name in networks:
                if network and net_name != network:
                    continue
                try:
                    net = client.networks.get(net_name)
                    net.disconnect(container_id)
                    self.logger.info(
                        "Container disconnected from network",
                        container_id=container_id[:12],
                        network=net_name,
                    )
                    disconnected = True
                except docker.errors.APIError as e:
                    self.logger.warning(
                        "Failed to disconnect network",
                        network=net_name,
                        error=str(e),
                    )

            return disconnected
        except docker.errors.NotFound:
            self.logger.warning("Container not found", container_id=container_id[:12])
            return False
        except docker.errors.APIError as e:
            self.logger.error(
                "Failed to disconnect networks",
                container_id=container_id[:12],
                error=str(e),
            )
            return False

    def get_container_info(self, container_id: str) -> ContainerInfo | None:
        """Get container information."""
        try:
            client = self.get_client()
            container = client.containers.get(container_id)
            return ContainerInfo(
                id=container.id,
                name=container.name,
                image=container.image.tags[0] if container.image.tags else "unknown",
                status=container.status,
                labels=container.labels,
            )
        except docker.errors.NotFound:
            return None

    def list_containers(self) -> list[ContainerInfo]:
        """List running containers."""
        client = self.get_client()
        containers = client.containers.list()
        return [
            ContainerInfo(
                id=c.id,
                name=c.name,
                image=c.image.tags[0] if c.image.tags else "unknown",
                status=c.status,
                labels=c.labels,
            )
            for c in containers
        ]
