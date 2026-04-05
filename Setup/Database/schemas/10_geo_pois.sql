-- world sim geo database schema

-- drop and create the database
DROP DATABASE IF EXISTS world_sim_geo;
CREATE DATABASE world_sim_geo CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- master heatmap table for subset of 10,000 POIs
CREATE TABLE IF NOT EXISTS world_sim_geo.poi_master_heatmap (
    osm_id BIGINT PRIMARY KEY,
    lat DECIMAL(10, 8) NOT NULL,
    lon DECIMAL(11, 8) NOT NULL,
    INDEX idx_poi_master_heatmap_lat_lon (lat, lon)
);

-- table for storing address point data from GeoJSON, optimized for fast Libpostal-style address lookups
CREATE TABLE IF NOT EXISTS world_sim_geo.addresses (
    hash CHAR(16) PRIMARY KEY, 
    number INT UNSIGNED,        
    street VARCHAR(128) COLLATE utf8mb4_unicode_ci,
    unit VARCHAR(32) COLLATE utf8mb4_unicode_ci,
    city VARCHAR(64) COLLATE utf8mb4_unicode_ci,
    district VARCHAR(64) COLLATE utf8mb4_unicode_ci,
    region VARCHAR(32) COLLATE utf8mb4_unicode_ci,
    postcode VARCHAR(16) COLLATE utf8mb4_unicode_ci,
    id VARCHAR(64),
    lat DECIMAL(10, 8) NOT NULL,
    lon DECIMAL(11, 8) NOT NULL,
    INDEX idx_address_full (number, street, city, region, postcode),
    INDEX idx_address_street_postcode (street, postcode),
    INDEX idx_addresses_lat_lon (lat, lon),
    INDEX idx_addresses_postcode (postcode),
    INDEX idx_addresses_city (city),
    INDEX idx_addresses_street (street),
    INDEX idx_addresses_region (region),
    INDEX idx_addresses_district (district)
);