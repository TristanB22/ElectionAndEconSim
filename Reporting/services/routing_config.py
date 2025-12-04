"""
Routing configuration for Valhalla costing models.

Defines defaults, penalties, and options for each transportation mode.
"""

from typing import Dict, Any, List

# Supported Valhalla costing models
SUPPORTED_MODES = [
    "auto",           # Standard driving (cars, trucks)
    "pedestrian",     # Walking and hiking
    "bicycle",        # Bicycle routing
    "bus",            # Public bus (requires GTFS)
    "transit",        # Walking + transit + transfers (requires GTFS)
    "truck",          # Heavy vehicle routing
    "motor_scooter",  # Moped/motorcycle
    "auto_shorter",   # Shortest path variant
    "auto_data",      # Data-driven routing
]

# Default costing options for each mode
# These are passed to Valhalla's costing_options parameter
COSTING_OPTIONS: Dict[str, Dict[str, Any]] = {
    "auto": {
        "maneuver_penalty": 5,           # Penalty for turns (seconds)
        "gate_cost": 30,                 # Cost to pass through gate
        "gate_penalty": 300,             # Penalty for gates
        "toll_booth_cost": 15,           # Cost for toll booth
        "toll_booth_penalty": 0,         # No penalty for tolls by default
        "country_crossing_cost": 600,    # 10 minutes to cross border
        "country_crossing_penalty": 0,   # No penalty for crossing
        "use_highways": 1.0,             # Preference for highways (0-1)
        "use_tolls": 1.0,                # Preference for tolls (0-1)
        "use_ferry": 1.0,                # Preference for ferries (0-1)
        "top_speed": 140,                # Max speed in km/h
    },
    "pedestrian": {
        "walking_speed": 5.1,            # km/h (3.2 mph)
        "walkway_factor": 1.0,           # Preference for walkways
        "sidewalk_factor": 1.0,          # Preference for sidewalks
        "alley_factor": 2.0,             # Penalty for alleys
        "driveway_factor": 5.0,          # Penalty for driveways
        "step_penalty": 30,              # Penalty for stairs (seconds)
        "use_ferry": 1.0,
        "use_living_streets": 0.5,       # Preference for living streets
        "use_tracks": 0.5,               # Preference for tracks
        "max_hiking_difficulty": 1,      # 0-6 scale (0=easy, 6=extreme)
    },
    "bicycle": {
        "cycling_speed": 20.0,           # km/h (12.4 mph)
        "use_roads": 0.5,                # Preference for roads (0-1)
        "use_hills": 0.5,                # Tolerance for hills (0-1)
        "avoid_bad_surfaces": 0.25,      # Avoid poor surfaces
        "use_ferry": 1.0,
        "bicycle_type": "Hybrid",        # Road, Hybrid, City, Cross, Mountain
        "maneuver_penalty": 5,
    },
    "bus": {
        "maneuver_penalty": 5,
        "use_bus": 1.0,
        "use_rail": 0.0,                 # Bus-only by default
        "use_transfers": 0.3,            # Penalty for transfers
    },
    "transit": {
        "use_bus": 1.0,
        "use_rail": 1.0,
        "use_transfers": 0.4,
        "walking_speed": 5.1,
    },
    "truck": {
        "maneuver_penalty": 5,
        "gate_cost": 30,
        "gate_penalty": 300,
        "toll_booth_cost": 15,
        "use_highways": 1.0,
        "use_tolls": 1.0,
        "use_ferry": 1.0,
        "height": 4.11,                  # meters (13.5 feet)
        "width": 2.6,                    # meters (8.5 feet)
        "length": 21.64,                 # meters (71 feet)
        "weight": 21.77,                 # metric tons (48,000 lbs)
        "axle_load": 9.07,               # metric tons (20,000 lbs)
        "hazmat": False,                 # Hazardous materials
    },
    "motor_scooter": {
        "maneuver_penalty": 5,
        "use_highways": 0.5,             # Avoid highways
        "use_tolls": 0.5,
        "use_ferry": 1.0,
        "top_speed": 45,                 # km/h
    }
}

# Human-readable mode names
MODE_LABELS: Dict[str, str] = {
    "auto": "Driving",
    "pedestrian": "Walking",
    "bicycle": "Cycling",
    "bus": "Bus",
    "transit": "Public Transit",
    "truck": "Truck",
    "motor_scooter": "Scooter/Motorcycle",
    "auto_shorter": "Driving (Shortest)",
    "auto_data": "Driving (Data-Driven)",
}

# Default speeds by mode (km/h) - for estimation when Valhalla unavailable
DEFAULT_SPEEDS: Dict[str, float] = {
    "auto": 60.0,
    "pedestrian": 5.1,
    "bicycle": 20.0,
    "bus": 40.0,
    "transit": 30.0,
    "truck": 55.0,
    "motor_scooter": 40.0,
}


def get_costing_options(mode: str, overrides: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Get costing options for a given mode with optional overrides.
    
    Args:
        mode: Transportation mode
        overrides: Optional dict to override default options
    
    Returns:
        Costing options dict for Valhalla
    """
    if mode not in COSTING_OPTIONS:
        mode = "auto"  # Fallback to auto
    
    options = COSTING_OPTIONS[mode].copy()
    
    if overrides:
        options.update(overrides)
    
    return options


def validate_mode(mode: str) -> str:
    """
    Validate and normalize mode string.
    
    Args:
        mode: Transportation mode
    
    Returns:
        Validated mode string
    
    Raises:
        ValueError: If mode is not supported
    """
    mode = mode.lower().strip()
    
    if mode not in SUPPORTED_MODES:
        raise ValueError(
            f"Unsupported mode: {mode}. "
            f"Supported modes: {', '.join(SUPPORTED_MODES)}"
        )
    
    return mode

