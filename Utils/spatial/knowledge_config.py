#!/usr/bin/env python3
"""
Configuration defaults for agent spatial knowledge modelling.

The goal is not to produce perfect urban science, but to provide a consistent
set of heuristics that the simulation can tune without touching core logic.
All values can be overridden via environment variables or higher-level config
objects if needed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple
import math

# ---------------------------------------------------------------------------
# Density classes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DensityClass:
    """Container describing heuristics for a density bucket."""

    name: str
    poi_threshold: Tuple[int, int]
    base_lambda_km: float
    target_range: Tuple[int, int]
    route_buffer_m: int
    tau_seen_days: float
    visit_alpha: float
    tenure_beta: float
    seed_tau_days: float


DENSITY_CLASSES: List[DensityClass] = [
    DensityClass(
        name="city",
        poi_threshold=(150, math.inf),
        base_lambda_km=0.45,
        target_range=(60, 100),
        route_buffer_m=75,
        tau_seen_days=20.0,
        visit_alpha=0.40,
        tenure_beta=0.020,
        seed_tau_days=60.0,
    ),
    DensityClass(
        name="suburban",
        poi_threshold=(60, 150),
        base_lambda_km=1.10,
        target_range=(80, 140),
        route_buffer_m=125,
        tau_seen_days=30.0,
        visit_alpha=0.35,
        tenure_beta=0.015,
        seed_tau_days=70.0,
    ),
    DensityClass(
        name="rural",
        poi_threshold=(0, 60),
        base_lambda_km=3.2,
        target_range=(100, 200),
        route_buffer_m=200,
        tau_seen_days=45.0,
        visit_alpha=0.25,
        tenure_beta=0.010,
        seed_tau_days=90.0,
    ),
]


def get_density_class(local_poi_count: int) -> DensityClass:
    """Return the density class based on the nearby POI count."""
    for density in DENSITY_CLASSES:
        lower, upper = density.poi_threshold
        if lower <= local_poi_count < upper:
            return density
    # Default to suburban heuristics if thresholds fail
    return DENSITY_CLASSES[1]


def get_lambda_for_density(density: DensityClass) -> float:
    """Return base lambda (km) for a density class."""
    return density.base_lambda_km


def get_target_knowledge_count(density: DensityClass) -> Tuple[int, int]:
    """Return the target count range (min, max) for knowledge seeding."""
    return density.target_range


# ---------------------------------------------------------------------------
# Category weights & intent mapping
# ---------------------------------------------------------------------------

DEFAULT_CATEGORY_WEIGHTS: Dict[str, float] = {
    # Essentials
    "gas_station": 1.0,
    "fuel": 1.0,
    "supermarket": 0.95,
    "grocery": 0.95,
    "pharmacy": 0.9,
    "clinic": 0.85,
    "hospital": 0.9,
    "bank": 0.85,
    "atm": 0.75,
    "school": 0.80,
    "college": 0.75,
    "post_office": 0.80,
    "government": 0.70,
    "transit": 0.70,
    # Core amenities
    "restaurant": 0.65,
    "cafe": 0.60,
    "bar": 0.45,
    "park": 0.70,
    "gym": 0.55,
    "library": 0.65,
    "shopping": 0.50,
    # Recreation / specialty
    "golf_course": 0.60,
    "movie_theater": 0.40,
    "museum": 0.45,
    "sports": 0.50,
    "nightlife": 0.30,
}


DEFAULT_NEED_INTENT_MAP: Dict[str, List[str]] = {
    "fuel": ["gas_station", "fuel"],
    "groceries": ["grocery", "supermarket", "market"],
    "pharmacy": ["pharmacy", "clinic"],
    "healthcare": ["clinic", "hospital"],
    "banking": ["bank", "atm"],
    "education": ["school", "college"],
    "post": ["post_office", "government"],
    "recreation": ["park", "sports", "gym"],
    "golf": ["golf_course"],
    "coffee": ["cafe"],
    "dining": ["restaurant"],
    "nightlife": ["bar", "nightlife"],
    "transit": ["transit"],
    "shopping": ["shopping", "mall"],
}
