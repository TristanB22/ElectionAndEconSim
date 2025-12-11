-- world sim geo simulations database schema

-- tables to hold inforamtion for each of the simulations
-- about the geography of the simulation

DROP TABLE IF EXISTS world_sim_simulations.poi_seen;
DROP TABLE IF EXISTS world_sim_simulations.poi_categories;

-- table to hold the geography of the simulation
CREATE TABLE world_sim_simulations.poi_categories (
	osm_id BIGINT UNSIGNED NOT NULL PRIMARY KEY,
	name VARCHAR(255) DEFAULT NULL COMMENT 'Display name of the POI (e.g., "Hannaford", "Portland City Hall")',
    category_name VARCHAR(64) NOT NULL COMMENT 'OSM category key (amenity, shop, tourism, etc.)',
	subcategory_name VARCHAR(64) NOT NULL COMMENT 'OSM category value (restaurant, supermarket, etc.)',
	lat DECIMAL(10, 8) NOT NULL,
	lon DECIMAL(11, 8) NOT NULL,
	INDEX idx_lat_lon (lat, lon),
    INDEX idx_category_name (category_name),
    INDEX idx_subcategory_name (subcategory_name),
    INDEX idx_name (name)
);

-- table for who has seen what POI in a simulation with other characteristics and heuristics
CREATE TABLE world_sim_simulations.poi_seen (
	simulation_id VARCHAR(64) NOT NULL,
	agent_id VARCHAR(64) NOT NULL,
	osm_id BIGINT UNSIGNED NOT NULL,
	distance_km_from_home DECIMAL(10, 3) NOT NULL,
	times_seen INT UNSIGNED NOT NULL DEFAULT 1,
	first_time_seen TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
	last_time_seen TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
	number_of_times_visited INT UNSIGNED NOT NULL DEFAULT 0,
	last_time_visited TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
	first_time_visited TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
	loaded_at_start_of_simulation BOOLEAN NOT NULL DEFAULT FALSE,
	source ENUM('init','route','need','social','system') NOT NULL DEFAULT 'init',
	PRIMARY KEY (simulation_id, agent_id, osm_id),
	INDEX idx_simulation_agent_osm (simulation_id, agent_id, osm_id),
	INDEX idx_distance_km_from_home (distance_km_from_home),
	INDEX idx_times_seen (times_seen),
	INDEX idx_simulation_agent (simulation_id, agent_id),
	INDEX idx_simulation (simulation_id),
	INDEX idx_last_time_seen (simulation_id, agent_id, last_time_seen DESC) COMMENT 'For recency sorting',
	INDEX idx_visits (simulation_id, agent_id, number_of_times_visited DESC) COMMENT 'For visit frequency sorting',
	INDEX idx_source (simulation_id, agent_id, source) COMMENT 'For filtering by knowledge source',
	FOREIGN KEY (simulation_id) REFERENCES world_sim_simulations.simulations(simulation_id) ON DELETE CASCADE,
	FOREIGN KEY (agent_id) REFERENCES world_sim_agents.agents(l2_voter_id) ON DELETE CASCADE,
	FOREIGN KEY (osm_id) REFERENCES world_sim_simulations.poi_categories(osm_id) ON DELETE CASCADE
);
