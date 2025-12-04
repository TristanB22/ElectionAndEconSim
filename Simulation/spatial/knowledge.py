#!/usr/bin/env python3
"""
Spatial knowledge orchestration for simulations.

This module stitches together database access and the heuristics defined in
Utils.spatial to seed, update, and query agent POI knowledge.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Tuple
import math

from Utils.spatial import (
    get_density_class,
    get_lambda_for_density,
    get_target_knowledge_count,
    compute_mobility_scalar,
    compute_seed_score,
    compute_exposure_probability,
    compute_knowledge_strength,
    DEFAULT_CATEGORY_WEIGHTS,
    DEFAULT_NEED_INTENT_MAP,
    DENSITY_CLASSES,
)
from Utils.spatial.knowledge_variation_config import (
    MOBILITY_MODES,
    get_category_preference_vector,
    CATEGORY_QUOTAS,
    sample_target_count,
    SOCIAL_SPILLOVER_CONFIG,
    compute_household_shares,
)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class AgentSpatialProfile:
    agent_id: str
    home_lat: float
    home_lon: float
    household_size: Optional[int]
    has_vehicle: bool
    age: Optional[float]
    income_quantile: Optional[float]
    wealth_bucket: Optional[str]
    tenure_years: float
    mobility_mode: str = "walk"  # car, transit, bike, walk
    category_preferences: Optional[Dict[str, float]] = None  # category_name -> preference weight
    household_id: Optional[str] = None  # For social spillover
    l2_interests: Optional[List[str]] = None  # L2 consumer interest signals


@dataclass
class POICandidate:
    osm_id: int
    category_name: str
    subcategory_name: str
    lat: float
    lon: float
    distance_km: Optional[float] = None
    name: Optional[str] = None  # Display name of the POI
    brand: Optional[str] = None  # Brand name if applicable


# ---------------------------------------------------------------------------
# Clustering helpers (dynamic boxes)
# ---------------------------------------------------------------------------

def _grid_key(lat: float, lon: float, cell_size_km: float) -> Tuple[int, int]:
    """Simple equirectangular projection to bucket lat/lon into square cells."""
    # Approx conversions (1 deg lat ~=111km, lon scales by cos(lat))
    lat_deg_span = cell_size_km / 111.0
    lon_deg_span = cell_size_km / max(0.0001, (111.0 * math.cos(math.radians(lat))))
    return (
        int(lat / lat_deg_span),
        int(lon / lon_deg_span),
    )


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compute haversine distance in kilometres."""
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1 - a)))
    return r * c


def cluster_agents_dynamic(
    agents: List[AgentSpatialProfile],
    density_class: str,
    max_agents_per_cluster: int = 200,
) -> Dict[Tuple[int, int], List[AgentSpatialProfile]]:
    """
    Cluster agents using simple grid bucketing tuned per density class.
    """
    if density_class == "city":
        cell_size_km = 0.5
    elif density_class == "suburban":
        cell_size_km = 1.2
    else:
        cell_size_km = 3.5

    clusters: Dict[Tuple[int, int], List[AgentSpatialProfile]] = {}
    for profile in agents:
        key = _grid_key(profile.home_lat, profile.home_lon, cell_size_km)
        clusters.setdefault(key, []).append(profile)

    # Split oversize clusters by halving cell size recursively once
    refined_clusters: Dict[Tuple[int, int, int], List[AgentSpatialProfile]] = {}
    for key, members in clusters.items():
        if len(members) <= max_agents_per_cluster:
            refined_clusters[(key[0], key[1], 0)] = members
            continue
        half_cell = cell_size_km / 2.0
        for profile in members:
            sub_key = _grid_key(profile.home_lat, profile.home_lon, half_cell)
            refined_clusters.setdefault((sub_key[0], sub_key[1], 1), []).append(profile)

    return {key: members for key, members in refined_clusters.items() if members}


# ---------------------------------------------------------------------------
# Seeding logic
# ---------------------------------------------------------------------------

