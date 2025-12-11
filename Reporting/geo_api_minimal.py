"""
Minimal Geo API endpoints - NO PostGIS dependencies
Only uses STR-tree for POI queries and MySQL for POI details
"""

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse, FileResponse
from typing import Dict, Any
import os
import logging
from pathlib import Path
import httpx

OSM_MAX_ZOOM = int(os.getenv("OSM_MAX_ZOOM", "19"))
OSM_USER_AGENT = os.getenv(
    "OSM_USER_AGENT",
    "world-sim-tile-proxy/1.0 (+https://tile.openstreetmap.org/; contact: change-me@example.com)",
)

# Configure logging
logger = logging.getLogger(__name__)

# Create router
geo_router = APIRouter(prefix="/api/geo", tags=["geo"])

# ==========================
# Feature toggles via environment
# ==========================
def _env_flag(name: str, default: bool = True) -> bool:
    val = str(os.getenv(name, str(default))).lower()
    return val in ("1", "true", "yes", "on")

GEO_ENABLE_TILES = _env_flag("GEO_ENABLE_TILES", True)
GEO_ENABLE_VECTOR_FEATURES = _env_flag("GEO_ENABLE_VECTOR_FEATURES", False)  # Disabled by default
GEO_ENABLE_POIS = _env_flag("GEO_ENABLE_POIS", True)

@geo_router.get("/config")
async def get_geo_config():
    """Expose which geo features are enabled to the frontend."""
    return {
        "tiles": GEO_ENABLE_TILES,
        "vector": GEO_ENABLE_VECTOR_FEATURES,  # Disabled - no PostGIS
        "pois": GEO_ENABLE_POIS
    }

@geo_router.get("/tiles/{z}/{x}/{y}.png")
async def get_tile(request: Request, z: int, x: int, y: int):
    """Serve tiles from NAS storage with proxy-on-miss."""
    if not GEO_ENABLE_TILES:
        raise HTTPException(status_code=404, detail="Tiles disabled")

    # Clamp zoom levels that the upstream tile server does not support
    # to avoid spamming OpenStreetMap with invalid requests.
    if z < 0 or z > OSM_MAX_ZOOM:
        logger.warning("Requested tile at unsupported zoom level z=%s (max=%s): %s/%s", z, OSM_MAX_ZOOM, x, y)
        # Treat as missing rather than proxying a guaranteed bad request.
        raise HTTPException(status_code=404, detail="Tile zoom level not supported")

    try:
        # Get tile directory from environment
        tiles_dir = os.getenv("NAS_MAPS_DATA_DIRECTORY", "/Volumes/Master Data/OpenStreetMap")
        tile_path = Path(tiles_dir) / "tiles" / str(z) / str(x) / f"{y}.png"

        # If the client has already disconnected (e.g., user panned away),
        # avoid doing any further work for this tile.
        if await request.is_disconnected():
            logger.info("Client disconnected before tile %s/%s/%s could be served", z, x, y)
            return JSONResponse(status_code=499, content={"detail": "Client disconnected"})

        if tile_path.exists():
            return FileResponse(tile_path, media_type="image/png")

        # Proxy-on-miss: download from OSM and save
        async with httpx.AsyncClient(
            headers={"User-Agent": OSM_USER_AGENT},
            timeout=httpx.Timeout(10.0, connect=5.0),
        ) as client:
            osm_url = f"https://tile.openstreetmap.org/{z}/{x}/{y}.png"

            # Check again before making the outbound request so we don't
            # hit the upstream server if the tile is no longer needed.
            if await request.is_disconnected():
                logger.info("Client disconnected before upstream fetch for tile %s/%s/%s", z, x, y)
                return JSONResponse(status_code=499, content={"detail": "Client disconnected"})

            response = await client.get(osm_url)

            if response.status_code == 200:
                # Save tile for future use
                tile_path.parent.mkdir(parents=True, exist_ok=True)
                tile_path.write_bytes(response.content)
                return FileResponse(tile_path, media_type="image/png")
            else:
                # Log the upstream error status to aid debugging but do not
                # propagate 4xx/5xx codes directly to clients.
                logger.warning(
                    "Upstream tile request to %s returned status %s", osm_url, response.status_code
                )
                raise HTTPException(status_code=404, detail="Tile not found")
                
    except Exception as e:
        logger.error(f"Error serving tile {z}/{x}/{y}: {e}")
        raise HTTPException(status_code=500, detail="Failed to serve tile")

@geo_router.get("/tiles/info")
async def get_tile_info():
    """Get information about tile serving configuration."""
    tiles_dir = os.getenv("NAS_MAPS_DATA_DIRECTORY", "/Volumes/Master Data/OpenStreetMap")
    tiles_path = Path(tiles_dir) / "tiles"
    
    return {
        "enabled": GEO_ENABLE_TILES,
        "directory": str(tiles_path),
        "exists": tiles_path.exists(),
        "proxy_on_miss": True
    }

@geo_router.get("/features/all")
async def get_all_features(min_lat: float, min_lon: float, max_lat: float, max_lon: float, zoom: int = 10):
    """Return empty features - vector features disabled (no PostGIS)."""
    if not GEO_ENABLE_VECTOR_FEATURES:
        return JSONResponse(content={
            "roads": {"type": "FeatureCollection", "features": []},
            "water": {"type": "FeatureCollection", "features": []},
            "buildings": {"type": "FeatureCollection", "features": []},
            "boundaries": {"type": "FeatureCollection", "features": []}
        })
    
    # If vector features are enabled but we don't have PostGIS, return empty
    return JSONResponse(content={
        "roads": {"type": "FeatureCollection", "features": []},
        "water": {"type": "FeatureCollection", "features": []},
        "buildings": {"type": "FeatureCollection", "features": []},
        "boundaries": {"type": "FeatureCollection", "features": []}
    })

@geo_router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Minimal Geo API",
        "features": {
            "tiles": GEO_ENABLE_TILES,
            "vector": GEO_ENABLE_VECTOR_FEATURES,
            "pois": GEO_ENABLE_POIS
        }
    }
