CREATE DATABASE IF NOT EXISTS traffic_pipeline;
USE traffic_pipeline;

CREATE TABLE IF NOT EXISTS locations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    station_code VARCHAR(30) NOT NULL UNIQUE,
    road_name VARCHAR(120) NOT NULL,
    direction VARCHAR(30) NOT NULL,
    city VARCHAR(80) NOT NULL,
    state VARCHAR(40) NOT NULL
);

CREATE TABLE IF NOT EXISTS weather_conditions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    weather_main VARCHAR(50) NOT NULL,
    weather_description VARCHAR(255) NOT NULL,
    CONSTRAINT uq_weather_label UNIQUE (weather_main, weather_description)
);

CREATE TABLE IF NOT EXISTS traffic_records (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    location_id INT NOT NULL,
    weather_condition_id INT NOT NULL,
    date_time DATETIME NOT NULL,
    holiday VARCHAR(80) NOT NULL DEFAULT 'No Holiday',
    temp DOUBLE NOT NULL,
    rain_1h DOUBLE NOT NULL DEFAULT 0,
    snow_1h DOUBLE NOT NULL DEFAULT 0,
    clouds_all TINYINT UNSIGNED NOT NULL,
    traffic_volume INT UNSIGNED NOT NULL,
    CONSTRAINT fk_traffic_location FOREIGN KEY (location_id) REFERENCES locations(id),
    CONSTRAINT fk_traffic_weather FOREIGN KEY (weather_condition_id) REFERENCES weather_conditions(id),
    CONSTRAINT uq_location_timestamp UNIQUE (location_id, date_time),
    INDEX idx_traffic_datetime (date_time),
    INDEX idx_traffic_location_datetime (location_id, date_time)
);

CREATE TABLE IF NOT EXISTS model_predictions (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    traffic_record_id BIGINT NOT NULL,
    predicted_volume DOUBLE NOT NULL,
    model_version VARCHAR(50) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_prediction_record FOREIGN KEY (traffic_record_id) REFERENCES traffic_records(id),
    INDEX idx_prediction_record (traffic_record_id)
);

INSERT INTO locations (id, station_code, road_name, direction, city, state)
VALUES (1, 'ATR-301', 'I-94 Westbound', 'Westbound', 'Minneapolis-St. Paul', 'Minnesota')
ON DUPLICATE KEY UPDATE road_name = VALUES(road_name);

