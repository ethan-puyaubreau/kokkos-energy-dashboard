#!/bin/bash

# Stop script if any command fails
set -e

# Check if a prefix was provided
if [ -z "$1" ]; then
  echo "Usage: ./setup.sh <output_files_prefix>"
  echo "Example: ./setup.sh my_experiment_run1"
  echo "This will look for: my_experiment_run1_power.csv, my_experiment_run1_kernels.csv, my_experiment_run1_kernel_energy.csv"
  exit 1
fi

PREFIX=$1

# Expected source file names
POWER_FILE="${PREFIX}_power.csv"
KERNELS_FILE="${PREFIX}_kernels.csv"
ENERGY_FILE="${PREFIX}_kernel_energy.csv"

# Check that source files exist
if [ ! -f "$POWER_FILE" ] || [ ! -f "$KERNELS_FILE" ] || [ ! -f "$ENERGY_FILE" ]; then
  echo "Error: One or more output files are missing."
  echo "Check that the following output files exist:"
  echo "- $POWER_FILE"
  echo "- $KERNELS_FILE"
  echo "- $ENERGY_FILE"
  exit 1
fi

echo "Cleaning previous environment..."

# Stop and remove associated Docker containers
if docker compose ps -q &>/dev/null; then
  echo "Stopping existing Docker containers..."
  docker compose down -v
fi

echo "Preparing environment..."

# Create 'data' folder if it doesn't exist and empty it
mkdir -p data
rm -f data/*

echo "Copying output data files with standardized names..."
# Copy output files to 'data' folder with generic names
# that the init.sql script can use
cp "$POWER_FILE" "data/power.csv"
cp "$KERNELS_FILE" "data/kernels.csv"
cp "$ENERGY_FILE" "data/kernel_energy.csv"

echo "Starting PostgreSQL database and Grafana via Docker Compose..."
# Start services in detached mode (-d)
docker compose up -d

echo ""
echo "Waiting for services to start completely..."
sleep 15

echo ""
echo "--------------------------------------------------------"
echo "Done! Your energy analysis environment is ready!"
echo ""
echo "Grafana Access:"
echo "    URL       : http://localhost:3000"
echo "    Username  : admin"
echo "    Password  : admin"
echo ""
echo "Your 'Energy Analysis Dashboard' is automatically"
echo "available and pre-configured with your data!"
echo ""
echo "PostgreSQL Database:"
echo "    Host      : localhost:5432"
echo "    Database  : energy_analysis"
echo "    User      : grafana_user"
echo "    Password  : super_secret_password"
echo "--------------------------------------------------------"
