#!/bin/bash

# Script to stop and completely clean the energy analysis environment
# Usage: ./remove.sh

set -e

echo "Stopping and cleaning energy analysis environment..."
echo ""

# Function to display steps
print_step() {
    echo "-> $1"
}

# Check if Docker Compose is running
if docker compose ps -q &>/dev/null; then
    print_step "Stopping Docker containers..."
    docker compose down
    echo "   Done: Containers stopped"
else
    echo "   Info: No containers running"
fi

# Remove Docker volumes (persistent data)
print_step "Removing Docker volumes..."
if docker volume ls -q | grep -q "grafana_energy"; then
    docker compose down -v
    echo "   Done: Volumes removed"
else
    echo "   Info: No volumes to remove"
fi

# Clean local data
print_step "Cleaning local data..."
if [ -d "data" ]; then
    rm -rf data/
    echo "   Done: 'data/' folder removed"
else
    echo "   Info: 'data/' folder doesn't exist"
fi

# Clean orphaned Docker processes
print_step "Cleaning orphaned Docker resources..."
docker system prune -f &>/dev/null
echo "   Done: Orphaned resources cleaned"

echo ""
echo "Cleanup completed!"
echo ""
echo "Summary of actions performed:"
echo "   - Docker containers stopped and removed"
echo "   - Data volumes removed"
echo "   - Local data folder cleaned"
echo "   - Orphaned Docker resources removed"
echo ""
echo "To restart the environment:"
echo "   ./setup.sh <your_experiment_name>"
echo ""
echo "Note: All data and custom Grafana configurations"
echo "have been removed. Next launch will start with"
echo "default configuration."
echo ""
