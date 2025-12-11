#!/usr/bin/env python3
"""
Heuristics and math helpers for agent spatial knowledge modelling.
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Dict, Any, Optional

from .knowledge_config import (
    DEFAULT_CATEGORY_WEIGHTS,
    get_density_class,
    get_lambda_for_density,
    get_target_knowledge_count,
    DENSITY_CLASSES,
)


# ---------------------------------------------------------------------------
# Mobility heuristic
# ---------------------------------------------------------------------------

def compute_mobility_scalar(
    has_vehicle: bool,
    age: Optional[float],
    income_quantile: Optional[float],
    wealth_bucket: Optional[str] = None,
) -> float:
    """
    Compute a coarse mobility scalar used to scale lambda and search radii.

    Stronger emphasis on transport availability:
    - With a vehicle: more tolerant to distance (higher lambda)
    - Without a vehicle: steeper distance decay (lower lambda)

    Returns:
        Scalar multiplier (typical range ~0.4 - 1.8)
    """
    scalar = 1.0

    # Primary transport effect
    if has_vehicle:
        scalar += 0.45
    else:
        scalar -= 0.45

    # Secondary demographic effects (kept modest)
    if age is not None:
        if age < 30:
            scalar += 0.05
        elif age > 75:
            scalar -= 0.20

    if income_quantile is not None:
        scalar += 0.15 * (income_quantile - 0.5)

    if wealth_bucket:
        # gentle nudge for high-net-worth households
        if "Greater than" in wealth_bucket or "$500,000" in wealth_bucket:
            scalar += 0.10

    # Clamp
    return max(0.4, min(1.8, scalar))


# ---------------------------------------------------------------------------
# Scoring for seeding
# ---------------------------------------------------------------------------

def compute_seed_score(
    distance_km: float,
    mobility_scalar: float,
    base_lambda_km: float,
    category_name: str,
    tenure_years: float,
    household_size: Optional[int] = None,
) -> float:
    """
    Score a POI candidate for initial seeding.
    """
    lambda_km = max(0.1, base_lambda_km * mobility_scalar)
    distance_term = math.exp(-distance_km / lambda_km)

    cat_weight = DEFAULT_CATEGORY_WEIGHTS.get(category_name, 0.4)
    tenure_boost = min(0.3, math.log1p(max(0.0, tenure_years)) / math.log1p(10.0)) if tenure_years else 0.0
    household_boost = 0.0
    if household_size:
        household_boost = min(0.1, (household_size - 2) * 0.02)

    return max(0.0, distance_term + cat_weight + tenure_boost + household_boost)


# ---------------------------------------------------------------------------
# Route exposure probability
# ---------------------------------------------------------------------------

ROAD_CLASS_WEIGHTS: Dict[str, float] = {
    "motorway": 0.20,
    "motorway_link": 0.25,
    "trunk": 0.35,
    "trunk_link": 0.40,
    "primary": 0.50,
    "primary_link": 0.55,
    "secondary": 0.70,
    "secondary_link": 0.75,
    "tertiary": 0.80,
    "residential": 1.00,
    "living_street": 1.00,
    "service": 0.95,
}


def compute_exposure_probability(
    base: float,
    edge_speed_kmh: Optional[float],
    road_class: Optional[str],
    distance_to_polyline_m: float,
    category_weight: float,
    time_of_day_boost: float = 1.0,
    novelty_penalty: float = 1.0,
) -> float:
    """
    Probability that a POI is noted during a route exposure.
    """
    speed_factor = 0.4
    if edge_speed_kmh and edge_speed_kmh > 0:
        speed_factor = max(0.05, min(1.0, 40.0 / edge_speed_kmh))

    class_factor = ROAD_CLASS_WEIGHTS.get(road_class or "", 0.6)
    distance_factor = math.exp(-distance_to_polyline_m / 40.0)  # half-life around 28m

    prob = base * speed_factor * class_factor * distance_factor * max(0.3, category_weight) * time_of_day_boost
    prob *= max(0.2, novelty_penalty)
    return max(0.0, min(1.0, prob))


# ---------------------------------------------------------------------------
# Knowledge strength calculation
# ---------------------------------------------------------------------------

def _days_since(reference: Optional[datetime], now: datetime) -> float:
    if reference is None:
        return float("inf")
    delta = now - reference
    return max(0.0, delta.total_seconds() / 86400.0)


def compute_knowledge_strength(
    record: Dict[str, Any],
    density: Optional[DensityClass],
    now: datetime,
) -> float:
    """
    Compute knowledge strength for a single POI record using stored stats.
    """
    density_cfg = density or DENSITY_CLASSES[1]

    days_since_seen = _days_since(record.get("last_time_seen"), now)
    days_since_known = _days_since(record.get("first_time_seen"), now)
    visits = int(record.get("number_of_times_visited") or 0)
    loaded_at_start = bool(record.get("loaded_at_start_of_simulation"))
    source = record.get("source") or "init"

    # Recency decay
    tau_seen = density_cfg.tau_seen_days
    recency = math.exp(-days_since_seen / tau_seen) if math.isfinite(days_since_seen) else 0.0

    # Visit saturation
    visit_alpha = density_cfg.visit_alpha
    visit_term = 1.0 - math.exp(-visit_alpha * visits)

    # Tenure (knowledge deepens over time even without visits)
    tenure_beta = density_cfg.tenure_beta
    tenure_term = 1.0 - math.exp(-tenure_beta * max(0.0, days_since_known))

    # Seed anchor (if preloaded and not too stale)
    seed_anchor = 0.0
    if loaded_at_start:
        tau_seed = density_cfg.seed_tau_days
        seed_anchor = 0.7 * math.exp(-days_since_seen / tau_seed) if math.isfinite(days_since_seen) else 0.4

    # Low confidence if system-added and never visited
    if source == "system" and visits == 0:
        seed_anchor *= 0.8
        recency *= 0.9

    # Combine weighted
    weights = {
        "seed": 0.20,
        "recency": 0.40,
        "visit": 0.25,
        "tenure": 0.15,
    }

    strength = (
        weights["seed"] * seed_anchor +
        weights["recency"] * recency +
        weights["visit"] * visit_term +
        weights["tenure"] * tenure_term
    )

    return max(0.0, min(1.0, strength))
