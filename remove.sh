#!/bin/bash

set -e

echo "Stopping and cleaning energy analysis environment..."
echo ""

print_step() {
    echo "-> $1"
}

if [ -f "init-db/init_tmp.sql" ]; then
  rm -f init-db/init_tmp.sql
fi

if docker compose ps -q &>/dev/null; then
    print_step "Stopping Docker containers..."
    docker compose down
    echo "   Done: Containers stopped"
else
    echo "   Info: No containers running"
fi

print_step "Removing Docker volumes..."
if docker volume ls -q | grep -q "grafana_energy"; then
    docker compose down -v
    echo "   Done: Volumes removed"
else
    echo "   Info: No volumes to remove"
fi

print_step "Cleaning local data..."
if [ -d "data" ]; then
    rm -rf data/
    echo "   Done: 'data/' folder removed"
else
    echo "   Info: 'data/' folder doesn't exist"
fi

print_step "Cleaning orphaned Docker resources..."
docker system prune -f &>/dev/null
echo "   Done: Orphaned resources cleaned"

echo ""
echo "Cleanup completed!"
echo ""
echo "To restart the environment:"
echo "   ./setup.sh"
echo ""
echo "Note: All data and custom Grafana configurations"
echo "have been removed. Next launch will start with"
echo "default configuration."
echo ""