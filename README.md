# Energy Analysis Dashboard for Energy Consumption Kokkos Tool
Author: Ethan Puyaubreau

Complete energy analysis environment with Grafana and PostgreSQL, ready to use with pre-configured dashboards.

## Quick Start

### Prerequisites
- Docker and Docker Compose installed
- Your energy analysis output CSV files

### Launch with one command

```bash
./setup.sh <output_files_prefix>
```

**Example:**
```bash
./setup.sh my_gpu_experiment
```

This command will:
1. Find your output CSV files (based on the provided prefix)
2. Clean the previous environment 
3. Configure PostgreSQL with your data
4. Launch Grafana with pre-configured dashboard
5. Connect everything automatically

### Expected output file format

The script looks for these output files in the current directory:
- `<prefix>_power.csv` - Power consumption data output
- `<prefix>_kernels.csv` - Kernel information output  
- `<prefix>_kernel_energy.csv` - Energy consumption per kernel output

## Dashboard Access

Once setup is complete:

**Grafana**: http://localhost:3000
- **Username**: admin
- **Password**: admin

The "Energy Analysis Dashboard" is automatically available with:
- Power consumption over time chart
- CPU/GPU distribution pie chart
- Duration/energy scatter plot
- Kernel efficiency table
- Top 10 most consuming kernels
- Quick metrics

## Project Structure

```
.
├── docker-compose.yml
├── setup.sh
├── remove.sh
├── data/
├── grafana/
│   ├── dashboards/
│   └── provisioning/
└── init-db/
    └── init.sql
```

## Features

### Automatic configuration
- PostgreSQL database configured
- Grafana datasource automatically connected
- Dashboard pre-loaded and ready to use
- No manual configuration required

### Interactive dashboard
- Multiple complementary visualizations
- Real-time data exploration
- Energy performance metrics
- Modern and intuitive interface

## Stop and Clean Environment

### Simple stop (keeps data)
```bash
docker compose down
```

### Complete cleanup (removes everything)
```bash
./remove.sh
```

The `remove.sh` script performs a complete cleanup:
- Stops all containers
- Removes data volumes  
- Cleans local files
- Frees disk space

## Customization

You can modify:
- `grafana/dashboards/energy-analysis-dashboard.json` - Main dashboard
- `grafana/provisioning/` - Datasource configuration
- `init-db/init.sql` - Database structure

After modification, simply run `./setup.sh <name>` to apply changes.

## Tips

- Use descriptive prefixes for your output files
- Data persists between restarts
- Dashboard automatically adapts to your new data
- All parameters are optimized for energy analysis
