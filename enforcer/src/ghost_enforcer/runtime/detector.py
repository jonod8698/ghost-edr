"""Auto-detect container runtime on macOS."""
from __future__ import annotations

import os
import subprocess

import structlog

from ghost_enforcer.runtime.base import ContainerRuntime
from ghost_enforcer.runtime.docker_desktop import DockerDesktopRuntime
from ghost_enforcer.runtime.orbstack import OrbStackRuntime

logger = structlog.get_logger()


def detect_container_runtime(
    preferred: str | None = None,
    socket_path: str | None = None,
) -> ContainerRuntime:
    """Detect the container runtime in use.

    Args:
        preferred: Preferred runtime type ("docker_desktop" or "orbstack")
        socket_path: Override socket path

    Returns:
        ContainerRuntime instance
    """
    if preferred:
        if preferred == "orbstack":
            return OrbStackRuntime(socket_path)
        elif preferred == "docker_desktop":
            return DockerDesktopRuntime(socket_path)

    # Check for OrbStack first (more specific)
    if _is_orbstack_running():
        logger.info("Detected OrbStack runtime")
        return OrbStackRuntime(socket_path)

    # Default to Docker Desktop
    if _is_docker_desktop_running():
        logger.info("Detected Docker Desktop runtime")
        return DockerDesktopRuntime(socket_path)

    # Fallback
    logger.warning("Could not detect runtime, defaulting to Docker Desktop")
    return DockerDesktopRuntime(socket_path)


def _is_orbstack_running() -> bool:
    """Check if OrbStack is running."""
    # Check for OrbStack socket
    orbstack_socket = os.path.expanduser("~/.orbstack/run/docker.sock")
    if os.path.exists(orbstack_socket):
        return True

    # Check for OrbStack process
    try:
        result = subprocess.run(
            ["pgrep", "-x", "OrbStack"],
            capture_output=True,
            timeout=5,
        )
        if result.returncode == 0:
            return True
    except (subprocess.SubprocessError, FileNotFoundError):
        pass

    # Check for orb CLI
    try:
        result = subprocess.run(
            ["which", "orb"],
            capture_output=True,
            timeout=5,
        )
        if result.returncode == 0:
            # Verify it's running
            result = subprocess.run(
                ["orb", "status"],
                capture_output=True,
                timeout=5,
            )
            if b"running" in result.stdout.lower():
                return True
    except (subprocess.SubprocessError, FileNotFoundError):
        pass

    return False


def _is_docker_desktop_running() -> bool:
    """Check if Docker Desktop is running."""
    # Check for Docker socket
    if os.path.exists("/var/run/docker.sock"):
        return True

    # Check for Docker Desktop socket
    docker_socket = os.path.expanduser(
        "~/Library/Containers/com.docker.docker/Data/docker.sock"
    )
    if os.path.exists(docker_socket):
        return True

    # Check for user docker socket
    user_socket = os.path.expanduser("~/.docker/run/docker.sock")
    if os.path.exists(user_socket):
        return True

    return False
