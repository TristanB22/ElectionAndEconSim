-- Agent Routes and Travel Timeline Tables
-- These tables enable frontend scrubbing and route visualization

-- table for the routes that agents take around the world
CREATE TABLE IF NOT EXISTS world_sim_simulations.agent_routes (
    route_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    simulation_id VARCHAR(64) NOT NULL,
    agent_id VARCHAR(64) NOT NULL,
    
    -- Temporal information
    route_start_time TIMESTAMP NOT NULL COMMENT 'Simulation time when route started',
    route_end_time TIMESTAMP NOT NULL COMMENT 'Simulation time when route completes',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Spatial information
    origin_lat DECIMAL(10,8) NOT NULL,
    origin_lon DECIMAL(11,8) NOT NULL,
    destination_lat DECIMAL(10,8) NOT NULL,
    destination_lon DECIMAL(11,8) NOT NULL,
    origin_place_id VARCHAR(255) NULL COMMENT 'OSM ID or symbolic location (home, work, etc.)',
    destination_place_id VARCHAR(255) NULL,
    
    -- Route characteristics
    mode ENUM('pedestrian', 'bicycle', 'auto', 'transit') NOT NULL DEFAULT 'pedestrian',
    distance_km DECIMAL(10,3) NOT NULL,
    duration_minutes DECIMAL(10,2) NOT NULL,
    provider VARCHAR(32) NOT NULL DEFAULT 'valhalla' COMMENT 'valhalla, haversine, or other',
    
    -- Geometry (encoded polyline and decoded coordinates)
    route_polyline TEXT NULL COMMENT 'Encoded polyline (Google/Valhalla format)',
    route_coordinates JSON NULL COMMENT 'Array of [lat,lon] pairs along the route',
    
    -- Metadata
    action_ledger_id BIGINT UNSIGNED NULL COMMENT 'Link to action_ledger entry if applicable',
    planner_metadata JSON NULL COMMENT 'Spatial planner decision context',
    
    -- Indexes for efficient querying
    INDEX idx_simulation_agent_time (simulation_id, agent_id, route_start_time),
    INDEX idx_time_range (simulation_id, route_start_time, route_end_time),
    INDEX idx_agent_routes (agent_id, route_start_time DESC),
    INDEX idx_mode (mode),
    
    FOREIGN KEY (simulation_id) REFERENCES world_sim_simulations.simulations(simulation_id) ON DELETE CASCADE,
    FOREIGN KEY (agent_id) REFERENCES world_sim_agents.agents(l2_voter_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Stores agent travel routes with full geometry for frontend visualization and scrubbing';


-- table for the interpolated agent positions for smooth scrubbing
CREATE TABLE IF NOT EXISTS world_sim_simulations.agent_location_timeline (
    simulation_id VARCHAR(64) NOT NULL,
    agent_id VARCHAR(64) NOT NULL,
    timeline_timestamp TIMESTAMP NOT NULL,
    
    -- Position
    latitude DECIMAL(10,8) NOT NULL,
    longitude DECIMAL(11,8) NOT NULL,
    
    -- Status
    is_traveling BOOLEAN NOT NULL DEFAULT FALSE,
    current_route_id BIGINT UNSIGNED NULL COMMENT 'Reference to active route if traveling',
    location_type ENUM('static', 'in_transit', 'interpolated') NOT NULL DEFAULT 'static',
    
    -- Place context
    current_place_id VARCHAR(255) NULL COMMENT 'OSM ID or symbolic location if not traveling',
    
    PRIMARY KEY (simulation_id, agent_id, timeline_timestamp),
    INDEX idx_sim_agent_time (simulation_id, agent_id, timeline_timestamp),
    INDEX idx_route_reference (current_route_id),
    INDEX idx_traveling (simulation_id, is_traveling, timeline_timestamp),
    
    FOREIGN KEY (simulation_id) REFERENCES world_sim_simulations.simulations(simulation_id) ON DELETE CASCADE,
    FOREIGN KEY (agent_id) REFERENCES world_sim_agents.agents(l2_voter_id) ON DELETE CASCADE,
    FOREIGN KEY (current_route_id) REFERENCES world_sim_simulations.agent_routes(route_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Fine-grained agent positions for smooth frontend scrubbing (1-minute granularity)';


-- table for the enhanced action ledger with route and location tracking
ALTER TABLE world_sim_simulations.action_ledger
ADD COLUMN IF NOT EXISTS route_id BIGINT UNSIGNED NULL COMMENT 'Link to agent_routes for Travel actions',
ADD COLUMN IF NOT EXISTS location_at_execution_lat DECIMAL(10,8) NULL,
ADD COLUMN IF NOT EXISTS location_at_execution_lon DECIMAL(11,8) NULL,
ADD COLUMN IF NOT EXISTS place_id VARCHAR(255) NULL COMMENT 'OSM ID or symbolic location',
ADD INDEX IF NOT EXISTS idx_route_id (route_id),
ADD INDEX IF NOT EXISTS idx_agent_timestamp (simulation_id, agent_id, timestamp DESC) COMMENT 'For action history queries',
ADD INDEX IF NOT EXISTS idx_action_type_time (simulation_id, action_name, timestamp) COMMENT 'For filtering by action type',
ADD FOREIGN KEY IF NOT EXISTS fk_action_ledger_route (route_id) REFERENCES world_sim_simulations.agent_routes(route_id) ON DELETE SET NULL;


-- table for the rich action history for LLM context and replay
CREATE TABLE IF NOT EXISTS world_sim_simulations.agent_action_context (
    context_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    simulation_id VARCHAR(64) NOT NULL,
    agent_id VARCHAR(64) NOT NULL,
    action_ledger_id BIGINT UNSIGNED NOT NULL,
    
    -- Temporal
    action_timestamp TIMESTAMP NOT NULL,
    day_offset INT NOT NULL DEFAULT 0 COMMENT 'Days from simulation start',
    
    -- Action details
    action_name VARCHAR(255) NOT NULL,
    action_summary TEXT NULL COMMENT 'Human-readable summary for LLM context',
    
    -- Spatial context
    location_before JSON NULL COMMENT '{lat, lon, place_id, place_name}',
    location_after JSON NULL,
    route_taken_id BIGINT UNSIGNED NULL,
    
    -- Social/economic context
    counterparties JSON NULL COMMENT 'Array of agent/firm IDs involved',
    items_exchanged JSON NULL COMMENT 'Goods/services/money exchanged',
    
    -- Outcomes
    success BOOLEAN NOT NULL,
    outcome_description TEXT NULL,
    events_generated JSON NULL COMMENT 'Key events from this action',
    
    -- Embeddings for semantic search (future-proofing)
    embedding_vector BLOB NULL COMMENT 'Vector embedding of action_summary',
    
    -- Indexes
    INDEX idx_simulation_agent_time (simulation_id, agent_id, action_timestamp DESC),
    INDEX idx_agent_day (agent_id, day_offset, action_timestamp),
    INDEX idx_action_type (simulation_id, action_name, action_timestamp),
    INDEX idx_success (simulation_id, agent_id, success),
    
    FOREIGN KEY (simulation_id) REFERENCES world_sim_simulations.simulations(simulation_id) ON DELETE CASCADE,
    FOREIGN KEY (agent_id) REFERENCES world_sim_agents.agents(l2_voter_id) ON DELETE CASCADE,
    FOREIGN KEY (action_ledger_id) REFERENCES world_sim_simulations.action_ledger(simulation_id, agent_id, timestamp) ON DELETE CASCADE,
    FOREIGN KEY (route_taken_id) REFERENCES world_sim_simulations.agent_routes(route_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Rich action history for LLM context, replay, and agent page visualization';



