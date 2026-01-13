#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== Starting Ghost EDR ==="
echo ""

cd "${PROJECT_DIR}/mole"

# Check if already running
if docker compose ps 2>/dev/null | grep -q "ghost-enforcer.*Up"; then
    echo "Ghost EDR is already running"
    echo ""
    docker compose ps
    exit 0
fi

# Start all containers
echo "Starting Ghost EDR containers..."
docker compose up -d

# Wait for health checks
echo ""
echo "Waiting for services to be healthy..."
sleep 5

# Show status
echo ""
docker compose ps

# Check enforcer health
echo ""
echo "Checking Enforcer health..."
HEALTH=$(curl -s http://localhost:8766/health 2>/dev/null || echo "")
if [[ -n "$HEALTH" ]]; then
    echo "  $HEALTH"
else
    echo "  Waiting for Enforcer to start..."
    sleep 3
    HEALTH=$(curl -s http://localhost:8766/health 2>/dev/null || echo "Not reachable")
    echo "  $HEALTH"
fi

echo ""
echo "Ghost EDR is running. Use 'docker compose logs -f' to follow logs."
