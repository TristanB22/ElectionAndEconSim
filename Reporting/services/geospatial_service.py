#!/usr/bin/env python3
from __future__ import annotations

import json as _json
import time
import threading
from typing import Any, Dict, List, Optional

try:
	import psycopg2  # type: ignore
	import psycopg2.extras  # type: ignore
	PSYCOPG2_AVAILABLE = True
except ImportError:
	PSYCOPG2_AVAILABLE = False
	psycopg2 = None
from fastapi.responses import JSONResponse

from ..dependencies import postgis_connection
from ..config import settings

# Session tracking for query cancellation
_active_pg_queries: Dict[str, Any] = {}
_active_pg_lock = threading.Lock()


def get_pois_spatial(
    min_lat: float,
    min_lon: float,
    max_lat: float,
    max_lon: float,
    session_id: str,
    simulation_id: Optional[str] = None,
    categories: Optional[str] = None,
    max_points: int = 5000000,
    zoom: Optional[int] = None,
    include_details: bool = False,
    exclude_other: bool = False,
    include_only_other: bool = False,
) -> JSONResponse:
    """
    Get POIs within a bounding box from PostGIS.
    
    Args:
        exclude_other: If True, exclude POIs that would be categorized as "other"
        include_only_other: If True, only return POIs that would be categorized as "other"
    """
    # Enforce a hard upper bound on max_points to protect the database
    # from accidentally huge LIMIT values (e.g. 5,000,000).
    # This does not change the API contract from the caller's perspective,
    # but ensures we never ask PostGIS for more than POIS_MAX_POINTS rows.
    requested_max_points = max_points
    max_points = max(1_000, min(max_points, settings.POIS_MAX_POINTS))
    with _active_pg_lock:
        if session_id in _active_pg_queries:
            old_conn = _active_pg_queries.pop(session_id)
            try:
                old_conn.cancel()
            except (psycopg2.Error, AttributeError):
                pass

    start_time = time.perf_counter()
    try:
        with postgis_connection() as conn:
            with _active_pg_lock:
                _active_pg_queries[session_id] = conn

            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                env_sql = "ST_Transform(ST_SetSRID(ST_MakeEnvelope(%s,%s,%s,%s,4326),4326),3857)"
                params = [min_lon, min_lat, max_lon, max_lat]
                
                # NOTE: simulation_id is accepted for API consistency but not used in this query
                # as the planet_osm tables are not simulation-specific.
                
                # Always include tags_json for proper categorization, even when include_details=False
                # Allows _categorize_poi to check tags hstore for category information
                # NOTE: 'craft' column doesn't exist in planet_osm_point, will check tags instead
                query_fields = """
                    osm_id, ST_X(ST_Transform(way,4326)) AS lon, ST_Y(ST_Transform(way,4326)) AS lat,
                    name, amenity, shop, tourism, leisure, highway, building, office, religion,
                    historic, "natural", place, "addr:housenumber", "addr:housename",
                    hstore_to_json(tags) AS tags_json
                """ if include_details else """
                    osm_id, ST_X(ST_Transform(way,4326)) AS lon, ST_Y(ST_Transform(way,4326)) AS lat,
                    amenity, shop, tourism, leisure, office, religion, historic, place, building,
                    hstore_to_json(tags) AS tags_json
                """
                
                # Build WHERE clause with category filtering
                where_clauses = [f"way && {env_sql}"]
                
                # Add category filtering logic
                if exclude_other and not include_only_other:
                    # Exclude "other" POIs - must have at least one category column or tag
                    where_clauses.append("""(
                        amenity IS NOT NULL OR
                        shop IS NOT NULL OR
                        tourism IS NOT NULL OR
                        leisure IS NOT NULL OR
                        office IS NOT NULL OR
                        religion IS NOT NULL OR
                        historic IS NOT NULL OR
                        place IS NOT NULL OR
                        building IS NOT NULL OR
                        tags ? 'amenity' OR
                        tags ? 'shop' OR
                        tags ? 'tourism' OR
                        tags ? 'leisure' OR
                        tags ? 'healthcare' OR
                        tags ? 'office' OR
                        tags ? 'craft' OR
                        tags ? 'religion' OR
                        tags ? 'historic' OR
                        tags ? 'building' OR
                        tags ? 'place'
                    )""")
                elif include_only_other:
                    # Include ONLY "other" POIs - must have NO category columns or tags
                    where_clauses.append("""(
                        amenity IS NULL AND
                        shop IS NULL AND
                        tourism IS NULL AND
                        leisure IS NULL AND
                        office IS NULL AND
                        religion IS NULL AND
                        historic IS NULL AND
                        place IS NULL AND
                        building IS NULL AND
                        NOT (tags ? 'amenity') AND
                        NOT (tags ? 'shop') AND
                        NOT (tags ? 'tourism') AND
                        NOT (tags ? 'leisure') AND
                        NOT (tags ? 'healthcare') AND
                        NOT (tags ? 'office') AND
                        NOT (tags ? 'craft') AND
                        NOT (tags ? 'religion') AND
                        NOT (tags ? 'historic') AND
                        NOT (tags ? 'building') AND
                        NOT (tags ? 'place')
                    )""")
                
                where_clause = " AND ".join(where_clauses)
                
                sql = f"""
                    SELECT {query_fields} FROM planet_osm_point
                    WHERE {where_clause} LIMIT %s
                """
                params.append(max_points)

                # Execute with a defensive fallback: if the database raises an
                # error for a very large LIMIT (e.g. resource constraints or
                # timeouts), retry once with a smaller limit instead of
                # surfacing a 500 to the client.
                try:
                    cur.execute(sql, params)
                    rows = cur.fetchall()
                except psycopg2.Error:
                    # Only retry when the effective limit is large; keep real
                    # SQL errors visible for small queries.
                    if max_points > 50_000:
                        safe_limit = 50_000
                        params[-1] = safe_limit
                        cur.execute(sql, params)
                        rows = cur.fetchall()
                        max_points = safe_limit
                    else:
                        raise

        query_time = (time.perf_counter() - start_time) * 1000.0

        features = []
        for row in rows:
            category, subcategory = _categorize_poi(row)
            props = {
                "osm_id": row.get("osm_id"), "category": category, "subcategory": subcategory, "name": row.get("name")
            }
            if include_details and row.get("tags_json"):
                props["tags"] = row["tags_json"]
            
            features.append({
                "type": "Feature",
                "properties": props,
                "geometry": {"type": "Point", "coordinates": [row.get("lon"), row.get("lat")]},
            })

        metadata: Dict[str, Any] = {
            "count": len(features),
            "query_time_ms": round(query_time, 2),
        }
        if requested_max_points != max_points:
            metadata["requested_max_points"] = requested_max_points
            metadata["effective_max_points"] = max_points

        return JSONResponse(
            content={
                "type": "FeatureCollection",
                "features": features,
                "metadata": metadata,
            },
            headers={"Cache-Control": "public, max-age=30"},
        )

    except psycopg2.Error as e:
        return JSONResponse(status_code=500, content={"error": f"Database error: {e}"})
    finally:
        with _active_pg_lock:
            _active_pg_queries.pop(session_id, None)


