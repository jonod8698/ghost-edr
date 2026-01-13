#!/bin/bash
set -e

GHOST_EDR_VERSION="1.0.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== Ghost EDR Installer v${GHOST_EDR_VERSION} ==="
echo ""

# Check for required dependencies
check_deps() {
    echo "Checking dependencies..."

    # Check for Docker
    if ! command -v docker &> /dev/null; then
        echo "ERROR: Docker is required but not found"
        exit 1
    fi
    echo "  Docker: OK"

    # Check for Docker Compose
    if docker compose version &> /dev/null; then
        echo "  Docker Compose: OK"
    elif docker-compose version &> /dev/null; then
        echo "  Docker Compose (standalone): OK"
    else
        echo "ERROR: Docker Compose is required but not found"
        exit 1
    fi
}

# Detect container runtime
detect_runtime() {
    echo ""
    echo "Detecting container runtime..."

    if [[ -S "${HOME}/.orbstack/run/docker.sock" ]]; then
        echo "  Detected: OrbStack"
        RUNTIME="orbstack"
    elif [[ -S "/var/run/docker.sock" ]]; then
        echo "  Detected: Docker Desktop"
        RUNTIME="docker_desktop"
    else
        echo "  WARNING: Could not detect runtime, defaulting to Docker Desktop"
        RUNTIME="docker_desktop"
    fi
}

# Build Docker images
build_images() {
    echo ""
    echo "Building Ghost EDR containers..."

    cd "${PROJECT_DIR}/mole"
    docker compose build --quiet
    echo "  Containers built successfully"
}

# Print usage instructions
print_usage() {
    echo ""
    echo "=== Installation Complete ==="
    echo ""
    echo "To start Ghost EDR:"
    echo ""
    echo "  cd ${PROJECT_DIR}/mole && docker compose up -d"
    echo ""
    echo "  Or use the helper script:"
    echo "     ${PROJECT_DIR}/scripts/start.sh"
    echo ""
    echo "To view logs:"
    echo "  docker compose logs -f"
    echo ""
    echo "To check health:"
    echo "  curl http://localhost:8766/health"
    echo ""
    echo "Configuration: ${PROJECT_DIR}/config/ghost-edr.yaml"
    echo ""
}

# Main installation
main() {
    check_deps
    detect_runtime
    build_images
    print_usage
}

main "$@"
