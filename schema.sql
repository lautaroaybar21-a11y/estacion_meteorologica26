CREATE DATABASE IF NOT EXISTS meteorologia
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE meteorologia;

CREATE TABLE IF NOT EXISTS mediciones (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    medido_en DATETIME NOT NULL,
    temperatura_bmp DECIMAL(6, 2) NOT NULL,
    temperatura_dht DECIMAL(6, 2) NOT NULL,
    humedad_aire DECIMAL(6, 2) NOT NULL,
    presion_hpa DECIMAL(7, 2) NOT NULL,
    humedad_suelo_raw SMALLINT UNSIGNED NOT NULL,
    humedad_suelo_pct DECIMAL(5, 2) NOT NULL,
    PRIMARY KEY (id),
    INDEX idx_mediciones_medido_en (medido_en)
);
