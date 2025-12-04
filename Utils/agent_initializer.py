#!/usr/bin/env python3
"""
Agent Initializer Utility for World_Sim

Utilities for creating agents directly from L2 data without requiring
pre-loading in the agents table.
"""

from __future__ import annotations
import os
import sys
from pathlib import Path
from typing import Optional, Dict, List, Any, TYPE_CHECKING
import json
import time

from Utils.path_manager import initialize_paths
initialize_paths()

from Utils.l2_data.l2_data_parser import L2DataParser

from Database.database_manager import execute_query as dm_execute_query
import os as _os
_agents_db = _os.getenv('DB_AGENTS_NAME', 'world_sim_agents')

def execute_agents_query(query: str, params=None, fetch: bool = True):
    """Compatibility wrapper that returns list[dict] when fetch=True."""
    result = dm_execute_query(query, params, database=_agents_db, fetch=fetch)
    if fetch:
        if hasattr(result, 'success') and hasattr(result, 'data'):
            return result.data if result.success else []
        return result or []
    # fetch == False
    if hasattr(result, 'success'):
        return result.success
    return bool(result)

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from Agent.agent import Agent


class AgentInitializer:
    """Utility class for initializing agents from L2 data."""
    
    def __init__(self):
        """Initialize the agent initializer."""
        pass
    
    def get_l2_data_by_voter_id(self, l2_voter_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve complete L2 data for a given voter ID.
        
        Args:
            l2_voter_id: The L2 voter ID to look up
            
        Returns:
            Complete L2 data dictionary or None if not found
        """
        verbosity = int(os.getenv('VERBOSITY', os.getenv('VERBOSITY_LEVEL', '1')))
        t_total = time.perf_counter() if verbosity >= 3 else None
        try:
            # Start with basic data
            enriched_data = {'LALVOTERID': l2_voter_id}
            
            # Load from l2_agent_core
            t0 = time.perf_counter() if verbosity >= 3 else None
            core_query = "SELECT * FROM l2_agent_core WHERE LALVOTERID = %s"
            core_data = execute_agents_query(core_query, (l2_voter_id,), fetch=True)
            if core_data:
                enriched_data.update(core_data[0])
            if verbosity >= 3:
                print(f"[agent_init] {l2_voter_id}: l2_agent_core query {time.perf_counter() - t0:.3f}s")
            
            # Load from l2_location
            t0 = time.perf_counter() if verbosity >= 3 else None
            location_query = "SELECT * FROM l2_location WHERE LALVOTERID = %s"
            location_data = execute_agents_query(location_query, (l2_voter_id,), fetch=True)
            if location_data:
                enriched_data.update(location_data[0])
            if verbosity >= 3:
                print(f"[agent_init] {l2_voter_id}: l2_location query {time.perf_counter() - t0:.3f}s")
            
            # Load from l2_political (check only existing partitions: 1, 2, 3)
            t0 = time.perf_counter() if verbosity >= 3 else None
            political_data = {}
            for i in range(1, 4):  # Only check partitions 1, 2, 3
                partition_query = f"SELECT * FROM l2_political_part_{i} WHERE LALVOTERID = %s"
                try:
                    partition_data = execute_agents_query(partition_query, (l2_voter_id,), fetch=True)
                    if partition_data:
                        political_data.update(partition_data[0])
                except Exception as e:
                    print(f"Warning: Could not access l2_political_part_{i}: {e}")
                    break  # No more partitions
            enriched_data.update(political_data)
            if verbosity >= 3:
                print(f"[agent_init] {l2_voter_id}: l2_political queries {time.perf_counter() - t0:.3f}s")
            
            # Load from l2_other (check only existing partitions: 1, 2, 3, 4)
            t0 = time.perf_counter() if verbosity >= 3 else None
            other_data = {}
            for i in range(1, 5):  # Only check partitions 1, 2, 3, 4
                partition_query = f"SELECT * FROM l2_other_part_{i} WHERE LALVOTERID = %s"
                try:
                    partition_data = execute_agents_query(partition_query, (l2_voter_id,), fetch=True)
                    if partition_data:
                        other_data.update(partition_data[0])
                except Exception as e:
                    print(f"Warning: Could not access l2_other_part_{i}: {e}")
                    break  # No more partitions
            enriched_data.update(other_data)
            if verbosity >= 3:
                print(f"[agent_init] {l2_voter_id}: l2_other queries {time.perf_counter() - t0:.3f}s")
            
            # Load from l2_geo
            t0 = time.perf_counter() if verbosity >= 3 else None
            geo_query = "SELECT * FROM l2_geo WHERE LALVOTERID = %s"
            geo_data = execute_agents_query(geo_query, (l2_voter_id,), fetch=True)
            if geo_data:
                enriched_data.update(geo_data[0])
            if verbosity >= 3:
                print(f"[agent_init] {l2_voter_id}: l2_geo query {time.perf_counter() - t0:.3f}s")
            
            if verbosity >= 3:
                print(f"[agent_init] {l2_voter_id}: TOTAL L2 data load {time.perf_counter() - t_total:.3f}s")
            
            return enriched_data if len(enriched_data) > 1 else None
            
        except Exception as e:
            print(f"Error retrieving L2 data for {l2_voter_id}: {e}")
            return None
    
    def create_agent_from_l2(self, l2_voter_id: str, agent_id: Optional[str] = None, 
                            api_key: Optional[str] = None, simulation_id: Optional[str] = None) -> Optional['Agent']:
        """
        Create an agent directly from L2 data.
        
        Args:
            l2_voter_id: The L2 voter ID to create agent from
            agent_id: Optional custom agent ID (defaults to l2_voter_id)
            api_key: Optional API key for LLM operations
            simulation_id: Optional simulation ID for database operations
            
        Returns:
            Agent instance or None if creation failed
        """
        verbosity = int(os.getenv('VERBOSITY', os.getenv('VERBOSITY_LEVEL', '1')))
        t_total = time.perf_counter() if verbosity >= 3 else None
        try:
            # Import here to avoid circular dependency
            from Agent.agent import Agent
            
            # Get L2 data
            t0 = time.perf_counter() if verbosity >= 3 else None
            l2_data = self.get_l2_data_by_voter_id(l2_voter_id)
            if verbosity >= 3:
                print(f"[agent_init] {l2_voter_id}: get_l2_data_by_voter_id {time.perf_counter() - t0:.3f}s")
            if not l2_data:
                print(f"No L2 data found for voter ID: {l2_voter_id}")
                return None
            
            # Parse L2 data
            t0 = time.perf_counter() if verbosity >= 3 else None
            l2_row = L2DataParser.parse_row(l2_data)
            if verbosity >= 3:
                print(f"[agent_init] {l2_voter_id}: L2DataParser.parse_row {time.perf_counter() - t0:.3f}s")
            
            # Use provided agent_id or default to l2_voter_id
            final_agent_id = agent_id or l2_voter_id
            
            # Create agent
            t0 = time.perf_counter() if verbosity >= 3 else None
            agent = Agent(agent_id=final_agent_id, l2_data=l2_row, simulation_id=simulation_id)
            if verbosity >= 3:
                print(f"[agent_init] {l2_voter_id}: Agent() constructor {time.perf_counter() - t0:.3f}s")
            
            if verbosity >= 3:
                print(f"[agent_init] {l2_voter_id}: TOTAL create_agent_from_l2 {time.perf_counter() - t_total:.3f}s")
            if verbosity >= 2:
                print(f"Created agent {final_agent_id} from L2 data for {l2_voter_id}")
            return agent
            
        except Exception as e:
            print(f"Error creating agent from L2 data: {e}")
            return None
    
    def create_agents_from_l2_list(self, l2_voter_ids: List[str], 
                                  agent_ids: Optional[List[str]] = None,
                                  api_key: Optional[str] = None) -> List['Agent']:
        """
        Create multiple agents from a list of L2 voter IDs.
        
        Args:
            l2_voter_ids: List of L2 voter IDs
            agent_ids: Optional list of custom agent IDs (must match length of l2_voter_ids)
            api_key: Optional API key for LLM operations
            
        Returns:
            List of created Agent instances
        """
        agents = []
        
        for i, l2_voter_id in enumerate(l2_voter_ids):
            agent_id = agent_ids[i] if agent_ids and i < len(agent_ids) else None
            agent = self.create_agent_from_l2(l2_voter_id, agent_id, api_key)
            if agent:
                agents.append(agent)
        
        print(f"Created {len(agents)} agents from L2 data")
        return agents
    
    def get_available_l2_voter_ids(self, limit: int = 100) -> List[str]:
        """
        Get a list of available L2 voter IDs from the database.
        
        Args:
            limit: Maximum number of voter IDs to return
            
        Returns:
            List of available L2 voter IDs
        """
        try:
            query = "SELECT LALVOTERID FROM l2_agent_core LIMIT %s"
            results = execute_agents_query(query, (limit,), fetch=True)
            return [row['LALVOTERID'] for row in results]
        except Exception as e:
            print(f"Error retrieving available L2 voter IDs: {e}")
            return []
    
    def get_agent_summary(self, l2_voter_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a summary of agent information from L2 data.
        
        Args:
            l2_voter_id: The L2 voter ID to get summary for
            
        Returns:
            Summary dictionary with key agent information
        """
        l2_data = self.get_l2_data_by_voter_id(l2_voter_id)
        if not l2_data:
            return None
        
        # Extract key information
        summary = {
            'l2_voter_id': l2_voter_id,
            'name': self._extract_name(l2_data),
            'age': self._extract_age(l2_data),
            'gender': self._extract_gender(l2_data),
            'address': self._extract_address(l2_data),
            'education': self._extract_education(l2_data),
            'income_tier': self._extract_income_tier(l2_data),
            'political_party': self._extract_political_party(l2_data),
            'voting_history': self._extract_voting_history(l2_data)
        }
        
        return summary
    
    def _extract_name(self, l2_data: Dict[str, Any]) -> str:
        """Extract full name from L2 data."""
        first_name = l2_data.get('Voters_FirstName', '')
        last_name = l2_data.get('Voters_LastName', '')
        middle_name = l2_data.get('Voters_MiddleName', '')
        
        parts = [part for part in [first_name, middle_name, last_name] if part]
        return ' '.join(parts) if parts else 'Unknown'
    
    def _extract_age(self, l2_data: Dict[str, Any]) -> Optional[int]:
        """Extract age from L2 data."""
        age = l2_data.get('Voters_Age')
        try:
            return int(age) if age else None
        except (ValueError, TypeError):
            return None
    
    def _extract_gender(self, l2_data: Dict[str, Any]) -> str:
        """Extract gender from L2 data."""
        return l2_data.get('Voters_Gender', 'Unknown')
    
    def _extract_address(self, l2_data: Dict[str, Any]) -> str:
        """Extract address from L2 data."""
        parts = []
        
        # Residence address
        if l2_data.get('Residence_Addresses_HouseNumber'):
            parts.append(str(l2_data['Residence_Addresses_HouseNumber']))
        
        if l2_data.get('Residence_Addresses_StreetName'):
            parts.append(l2_data['Residence_Addresses_StreetName'])
        
        if l2_data.get('Residence_Addresses_Designator'):
            parts.append(l2_data['Residence_Addresses_Designator'])
        
        if l2_data.get('Residence_Addresses_City'):
            parts.append(l2_data['Residence_Addresses_City'])
        
        if l2_data.get('Residence_Addresses_Zip'):
            parts.append(l2_data['Residence_Addresses_Zip'])
        
        return ', '.join(parts) if parts else 'Address Unknown'
    
    def _extract_education(self, l2_data: Dict[str, Any]) -> str:
        """Extract education level from L2 data."""
        # This would need to be mapped from L2 education codes
        return l2_data.get('Voters_Education', 'Unknown')
    
    def _extract_income_tier(self, l2_data: Dict[str, Any]) -> str:
        """Extract income tier from L2 data."""
        # This would need to be mapped from L2 income codes
        return l2_data.get('Voters_Income', 'Unknown')
    
    def _extract_political_party(self, l2_data: Dict[str, Any]) -> str:
        """Extract political party from L2 data."""
        return l2_data.get('Voters_Party', 'Unknown')
    
    def _extract_voting_history(self, l2_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract voting history from L2 data."""
        history = {}
        
        # Look for voting performance fields
        for key, value in l2_data.items():
            if 'VotingPerformance' in key and value:
                # Extract election type and participation
                if 'Presidential' in key:
                    history['presidential'] = value
                elif 'General' in key:
                    history['general'] = value
                elif 'Primary' in key:
                    history['primary'] = value
        
        return history


# Convenience functions
def create_agent_from_l2(l2_voter_id: str, agent_id: Optional[str] = None, 
                         api_key: Optional[str] = None) -> Optional['Agent']:
    """Convenience function to create an agent from L2 data."""
    initializer = AgentInitializer()
    return initializer.create_agent_from_l2(l2_voter_id, agent_id, api_key)


def get_agent_summary(l2_voter_id: str) -> Optional[Dict[str, Any]]:
    """Convenience function to get agent summary from L2 data."""
    initializer = AgentInitializer()
    return initializer.get_agent_summary(l2_voter_id)


if __name__ == '__main__':
    # Example usage
    initializer = AgentInitializer()
    
    # Get available voter IDs
    available_ids = initializer.get_available_l2_voter_ids(limit=5)
    print(f"Available L2 voter IDs: {available_ids[:3]}...")
    
    if available_ids:
        # Create an agent from the first available ID
        agent = initializer.create_agent_from_l2(available_ids[0])
        if agent:
            print(f"Created agent: {agent.agent_id}")
            
            # Get summary
            summary = initializer.get_agent_summary(available_ids[0])
            print(f"Agent summary: {json.dumps(summary, indent=2, default=str)}")
