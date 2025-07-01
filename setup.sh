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
rm -rf data/nvml_power
mkdir -p data/nvml_power
rm -rf data/nvml_energy
mkdir -p data/nvml_energy
rm -rf data/variorum
mkdir -p data/variorum

echo "Aggregating data into input files..."

echo "Create venv and install requirements..."
python3 -m venv venv
source venv/bin/activate
pip install numpy pandas

python3 scripts/aggregate_nvml_energy.py
python3 scripts/aggregate_nvml.py
python3 scripts/aggregate_variorum.py

echo "Delete venv"
deactivate
rm -rf venv

echo "Starting PostgreSQL database and Grafana via Docker Compose..."

NVML_DIR="data/nvml_power"
NVML_FILES=("nvml_relative.csv" "nvml_absolute.csv" "nvml_stats.csv")
ANY_NVML_FOUND=false
for f in "${NVML_FILES[@]}"; do
  if [ -f "$NVML_DIR/$f" ]; then
    ANY_NVML_FOUND=true
  fi

done
if [ "$ANY_NVML_FOUND" = false ]; then
  echo "WARNING: No NVML Power data found in $NVML_DIR." >&2
fi

NVML_ENERGY_DIR="data/nvml_energy"
NVML_ENERGY_FILES=("nvml_energy_relative.csv" "nvml_energy_absolute.csv" "nvml_energy_stats.csv")
ANY_NVML_ENERGY_FOUND=false
for f in "${NVML_ENERGY_FILES[@]}"; do
  if [ -f "$NVML_ENERGY_DIR/$f" ]; then
    ANY_NVML_ENERGY_FOUND=true
  fi
done
if [ "$ANY_NVML_ENERGY_FOUND" = false ]; then
  echo "WARNING: No NVML Energy data found in $NVML_ENERGY_DIR." >&2
fi

VARIORUM_DIR="data/variorum"
VARIORUM_FILES=("variorum_relative.csv" "variorum_absolute.csv" "variorum_gpus.csv" "variorum_kernels.csv" "variorum_stats.csv")
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
for f in "${NVML_FILES[@]}"; do
  if [ -f "$NVML_DIR/$f" ]; then
    TABLE_NAME="${f%.csv}"
    IMPORT_SQL+="\n\\COPY $TABLE_NAME FROM '/csv_data/nvml_power/$f' WITH (FORMAT csv, HEADER true);\n"
  else
    echo "WARNING: $f not found, import SQL ignored."
  fi
done
for f in "${NVML_ENERGY_FILES[@]}"; do
  if [ -f "$NVML_ENERGY_DIR/$f" ]; then
    TABLE_NAME="${f%.csv}"
    IMPORT_SQL+="\\COPY $TABLE_NAME FROM '/csv_data/nvml_energy/$f' WITH (FORMAT csv, HEADER true);\n"
  else
    echo "WARNING: $f not found, import SQL ignored."
  fi
done
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
echo "available and pre-configured with your data!"
echo ""
echo "PostgreSQL Database:"
echo "    Host      : localhost:5432"
echo "    Database  : energy_analysis"
echo "    User      : grafana_user"
echo "    Password  : super_secret_password"
echo "--------------------------------------------------------"
