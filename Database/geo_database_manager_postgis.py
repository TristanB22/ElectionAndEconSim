#!/usr/bin/env python3
"""
PostGIS Geo Database Manager

The PostGIS Geo db is separate from the main db that we have
so we want our own db manager for it
"""

from __future__ import annotations

import os
from pathlib import Path
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

# Optional psycopg2 import - gracefully handle if not available
try:
	import psycopg2
	import psycopg2.extras
	PSYCOPG2_AVAILABLE = True
except ImportError:
	PSYCOPG2_AVAILABLE = False
	psycopg2 = None

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Ensure World_Sim/.env is loaded so POSTGRES_* are available even if the app
# Load environment variables using centralized loader
try:
    from Utils.env_loader import load_environment
    # Load from World_Sim directory (parents[1])
    env_path = Path(__file__).resolve().parents[1] / ".env"
    load_environment(env_path)
except ImportError:
    # Fallback to basic dotenv loading if centralized loader not available
    try:
        from dotenv import load_dotenv
        if env_path.exists():
            load_dotenv(dotenv_path=env_path)
    except Exception:
        # If python-dotenv isn't installed or .env missing, proceed with process env
        pass


class PostGISGeoDatabaseManager:
    """Minimal PostGIS manager exposing the methods used by geo_api."""

    def __init__(self) -> None:
        if not PSYCOPG2_AVAILABLE:
            logger.warning("psycopg2 not available - PostGIS features will be disabled")
            return
        
        self.host = os.getenv("POSTGRES_HOST", "localhost")
        self.port = int(os.getenv("POSTGRES_HOST", "5432"))
        self.database = os.getenv("POSTGRES_DB", "world_sim_geo")
        self.user = os.getenv("POSTGRES_USER", "postgres")
        self.password = os.getenv("POSTGRES_PASSWORD")

    def _connect(self):
        if not PSYCOPG2_AVAILABLE:
            raise RuntimeError("psycopg2 not available")
        return psycopg2.connect(
            host=self.host,
            port=self.port,
            dbname=self.database,
            user=self.user,
            password=self.password,
        )

    def _bbox_envelope_3857(self, min_lat: float, min_lon: float, max_lat: float, max_lon: float) -> str:
        # Build ST_Transform(ST_MakeEnvelope(...,4326),3857) in SQL side; here we just pass numbers
        return "ST_Intersects(way, ST_Transform(ST_MakeEnvelope(%s,%s,%s,%s,4326),3857))"

    def _row_to_poi(self, row: Dict[str, Any]) -> Dict[str, Any]:
        # Map a PostGIS row to the POI dict shape used by the frontend
        tags = row.get("tags_json") or {}
        if isinstance(tags, str):
            try:
                tags = json.loads(tags)
            except Exception:
                tags = {}

        # use same categorization logic as frontend (_categorize_poi)
        # category = the key/column name (e.g., "amenity", "shop")
        # subcategory = the value in that key (e.g., "restaurant", "supermarket")
        category = "other"
        subcategory = "unknown"
        
        # check dedicated columns first (same priority order as _categorize_poi)
        if row.get("amenity"):
            category = "amenity"
            subcategory = row.get("amenity")
        elif row.get("shop"):
            category = "shop"
            subcategory = row.get("shop")
        elif row.get("tourism"):
            category = "tourism"
            subcategory = row.get("tourism")
        elif row.get("leisure"):
            category = "leisure"
            subcategory = row.get("leisure")
        elif row.get("office"):
            category = "office"
            subcategory = row.get("office")
        elif row.get("religion"):
            category = "religion"
            subcategory = row.get("religion")
        elif row.get("historic"):
            category = "historic"
            subcategory = row.get("historic")
        elif row.get("place"):
            category = "place"
            subcategory = row.get("place")
        elif row.get("building"):
            category = "building"
            subcategory = row.get("building")
        else:
            # check tags if no column matches
            if isinstance(tags, dict):
                if tags.get("amenity"):
                    category = "amenity"
                    subcategory = tags.get("amenity")
                elif tags.get("shop"):
                    category = "shop"
                    subcategory = tags.get("shop")
                elif tags.get("tourism"):
                    category = "tourism"
                    subcategory = tags.get("tourism")
                elif tags.get("leisure"):
                    category = "leisure"
                    subcategory = tags.get("leisure")
                elif tags.get("healthcare"):
                    category = "healthcare"
                    subcategory = tags.get("healthcare")
                elif tags.get("office"):
                    category = "office"
                    subcategory = tags.get("office")
                elif tags.get("craft"):
                    category = "craft"
                    subcategory = tags.get("craft")
                elif tags.get("religion"):
                    category = "religion"
                    subcategory = tags.get("religion")
                elif tags.get("historic"):
                    category = "historic"
                    subcategory = tags.get("historic")
                elif tags.get("building"):
                    category = "building"
                    subcategory = tags.get("building")
                elif tags.get("place"):
                    category = "place"
                    subcategory = tags.get("place")

        # merge promoted columns into properties while keeping raw tags
        properties: Dict[str, Any] = {
            "osm_id": row.get("osm_id"),
            "name": row.get("name"),
            "category": category,
            "subcategory": subcategory,
            "brand": row.get("brand"),
            "operator": row.get("operator"),
        }
        # add common OSM keys if present
        for key in ["amenity", "shop", "tourism", "leisure", "building"]:
            if row.get(key) is not None:
                properties[key] = row.get(key)
        # merge tags json last so it doesn't overwrite critical keys unexpectedly
        if isinstance(tags, dict):
            for k, v in tags.items():
                if v is not None and v != "":
                    properties.setdefault(k, v)

        poi = {
            "id": int(row.get("osm_id")) if row.get("osm_id") is not None else None,
            "osm_id": int(row.get("osm_id")) if row.get("osm_id") is not None else None,
            "name": row.get("name"),
            "category": category,
            "subcategory": subcategory,
            "brand": row.get("brand"),
            "latitude": float(row.get("latitude")) if row.get("latitude") is not None else None,
            "longitude": float(row.get("longitude")) if row.get("longitude") is not None else None,
            "properties": properties,
        }
        return poi

    def get_pois_in_bounds(
        self,
        min_lat: float,
        min_lon: float,
        max_lat: float,
        max_lon: float,
        category: Optional[str] = None,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """Query POIs from planet_osm_point within a lon/lat bbox."""
        sql = (
            """
            SELECT 
                p.osm_id,
                p.name,
                p.amenity, p.shop, p.tourism, p.leisure, p.building,
                p.operator, p.brand,
                ST_Y(ST_Transform(p.way, 4326)) AS latitude,
                ST_X(ST_Transform(p.way, 4326)) AS longitude,
                hstore_to_json(p.tags) AS tags_json
            FROM planet_osm_point p
            WHERE 
                ST_Intersects(
                    p.way,
                    ST_Transform(ST_MakeEnvelope(%s, %s, %s, %s, 4326), 3857)
                )
            """
        )

        params: List[Any] = [min_lon, min_lat, max_lon, max_lat]

        if category:
            # filter by a common OSM grouping
            sql += " AND (p.amenity = %s OR p.shop = %s OR p.tourism = %s OR p.leisure = %s OR p.building = %s)"
            params += [category, category, category, category, category]

        sql += " LIMIT %s"
        params.append(limit)

        try:
            with self._connect() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(sql, params)
                    rows = cur.fetchall()
            return [self._row_to_poi(r) for r in rows]
        except Exception as e:
            logger.error(f"PostGIS get_pois_in_bounds error: {e}")
            return []

    def fetch_point_coords(self, count: int, testing: bool = False) -> List[Dict[str, float]]:
        """Fetch point coordinates from planet_osm_point.

        returns a list of dicts: { 'lat': float, 'lon': float }
        If testing=True, fetches the first N records for speed; otherwise uses RANDOM().
        """
        if testing:
            sql = (
                """
                SELECT 
                    ST_Y(ST_Transform(way, 4326)) AS lat,
                    ST_X(ST_Transform(way, 4326)) AS lon
                FROM planet_osm_point 
                WHERE way IS NOT NULL
                ORDER BY osm_id
                LIMIT %s
                """
            )
            params: Tuple[Any, ...] = (count,)
        else:
            sql = (
                """
                SELECT 
                    ST_Y(ST_Transform(way, 4326)) AS lat,
                    ST_X(ST_Transform(way, 4326)) AS lon
                FROM planet_osm_point 
                WHERE way IS NOT NULL
                ORDER BY RANDOM()
                LIMIT %s
                """
            )
            params = (count,)

        try:
            with self._connect() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(sql, params)
                    rows = cur.fetchall()
            # normalize to simple list of dicts with float values
            out: List[Dict[str, float]] = []
            for r in rows:
                lat = r.get("lat")
                lon = r.get("lon")
                if lat is None or lon is None:
                    continue
                out.append({"lat": float(lat), "lon": float(lon)})
            return out
        except Exception as e:
            logger.error(f"PostGIS fetch_point_coords error: {e}")
            return []

    def search_pois(self, query_text: str, limit: int = 100) -> List[Dict[str, Any]]:
        sql = (
            """
            SELECT 
                p.osm_id,
                p.name,
                p.amenity, p.shop, p.tourism, p.leisure, p.building,
                p.operator, p.brand,
                ST_Y(ST_Transform(p.way, 4326)) AS latitude,
                ST_X(ST_Transform(p.way, 4326)) AS longitude,
                hstore_to_json(p.tags) AS tags_json
            FROM planet_osm_point p
            WHERE p.name ILIKE %s
            ORDER BY p.name
            LIMIT %s
            """
        )
        try:
            with self._connect() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(sql, (f"%{query_text}%", limit))
                    rows = cur.fetchall()
            return [self._row_to_poi(r) for r in rows]
        except Exception as e:
            logger.error(f"PostGIS search_pois error: {e}")
            return []

    def get_poi_by_id(self, osm_id: int) -> Optional[Dict[str, Any]]:
        # try point, then polygon centroid as fallback
        sql_point = (
            """
            SELECT 
                p.osm_id,
                p.name,
                p.amenity, p.shop, p.tourism, p.leisure, p.building,
                p.operator, p.brand,
                ST_Y(ST_Transform(p.way, 4326)) AS latitude,
                ST_X(ST_Transform(p.way, 4326)) AS longitude,
                hstore_to_json(p.tags) AS tags_json
            FROM planet_osm_point p
            WHERE p.osm_id = %s
            """
        )

        sql_poly = (
            """
            SELECT 
                g.osm_id,
                g.name,
                g.amenity, g.shop, g.tourism, g.leisure, g.building,
                g.operator, g.brand,
                ST_Y(ST_Transform(ST_Centroid(g.way), 4326)) AS latitude,
                ST_X(ST_Transform(ST_Centroid(g.way), 4326)) AS longitude,
                hstore_to_json(g.tags) AS tags_json
            FROM planet_osm_polygon g
            WHERE g.osm_id = %s
            """
        )

        try:
            with self._connect() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(sql_point, (osm_id,))
                    row = cur.fetchone()
                    if row:
                        return self._row_to_poi(row)
                    cur.execute(sql_poly, (osm_id,))
                    row = cur.fetchone()
                    if row:
                        return self._row_to_poi(row)
            return None
        except Exception as e:
            logger.error(f"PostGIS get_poi_by_id error: {e}")
            return None

    def get_poi_statistics(self, region: str = None) -> Dict[str, Any]:
        # basic counts from planet_osm_point
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM planet_osm_point")
                    total = cur.fetchone()[0]
                    cur.execute(
                        """
                        SELECT key, COUNT(*) FROM (
                            SELECT CASE
                                WHEN amenity IS NOT NULL THEN 'amenity'
                                WHEN shop IS NOT NULL THEN 'shop'
                                WHEN tourism IS NOT NULL THEN 'tourism'
                                WHEN leisure IS NOT NULL THEN 'leisure'
                                WHEN building IS NOT NULL THEN 'building'
                                ELSE 'other'
                            END AS key
                            FROM planet_osm_point
                        ) t
                        GROUP BY key
                        ORDER BY COUNT(*) DESC
                        """
                    )
                    cats = cur.fetchall()
            return {
                "total_pois": total,
                "categories": [{"category": k, "count": v} for (k, v) in cats],
                "region": region or "all",
            }
        except Exception as e:
            logger.error(f"PostGIS get_poi_statistics error: {e}")
            return {"total_pois": 0, "categories": [], "region": region or "all"}

    


    def get_all_pois(
        self,
        region: Optional[str] = None,
        limit: Optional[int] = None,
        min_lat: Optional[float] = None,
        min_lon: Optional[float] = None,
        max_lat: Optional[float] = None,
        max_lon: Optional[float] = None,
        sample_size: Optional[int] = None,
        **filter_params: Any,
    ) -> List[Dict[str, Any]]:
        # prefer bounds if provided
        if None not in (min_lat, min_lon, max_lat, max_lon):
            return self.get_pois_in_bounds(
                min_lat=min_lat, min_lon=min_lon, max_lat=max_lat, max_lon=max_lon, category=None, limit=limit or 5000
            )

        # otherwise return all POIs
        sql = (
            """
            SELECT 
                p.osm_id,
                p.name,
                p.amenity, p.shop, p.tourism, p.leisure, p.building,
                p.operator, p.brand,
                ST_Y(ST_Transform(p.way, 4326)) AS latitude,
                ST_X(ST_Transform(p.way, 4326)) AS longitude,
                hstore_to_json(p.tags) AS tags_json
            FROM planet_osm_point p
            WHERE p.amenity IS NOT NULL OR p.shop IS NOT NULL OR p.tourism IS NOT NULL OR p.leisure IS NOT NULL OR p.building IS NOT NULL
            """
        )

        # add LIMIT only if specified
        if limit is not None:
            sql += " LIMIT %s"

        try:
            logger.info(f"get_all_pois called with limit={limit}")
            with self._connect() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    if limit is not None:
                        logger.info(f"Executing SQL with limit {limit}")
                        cur.execute(sql, (limit,))
                    else:
                        logger.info("Executing SQL without limit")
                        cur.execute(sql)
                    rows = cur.fetchall()
                    logger.info(f"Query returned {len(rows)} rows")
            return [self._row_to_poi(r) for r in rows]
        except Exception as e:
            logger.error(f"PostGIS get_all_pois error: {e}")
            return []


# global postgis manager
_postgis_manager: Optional[PostGISGeoDatabaseManager] = None


def get_geo_database_manager() -> PostGISGeoDatabaseManager:
    """
    get the global postgis manager
    """
    # get the global postgis manager
    global _postgis_manager
    
    # if the postgis manager is not set, set it
    if _postgis_manager is None:
        _postgis_manager = PostGISGeoDatabaseManager()
    
    # return the pois manager
    return _postgis_manager


