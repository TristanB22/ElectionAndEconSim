"""
Routing service for Valhalla integration.

Production-grade implementation with:
- Multi-modal routing (auto, pedestrian, bicycle, etc.)
- Mode-specific costing options
- Future-proof parameter support
- Clean error handling
"""

import requests
import polyline
from typing import Optional, List, Dict, Any

from Reporting.config import settings
from Reporting.services.routing_config import (
    validate_mode,
    get_costing_options,
    MODE_LABELS,
)


class RoutingService:
    """Service for managing routing requests via Valhalla."""
    
    def __init__(self):
        self.base_url = settings.VALHALLA_BASE_URL
        self.timeout = settings.VALHALLA_TIMEOUT
        self.session = requests.Session()
    
    
    def calculate_route(
        self,
        start_lat: float,
        start_lon: float,
        end_lat: float,
        end_lon: float,
        mode: str = "auto",
        include_directions: bool = False,
        units: str = "miles",
        # Future-proof parameters
        costing_options_override: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Calculate route between two points via Valhalla.
        
        Coordinates are automatically snapped to nearest road.
        Returns decoded lat/lon pairs (not encoded polyline).
        
        Args:
            start_lat: Starting latitude
            start_lon: Starting longitude
            end_lat: Ending latitude
            end_lon: Ending longitude
            mode: Travel mode - "auto" (default), "pedestrian", "bicycle", etc.
            include_directions: If True, include first-person turn-by-turn directions
            units: Distance units - "miles" (default) or "kilometers"
            costing_options_override: Override default costing options
        
        Returns:
            {
                "coordinates": [[lon, lat], ...],
                "distance_km": float,
                "distance_miles": float,
                "duration_minutes": float,
                "has_toll": bool,
                "has_highway": bool,
                "mode": str,
                "mode_label": str,
                "directions": [...] (if include_directions=True)
            }
        """
        
        # Validate mode
        try:
            mode = validate_mode(mode)
        except ValueError as e:
            raise ValueError(str(e))
        
        # Get mode-specific costing options
        costing_options = get_costing_options(mode, costing_options_override)
        
        # Build Valhalla request
        valhalla_request = {
            "locations": [
                {"lat": start_lat, "lon": start_lon},
                {"lat": end_lat, "lon": end_lon}
            ],
            "costing": mode,
            "units": units,
            "shape_format": "polyline6",
            "directions_options": {
                "units": units,
                "narrative": include_directions
            },
            "costing_options": {
                mode: costing_options
            }
        }
        
        # Query Valhalla
        try:
            response = self.session.post(
                f"{self.base_url}/route",
                json=valhalla_request,
                headers={"Content-Type": "application/json"},
                timeout=self.timeout
            )
            response.raise_for_status()
            valhalla_data = response.json()
        
        except requests.exceptions.Timeout:
            raise RuntimeError(
                f"Valhalla routing timeout after {self.timeout}s. "
                "The route may be too long or the service is overloaded."
            )
        except requests.exceptions.ConnectionError:
            raise RuntimeError(
                f"Cannot connect to Valhalla at {self.base_url}. "
                "Check that the service is running on the NAS."
            )
        except requests.exceptions.HTTPError as e:
            error_detail = e.response.text
            raise RuntimeError(
                f"Valhalla returned error {e.response.status_code}: {error_detail}"
            )
        except Exception as e:
            raise RuntimeError(f"Valhalla routing failed: {str(e)}")
        
        # Parse response
        trip = valhalla_data.get("trip", {})
        leg = trip.get("legs", [{}])[0]
        summary = leg.get("summary", {})
        
        # Decode polyline to lat/lon pairs
        encoded_shape = leg.get("shape", "")
        decoded_coords = polyline.decode(encoded_shape, precision=6)
        
        # Convert to [lon, lat] format (GeoJSON standard)
        coordinates = [[lon, lat] for lat, lon in decoded_coords]
        
        # Convert distance based on units
        distance_value = summary.get("length", 0)
        if units == "miles":
            distance_km = distance_value * 1.60934
            distance_miles = distance_value
        else:
            distance_km = distance_value
            distance_miles = distance_value * 0.621371
        
        # Build result
        result = {
            "coordinates": coordinates,
            "distance_km": distance_km,
            "distance_miles": distance_miles,
            "duration_minutes": summary.get("time", 0) / 60,
            "has_toll": summary.get("has_toll", False),
            "has_highway": summary.get("has_highway", False),
            "mode": mode,
            "mode_label": MODE_LABELS.get(mode, mode.title()),
        }
        
        # Add first-person directions if requested
        if include_directions:
            directions = self._format_directions(
                leg.get("maneuvers", []),
                units
            )
            result["directions"] = directions
        
        return result
    
    
    def _format_directions(
        self,
        maneuvers: List[Dict[str, Any]],
        units: str
    ) -> List[str]:
        """
        Convert Valhalla maneuvers to first-person natural language directions.
        
        Example output:
        [
            "Head north on Main Street for 0.3 miles",
            "Turn right onto US Route 1 and continue for 45.2 miles",
            "Take exit 113 toward Augusta",
            "Arrive at your destination"
        ]
        """
        directions = []
        
        for maneuver in maneuvers:
            instruction = maneuver.get("instruction", "")
            distance = maneuver.get("length", 0)  # in miles or km
            
            # Format distance
            if distance < 0.1:
                distance_str = ""
            elif distance < 1.0:
                unit_label = "miles" if units == "miles" else "kilometers"
                distance_str = f" for {distance:.1f} {unit_label}"
            else:
                unit_label = "miles" if units == "miles" else "kilometers"
                distance_str = f" and continue for {distance:.1f} {unit_label}"
            
            # Combine instruction with distance
            if distance_str:
                direction = f"{instruction}{distance_str}"
            else:
                direction = instruction
            
            directions.append(direction)
        
        return directions


# Global service instance
routing_service = RoutingService()

