#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== Ghost EDR Status ==="
echo ""

cd "${PROJECT_DIR}/mole"

# Check containers
echo "Containers:"
if docker compose ps 2>/dev/null | grep -q "ghost"; then
    docker compose ps
else
    echo "  No Ghost EDR containers running"
fi

# Check configuration
echo ""
echo "Configuration:"
if [[ -f "${PROJECT_DIR}/config/ghost-edr.yaml" ]]; then
    echo "  ${PROJECT_DIR}/config/ghost-edr.yaml (exists)"
else
    echo "  ${PROJECT_DIR}/config/ghost-edr.yaml (not found)"
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
HEALTH=$(curl -s http://localhost:8766/health 2>/dev/null || echo "")
if [[ -n "$HEALTH" ]]; then
    echo "  $HEALTH"
else
    echo "  Not reachable (port 8766)"
fi

# Show recent logs
echo ""
echo "Recent Enforcer Logs:"
docker logs ghost-enforcer --tail 5 2>/dev/null || echo "  Container not running"
