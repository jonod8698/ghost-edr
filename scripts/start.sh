#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG_DIR="${HOME}/.config/ghost-edr"

echo "=== Starting Ghost EDR ==="

# Check if config exists
if [[ ! -f "${CONFIG_DIR}/config.yaml" ]]; then
    echo "Configuration not found. Running install first..."
    "${SCRIPT_DIR}/install.sh"
fi

# Start The Mole
echo ""
echo "Starting The Mole (Falco)..."
cd "${PROJECT_DIR}/mole"

if docker compose ps 2>/dev/null | grep -q "ghost-mole"; then
    echo "  The Mole is already running"
else
    docker compose up -d
    echo "  The Mole started"
fi

# Wait for Falco to be ready
echo ""
echo "Waiting for Falco to initialize..."
sleep 5

# Check Falco health
if docker compose ps 2>/dev/null | grep -q "healthy"; then
    echo "  Falco is healthy"
else
    echo "  Falco is starting (may take a moment)..."
fi

# Start The Enforcer
echo ""
echo "Starting The Enforcer..."
echo "  Config: ${CONFIG_DIR}/config.yaml"
echo ""
echo "Press Ctrl+C to stop"
echo ""

ghost-enforcer run --config "${CONFIG_DIR}/config.yaml"
