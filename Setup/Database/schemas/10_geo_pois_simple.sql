-- world sim geo database schema

-- master heatmap table for subset of 10,000 POIs
CREATE TABLE IF NOT EXISTS pois (
    id INT AUTO_INCREMENT PRIMARY KEY,
    osm_id BIGINT NOT NULL,
    name VARCHAR(255),
    category VARCHAR(50) NOT NULL, -- amenity, shop, tourism, etc.
    subcategory VARCHAR(100), -- restaurant, cafe, hotel, etc.
    brand VARCHAR(255),
    
    -- Spatial data
    geometry POINT NOT NULL,
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL,
    
    -- Address information
    street VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(50),
    postcode VARCHAR(20),
    country VARCHAR(50) DEFAULT 'US',
    
    -- Contact information
    phone VARCHAR(50),
    website TEXT,
    email VARCHAR(255),
    opening_hours TEXT,
    
    -- All other OSM properties as JSON for flexible querying
    properties JSON DEFAULT ('{}'),
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_verified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Data source tracking
    source VARCHAR(50) DEFAULT 'osm',
    region VARCHAR(50) DEFAULT 'maine',
    
    -- Quality metrics
    confidence_score DECIMAL(3, 2) DEFAULT 1.0, -- 0.0 to 1.0
    is_verified BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Prevent duplicates based on OSM ID and location
    UNIQUE KEY unique_osm_location (osm_id, latitude, longitude),
    
    -- Spatial index
    SPATIAL INDEX(geometry)
);

-- Spatial clustering table for efficient map rendering
CREATE TABLE IF NOT EXISTS poi_clusters (
    id INT AUTO_INCREMENT PRIMARY KEY,
    zoom_level INT NOT NULL,
    cluster_id VARCHAR(50) NOT NULL,
    center_lat DECIMAL(10, 8) NOT NULL,
    center_lon DECIMAL(11, 8) NOT NULL,
    center_geometry POINT NOT NULL,
    poi_count INT NOT NULL,
    bounds_geometry POLYGON,
    category_counts JSON DEFAULT ('{}'),
    amenity_counts JSON DEFAULT ('{}'),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    UNIQUE KEY unique_cluster (zoom_level, cluster_id),
    SPATIAL INDEX(center_geometry)
);

-- Real-time updates tracking
CREATE TABLE IF NOT EXISTS poi_updates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    poi_id INT,
    update_type VARCHAR(20) NOT NULL, -- 'created', 'updated', 'deleted'
    old_data JSON,
    new_data JSON,
    updated_by VARCHAR(100) DEFAULT 'system',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (poi_id) REFERENCES pois(id) ON DELETE CASCADE
);

-- Search optimization table
CREATE TABLE IF NOT EXISTS poi_search_index (
    id INT AUTO_INCREMENT PRIMARY KEY,
    poi_id INT,
    search_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (poi_id) REFERENCES pois(id) ON DELETE CASCADE,
    FULLTEXT INDEX(search_text)
);

-- Create all indexes after tables are created
-- Primary indexes for efficient queries
CREATE INDEX idx_pois_osm_id ON pois(osm_id);
CREATE INDEX idx_pois_lat_lon ON pois(latitude, longitude);
CREATE INDEX idx_pois_category ON pois(category);
CREATE INDEX idx_pois_subcategory ON pois(subcategory);
CREATE INDEX idx_pois_brand ON pois(brand);
CREATE INDEX idx_pois_city ON pois(city);
CREATE INDEX idx_pois_state ON pois(state);
CREATE INDEX idx_pois_postcode ON pois(postcode);
CREATE INDEX idx_pois_active ON pois(is_active);
CREATE INDEX idx_pois_verified ON pois(is_verified);
CREATE INDEX idx_pois_region ON pois(region);
CREATE INDEX idx_pois_source ON pois(source);
CREATE INDEX idx_pois_confidence ON pois(confidence_score);

