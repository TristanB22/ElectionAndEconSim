#!/usr/bin/env python3
"""
Firms Database Manager for World_Sim

Manages all firm-related database operations including:
- Firm CRUD operations
- Firm locations
- Inventory management
"""

from __future__ import annotations

import os
import logging
from typing import Dict, List, Any, Optional

from .base import BaseDatabaseManager

logger = logging.getLogger(__name__)


class FirmsDatabaseManager(BaseDatabaseManager):
    """
    Specialized manager for firm data operations.
    
    Handles:
    - Firm creation and updates
    - Firm location management
    - Inventory tracking
    - Firm queries
    """
    
    _db_name = os.getenv('DB_FIRMS_NAME', 'world_sim_firms')
    
    def ensure_firm_exists(self, firm_id: str, company_name: str) -> None:
        """
        Insert a firm row if it does not exist.
        
        Args:
            firm_id: Unique firm identifier
            company_name: Name of the company
        """
        # Check if firm exists
        check_query = f"SELECT COUNT(*) AS c FROM {self._format_table('firms')} WHERE id = %s"
        result = self.execute_query(check_query, (firm_id,), fetch=True)
        
        count = int(result.data[0]["c"]) if result.success and result.data else 0
        
        if count == 0:
            insert_query = f"INSERT INTO {self._format_table('firms')} (id, company_name) VALUES (%s, %s)"
            self.execute_query(insert_query, (firm_id, company_name), fetch=False)
            logger.info(f"Created firm {firm_id}: {company_name}")
    
    def list_firms(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        List all firms.
        
        Args:
            limit: Maximum number of firms to return
            
        Returns:
            List of firm dictionaries
        """
        query = f"SELECT * FROM {self._format_table('firms')} ORDER BY company_name LIMIT %s"
        result = self.execute_query(query, (limit,), fetch=True)
        
        if result.success:
            return result.data
        
        return []
    
    def get_firm(self, firm_id: str) -> Optional[Dict[str, Any]]:
        """
        Get firm details by ID.
        
        Args:
            firm_id: Firm identifier
            
        Returns:
            Firm dictionary or None
        """
        query = f"SELECT * FROM {self._format_table('firms')} WHERE id = %s"
        result = self.execute_query(query, (firm_id,), fetch=True)
        
        if result.success and result.data:
            return result.data[0]
        
        return None
    
    def create_firm(self, firm_data: Dict[str, Any]) -> str:
        """
        Create a new firm.
        
        Args:
            firm_data: Dictionary with firm attributes
            
        Returns:
            Firm ID
        """
        firm_id = firm_data.get('id')
        company_name = firm_data.get('company_name')
        
        if not firm_id or not company_name:
            raise ValueError("Firm must have 'id' and 'company_name'")
        
        self.ensure_firm_exists(firm_id, company_name)
        return firm_id
    
    def update_firm(self, firm_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update firm attributes.
        
        Args:
            firm_id: Firm identifier
            updates: Dictionary of fields to update
            
        Returns:
            True if successful
        """
        if not updates:
            return True
        
        # Build SET clause
        set_clauses = []
        params = []
        
        for key, value in updates.items():
            if key != 'id':  # Don't update primary key
                set_clauses.append(f"{key} = %s")
                params.append(value)
        
        if not set_clauses:
            return True
        
        params.append(firm_id)
        
        query = f"UPDATE {self._format_table('firms')} SET {', '.join(set_clauses)} WHERE id = %s"
        result = self.execute_query(query, tuple(params), fetch=False)
        
        return result.success
    
    def get_firm_locations(self, firm_id: str) -> List[Dict[str, Any]]:
        """
        Get firm locations.
        
        Args:
            firm_id: Firm identifier
            
        Returns:
            List of location dictionaries
        """
        # Placeholder - implement based on firm_locations table schema
        query = f"SELECT * FROM {self._format_table('firm_locations')} WHERE firm_id = %s"
        result = self.execute_query(query, (firm_id,), fetch=True)
        
        if result.success:
            return result.data
        
        return []
    
    def update_firm_inventory(self, firm_id: str, inventory_data: Dict[str, Any]) -> bool:
        """
        Update firm inventory.
        
        Args:
            firm_id: Firm identifier
            inventory_data: Inventory updates
            
        Returns:
            True if successful
        """
        # Placeholder - implement based on firm_inventory table schema
        logger.info(f"Inventory update for firm {firm_id}: {inventory_data}")
        return True


# Singleton accessor
def get_firms_manager() -> FirmsDatabaseManager:
    """Get the singleton instance of FirmsDatabaseManager."""
    return FirmsDatabaseManager.get_singleton()

