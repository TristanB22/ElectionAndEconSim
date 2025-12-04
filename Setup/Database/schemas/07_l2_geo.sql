-- L2 Geo Table
DROP TABLE IF EXISTS world_sim_agents.l2_geo;

CREATE TABLE IF NOT EXISTS world_sim_agents.l2_geo (
    LALVOTERID VARCHAR(64) PRIMARY KEY,
    latitude DECIMAL(10,8) NULL,
    longitude DECIMAL(11,8) NULL,
    INDEX idx_lat_lon (latitude, longitude)
);
