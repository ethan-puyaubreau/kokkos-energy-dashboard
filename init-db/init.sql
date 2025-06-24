-- init-db/init.sql

-- Création des tables
CREATE TABLE power_over_time (
    timestamp_ms BIGINT PRIMARY KEY,
    device_id INT,
    device_name TEXT,
    power_watts DOUBLE PRECISION
);

CREATE TABLE kernels_info (
    id INT PRIMARY KEY,
    name TEXT,
    type TEXT,
    execution_space TEXT,
    device_id INT,
    start_time_ms BIGINT,
    end_time_ms BIGINT,
    duration_ms BIGINT,
    energy_joules DOUBLE PRECISION,
    average_power_watts DOUBLE PRECISION
);

CREATE TABLE regions (
    id INT PRIMARY KEY,
    name TEXT,
    start_time_ms BIGINT,
    end_time_ms BIGINT,
    duration_ms BIGINT
);

-- Importation des données depuis les fichiers CSV
-- Les chemins pointent vers l'intérieur du conteneur Docker, où nous avons monté le volume.
COPY power_over_time FROM '/csv_data/power.csv' DELIMITER ',' CSV HEADER;
COPY kernels_info FROM '/csv_data/kernels.csv' DELIMITER ',' CSV HEADER;
COPY regions FROM '/csv_data/regions.csv' DELIMITER ',' CSV HEADER;

-- Vues utiles pour l'analyse Grafana
-- Vue principale pour CPU vs GPU
CREATE OR REPLACE VIEW cpu_gpu_summary AS
SELECT
    execution_space,
    COUNT(*) as kernel_count,
    SUM(duration_ms) as total_duration_ms,
    SUM(energy_joules) as total_energy_joules,
    AVG(average_power_watts) as avg_power_watts
FROM kernels_info
WHERE energy_joules > 0
GROUP BY execution_space;

-- Vue pour calculer l'énergie GPU gaspillée pendant les kernels CPU
CREATE OR REPLACE VIEW gpu_waste_analysis AS
WITH cpu_periods AS (
    SELECT start_time_ms, end_time_ms, duration_ms, name
    FROM kernels_info 
    WHERE execution_space = 'OpenMP'
),
gpu_idle_power AS (
    SELECT 
        cp.name as cpu_kernel,
        cp.duration_ms as cpu_duration_ms,
        AVG(pot.power_watts) as avg_gpu_power_during_cpu
    FROM cpu_periods cp
    JOIN power_over_time pot ON 
        pot.timestamp_ms BETWEEN cp.start_time_ms AND cp.end_time_ms
    GROUP BY cp.name, cp.duration_ms
),
totals AS (
    SELECT SUM(energy_joules) as total_energy FROM kernels_info
)
SELECT 
    gip.*,
    (gip.avg_gpu_power_during_cpu * gip.cpu_duration_ms / 1000.0) as gpu_waste_energy_joules,
    ROUND(
        ((gip.avg_gpu_power_during_cpu * gip.cpu_duration_ms / 1000.0) / t.total_energy * 100)::numeric, 
        2
    ) as waste_percentage
FROM gpu_idle_power gip
CROSS JOIN totals t
ORDER BY gpu_waste_energy_joules DESC;

-- Vue simple pour pie chart du temps CPU vs GPU
CREATE OR REPLACE VIEW cpu_gpu_time_distribution AS
SELECT
    CASE 
        WHEN execution_space = 'Cuda' THEN 'GPU'
        WHEN execution_space = 'OpenMP' THEN 'CPU'
        ELSE execution_space
    END AS processor_type,
    SUM(duration_ms) AS total_duration_ms
FROM kernels_info
GROUP BY 
    CASE 
        WHEN execution_space = 'Cuda' THEN 'GPU'
        WHEN execution_space = 'OpenMP' THEN 'CPU'
        ELSE execution_space
    END;
