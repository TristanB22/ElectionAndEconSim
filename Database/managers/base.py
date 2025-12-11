#!/usr/bin/env python3
"""
Base Database Manager for World_Sim

Abstract base class for domain-specific database managers.
Handles automatic database name injection and provides a consistent query interface
over the shared MySQL adapter. Supports singleton pattern per manager type.

Separate from the low-level MySQL adapter (MySQLConnectionBase) which handles
raw connections and pooling.
"""

from __future__ import annotations

import os
import logging
import threading
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple, ClassVar

logger = logging.getLogger(__name__)


class BaseDatabaseManager(ABC):
    """
    Abstract base class for specialized **domain** database managers.
    
    Each subclass must define:
    - ``_db_name``: The logical database this manager operates on
    
    This class:
    - Holds a shared ``MySQLDatabaseManager`` adapter
    - Injects the correct database name into every query
    - Implements a per-subclass singleton pattern
    """
    
    # Subclasses must set this
    _db_name: ClassVar[str] = None
    
    # Singleton tracking per subclass
    _instances: ClassVar[Dict[type, 'BaseDatabaseManager']] = {}
    _instances_lock = threading.Lock()
    
    def __init__(self):
        """Initialize the database manager."""
        if self._db_name is None:
            raise NotImplementedError(
                f"{self.__class__.__name__} must define _db_name class attribute"
            )
        # Lazily import the shared MySQL adapter to avoid circular imports.
        from Database.database_manager import MySQLDatabaseManager
        # Each domain manager instance holds an adapter, which in turn uses
        # the centralized connection pool manager under the hood.
        self._db = MySQLDatabaseManager()
        
        # Only log if verbosity >= 1
        verbosity = int(os.getenv('VERBOSITY', '3'))
        if verbosity >= 1:
            logger.info(f"Initialized {self.__class__.__name__} for database: {self._db_name}")
    
    @classmethod
    def get_singleton(cls) -> 'BaseDatabaseManager':
        """
        Get the singleton instance of this manager class.
        Each subclass gets its own singleton instance.
        """
        with cls._instances_lock:
            if cls not in cls._instances:
                cls._instances[cls] = cls()
            return cls._instances[cls]
    
    @classmethod
    def reset_singleton(cls) -> None:
        """Reset the singleton instance (useful for testing)."""
        with cls._instances_lock:
            if cls in cls._instances:
                del cls._instances[cls]
    
    def _get_db_name(self) -> str:
        """Get the database name this manager operates on."""
        return self._db_name
    
    def _format_table(self, table_name: str) -> str:
        """
        Format table name with database qualifier.
        Returns: "database.table"
        """
        return f"{self._db_name}.{table_name}"
    
    def execute_query(self, query: str, params: Optional[Tuple] = None, 
                     fetch: bool = True) -> 'QueryResult':
        """
        Execute a query on this manager's database.
        
        Args:
            query: SQL query string
            params: Query parameters tuple
            fetch: Whether to fetch results
            
        Returns:
            ``QueryResult`` object with data and metadata
        """
        return self._db.execute_query(
            query=query,
            params=params,
            database=self._db_name,
            fetch=fetch,
        )
    
    def execute_many(self, query: str, params_list: List[Tuple]) -> 'QueryResult':
        """
        Execute a query multiple times with different parameters.
        
        Args:
            query: SQL query string
            params_list: List of parameter tuples
            
        Returns:
            ``QueryResult`` object with metadata
        """
        return self._db.execute_many(
            query=query,
            params_list=params_list,
            database=self._db_name,
        )
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on this database.
        
        Returns:
            Dictionary with health status
        """
        try:
            result = self.execute_query("SELECT 1 as health_check", fetch=True)
            return {
                'status': 'healthy' if result.success else 'unhealthy',
                'database': self._db_name,
                'error': result.error if not result.success else None
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'database': self._db_name,
                'error': str(e)
            }
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection information for this database."""
        return {
            'database': self._db_name,
            'manager_class': self.__class__.__name__,
            'initialized': True
        }