def get_roads_spatial(
    min_lat: float,
    min_lon: float,
    max_lat: float,
    max_lon: float,
    simulation_id: Optional[str] = None,
    zoom: Optional[int] = None,
    max_features: int = 10000,
    enforce_limits: Optional[bool] = None,
    include_excluded: Optional[bool] = None,
    include_boundaries: Optional[bool] = None,
) -> JSONResponse:
    """Get road centerlines from PostGIS within a bbox."""
    start_time = time.perf_counter()
    try:
        with postgis_connection() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            z = zoom or 10
            # Use simplified roads table only for very low zoom; otherwise use full line table
            if z < 10:
                table, max_features = "planet_osm_roads", min(max_features, 2000)
            elif z < 14:
                table, max_features = "planet_osm_line", min(max_features, 8000)
            else:
                table, max_features = "planet_osm_line", min(max_features, 12000)

            where = ["way && ST_Transform(ST_SetSRID(ST_MakeEnvelope(%s,%s,%s,%s,4326),4326),3857)"]
            params = [min_lon, min_lat, max_lon, max_lat]

            # Determine boundary inclusion
            _include_boundaries = True if include_boundaries is None else include_boundaries
            _include_excluded = include_excluded if include_excluded is not None else settings.ROADS_INCLUDE_EXCLUDED

            if table == "planet_osm_roads":
                # planet_osm_roads: simplified table for very low zoom
                # Keep only major roads (including ferry). Do not reference non-existent columns.
                where.append("highway IN ('motorway','trunk','primary','secondary','ferry')")

            elif table == "planet_osm_line":
                # planet_osm_line: full table for high zoom
                # Optionally exclude boundaries
                if _include_boundaries:
                    where.append("(highway IS NOT NULL OR boundary IS NOT NULL OR tags ? 'border_type')")
                else:
                    where.append("(highway IS NOT NULL)")
                # Configurable inclusion of previously excluded routes
                if not _include_excluded:
                    where.append("(highway NOT IN ('footway','path','steps','cycleway','bridleway','corridor','pedestrian') OR highway IS NULL)")

            # Build appropriate ORDER BY per table to avoid referencing non-existent columns
            if table == "planet_osm_roads":
                order = """
                    CASE
                    WHEN highway IN ('motorway','trunk') THEN 1
                    WHEN highway IN ('primary') THEN 2
                    WHEN highway IN ('secondary') THEN 3
                    WHEN highway IN ('tertiary') THEN 4
                    WHEN highway IN ('residential','unclassified') THEN 5
                    ELSE 6 END, COALESCE(name,'')
                """
            else:
                order = """
                    CASE
                    WHEN tags->'border_type' = 'country' THEN 1 WHEN tags->'border_type' = 'state' THEN 2
                    WHEN tags->'border_type' = 'county' THEN 3 WHEN tags->'border_type' = 'city' THEN 4
                    WHEN tags->'border_type' = 'town' THEN 5 WHEN boundary IS NOT NULL THEN 6
                    WHEN highway IN ('motorway','trunk') THEN 7 WHEN highway IN ('primary') THEN 8
                    WHEN highway IN ('secondary') THEN 9 WHEN highway IN ('tertiary') THEN 10
                    WHEN highway IN ('residential','unclassified') THEN 11 ELSE 12 END, COALESCE(name,'')
                """
            
            # Configurable limit enforcement
            _enforce_limits = enforce_limits if enforce_limits is not None else settings.ROADS_ENFORCE_LIMITS
            if table == "planet_osm_roads":
                if _enforce_limits:
                    query = f"""
                        SELECT osm_id, name, highway, ref, oneway, bridge, tunnel, surface,
                               ST_AsGeoJSON(ST_Transform(way, 4326)) as geometry
                        FROM {table} WHERE {' AND '.join(where)} ORDER BY {order} LIMIT %s
                    """
                    params.append(max_features)
                else:
                    query = f"""
                        SELECT osm_id, name, highway, ref, oneway, bridge, tunnel, surface,
                               ST_AsGeoJSON(ST_Transform(way, 4326)) as geometry
                        FROM {table} WHERE {' AND '.join(where)} ORDER BY {order}
                    """
            else:
                if _enforce_limits:
                    query = f"""
                        SELECT osm_id, name, highway, ref, boundary, admin_level, oneway, bridge, tunnel, surface, access,
                               ST_AsGeoJSON(ST_Transform(way, 4326)) as geometry, hstore_to_json(tags) AS tags_json
                        FROM {table} WHERE {' AND '.join(where)} ORDER BY {order} LIMIT %s
                    """
                    params.append(max_features)
                else:
                    query = f"""
                        SELECT osm_id, name, highway, ref, boundary, admin_level, oneway, bridge, tunnel, surface, access,
                               ST_AsGeoJSON(ST_Transform(way, 4326)) as geometry, hstore_to_json(tags) AS tags_json
                        FROM {table} WHERE {' AND '.join(where)} ORDER BY {order}
                    """
            
            cur.execute(query, params)
            rows = cur.fetchall()

        query_time = (time.perf_counter() - start_time) * 1000.0
        features = []
        for row in rows:
            geom = _json.loads(row["geometry"]) if row.get("geometry") else None
            if not geom:
                continue

            if table == "planet_osm_roads":
                props = {
                    "osm_id": row.get("osm_id"),
                    "name": row.get("name"),
                    "highway": row.get("highway"),
                    "ref": row.get("ref"),
                    "oneway": row.get("oneway"),
                    "bridge": row.get("bridge"),
                    "tunnel": row.get("tunnel"),
                    "surface": row.get("surface"),
                    "source": table,
                }
            else:
                tags = row.get("tags_json") or {}
                props = {
                    "osm_id": row.get("osm_id"), "name": row.get("name"), "highway": row.get("highway"),
                    "ref": row.get("ref"), "boundary": row.get("boundary"), "admin_level": row.get("admin_level"),
                    "border_type": tags.get("border_type"), "oneway": row.get("oneway"),
                    "maxspeed": tags.get("maxspeed"), "bridge": row.get("bridge"), "tunnel": row.get("tunnel"),
                    "surface": row.get("surface"), "lanes": tags.get("lanes"), "layer": tags.get("layer"),
                    "access": row.get("access"), "tags": tags, "source": table,
                }
            features.append({"type": "Feature", "properties": props, "geometry": geom})

        return JSONResponse(
            content={
                "type": "FeatureCollection", "features": features,
                "metadata": {"count": len(features), "query_time_ms": round(query_time, 2), "source": table},
            },
            headers={"Cache-Control": "public, max-age=30"},
        )

    except psycopg2.Error as e:
        return JSONResponse(status_code=500, content={"error": f"Roads query failed: {e}"})


