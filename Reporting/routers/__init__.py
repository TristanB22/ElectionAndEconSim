"""
API Routers for World Sim Backend

This package contains modular routers organized by domain.
"""
from .geospatial_router import router as geospatial_router
from .utility_router import router as utility_router
from .financial_router import router as financial_router
from .simulation_router import router as simulation_router
from .economic_router import router as economic_router
from .map_router import router as map_router
from .routing_router import router as routing_router
from .agent_router import router as agent_router

__all__ = [
    "geospatial_router",
    "utility_router",
    "financial_router",
    "simulation_router",
    "economic_router",
    "map_router",
    "routing_router",
    "agent_router",
]

