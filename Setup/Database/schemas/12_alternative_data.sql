-- world sim alternative data database schema

-- tables for alternative data that we might use in either setting up the 
-- simulation that we are going to run or for the heuristics of the agents

DROP DATABASE IF EXISTS world_sim_alternative_data;
CREATE DATABASE world_sim_alternative_data CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- alternative data tables

DROP TABLE IF EXISTS world_sim_alternative_data.hpi_data;
CREATE TABLE IF NOT EXISTS world_sim_alternative_data.hpi_data (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    hpi_type VARCHAR(64) NOT NULL,
    hpi_flavor VARCHAR(64) NOT NULL,
    frequency VARCHAR(32) NOT NULL,
    level VARCHAR(128) NOT NULL,
    place_name VARCHAR(128) NOT NULL,
    place_id VARCHAR(32) NOT NULL,
    yr INT NOT NULL,
    period INT NOT NULL,
    index_nsa DECIMAL(12,4),
    index_sa DECIMAL(12,4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_place_id (place_id),
    INDEX idx_place_name (place_name),
    INDEX idx_year_period (yr, period),
    INDEX idx_level (level),
    INDEX idx_frequency (frequency)
);


DROP TABLE IF EXISTS world_sim_alternative_data.metro_county_info;
CREATE TABLE IF NOT EXISTS world_sim_alternative_data.metro_county_info (
    cbsa_code SMALLINT UNSIGNED NOT NULL,                -- e.g. 33860
    metropolitandivisioncode SMALLINT UNSIGNED,   -- e.g. 388
    csacode SMALLINT UNSIGNED,   -- e.g. 388
    cbsa_title VARCHAR(128),              -- e.g. Montgomery, AL
    metropolitanmicropolitanstatis VARCHAR(128), -- e.g. Metropolitan Statistical Area/Montgomery, AL
    metropolitandivisiontitle VARCHAR(128), -- e.g. Metropolitan Statistical Area/Montgomery, AL
    csatitle VARCHAR(128), -- e.g. Montgomery County
    countycountyequivalent VARCHAR(128), -- e.g. Montgomery County
    statename VARCHAR(128), -- e.g. Alabama
    fipsstatecode SMALLINT UNSIGNED, -- e.g. 1
    fipscountycode SMALLINT UNSIGNED NOT NULL, -- e.g. 1
    centraloutlyingcounty VARCHAR(16), -- e.g. Central/Outlying
    PRIMARY KEY (cbsa_code, fipscountycode)
);


