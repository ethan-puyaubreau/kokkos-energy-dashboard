# Energy Analysis Dashboard for Energy Consumption Kokkos Tool
Author: Ethan Puyaubreau

Complete energy analysis environment with Grafana and PostgreSQL, ready to use with pre-configured dashboards.

## Quick Start

### Prerequisites
- Docker and Docker Compose installed
- Your energy analysis output CSV files or Kokkos tool ready for benchmarking (see `input/generic_script.sh` for an boilerplate script for easy benchmarking and sorting of results)
- Python (to allow for aggregation of data for the dashboard)

### Setup
1. Clone the repository:
    ```bash
    git clone https://github.com/ethan-puyaubreau/kokkos-energy-dashboard.git
    cd kokkos-energy-dashboard
    ```
2. Optional (if you want to use the provided script) (Measure and Input):
   - Modify `input/generic_script.sh` to set your Kokkos program command and paths to NVML and Variorum libraries.
   - Run the script to generate energy data:
    ```bash
    ./input/generic_script.sh
    ```

If you already have the output files, ensure they are placed in the `input/` in each dedicated folder:

#### 2. (bis) Manually Adding Your Measurement Results

If you want to manually add your own measurement CSV files:

##### **Place your CSV files in the correct folder**  
   - Copy your files into the appropriate `input/` subfolder:
     - `input/nvml_power/` for NVML Power measurements
     - `input/nvml_energy/` for NVML Energy measurements
     - `input/variorum/` for Variorum measurements
   - Each batch of results can have its own subfolders (e.g., `energy_bench_nvml_power_1/`).

##### **File naming**  
   - The aggregation scripts look for files with specific suffixes, for example:
     - `*-nvml-power-relative.csv`
     - `*-nvml-power.csv`
     - `*-nvml-power.dat`
     - `*-variorum-power-relative.csv`
     - `*-variorum-power.csv`
     - `*-variorum-power-gpus.csv`
     - `*-variorum-power-kernels.csv`
     - `*-variorum-power-regions.csv`
   - For Variorum, the regions file must end with `-variorum-power-regions.csv`.

> Note: The Kokkos tool is expected to generate these files in the specified format so you would not need to manually rename them.

3. Start the environment:
    ```bash
    ./setup.sh
    ```
4. Wait for the setup to complete:
    - The script will create a Python virtual environment, install the required dependencies, and run the aggregation scripts to generate the necessary SQL files, then delete this same virtual environment afterwards.
    - This will input the CSV and .dat files from the `input/` directory into the PostgreSQL database.
    - Grafana will be configured with the datasource and the "Energy Analysis Dashboard" will be created automatically via Docker Compose.
    - The database will be populated with the energy data from the CSV files.
5. Access the dashboard:
    - Open your web browser and go to `http://localhost:3000` to access Grafana.

## Dashboard Access

Once setup is complete:

**Grafana**: http://localhost:3000
- **Username**: admin
- **Password**: admin

The "Energy Analysis Dashboard" is automatically available with some charts and visualizations.

## Features

### Automatic configuration - no manual configuration required
- Docker Compose setup for easy deployment
- PostgreSQL database pre-configured (no manual setup required)
- Grafana datasource automatically connected
- Dashboard pre-loaded and ready to use


### Interactive dashboard with Grafana
- Multiple complementary visualizations
- Energy performance metrics in a modern and intuitive interface

## Stop and Clean Environment

### Simple stop (keeps data)
```bash
docker compose down
```

### Complete cleanup (removes everything)
```bash
./remove.sh
```

A cleanup script is also available to remove all input files:
```bash
./input/clean.sh
```

The `remove.sh` script performs a complete cleanup:
- Stops all containers
- Removes data volumes  
- Cleans temporary files generated during the setup