-- Composite indexes for common query patterns
CREATE INDEX idx_pois_category_location ON pois(category, latitude, longitude);
CREATE INDEX idx_pois_region_active ON pois(region, is_active);
CREATE INDEX idx_pois_category_active ON pois(category, is_active);
CREATE INDEX idx_pois_city_category ON pois(city, category);
CREATE INDEX idx_pois_state_category ON pois(state, category);
CREATE INDEX idx_pois_region_category ON pois(region, category);
CREATE INDEX idx_pois_active_verified ON pois(is_active, is_verified);
CREATE INDEX idx_pois_created_at ON pois(created_at);
CREATE INDEX idx_pois_updated_at ON pois(updated_at);

-- Text search indexes
CREATE INDEX idx_pois_name ON pois(name(50)); -- Prefix index for name searches
CREATE INDEX idx_pois_street ON pois(street(50)); -- Prefix index for street searches

-- Additional spatial indexes
CREATE INDEX idx_pois_geometry_spatial ON pois(geometry(1)); -- Spatial index on geometry
CREATE INDEX idx_pois_bounds ON pois(latitude, longitude, is_active); -- For bounding box queries

-- Indexes for clustering table
CREATE INDEX idx_clusters_zoom_center ON poi_clusters(zoom_level, center_lat, center_lon);
CREATE INDEX idx_clusters_zoom_level ON poi_clusters(zoom_level);
CREATE INDEX idx_clusters_poi_count ON poi_clusters(poi_count);
CREATE INDEX idx_clusters_created_at ON poi_clusters(created_at);

-- Indexes for updates table
CREATE INDEX idx_poi_updates_poi_id ON poi_updates(poi_id);
CREATE INDEX idx_poi_updates_created_at ON poi_updates(created_at);
CREATE INDEX idx_poi_updates_type ON poi_updates(update_type);
CREATE INDEX idx_poi_updates_updated_by ON poi_updates(updated_by);
CREATE INDEX idx_poi_updates_poi_type ON poi_updates(poi_id, update_type);

-- Add constraints for data integrity
ALTER TABLE pois ADD CONSTRAINT chk_latitude CHECK (latitude >= -90 AND latitude <= 90);
ALTER TABLE pois ADD CONSTRAINT chk_longitude CHECK (longitude >= -180 AND longitude <= 180);
ALTER TABLE pois ADD CONSTRAINT chk_confidence_score CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0);

-- Create additional views for common queries
CREATE OR REPLACE VIEW active_pois AS
SELECT 
    id, osm_id, name, category, subcategory, brand,
    latitude, longitude, street, city, state, postcode,
    phone, website, properties, confidence_score, is_verified
FROM pois 
WHERE is_active = TRUE;

CREATE OR REPLACE VIEW verified_pois AS
SELECT 
    id, osm_id, name, category, subcategory, brand,
    latitude, longitude, street, city, state, postcode,
    phone, website, properties, confidence_score
FROM pois 
WHERE is_active = TRUE AND is_verified = TRUE;

-- View for easy POI statistics
CREATE OR REPLACE VIEW poi_stats AS
SELECT 
    region,
    category,
    COUNT(*) as total_count,
    COUNT(CASE WHEN is_active THEN 1 END) as active_count,
    COUNT(CASE WHEN is_verified THEN 1 END) as verified_count,
    AVG(confidence_score) as avg_confidence,
    MIN(created_at) as first_created,
    MAX(updated_at) as last_updated
FROM pois
GROUP BY region, category
ORDER BY region, total_count DESC;

-- Performance monitoring view
CREATE OR REPLACE VIEW index_usage_stats AS
SELECT 
    TABLE_NAME,
    INDEX_NAME,
    CARDINALITY,
    SUB_PART,
    PACKED,
    NULLABLE,
    INDEX_TYPE
FROM information_schema.STATISTICS 
WHERE TABLE_SCHEMA = 'world_sim_geo' 
AND TABLE_NAME = 'pois'
ORDER BY TABLE_NAME, SEQ_IN_INDEX;