#!/usr/bin/env python3
from __future__ import annotations

from fastapi import APIRouter, Query, Request, Depends
from fastapi.responses import JSONResponse
from typing import Optional

from ..services import geospatial_service
from ..dependencies import get_client_session, require_api_key

router = APIRouter(
    prefix="/api",
    tags=["geospatial"],
    # Note: API key enforcement handled by middleware, not router-level dependency
)


@router.get("/pois/spatial")
def pois_spatial(
    request: Request,
    min_lat: float = Query(...),
    min_lon: float = Query(...),
    max_lat: float = Query(...),
    max_lon: float = Query(...),
    session_id: str = Depends(get_client_session),
    categories: Optional[str] = Query(None),
    # Allow the client to request a limit, but clamp it in the service layer
    # to a safe maximum (see settings.POIS_MAX_POINTS).
    max_points: int = Query(500_000),
    zoom: Optional[int] = Query(None),
    include_details: bool = Query(False),
    exclude_other: bool = Query(False, description="Exclude POIs categorized as 'other'"),
    include_only_other: bool = Query(False, description="Only return POIs categorized as 'other'"),
):
    """Get POIs within a bounding box from PostGIS."""
    simulation_id = getattr(request.state, "simulation_id", None)
    return geospatial_service.get_pois_spatial(
        min_lat=min_lat,
        min_lon=min_lon,
        max_lat=max_lat,
        max_lon=max_lon,
        session_id=session_id,
        simulation_id=simulation_id,
        categories=categories,
        max_points=max_points,
        zoom=zoom,
        include_details=include_details,
        exclude_other=exclude_other,
        include_only_other=include_only_other,
    )


@router.get("/roads/spatial")
def roads_spatial(
    request: Request,
    min_lat: float = Query(...),
    min_lon: float = Query(...),
    max_lat: float = Query(...),
    max_lon: float = Query(...),
    zoom: Optional[int] = Query(None),
    max_features: int = Query(10_000),
    enforce_limits: Optional[bool] = Query(None, description="Override config to enforce LIMITs on query"),
    include_excluded: Optional[bool] = Query(None, description="Override config to include footway/path/cycleway etc."),
    include_boundaries: Optional[bool] = Query(None, description="Include administrative boundaries in response"),
):
    """Get roads and boundaries within a bounding box."""
    simulation_id = getattr(request.state, "simulation_id", None)
    return geospatial_service.get_roads_spatial(
        min_lat=min_lat,
        min_lon=min_lon,
        max_lat=max_lat,
        max_lon=max_lon,
        simulation_id=simulation_id,
        zoom=zoom,
        max_features=max_features,
        enforce_limits=enforce_limits,
        include_excluded=include_excluded,
        include_boundaries=include_boundaries,
    )


@router.get("/pois/spatial/heatmap")
def pois_heatmap(
    request: Request,
    min_lat: float = Query(None),
    min_lon: float = Query(None),
    max_lat: float = Query(None),
    max_lon: float = Query(None),
    max_points: int = Query(1_000_000),
):
    """Return aggregated heatmap data for POIs in bbox (delegates to service)."""
    simulation_id = getattr(request.state, "simulation_id", None)
    # Provide safe defaults if parameters are missing (fallback to broad bbox)
    min_lat = min_lat if min_lat is not None else -90.0
    min_lon = min_lon if min_lon is not None else -180.0
    max_lat = max_lat if max_lat is not None else 90.0
    max_lon = max_lon if max_lon is not None else 180.0
    return geospatial_service.get_pois_heatmap(min_lat, min_lon, max_lat, max_lon, max_points, simulation_id)


@router.get("/pois/spatial/{osm_id}")
def get_poi_by_id(osm_id: int, request: Request):
    """Get POI details by OSM ID from MySQL database."""
    simulation_id = getattr(request.state, "simulation_id", None)
    return geospatial_service.get_poi_details(osm_id, simulation_id)


@router.get("/pois/spatial/status")
def get_pois_status(request: Request):
    """Get POI spatial data status/statistics."""
    simulation_id = getattr(request.state, "simulation_id", None)
    return geospatial_service.get_pois_status(simulation_id)


@router.get("/buildings/spatial")
def buildings_spatial(
    request: Request,
    min_lat: float = Query(...),
    min_lon: float = Query(...),
    max_lat: float = Query(...),
    max_lon: float = Query(...),
    zoom: Optional[int] = Query(None),
    max_features: int = Query(10_000),
):
    """Get buildings within a bounding box."""
    simulation_id = getattr(request.state, "simulation_id", None)
    return geospatial_service.get_buildings_spatial(
        min_lat, min_lon, max_lat, max_lon, simulation_id, zoom, max_features
    )


@router.get("/addresses/search")
def search_addresses(
    request: Request,
    query: str = Query(...),
    limit: int = Query(10),
):
    """Search addresses by text query."""
    simulation_id = getattr(request.state, "simulation_id", None)
    return geospatial_service.search_addresses(query, limit, simulation_id)