def seed_agent_candidates(
    cluster_agents: List[AgentSpatialProfile],
    poi_candidates: List[POICandidate],
    density_class: str,
    simulation_start_datetime: datetime,
) -> Dict[str, List[Dict[str, any]]]:
    """
    Produce seed rows for `poi_seen` for each agent in a cluster with variation.
    Uses mobility modes, category preferences, quotas, and personalized scoring.
    Returns mapping agent_id -> list of dicts ready for DB insertion.
    """
    import random
    from typing import Counter
    
    density_cfg = next(dc for dc in DENSITY_CLASSES if dc.name == density_class)
    lambda_base = get_lambda_for_density(density_cfg)
    min_target, max_target = get_target_knowledge_count(density_cfg)

    essential_categories = {
        "gas_station",
        "fuel",
        "grocery",
        "supermarket",
        "pharmacy",
        "clinic",
        "hospital",
        "bank",
        "atm",
        "school",
        "post_office",
    }

    per_agent_rows: Dict[str, List[Dict[str, any]]] = {}

    for profile in cluster_agents:
        # Determine mobility mode lambda multiplier
        mobility_cfg = MOBILITY_MODES.get(profile.mobility_mode, MOBILITY_MODES["walk"])
        lambda_multiplier = random.uniform(*mobility_cfg.lambda_multiplier_range)
        personal_lambda = lambda_base * lambda_multiplier
        
        # Get category preferences (fallback to defaults if not provided)
        if profile.category_preferences:
            cat_prefs = profile.category_preferences
        else:
            # Generate from L2 interests if available
            l2_ints = profile.l2_interests or []
            cat_prefs = get_category_preference_vector(l2_ints)
        
        # Sample personalized target count
        personal_target = sample_target_count(
            density_min=min_target,
            density_max=max_target,
            tenure_years=profile.tenure_years,
            household_size=profile.household_size,
            base_multiplier=1.0,  # Could adjust based on mobility mode
        )
        
        # Score POIs with personalized parameters
        scored: List[Tuple[float, POICandidate]] = []
        for poi in poi_candidates:
            distance_km = poi.distance_km
            if distance_km is None:
                distance_km = _haversine_km(profile.home_lat, profile.home_lon, poi.lat, poi.lon)
            
            # Base score with personalized lambda
            base_score = compute_seed_score(
                distance_km=distance_km,
                mobility_scalar=lambda_multiplier,  # Use lambda_multiplier as mobility_scalar proxy
                base_lambda_km=personal_lambda,
                category_name=poi.category_name,
                tenure_years=profile.tenure_years,
                household_size=profile.household_size,
            )
            
            # Apply category preference boost
            category_boost = cat_prefs.get(poi.category_name, 0.0) * 0.3  # Max 30% boost
            final_score = base_score + category_boost
            
            scored.append((final_score, POICandidate(
                osm_id=poi.osm_id,
                category_name=poi.category_name,
                subcategory_name=poi.subcategory_name,
                lat=poi.lat,
                lon=poi.lon,
                distance_km=distance_km,
            )))

        scored.sort(reverse=True, key=lambda item: item[0])

        # Track category counts for quota enforcement
        category_counts: Dict[str, int] = {}
        selected: Dict[int, Dict[str, any]] = {}
        
        # First pass: ensure essentials (respect quotas)
        for score, poi in scored:
            if poi.osm_id in selected:
                continue
            
            quota = CATEGORY_QUOTAS.get(poi.category_name)
            current_count = category_counts.get(poi.category_name, 0)
            
            if poi.category_name in essential_categories:
                # Essential: check if we need it and haven't hit max
                if quota:
                    if current_count < quota.min_per_agent and current_count < quota.max_per_agent:
                        selected[poi.osm_id] = _build_seed_row(
                            profile, poi, source="init", 
                            simulation_start_datetime=simulation_start_datetime
                        )
                        category_counts[poi.category_name] = current_count + 1
                else:
                    # No quota defined, include if essential
                    selected[poi.osm_id] = _build_seed_row(
                        profile, poi, source="init", 
                        simulation_start_datetime=simulation_start_datetime
                    )
                    category_counts[poi.category_name] = current_count + 1

        # Second pass: fill to target respecting quotas
        for score, poi in scored:
            if poi.osm_id in selected:
                continue
            
            if len(selected) >= personal_target:
                break
            
            # Check quota
            quota = CATEGORY_QUOTAS.get(poi.category_name)
            current_count = category_counts.get(poi.category_name, 0)
            
            if quota and current_count >= quota.max_per_agent:
                continue  # Skip, hit quota limit
            
            # Allow lower salience categories later
            if score < 0.1 and len(selected) >= min_target:
                continue
            
            selected[poi.osm_id] = _build_seed_row(
                profile, poi, source="init",
                simulation_start_datetime=simulation_start_datetime
            )
            category_counts[poi.category_name] = current_count + 1

        rows = list(selected.values())
        per_agent_rows[profile.agent_id] = rows[:personal_target] if personal_target < len(rows) else rows

    return per_agent_rows


