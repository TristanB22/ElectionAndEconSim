"""
Routing API endpoints for Valhalla integration.

Production-grade implementation with multi-modal support.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

from Reporting.services.routing_service import routing_service
from Reporting.services.routing_config import SUPPORTED_MODES, MODE_LABELS


router = APIRouter(prefix="/api/routing", tags=["routing"])


class RouteRequest(BaseModel):
    """Request body for route calculation."""
    start_lat: float = Field(..., description="Starting latitude", ge=-90, le=90)
    start_lon: float = Field(..., description="Starting longitude", ge=-180, le=180)
    end_lat: float = Field(..., description="Ending latitude", ge=-90, le=90)
    end_lon: float = Field(..., description="Ending longitude", ge=-180, le=180)
    
    # Core parameters
    mode: str = Field(
        "auto",
        description=f"Travel mode: {', '.join(SUPPORTED_MODES)}"
    )
    include_directions: bool = Field(
        False,
        description="Include first-person turn-by-turn directions"
    )
    units: str = Field(
        "miles",
        description="Distance units: 'miles' or 'kilometers'"
    )
    
    # Future-proof parameters
    costing_options: Optional[Dict[str, Any]] = Field(
        None,
        description="Override default costing options for mode"
    )


@router.post("/route")
async def calculate_route(request: RouteRequest):
    """
    Calculate optimal route between two points using Valhalla.
    
    Supports multiple transportation modes with mode-specific routing logic.
    Coordinates are automatically snapped to nearest routable edge.
    
    ## Supported Modes
    
    - **auto**: Standard driving (cars, trucks)
    - **pedestrian**: Walking and hiking paths
    - **bicycle**: Bicycle routing with cycleway preference
    - **bus**: Public bus routing (requires GTFS data)
    - **transit**: Walking + transit + transfers (requires GTFS)
    - **truck**: Heavy vehicle routing with restrictions
    - **motor_scooter**: Moped/motorcycle routing
    
    ## Request Example
    
    ```json
    {
        "start_lat": 43.6591,
        "start_lon": -70.2568,
        "end_lat": 44.8012,
        "end_lon": -68.7778,
        "mode": "auto",
        "include_directions": false,
        "units": "miles"
    }
    ```
    
    ## Response Example
    
    ```json
    {
        "coordinates": [[lon, lat], [lon, lat], ...],
        "distance_km": 207.0,
        "distance_miles": 128.7,
        "duration_minutes": 117.3,
        "has_toll": true,
        "has_highway": true,
        "mode": "auto",
        "mode_label": "Driving",
        "directions": [...]  // Only if include_directions=true
    }
    ```
    """
    try:
        result = routing_service.calculate_route(
            start_lat=request.start_lat,
            start_lon=request.start_lon,
            end_lat=request.end_lat,
            end_lon=request.end_lon,
            mode=request.mode,
            include_directions=request.include_directions,
            units=request.units,
            costing_options_override=request.costing_options,
        )
        
        return JSONResponse(content=result)
    
    except ValueError as e:
        # Invalid mode or parameters
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        # Valhalla-specific errors (timeout, connection, etc.)
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        # Unexpected errors
        raise HTTPException(status_code=500, detail=f"Routing failed: {str(e)}")


@router.get("/modes")
async def get_supported_modes():
    """
    Get list of supported routing modes with descriptions.
    
    Returns:
        {
            "modes": [
                {"id": "auto", "label": "Driving"},
                {"id": "pedestrian", "label": "Walking"},
                ...
            ]
        }
    """
    modes = [
        {"id": mode, "label": MODE_LABELS.get(mode, mode.title())}
        for mode in SUPPORTED_MODES
    ]
    
    return JSONResponse(content={"modes": modes})

