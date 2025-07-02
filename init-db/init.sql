-- init-db/init.sql

-- Tables for NVML Tool (Power variant)
CREATE TABLE IF NOT EXISTS nvml_relative (
    time_relative_ms DECIMAL(12,3) NOT NULL,
    power_watts DECIMAL(12,6) NOT NULL,
    energy_relative_joules DECIMAL(18,9) NOT NULL
);

CREATE TABLE IF NOT EXISTS nvml_absolute (
    timestamp_system_epoch_ms DECIMAL(18,3) NOT NULL,
    nvml_power_watts DECIMAL(12,6) NOT NULL,
    nvml_integrated_energy_joules DECIMAL(18,9) NOT NULL
);

CREATE TABLE IF NOT EXISTS nvml_stats (
    stat_name TEXT NOT NULL,
    value TEXT NOT NULL
);

-- NVML ENERGY TABLES
CREATE TABLE IF NOT EXISTS nvml_energy_relative (
    time_relative_ms DECIMAL(12,3) NOT NULL,
    energy_joules DECIMAL(18,9) NOT NULL
);

CREATE TABLE IF NOT EXISTS nvml_energy_absolute (
    timestamp_system_epoch_ms DECIMAL(18,3) NOT NULL,
    nvml_energy_joules DECIMAL(18,9) NOT NULL
);

CREATE TABLE IF NOT EXISTS nvml_energy_stats (
    stat_name TEXT NOT NULL,
    value TEXT NOT NULL
);

-- VARIORUM TABLES
CREATE TABLE IF NOT EXISTS variorum_relative (
    time_relative_ms DECIMAL(12,3) NOT NULL,
    power_watts DECIMAL(12,6) NOT NULL,
    energy_relative_joules DECIMAL(18,9) NOT NULL
);

CREATE TABLE IF NOT EXISTS variorum_absolute (
    timestamp_system_epoch_ms DECIMAL(18,3) NOT NULL,
    variorum_power_watts DECIMAL(12,6) NOT NULL,
    variorum_integrated_energy_joules DECIMAL(18,9) NOT NULL
);

CREATE TABLE IF NOT EXISTS variorum_gpus (
    timestamp_ms DECIMAL(18,3) NOT NULL,
    power_watts DECIMAL(12,6) NOT NULL,
    device_id INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS variorum_kernels (
    kernel_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    start_time_ms DECIMAL(18,3) NOT NULL,
    end_time_ms DECIMAL(18,3) NOT NULL,
    duration_ms DECIMAL(18,3) NOT NULL
);

CREATE TABLE IF NOT EXISTS variorum_stats (
    stat_name TEXT NOT NULL,
    value TEXT NOT NULL
);

DROP TABLE IF EXISTS variorum_regions;
CREATE TABLE IF NOT EXISTS variorum_regions (
    name TEXT NOT NULL,
    start_time_ms DECIMAL(18,3) NOT NULL,
    end_time_ms DECIMAL(18,3) NOT NULL
);

-- COPY commands will be dynamically added by the setup.sh script