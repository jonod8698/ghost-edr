"""Base class for container runtime implementations."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import docker


@dataclass
class ContainerInfo:
    """Information about a container."""

    id: str
    name: str
    image: str
    status: str
    labels: dict[str, str] = field(default_factory=dict)


class ContainerRuntime(ABC):
    """Abstract base class for container runtime implementations."""

    name: str = "unknown"
    socket_path: str = ""

    @abstractmethod
    def get_client(self) -> docker.DockerClient:
        """Get the Docker client."""
        pass

    @abstractmethod
    def kill_container(self, container_id: str, signal: str = "SIGKILL") -> bool:
        """Kill a container.

        Args:
            container_id: Container ID or name
            signal: Signal to send (default SIGKILL)

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def pause_container(self, container_id: str) -> bool:
        """Pause a container.

        Args:
            container_id: Container ID or name

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def disconnect_network(
        self, container_id: str, network: str | None = None
    ) -> bool:
        """Disconnect a container from its networks.

        Args:
            container_id: Container ID or name
            network: Specific network to disconnect, or None for all

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def get_container_info(self, container_id: str) -> ContainerInfo | None:
        """Get information about a container.

        Args:
            container_id: Container ID or name

        Returns:
            ContainerInfo if found, None otherwise
        """
        pass

    @abstractmethod
    def list_containers(self) -> list[ContainerInfo]:
        """List all running containers.

        Returns:
            List of ContainerInfo objects
        """
        pass
