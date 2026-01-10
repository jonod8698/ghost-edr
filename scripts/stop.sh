#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== Stopping Ghost EDR ==="

# Stop The Mole
echo ""
echo "Stopping The Mole (Falco)..."
cd "${PROJECT_DIR}/mole"

if docker compose ps 2>/dev/null | grep -q "ghost-mole"; then
    docker compose down
    echo "  The Mole stopped"
else
    echo "  The Mole is not running"
fi

echo ""
echo "Ghost EDR stopped"
echo ""
echo "Note: If The Enforcer is running in a terminal, use Ctrl+C to stop it."
