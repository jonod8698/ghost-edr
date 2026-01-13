#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== Stopping Ghost EDR ==="
echo ""

cd "${PROJECT_DIR}/mole"

if docker compose ps 2>/dev/null | grep -q "ghost"; then
    docker compose down
    echo ""
    echo "Ghost EDR stopped"
else
    echo "Ghost EDR is not running"
fi
