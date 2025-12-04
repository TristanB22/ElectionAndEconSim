#!/usr/bin/env python3
"""
Database Managers for World_Sim

Centralized, hierarchical database management system with:
- Base manager class with common functionality
- Specialized managers for each database/domain
- Singleton pattern for efficient resource usage
- Automatic database name injection
- Consistent query interface
"""

from .base import BaseDatabaseManager
from .simulations import SimulationsDatabaseManager, get_simulations_manager
from .firms import FirmsDatabaseManager, get_firms_manager
from .agents import AgentsDatabaseManager, get_agents_manager
from .l2 import L2DatabaseManager, get_l2_manager
from .geo import GeoDatabaseManager, get_geo_manager
from .alternative_data import AlternativeDataDatabaseManager, get_alternative_data_manager
from .atus import ATUSDatabaseManager, get_atus_database_manager

__all__ = [
    # Base class
    'BaseDatabaseManager',
    
    # Manager classes
    'SimulationsDatabaseManager',
    'FirmsDatabaseManager',
    'AgentsDatabaseManager',
    'L2DatabaseManager',
    'GeoDatabaseManager',
    'AlternativeDataDatabaseManager',
    'ATUSDatabaseManager',
    
    # Singleton accessors
    'get_simulations_manager',
    'get_firms_manager',
    'get_agents_manager',
    'get_l2_manager',
    'get_geo_manager',
    'get_alternative_data_manager',
    'get_atus_database_manager',
]

