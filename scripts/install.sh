#!/bin/bash
set -e

GHOST_EDR_VERSION="1.0.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG_DIR="${HOME}/.config/ghost-edr"

echo "=== Ghost EDR Installer v${GHOST_EDR_VERSION} ==="
echo ""

# Check for required dependencies
check_deps() {
    echo "Checking dependencies..."

    # Check for Python 3.10+
    if ! command -v python3 &> /dev/null; then
        echo "ERROR: Python 3 is required but not found"
        exit 1
    fi

    PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
    PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

    if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]); then
        echo "ERROR: Python 3.10+ required, found $PYTHON_VERSION"
        exit 1
    fi
    echo "  Python $PYTHON_VERSION: OK"

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

# Install The Enforcer
install_enforcer() {
    echo ""
    echo "Installing The Enforcer..."

    cd "${PROJECT_DIR}/enforcer"
    python3 -m pip install --user -e . --quiet

    echo "  Enforcer installed"
}

# Create default configuration
create_config() {
    echo ""
    echo "Creating configuration..."

    mkdir -p "${CONFIG_DIR}"

    if [[ ! -f "${CONFIG_DIR}/config.yaml" ]]; then
        cp "${PROJECT_DIR}/config/ghost-edr.example.yaml" "${CONFIG_DIR}/config.yaml"
        echo "  Created ${CONFIG_DIR}/config.yaml"
    else
        echo "  Config already exists, skipping"
    fi
}

# Print usage instructions
print_usage() {
    echo ""
    echo "=== Installation Complete ==="
    echo ""
    echo "To start Ghost EDR:"
    echo ""
    echo "  1. Start The Mole (in a container):"
    echo "     cd ${PROJECT_DIR}/mole && docker compose up -d"
    echo ""
    echo "  2. Start The Enforcer (on macOS host):"
    echo "     ghost-enforcer run --config ${CONFIG_DIR}/config.yaml"
    echo ""
    echo "  Or use the helper script:"
    echo "     ${PROJECT_DIR}/scripts/start.sh"
    echo ""
    echo "Configuration: ${CONFIG_DIR}/config.yaml"
    echo ""
}

# Main installation
main() {
    check_deps
    detect_runtime
    install_enforcer
    create_config
    print_usage
}

main "$@"
