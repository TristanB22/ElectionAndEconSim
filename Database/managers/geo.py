#!/usr/bin/env python3
"""
Geo Database Manager for World_Sim

Manages geographic and POI data operations in MySQL.
Note: PostGIS operations remain separate in Reporting/services/geospatial_service.py
"""

from __future__ import annotations

import os
import logging
from typing import Dict, List, Any, Optional

from .base import BaseDatabaseManager

logger = logging.getLogger(__name__)


class GeoDatabaseManager(BaseDatabaseManager):
    """
    Specialized manager for geographic data operations in MySQL.
    
    Handles:
    - POI data (MySQL-based)
    - Heatmap data
    - Geographic queries
    
    Note: PostGIS operations (roads, buildings, etc.) are handled separately
    in Reporting/services/geospatial_service.py using PostgreSQL.
    """
    
    _db_name = os.getenv('DB_GEO_NAME', 'world_sim_geo')
    
    def get_poi(self, poi_id: int) -> Optional[Dict[str, Any]]:
        """
        Get POI details by ID.
        
        Args:
            poi_id: POI identifier (osm_id)
            
        Returns:
            POI dictionary or None
        """
        query = f"SELECT * FROM {self._format_table('pois')} WHERE osm_id = %s"
        result = self.execute_query(query, (poi_id,), fetch=True)
        
        if result.success and result.data:
            return result.data[0]
        
        return None
    
    def get_pois_in_bbox(self, min_lat: float, min_lon: float,
                        max_lat: float, max_lon: float,
                        limit: int = 5000) -> List[Dict[str, Any]]:
        """
        Get POIs within a bounding box.
        
        Args:
            min_lat: Minimum latitude
            min_lon: Minimum longitude
            max_lat: Maximum latitude
            max_lon: Maximum longitude
            limit: Maximum number of POIs to return
            
        Returns:
            List of POI dictionaries
        """
        query = f"""
            SELECT * FROM {self._format_table('pois')}
            WHERE lat BETWEEN %s AND %s
              AND lon BETWEEN %s AND %s
            LIMIT %s
        """
        
        result = self.execute_query(
            query,
            (min_lat, max_lat, min_lon, max_lon, limit),
            fetch=True
        )
        
        if result.success:
            return result.data
        
        return []
    
    def store_poi(self, poi_data: Dict[str, Any]) -> int:
        """
        Store or update a POI.
        
        Args:
            poi_data: Dictionary with POI attributes
            
        Returns:
            POI ID (osm_id)
        """
        # Placeholder - implement based on actual pois table schema
        osm_id = poi_data.get('osm_id')
        logger.info(f"Store POI: {osm_id}")
        return osm_id
    
    def get_heatmap_data(self, min_lat: float, min_lon: float,
                        max_lat: float, max_lon: float,
                        limit: int = 1000000) -> List[Dict[str, Any]]:
        """
        Get aggregated heatmap data for POIs in bounding box.
        
        Args:
            min_lat: Minimum latitude
            min_lon: Minimum longitude
            max_lat: Maximum latitude
            max_lon: Maximum longitude
            limit: Maximum number of points
            
        Returns:
            List of heatmap point dictionaries
        """
        query = f"""
            SELECT lat, lon, weight
            FROM {self._format_table('heatmap_data')}
            WHERE lat BETWEEN %s AND %s
              AND lon BETWEEN %s AND %s
            LIMIT %s
        """
        
        result = self.execute_query(
            query,
            (min_lat, max_lat, min_lon, max_lon, limit),
            fetch=True
        )
        
        if result.success:
            return result.data
        
        return []


# Singleton accessor
def get_geo_manager() -> GeoDatabaseManager:
    """Get the singleton instance of GeoDatabaseManager."""
    return GeoDatabaseManager.get_singleton()