def _build_seed_row(
    profile: AgentSpatialProfile,
    poi: POICandidate,
    source: str,
    simulation_start_datetime: datetime,
) -> Dict[str, any]:
    """
    Construct a row dict for insertion into poi_seen with realistic timestamps.
    
    Generates timestamps that:
    - Are before or equal to simulation start
    - Vary based on tenure (longer tenure = older first_time_seen possible)
    - Vary recency (some places seen recently, others longer ago)
    - Respect business hours for commercial POIs
    """
    import random
    from datetime import timedelta
    
    # Determine realistic time windows based on POI category
    category = poi.category_name
    
    # Business hours by category (hour of day when typically open)
    # Most commercial places: 9 AM - 5 PM weekdays, some restaurants 11 AM - 9 PM
    business_hours = {
        "restaurant": (11, 21),  # 11 AM - 9 PM
        "fast_food": (6, 23),     # 6 AM - 11 PM
        "cafe": (7, 20),          # 7 AM - 8 PM
        "bank": (9, 17),          # 9 AM - 5 PM (weekdays)
        "pharmacy": (8, 20),      # 8 AM - 8 PM
        "grocery": (7, 22),       # 7 AM - 10 PM
        "supermarket": (7, 22),   # 7 AM - 10 PM
        "fuel": (0, 23),          # 24/7
        "gas_station": (0, 23),   # 24/7
        "atm": (0, 23),           # 24/7
        "park": (6, 22),          # Dawn to dusk
        "school": (7, 17),        # School hours
    }
    
    default_hours = (9, 17)  # Default 9 AM - 5 PM
    open_hour, close_hour = business_hours.get(category, default_hours)
    
    # Maximum lookback for last_time_seen: at most one month before simulation start
    max_days_back_last_seen = 30  # One month max
    min_days_back = 1  # At least 1 day ago
    
    # Maximum lookback for first_time_seen: can be older to show historical knowledge
    # Long-term residents can know places from years ago (first time they encountered it)
    max_days_back_first_seen = min(int(profile.tenure_years * 365 * 0.8), 365 * 5)  # Up to 5 years or 80% of tenure
    
    # Distribution: higher scores (closer, essential) = more recent
    # Use score-like heuristic: closer/essential places seen more recently
    distance_factor = min(1.0, poi.distance_km / 10.0) if poi.distance_km else 0.5
    essential_factor = 1.0 if category in {
        "gas_station", "fuel", "grocery", "supermarket", "pharmacy", 
        "bank", "atm", "post_office", "school"
    } else 0.7
    
    # Bias toward recent for essential/close places, older for distant/less essential
    recency_bias = (distance_factor * 0.3 + essential_factor * 0.7)
    
    # Generate days_ago for last_time_seen (at most one month)
    # Higher recency_bias = more likely to be recent
    base_days = random.expovariate(1.0 / (max_days_back_last_seen * (1 - recency_bias * 0.6)))
    days_ago = max(min_days_back, min(int(base_days), max_days_back_last_seen))
    
    # Generate first_time_seen (can be older than last_time_seen, up to tenure limit)
    # First encounter can be months/years ago, but last seen is recent (within month)
    first_days_ago = days_ago + random.randint(0, min(max_days_back_first_seen - days_ago, max_days_back_first_seen // 2))
    first_days_ago = min(first_days_ago, max_days_back_first_seen)
    
    # Calculate timestamps
    last_seen = simulation_start_datetime - timedelta(days=days_ago)
    first_seen = simulation_start_datetime - timedelta(days=first_days_ago)
    
    # Adjust to reasonable hour within business hours
    # Also consider weekday vs weekend patterns
    import random
    from datetime import timedelta
    
    # Weekday/weekend awareness for certain categories
    if category in business_hours or category in {"restaurant", "cafe", "fast_food", "bank", "pharmacy", "grocery", "supermarket", "school"}:
        # Special handling for categories with weekday restrictions
        if category == "school":
            # Schools only open weekdays, typically 7-17
            if last_seen.weekday() >= 5:  # Weekend
                days_back = 1 if last_seen.weekday() == 6 else 2  # Sunday->Friday, Saturday->Thursday
                last_seen = last_seen - timedelta(days=days_back)
            if first_seen.weekday() >= 5:
                days_back = 1 if first_seen.weekday() == 6 else 2
                first_seen = first_seen - timedelta(days=days_back)
            hour = random.randint(7, 16)
            last_seen = last_seen.replace(hour=hour, minute=random.randint(0, 59), second=0, microsecond=0)
            first_seen = first_seen.replace(hour=random.randint(7, 16), minute=random.randint(0, 59), second=0, microsecond=0)
        elif category == "bank":
            # Banks typically weekdays only, 9-17
            if last_seen.weekday() >= 5:  # Weekend
                days_back = 1 if last_seen.weekday() == 6 else 2  # Sunday->Friday, Saturday->Thursday
                last_seen = last_seen - timedelta(days=days_back)
            if first_seen.weekday() >= 5:
                days_back = 1 if first_seen.weekday() == 6 else 2
                first_seen = first_seen - timedelta(days=days_back)
            hour = random.randint(9, 16)
            last_seen = last_seen.replace(hour=hour, minute=random.randint(0, 59), second=0, microsecond=0)
            first_seen = first_seen.replace(hour=random.randint(9, 16), minute=random.randint(0, 59), second=0, microsecond=0)
        elif category in {"restaurant", "cafe", "fast_food"}:
            # Restaurants more active on weekends, evenings
            if last_seen.weekday() >= 5:  # Weekend
                hour = random.randint(11, 21)  # Broader hours on weekends
            else:
                hour = random.randint(open_hour, close_hour - 1)
            last_seen = last_seen.replace(hour=hour, minute=random.randint(0, 59), second=0, microsecond=0)
            first_seen = first_seen.replace(hour=random.randint(open_hour, min(close_hour, 21) - 1), minute=random.randint(0, 59), second=0, microsecond=0)
        else:
            # Default: use business hours
            hour = random.randint(open_hour, close_hour - 1)
            last_seen = last_seen.replace(hour=hour, minute=random.randint(0, 59), second=0, microsecond=0)
            first_seen = first_seen.replace(hour=random.randint(open_hour, close_hour - 1), minute=random.randint(0, 59), second=0, microsecond=0)
    
    # Times visited: some places visited multiple times, others just seen
    # Essential/close places more likely to be visited
    if essential_factor > 0.8 and distance_factor < 0.3:
        # Close essentials: likely visited
        times_visited = random.choices(
            [0, 1, 2, 3, 5, 10],
            weights=[0.1, 0.2, 0.3, 0.2, 0.15, 0.05]
        )[0]
        first_visited = first_seen + timedelta(days=random.randint(0, days_ago // 2))
        last_visited = last_seen if times_visited > 0 else last_seen
    else:
        # Distant or less essential: mostly just seen, not visited
        times_visited = random.choices([0, 1], weights=[0.7, 0.3])[0]
        first_visited = last_seen if times_visited > 0 else first_seen
        last_visited = last_seen if times_visited > 0 else first_seen
    
    # Ensure first_visited <= last_visited and both <= simulation start
    if first_visited > last_visited:
        first_visited = last_visited
    if last_seen > simulation_start_datetime:
        last_seen = simulation_start_datetime
    if first_seen > simulation_start_datetime:
        first_seen = simulation_start_datetime
    
    return {
        "agent_id": profile.agent_id,
        "osm_id": poi.osm_id,
        "distance_km_from_home": poi.distance_km,
        "times_seen": random.randint(1, max(1, int(days_ago / 7) + 1)),  # Roughly weekly sightings
        "first_time_seen": first_seen,
        "last_time_seen": last_seen,
        "number_of_times_visited": times_visited,
        "first_time_visited": first_visited if times_visited > 0 else first_seen,
        "last_time_visited": last_visited if times_visited > 0 else first_seen,
        "loaded_at_start_of_simulation": True,
        "source": source,
    }


# ---------------------------------------------------------------------------
# Route exposure helper
# ---------------------------------------------------------------------------

def compute_route_updates(
    agent_profile: AgentSpatialProfile,
    candidates: Iterable[Dict[str, any]],
    base_probability: float,
    current_time: datetime,
) -> List[Dict[str, any]]:
    """
    Given candidate POIs encountered along a route, compute which ones to insert/update.
    `candidates` expected to contain keys:
        - osm_id
        - category_name
        - distance_to_polyline_m
        - road_class
        - edge_speed_kmh
        - times_seen (optional)
    """
    updates: List[Dict[str, any]] = []
    category_weights = DEFAULT_CATEGORY_WEIGHTS

    for row in candidates:
        cat_weight = category_weights.get(row.get("category_name"), 0.4)
        novelty_penalty = max(0.3, 1.0 - 0.05 * max(0, row.get("times_seen", 0)))

        probability = compute_exposure_probability(
            base=base_probability,
            edge_speed_kmh=row.get("edge_speed_kmh"),
            road_class=row.get("road_class"),
            distance_to_polyline_m=row.get("distance_to_polyline_m", 0.0),
            category_weight=cat_weight,
            time_of_day_boost=row.get("time_of_day_boost", 1.0),
            novelty_penalty=novelty_penalty,
        )

        if row.get("forced"):
            probability = 1.0

        if probability >= row.get("sample_threshold", 0.0):
            updates.append({
                "osm_id": row["osm_id"],
                "distance_km_from_home": row.get("distance_km_from_home", 0.0),
                "times_seen_increment": 1,
                "last_time_seen": current_time,
                "source": "route",
            })

    return updates


# ---------------------------------------------------------------------------
# Need-based discovery helper
# ---------------------------------------------------------------------------

def choose_poi_for_need(
    intent: str,
    known_pois: List[Dict[str, any]],
    fallback_candidates: List[POICandidate],
    current_time: datetime,
) -> Optional[Dict[str, any]]:
    """
    Decide which POI to use for a need. Prefers known POIs ordered by knowledge strength
    (assumed to be provided) and distance. Falls back to new candidates if necessary.
    """
    if known_pois:
        known_sorted = sorted(known_pois, key=lambda row: (-row.get("knowledge_strength", 0.0), row.get("distance_km_from_home", 0.0)))
        return {
            "type": "known",
            "poi": known_sorted[0],
        }

    if fallback_candidates:
        best = min(fallback_candidates, key=lambda poi: poi.distance_km)
        return {
            "type": "new",
            "poi": best,
            "insert_row": {
                "osm_id": best.osm_id,
                "distance_km_from_home": best.distance_km,
                "times_seen": 1,
                "number_of_times_visited": 0,
                "first_time_seen": current_time,
                "last_time_seen": current_time,
                "first_time_visited": current_time,
                "last_time_visited": current_time,
                "loaded_at_start_of_simulation": False,
                "source": "need",
            }
        }

    return None


# ---------------------------------------------------------------------------
# Knowledge strength render helper
# ---------------------------------------------------------------------------

def enrich_with_knowledge_strength(
    rows: List[Dict[str, any]],
    now: datetime,
) -> List[Dict[str, any]]:
    """
    Given raw DB rows for poi_seen, compute knowledge strength for each and return
    updated dictionaries.
    """
    enriched: List[Dict[str, any]] = []
    for row in rows:
        density = get_density_class(row.get("local_poi_count", 80))
        strength = compute_knowledge_strength(row, density, now)
        enriched_row = dict(row)
        enriched_row["knowledge_strength"] = strength
        enriched.append(enriched_row)
    return enriched