def get_pois_heatmap(
    min_lat: float,
    min_lon: float,
    max_lat: float,
    max_lon: float,
    max_points: int = 1_000_000,
    simulation_id: Optional[str] = None,
) -> JSONResponse:
    """
    Get POI coordinates from MySQL `poi_master_heatmap` for heatmap visualization.
    Uses the pre-populated heatmap table for performance.
    """
    try:
        import time
        from Database.database_manager import execute_query
        
        start_time = time.perf_counter()
        
        # Build query: bbox-aware if provided; otherwise global random sample
        if None not in (min_lat, min_lon, max_lat, max_lon):
            heatmap_query = (
                "SELECT lat, lon FROM poi_master_heatmap "
                "WHERE lat BETWEEN %s AND %s AND lon BETWEEN %s AND %s "
                "ORDER BY RAND() LIMIT %s"
            )
            params = (min_lat, max_lat, min_lon, max_lon, max_points)
        else:
            heatmap_query = (
                "SELECT lat, lon FROM poi_master_heatmap "
                "ORDER BY RAND() LIMIT %s"
            )
            params = (max_points,)
        
        try:
            # execute_query signature: (query, params, database=None, fetch=True)
            # poi_master_heatmap table is in the 'world_sim_geo' database on NAS MySQL
            result = execute_query(heatmap_query, params, database='world_sim_geo', fetch=True)

            heatmap_points = []
            if result.success and result.data:
                for row in result.data:
                    heatmap_points.append({
                        "type": "Feature",
                        "properties": {"weight": 1},
                        "geometry": {
                            "type": "Point",
                            "coordinates": [float(row['lon']), float(row['lat'])]
                        }
                    })
            else:
                # Log minimal info; keep response consistent
                heatmap_points = []
        except Exception as e:
            print(f"Error getting POIs from poi_master_heatmap table: {e}")
            import traceback
            traceback.print_exc()
            # Fallback to empty heatmap if query fails
            heatmap_points = []
        
        processing_time = (time.perf_counter() - start_time) * 1000
        
        return JSONResponse(
            content={
                "type": "FeatureCollection",
                "features": heatmap_points,
                "metadata": {
                    "count": len(heatmap_points),
                    "processing_time_ms": round(processing_time, 2),
                    "source": "poi_master_heatmap"
                }
            },
            headers={
                "Cache-Control": "public, max-age=3600",
                "X-Processing-Time-ms": f"{processing_time:.1f}",
                "X-Source": "MySQL"
            }
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": f"Heatmap query failed: {e}"})

def _categorize_poi(row: Dict[str, Any]) -> tuple[str, str]:
    """
    Helper to determine category and subcategory from a POI row.
    Checks both dedicated columns and tags hstore for category information.
    """
    # Check dedicated columns first (fastest)
    # NOTE: 'craft' doesn't exist as a column, only in tags
    if row.get("amenity"): return "amenity", row["amenity"]
    if row.get("shop"): return "shop", row["shop"]
    if row.get("tourism"): return "tourism", row["tourism"]
    if row.get("leisure"): return "leisure", row["leisure"]
    if row.get("office"): return "office", row["office"]
    if row.get("religion"): return "religion", row["religion"]
    if row.get("historic"): return "historic", row["historic"]
    if row.get("place"): return "place", row["place"]
    if row.get("building"): return "building", row["building"]
    
    # Check tags hstore if available (for POIs where category is only in tags)
    tags = row.get("tags_json") or {}
    if isinstance(tags, dict):
        # Check OSM category tags in priority order
        if tags.get("amenity"): return "amenity", tags["amenity"]
        if tags.get("shop"): return "shop", tags["shop"]
        if tags.get("tourism"): return "tourism", tags["tourism"]
        if tags.get("leisure"): return "leisure", tags["leisure"]
        if tags.get("healthcare"): return "healthcare", tags["healthcare"]
        if tags.get("office"): return "office", tags["office"]
        if tags.get("craft"): return "craft", tags["craft"]
        if tags.get("religion"): return "religion", tags["religion"]
        if tags.get("historic"): return "historic", tags["historic"]
        if tags.get("building"): return "building", tags["building"]
        if tags.get("place"): return "place", tags["place"]
    
    # If no category found, return "other"
    return "other", "unknown"


def get_poi_details(osm_id: int, simulation_id: Optional[str] = None) -> JSONResponse:
    """Get POI details by OSM ID from PostGIS database."""
    try:
        import time
        start_time = time.perf_counter()
        
        from Database.geo_database_manager_postgis import get_geo_database_manager
        db = get_geo_database_manager()
        poi_data = db.get_poi_by_id(int(osm_id))
        
        search_time = (time.perf_counter() - start_time) * 1000
        
        if not poi_data:
            return JSONResponse(status_code=404, content={"error": "POI not found"})
        
        # Derive display name when explicit name is missing
        def _derive_display_name(p: dict) -> str | None:
            name = p.get('name') or None
            if name:
                return name
            category = p.get('category') or None
            subcategory = p.get('subcategory') or None
            props = p.get('properties') or {}
            tag_keys_in_preference = [
                'amenity', 'shop', 'tourism', 'leisure', 'highway', 'building',
                'office', 'religion', 'historic', 'natural', 'place', 'craft', 'healthcare'
            ]
            for k in tag_keys_in_preference:
                v = props.get(k)
                if isinstance(v, str) and v:
                    subcategory = v
                    if not category:
                        category = k
                    break
            def _humanize(value: str | None) -> str | None:
                if not value:
                    return None
                return value.replace('_', ' ').replace('-', ' ').title()
            if subcategory:
                return _humanize(subcategory)
            if category:
                return _humanize(category)
            return None
        
        # Return POI data in GeoJSON format
        return JSONResponse(
            content={
                "type": "Feature",
                "properties": {
                    "osm_id": poi_data.get('osm_id'),
                    "name": poi_data.get('name'),
                    "display_name": _derive_display_name(poi_data) or poi_data.get('name') or "Unnamed Location",
                    "category": poi_data.get('category'),
                    "subcategory": poi_data.get('subcategory'),
                    "brand": poi_data.get('brand'),
                    "properties": poi_data.get('properties'),
                    "source": "PostGIS",
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [poi_data.get('longitude'), poi_data.get('latitude')]
                }
            },
            headers={
                "X-Search-Time-ms": f"{search_time:.1f}",
                "X-Source": "PostGIS"
            }
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Failed to fetch POI details: {str(e)}"})


def get_pois_status(simulation_id: Optional[str] = None) -> dict:
    """Get the current spatial query status."""
    return {
        "status": "active",
        "source": "PostGIS database",
        "message": "Spatial queries using PostGIS database"
    }


def get_buildings_spatial(
    min_lat: float,
    min_lon: float,
    max_lat: float,
    max_lon: float,
    simulation_id: Optional[str] = None,
    zoom: Optional[int] = None,
    max_features: int = 10_000,
) -> JSONResponse:
    """Get building polygons from PostGIS database with address information."""
    try:
        start_time = time.perf_counter()
        
        with postgis_connection() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Build query based on parameters
            where_conditions = [
                "way && ST_Transform(ST_SetSRID(ST_MakeEnvelope(%s,%s,%s,%s,4326),4326),3857)",
                "building IS NOT NULL"
            ]
            params = [min_lon, min_lat, max_lon, max_lat]
            
            # Adjust limit based on zoom level
            if zoom and zoom < 12:
                max_features = min(max_features, 100000)  # Fewer buildings at low zoom
            elif zoom and zoom < 14:
                max_features = min(max_features, 500000)  # Medium zoom
            
            query = f"""
                SELECT 
                    osm_id,
                    name,
                    "addr:housenumber" as house_number,
                    "addr:housename" as house_name,
                    building,
                    amenity,
                    shop,
                    office,
                    tourism,
                    leisure,
                    religion,
                    historic,
                    ST_AsGeoJSON(ST_Transform(way, 4326)) as geometry,
                    ST_Y(ST_Centroid(ST_Transform(way, 4326))) as lat,
                    ST_X(ST_Centroid(ST_Transform(way, 4326))) as lon
                FROM planet_osm_polygon 
                WHERE {' AND '.join(where_conditions)}
                ORDER BY 
                    CASE 
                        WHEN name IS NOT NULL THEN 1
                        WHEN "addr:housenumber" IS NOT NULL THEN 2
                        ELSE 3
                    END,
                    name
                LIMIT %s
            """
            params.append(max_features)
            
            cur.execute(query, params)
            rows = cur.fetchall()
        
        query_time = (time.perf_counter() - start_time) * 1000
        
        features = []
        for row in rows:
            if not row.get('geometry'):
                continue
            
            geometry = _json.loads(row['geometry'])
            
            properties = {
                "osm_id": row.get('osm_id'),
                "name": row.get('name'),
                "building": row.get('building'),
                "house_number": row.get('house_number'),
                "house_name": row.get('house_name'),
                "amenity": row.get('amenity'),
                "shop": row.get('shop'),
                "office": row.get('office'),
                "tourism": row.get('tourism'),
                "leisure": row.get('leisure'),
                "religion": row.get('religion'),
                "historic": row.get('historic'),
                "lat": row.get('lat'),
                "lon": row.get('lon'),
            }
            
            features.append({
                "type": "Feature",
                "properties": properties,
                "geometry": geometry
            })
        
        return JSONResponse(
            content={
                "type": "FeatureCollection",
                "features": features,
                "metadata": {
                    "count": len(features),
                    "query_time_ms": round(query_time, 2)
                }
            },
            headers={"Cache-Control": "public, max-age=30"}
        )
    
    except psycopg2.Error as e:
        return JSONResponse(status_code=500, content={"error": f"Buildings query failed: {e}"})


def search_addresses(query: str, limit: int = 10, simulation_id: Optional[str] = None) -> dict:
    """
    Simple fallback address search.
    Note: The intelligent search with LLM is not implemented in the service layer.
    This is a basic fallback.
    """
    try:
        if not query or len(query.strip()) < 2:
            return {"results": [], "total": 0, "query": query}
        
        # Try to search POIs by name in PostGIS
        with postgis_connection() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            sql = """
                SELECT osm_id, name, amenity, shop, tourism,
                       ST_Y(ST_Transform(way,4326)) AS lat,
                       ST_X(ST_Transform(way,4326)) AS lon
                FROM planet_osm_point
                WHERE name ILIKE %s
                LIMIT %s
            """
            cur.execute(sql, (f"%{query}%", limit))
            rows = cur.fetchall()
        
        results = []
        for row in rows:
            results.append({
                "name": row.get('name', ''),
                "full_address": row.get('name', ''),
                "amenity": row.get('amenity', ''),
                "shop": row.get('shop', ''),
                "tourism": row.get('tourism', ''),
                "lat": float(row.get('lat', 0)),
                "lon": float(row.get('lon', 0)),
                "result_type": "poi"
            })
        
        return {
            "results": results,
            "total": len(results),
            "query": query
        }
    
    except Exception as e:
        return {
            "results": [],
            "total": 0,
            "query": query,
            "error": str(e)
        }
