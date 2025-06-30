# Energy Analysis Dashboard for Energy Consumption Kokkos Tool
Author: Ethan Puyaubreau

Complete energy analysis environment with Grafana and PostgreSQL, ready to use with pre-configured dashboards.

## Quick Start

### Prerequisites
- Docker and Docker Compose installed
- Your energy analysis output CSV files or Kokkos tool ready for benchmarking (see `input/generic_script.sh` for an boilerplate script for easy benchmarking and sorting of results)

### Setup
1. Clone the repository:
    ```bash
    git clone https://github.com/ethan-puyaubreau/kokkos-energy-dashboard.git
    cd kokkos-energy-dashboard
    ```
2. Optional (if you want to use the provided script):
   - Modify `input/generic_script.sh` to set your Kokkos program command and paths to NVML and Variorum libraries.
   - Run the script to generate energy data:
    ```bash
    ./input/generic_script.sh
    ```
3. Start the environment:
    ```bash
    ./setup.sh
    ```
4. Wait for the setup to complete:
    - This will input the CSV and .dat files from the `input/` directory into the PostgreSQL database.
    - Grafana will be configured with the datasource and the "Energy Analysis Dashboard" will be created automatically.
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