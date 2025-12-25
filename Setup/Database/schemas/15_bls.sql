-- world sim bls database schema
DROP DATABASE IF EXISTS world_sim_bls;
CREATE DATABASE world_sim_bls CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;


DROP TABLE IF EXISTS world_sim_bls.ap_data;
DROP TABLE IF EXISTS world_sim_bls.ap_series;
DROP TABLE IF EXISTS world_sim_bls.ap_item;
DROP TABLE IF EXISTS world_sim_bls.ap_area;

CREATE TABLE world_sim_bls.ap_item (
    item_code VARCHAR(10) NOT NULL PRIMARY KEY,
    item_name VARCHAR(255) NOT NULL
);


CREATE TABLE world_sim_bls.ap_area (
	area_code VARCHAR(4) NOT NULL PRIMARY KEY,
	area_name VARCHAR(255) NOT NULL
);

CREATE TABLE world_sim_bls.ap_series (
    series_id VARCHAR(16) NOT NULL PRIMARY KEY,
    area_code VARCHAR(4) NOT NULL,
    item_code VARCHAR(10) NOT NULL,
    series_title TEXT NOT NULL,
    footnote_codes VARCHAR(32),
    begin_year INT NOT NULL,
    begin_period VARCHAR(4) NOT NULL,
    end_year INT NOT NULL,
    end_period VARCHAR(4) NOT NULL,
    INDEX idx_area_code (area_code),
    INDEX idx_item_code (item_code),
    FOREIGN KEY (area_code) REFERENCES world_sim_bls.ap_area(area_code) ON DELETE CASCADE,
    FOREIGN KEY (item_code) REFERENCES world_sim_bls.ap_item(item_code) ON DELETE CASCADE
);


CREATE TABLE world_sim_bls.ap_data (
    series_id VARCHAR(16) NOT NULL,
	area_code VARCHAR(4) NOT NULL,
	item_code VARCHAR(10) NOT NULL,
	year INT NOT NULL,
	period VARCHAR(4) NOT NULL,
	value DECIMAL(10, 2) NOT NULL,
	footnotes TEXT NOT NULL,
	PRIMARY KEY (series_id, area_code, item_code, year, period),
	INDEX idx_series_id (series_id),
	INDEX idx_area_code (area_code),
	INDEX idx_item_code (item_code),
	INDEX idx_year_period (year, period),
	INDEX idx_value (value),
	INDEX idx_footnotes (footnotes),
	FOREIGN KEY (series_id) REFERENCES world_sim_bls.ap_series(series_id) ON DELETE CASCADE,
	FOREIGN KEY (area_code) REFERENCES world_sim_bls.ap_area(area_code) ON DELETE CASCADE,
	FOREIGN KEY (item_code) REFERENCES world_sim_bls.ap_item(item_code) ON DELETE CASCADE
);
