#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG_DIR="${HOME}/.config/ghost-edr"

echo "=== Ghost EDR Status ==="
echo ""

# Check The Mole
echo "The Mole (Falco):"
cd "${PROJECT_DIR}/mole"
if docker compose ps 2>/dev/null | grep -q "ghost-mole"; then
    STATUS=$(docker compose ps --format "table {{.Name}}\t{{.Status}}" 2>/dev/null | grep ghost-mole || echo "  ghost-mole  Unknown")
    echo "  $STATUS"
else
    echo "  Not running"
fi

# Check The Enforcer
echo ""
echo "The Enforcer:"
if pgrep -f "ghost-enforcer" > /dev/null 2>&1; then
    echo "  Running (PID: $(pgrep -f 'ghost-enforcer'))"
else
    echo "  Not running"
fi

# Check configuration
echo ""
echo "Configuration:"
if [[ -f "${CONFIG_DIR}/config.yaml" ]]; then
    echo "  ${CONFIG_DIR}/config.yaml (exists)"
else
    echo "  ${CONFIG_DIR}/config.yaml (not found)"
fi

# Check Docker runtime
echo ""
echo "Container Runtime:"
if [[ -S "${HOME}/.orbstack/run/docker.sock" ]]; then
    echo "  OrbStack"
elif [[ -S "/var/run/docker.sock" ]]; then
    echo "  Docker Desktop"
else
    echo "  Not detected"
fi

# Check Enforcer health endpoint
echo ""
echo "Enforcer Health:"
HEALTH=$(curl -s http://localhost:8765/health 2>/dev/null || echo "")
if [[ -n "$HEALTH" ]]; then
    echo "  $HEALTH"
else
    echo "  Not reachable (port 8765)"
fi
