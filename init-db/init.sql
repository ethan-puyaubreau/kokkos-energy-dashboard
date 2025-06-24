-- init-db/init.sql

-- Création des tables
CREATE TABLE power_over_time (
    timestamp_ms BIGINT PRIMARY KEY,
    device_id INT,
    power_watts DOUBLE PRECISION
);

CREATE TABLE kernels_info (
    name TEXT,
    type TEXT,
    start_time_ms BIGINT PRIMARY KEY,
    end_time_ms BIGINT,
    duration_ms BIGINT
);

CREATE TABLE kernel_energy (
    name TEXT,
    type TEXT,
    duration_ms BIGINT,
    total_energy_joules DOUBLE PRECISION,
    average_power_watts DOUBLE PRECISION
);

-- Importation des données depuis les fichiers CSV
-- Les chemins pointent vers l'intérieur du conteneur Docker, où nous avons monté le volume.
COPY power_over_time FROM '/csv_data/power.csv' DELIMITER ',' CSV HEADER;
COPY kernels_info FROM '/csv_data/kernels.csv' DELIMITER ',' CSV HEADER;
COPY kernel_energy FROM '/csv_data/kernel_energy.csv' DELIMITER ',' CSV HEADER;

-- Création de la vue pour simplifier les requêtes dans Grafana
CREATE OR REPLACE VIEW kernels_detailed AS
SELECT
    ki.name,
    ki.type,
    ki.start_time_ms,
    ki.end_time_ms,
    ki.duration_ms,
    ke.total_energy_joules,
    ke.average_power_watts
FROM
    kernels_info ki
LEFT JOIN
    kernel_energy ke ON ki.name = ke.name;
