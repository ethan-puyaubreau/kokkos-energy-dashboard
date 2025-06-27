-- init-db/init.sql

-- Création des tables
CREATE TABLE IF NOT EXISTS stuff (
    x INT NOT NULL,
    y INT NOT NULL
);

-- Table pour les données de puissance GPU
CREATE TABLE IF NOT EXISTS gpu_power_profile (
    timestamp_nanoseconds BIGINT NOT NULL,
    power_watts DECIMAL(10,3) NOT NULL,
    device_id INT NOT NULL
);

-- Table pour les données des kernels
CREATE TABLE IF NOT EXISTS kernels_profile (
    kernel_id INT NOT NULL,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL,
    start_time_ns BIGINT NOT NULL,
    end_time_ns BIGINT NOT NULL,
    duration_ns BIGINT NOT NULL
);

COPY stuff FROM '/csv_data/test.csv' WITH (FORMAT csv, HEADER true);
COPY gpu_power_profile FROM '/csv_data/power_profile_output_gpu_power.csv' WITH (FORMAT csv, HEADER true);
COPY kernels_profile FROM '/csv_data/power_profile_output_kernels.csv' WITH (FORMAT csv, HEADER true);