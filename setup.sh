#!/bin/bash

set -e

if [ -f "init-db/init_tmp.sql" ]; then
  rm -f init-db/init_tmp.sql
fi

echo "Cleaning previous environment..."

if docker compose ps -q &>/dev/null; then
  echo "Stopping existing Docker containers..."
  docker compose down -v
fi

echo "Preparing environment..."

mkdir -p data
rm -rf data/variorum
mkdir -p data/variorum

echo "Aggregating data into input files..."

echo "Create venv and install requirements..."
python3 -m venv venv
source venv/bin/activate
pip install numpy pandas

python3 scripts/variorum/aggregate_variorum.py

echo "Delete venv"
deactivate
rm -rf venv

echo "Starting PostgreSQL database and Grafana via Docker Compose..."

VARIORUM_DIR="data/variorum"
VARIORUM_FILES=("variorum_relative.csv" "variorum_absolute.csv" "variorum_gpus.csv" "variorum_kernels.csv" "variorum_stats.csv" "variorum_regions.csv")
ANY_VARIORUM_FOUND=false
for f in "${VARIORUM_FILES[@]}"; do
  if [ -f "$VARIORUM_DIR/$f" ]; then
    ANY_VARIORUM_FOUND=true
  fi
done
if [ "$ANY_VARIORUM_FOUND" = false ]; then
  echo "WARNING: No Variorum data found in $VARIORUM_DIR." >&2
fi

IMPORT_SQL=""
for f in "${VARIORUM_FILES[@]}"; do
  if [ -f "$VARIORUM_DIR/$f" ]; then
    TABLE_NAME="${f%.csv}"
    IMPORT_SQL+="\\COPY $TABLE_NAME FROM '/csv_data/variorum/$f' WITH (FORMAT csv, HEADER true);\n"
  else
    echo "WARNING: $f not found, import SQL ignored."
  fi
done

cat init-db/init.sql > init-db/init_tmp.sql
sed -i '/COPY.*FROM/d' init-db/init_tmp.sql
printf "%b" "$IMPORT_SQL" >> init-db/init_tmp.sql

if [ -f "$VARIORUM_DIR/variorum_series.sql" ]; then
  cat "$VARIORUM_DIR/variorum_series.sql" >> init-db/init_tmp.sql
else
  echo "WARNING: variorum_series.sql not found, SQL for variorum_series table not imported."
fi

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
echo "available and pre-configured with your Variorum data!"
echo ""
echo "PostgreSQL Database:"
echo "    Host      : localhost:5432"
echo "    Database  : energy_analysis"
echo "    User      : grafana_user"
echo "    Password  : super_secret_password"
echo "--------------------------------------------------------"
