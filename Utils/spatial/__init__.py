#!/usr/bin/env python3
"""
Spatial utilities package for agent geographic reasoning.

Provides configuration constants, scoring helpers, and knowledge-strength
calculations shared across simulation initialization, routing updates,
and backend API surfaces.
"""

from .knowledge_config import (
    DEFAULT_CATEGORY_WEIGHTS,
    DEFAULT_NEED_INTENT_MAP,
    DENSITY_CLASSES,
    get_density_class,
    get_lambda_for_density,
    get_target_knowledge_count,
)
from .knowledge_math import (
    compute_mobility_scalar,
    compute_seed_score,
    compute_exposure_probability,
    compute_knowledge_strength,
)

__all__ = [
    "DEFAULT_CATEGORY_WEIGHTS",
    "DEFAULT_NEED_INTENT_MAP",
    "DENSITY_CLASSES",
    "get_density_class",
    "get_lambda_for_density",
    "get_target_knowledge_count",
    "compute_mobility_scalar",
    "compute_seed_score",
    "compute_exposure_probability",
    "compute_knowledge_strength",
]
