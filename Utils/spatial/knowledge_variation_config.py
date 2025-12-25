#!/usr/bin/env python3
"""
Knowledge Variation Configuration

Defines parameters for believable agent knowledge distribution variation.
All values can be tuned via this config without touching core logic.
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional

# ---------------------------------------------------------------------------
# Mobility Mode Parameters
# ---------------------------------------------------------------------------

@dataclass
class MobilityModeConfig:
    """Configuration for a mobility mode (car, transit, bike, walk)."""
    name: str
    lambda_multiplier_range: Tuple[float, float]  # Min/max multiplier for distance decay
    max_radius_km_range: Tuple[float, float]  # Min/max search radius in km
    transit_accessibility_required: bool = False  # If True, requires nearby transit


MOBILITY_MODES: Dict[str, MobilityModeConfig] = {
    "car": MobilityModeConfig(
        name="car",
        lambda_multiplier_range=(1.3, 1.8),  # 30-80% more tolerant to distance
        max_radius_km_range=(10.0, 16.0),  # 10-16 km (6-10 miles)
    ),
    "transit": MobilityModeConfig(
        name="transit",
        lambda_multiplier_range=(0.9, 1.2),
        max_radius_km_range=(5.0, 12.0),  # Transit accessible range
        transit_accessibility_required=True,
    ),
    "bike": MobilityModeConfig(
        name="bike",
        lambda_multiplier_range=(0.7, 1.0),
        max_radius_km_range=(3.0, 8.0),  # 3-8 km (2-5 miles)
    ),
    "walk": MobilityModeConfig(
        name="walk",
        lambda_multiplier_range=(0.5, 0.8),
        max_radius_km_range=(1.5, 5.0),  # 1.5-5 km (1-3 miles)
    ),
}


# ---------------------------------------------------------------------------
# Category Preferences by L2 Signals
# ---------------------------------------------------------------------------

# Maps L2 consumer interest categories to POI category preferences
L2_CATEGORY_MAPPING: Dict[str, List[str]] = {
    # Shopping & Retail
    "shopping": ["grocery", "supermarket", "convenience", "shopping", "mall"],
    "fashion": ["clothing", "shoes", "beauty", "hairdresser"],
    "home_garden": ["hardware", "doityourself", "garden_centre", "furniture"],
    "electronics": ["electronics", "computer", "phone"],
    "automotive": ["fuel", "gas_station", "car", "car_parts", "car_repair"],
    
    # Health & Wellness
    "health": ["pharmacy", "clinic", "hospital", "doctors", "dentist", "gym", "healthcare"],
    "fitness": ["gym", "sports", "sports_hall", "outdoor"],
    
    # Food & Dining
    "dining": ["restaurant", "fast_food", "cafe"],
    "gourmet": ["restaurant", "cafe", "bakery"],
    "alcohol": ["pub", "bar", "alcohol"],
    
    # Recreation & Leisure
    "outdoor": ["park", "playground", "picnic_site", "viewpoint", "hiking"],
    "sports": ["sports", "sports_hall", "gym", "golf_course"],
    "culture": ["museum", "artwork", "theatre", "attraction"],
    "entertainment": ["cinema", "nightlife", "bar"],
    
    # Services & Professional
    "financial": ["bank", "atm", "financial_advisor"],
    "education": ["school", "university", "college", "library"],
    "government": ["government", "townhall", "post_office"],
    
    # Family & Lifestyle
    "family": ["school", "playground", "park", "library"],
    "senior": ["pharmacy", "healthcare", "hospital", "park"],
}


def get_category_preference_vector(l2_interests: List[str], default_weight: float = 0.4) -> Dict[str, float]:
    """
    Convert L2 interest signals to POI category preference weights.
    
    Args:
        l2_interests: List of interest strings from L2 data
        default_weight: Default weight for categories not in mapping
    
    Returns:
        Dict mapping category_name -> preference weight (0.0 to 1.0)
    """
    weights: Dict[str, float] = {}
    
    # Count how many L2 interests map to each category
    for interest in l2_interests or []:
        interest_lower = interest.lower().replace("_", " ").replace("-", " ")
        for l2_key, categories in L2_CATEGORY_MAPPING.items():
            if l2_key in interest_lower or interest_lower in l2_key:
                for cat in categories:
                    weights[cat] = weights.get(cat, 0.0) + 0.15
    
    # Normalize and cap at 1.0
    if weights:
        max_weight = max(weights.values())
        if max_weight > 0:
            for cat in weights:
                weights[cat] = min(1.0, weights[cat] / max_weight)
    
    return weights


# ---------------------------------------------------------------------------
# Category Quotas
# ---------------------------------------------------------------------------

@dataclass
class CategoryQuota:
    """Quota constraints for a POI category."""
    category_name: str
    min_per_agent: int = 0  # Minimum to ensure if available
    max_per_agent: int = 1000  # Maximum to prevent overloading
    essential: bool = False  # If True, must include if available


CATEGORY_QUOTAS: Dict[str, CategoryQuota] = {
    # Essentials (no max, must include if available)
    "fuel": CategoryQuota("fuel", min_per_agent=1, essential=True),
    "gas_station": CategoryQuota("gas_station", min_per_agent=1, essential=True),
    "grocery": CategoryQuota("grocery", min_per_agent=1, essential=True),
    "supermarket": CategoryQuota("supermarket", min_per_agent=1, essential=True),
    "pharmacy": CategoryQuota("pharmacy", min_per_agent=1, essential=True),
    "bank": CategoryQuota("bank", min_per_agent=1, essential=True),
    "atm": CategoryQuota("atm", min_per_agent=0, essential=False),
    "post_office": CategoryQuota("post_office", min_per_agent=1, essential=True),
    "school": CategoryQuota("school", min_per_agent=0, essential=False),  # Only if have kids
    
    # Low-value categories (strict limits)
    "bench": CategoryQuota("bench", max_per_agent=5),
    "viewpoint": CategoryQuota("viewpoint", max_per_agent=3),
    "picnic_table": CategoryQuota("picnic_table", max_per_agent=2),
    "locality": CategoryQuota("locality", max_per_agent=2),
    "village": CategoryQuota("village", max_per_agent=2),
    "neighbourhood": CategoryQuota("neighbourhood", max_per_agent=3),
    
    # Reasonable limits for common categories
    "parking": CategoryQuota("parking", max_per_agent=10),
    "information": CategoryQuota("information", max_per_agent=5),
    "restaurant": CategoryQuota("restaurant", max_per_agent=15),
    "cafe": CategoryQuota("cafe", max_per_agent=8),
    "fast_food": CategoryQuota("fast_food", max_per_agent=10),
}


# ---------------------------------------------------------------------------
# Target Count Variation
# ---------------------------------------------------------------------------

def sample_target_count(
    density_min: int,
    density_max: int,
    tenure_years: float,
    household_size: Optional[int],
    base_multiplier: float = 1.0,
) -> int:
    """
    Sample a target knowledge count for an agent.
    
    Factors:
    - Base range from density class
    - Tenure boost (longer tenure = more places)
    - Household size boost (families know more)
    - Random variation
    
    Args:
        density_min: Minimum target from density class
        density_max: Maximum target from density class
        tenure_years: Years at current location
        household_size: Number of people in household
        base_multiplier: Base multiplier (for mobility adjustments)
    
    Returns:
        Sampled target count
    """
    import random
    import math
    
    # Base target from density
    base_range = density_max - density_min
    base_target = density_min + random.uniform(0, base_range)
    
    # Tenure multiplier: 0.8 at 0 years, 1.4 at 10+ years
    tenure_mult = 0.8 + min(0.6, tenure_years / 10.0 * 0.6)
    
    # Household size multiplier: 1.0 at 1 person, 1.2 at 4+ people
    household_mult = 1.0
    if household_size:
        household_mult = 1.0 + min(0.2, (household_size - 1) * 0.067)
    
    # Apply multipliers
    target = int(base_target * tenure_mult * household_mult * base_multiplier)
    
    # Add some randomness (±10%)
    target = int(target * random.uniform(0.9, 1.1))
    
    # Clamp to reasonable bounds
    return max(density_min, min(density_max * 2, target))


# ---------------------------------------------------------------------------
# Household Social Spillover
# ---------------------------------------------------------------------------

SOCIAL_SPILLOVER_CONFIG = {
    "household_share_fraction": (0.10, 0.20),  # 10-20% of knowledge shared within household
    "neighbor_share_fraction": (0.02, 0.05),  # 2-5% from immediate neighbors
    "neighbor_radius_m": 500,  # 500m for neighbor definition
}


def compute_household_shares(
    agent_knowledge_counts: Dict[str, int],
    household_groups: Dict[str, List[str]],
) -> Dict[str, Dict[str, float]]:
    """
    Compute how much knowledge each agent should share with household members.
    
    Returns:
        Dict[agent_id, Dict[household_member_id, share_fraction]]
    """
    import random
    
    shares: Dict[str, Dict[str, float]] = {}
    
    for household_id, member_ids in household_groups.items():
        if len(member_ids) < 2:
            continue  # No sharing for single-person households
        
        # Each agent shares 10-20% with each household member
        for agent_id in member_ids:
            if agent_id not in shares:
                shares[agent_id] = {}
            
            for other_id in member_ids:
                if other_id != agent_id:
                    share = random.uniform(*SOCIAL_SPILLOVER_CONFIG["household_share_fraction"])
                    shares[agent_id][other_id] = share
    
    return shares

