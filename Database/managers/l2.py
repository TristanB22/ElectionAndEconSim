#!/usr/bin/env python3
"""
L2 Database Manager for World_Sim

Manages L2 voter data operations (delegates to existing L2DataManager).
L2 data lives in the agents database.
"""

from __future__ import annotations

import os
import logging
from typing import Dict, List, Any, Optional

from .base import BaseDatabaseManager

logger = logging.getLogger(__name__)


class L2DatabaseManager(BaseDatabaseManager):
    """
    Specialized manager for L2 voter data operations.
    
    Wraps existing L2DataManager functionality while conforming to
    the base manager interface.
    """
    
    _db_name = os.getenv('DB_AGENTS_NAME', 'world_sim_agents')
    
    def __init__(self):
        """Initialize L2 database manager."""
        super().__init__()
        # Import here to avoid circular dependencies
        from Database.l2_data_manager import L2DataManager
        self._l2_manager = L2DataManager(db_manager=None)  # Will use centralized manager
    
    def load_l2_data_bulk(self, data: List[Dict[str, Any]],
                          batch_size: int = 10000,
                          table_mapping: Optional[Dict[str, List[str]]] = None) -> Dict[str, 'QueryResult']:
        """
        Load L2 data in bulk across multiple tables.
        Delegates to existing L2DataManager.
        """
        return self._l2_manager.load_l2_data_bulk(data, batch_size, table_mapping)
    
    def get_l2_data_by_voter_id(self, voter_id: str,
                               tables: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Get complete L2 data for a voter by LALVOTERID.
        Delegates to existing L2DataManager.
        """
        return self._l2_manager.get_l2_data_by_voter_id(voter_id, tables)
    
    def search_l2_data(self, criteria: Dict[str, Any],
                      tables: Optional[List[str]] = None,
                      limit: int = 100) -> List[Dict[str, Any]]:
        """
        Search L2 data based on criteria.
        Delegates to existing L2DataManager.
        """
        return self._l2_manager.search_l2_data(criteria, tables, limit)
    
    def get_l2_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about L2 data in the database.
        Delegates to existing L2DataManager.
        """
        return self._l2_manager.get_l2_statistics()
    
    def optimize_l2_tables(self) -> Dict[str, 'QueryResult']:
        """
        Optimize L2 tables for better performance.
        Delegates to existing L2DataManager.
        """
        return self._l2_manager.optimize_l2_tables()


# Singleton accessor
def get_l2_manager() -> L2DatabaseManager:
    """Get the singleton instance of L2DatabaseManager."""
    return L2DatabaseManager.get_singleton()

