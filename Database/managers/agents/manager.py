#!/usr/bin/env python3
"""
Agents Database Manager for World_Sim

Manages all agent-related database operations including:
- Agent CRUD operations
- Personal summaries
- Agent experiences
"""

from __future__ import annotations

import os
import logging
from typing import Dict, List, Any, Optional

from ..base import BaseDatabaseManager

logger = logging.getLogger(__name__)


class AgentsDatabaseManager(BaseDatabaseManager):
    """
    Specialized manager for agent data operations.
    
    Handles:
    - Agent creation and updates
    - Personal summary management
    - Agent experience tracking
    - Agent queries
    """
    
    _db_name = os.getenv('DB_AGENTS_NAME', 'world_sim_agents')
    
    def ensure_agent(self, agent_id: str, name: Optional[str] = None,
                    l2_voter_id: Optional[str] = None) -> None:
        """
        Ensure agent record exists in database.
        
        Args:
            agent_id: Agent identifier (typically L2 voter ID)
            name: Agent name
            l2_voter_id: L2 voter ID (if different from agent_id)
        """
        # Treat agent_id as L2 voter id key in the new schema
        lvoter = l2_voter_id or agent_id
        
        insert_query = f"""
            INSERT INTO {self._format_table('agents')} (l2_voter_id, name)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE name=VALUES(name)
        """
        
        self.execute_query(insert_query, (lvoter, name), fetch=False)
        logger.debug(f"Ensured agent record for {lvoter}")
    
    def upsert_agent_summary(self, agent_id: str, summary: str,
                            summary_type: str = "personal_summary",
                            reasoning: str = "",
                            metadata: dict = None) -> None:
        """
        Insert or update agent personal summary.
        
        Args:
            agent_id: Agent identifier (L2 voter ID)
            summary: Summary text
            summary_type: Type of summary
            reasoning: Reasoning/explanation for the summary
            metadata: JSON metadata about the LLM call (model, tokens, etc.)
        """
        import json
        
        # First ensure agent exists
        self.ensure_agent(agent_id, l2_voter_id=agent_id)

        # If a summary already exists for this type, do not create a new one
        exists_q = f"""
            SELECT 1 FROM {self._format_table('agent_personal_summaries')}
            WHERE agent_id = %s AND summary_type = %s
            LIMIT 1
        """
        exists_res = self.execute_query(exists_q, (agent_id, summary_type), fetch=True)
        if exists_res.success and exists_res.data:
            logger.debug(f"Summary already exists for agent {agent_id} type {summary_type}; skipping insert")
            return

        # Convert metadata dict to JSON string
        metadata_json = json.dumps(metadata) if metadata else None

        # Insert new summary record
        insert_query = f"""
            INSERT INTO {self._format_table('agent_personal_summaries')}
            (agent_id, summary_type, reasoning, content, metadata, last_updated)
            VALUES (%s, %s, %s, %s, %s, NOW())
        """

        self.execute_query(insert_query, (agent_id, summary_type, reasoning, summary, metadata_json), fetch=False)
        logger.debug(f"Upserted summary for agent {agent_id}")

    def bulk_upsert_llm_personal_summaries(self, rows: List[Dict[str, Any]]) -> None:
        """
        Bulk insert llm personal summaries (skips existing via INSERT IGNORE).

        Args:
            rows: List of dicts with keys: agent_id, summary, reasoning, metadata (optional)
        """
        if not rows:
            return
        import json
        # Ensure agents exist first (minimal cost via insert-ignore)
        ensure_values = ",".join(["(%s,%s)"] * len(rows))
        ensure_query = f"""
            INSERT INTO {self._format_table('agents')} (l2_voter_id, name)
            VALUES {ensure_values}
            ON DUPLICATE KEY UPDATE name=VALUES(name)
        """
        ensure_params: List[Any] = []
        for r in rows:
            ensure_params.extend([r['agent_id'], None])
        self.execute_query(ensure_query, tuple(ensure_params), fetch=False)

        # Build bulk insert for summaries
        values_sql = ",".join(["(%s,%s,%s,%s,%s,NOW())"] * len(rows))
        insert_query = f"""
            INSERT IGNORE INTO {self._format_table('agent_personal_summaries')}
            (agent_id, summary_type, reasoning, content, metadata, last_updated)
            VALUES {values_sql}
        """
        insert_params: List[Any] = []
        for r in rows:
            meta_json = json.dumps(r.get('metadata')) if r.get('metadata') else None
            insert_params.extend([
                r['agent_id'],
                'llm_personal',
                r.get('reasoning', ''),
                r['summary'],
                meta_json,
            ])
        self.execute_query(insert_query, tuple(insert_params), fetch=False)
    
    def get_agent_summary(self, agent_id: str,
                         summary_type: str = "llm_personal") -> Optional[str]:
        """
        Get agent personal summary.
        
        Args:
            agent_id: Agent identifier
            summary_type: Type of summary
            
        Returns:
            Summary text or None
        """
        query = f"""
            SELECT content 
            FROM {self._format_table('agent_personal_summaries')}
            WHERE agent_id = %s AND summary_type = %s
            ORDER BY last_updated DESC 
            LIMIT 1
        """
        
        result = self.execute_query(query, (agent_id, summary_type), fetch=True)
        
        if result.success and result.data:
            return result.data[0].get('content')
        
        return None
    
    def get_all_agent_summaries(self, agent_id: str) -> List[Dict[str, Any]]:
        """
        Get all personal summaries for an agent (all types, with metadata).
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            List of summary records with type, content, and timestamps
        """
        query = f"""
            SELECT agent_id, summary_type, content, last_updated, metadata
            FROM {self._format_table('agent_personal_summaries')}
            WHERE agent_id = %s
            ORDER BY last_updated DESC
        """
        result = self.execute_query(query, (agent_id,), fetch=True)
        if result.success and result.data:
            return result.data
        return []
    
    def get_missing_summary_ids(self, agent_ids: List[str], summary_type: str = "llm_personal") -> List[str]:
        """
        Get agent IDs that don't have summaries yet using a single SQL query.
        This is more efficient than checking each one individually.
        
        Args:
            agent_ids: List of agent IDs to check
            summary_type: Type of summary to check
            
        Returns:
            List of agent IDs that are missing summaries
        """
        if not agent_ids:
            return []
        
        # Use a single query with LEFT JOIN to find missing IDs
        # Process in chunks to avoid SQL parameter limits
        missing_ids = []
        chunk_size = 1000
        for i in range(0, len(agent_ids), chunk_size):
            chunk = agent_ids[i:i + chunk_size]
            placeholders = ",".join(["%s"] * len(chunk))
            query = f"""
                SELECT t.agent_id
                FROM (
                    SELECT %s as agent_id
                ) AS t
                LEFT JOIN {self._format_table('agent_personal_summaries')} AS s
                    ON t.agent_id = s.agent_id AND s.summary_type = %s
                WHERE s.agent_id IS NULL
            """
            # Actually, MySQL doesn't support VALUES in subquery like that
            # Let's use a different approach with NOT IN
            query = f"""
                SELECT DISTINCT agent_id
                FROM (
                    SELECT %s as agent_id
                ) AS t
                WHERE agent_id NOT IN (
                    SELECT agent_id 
                    FROM {self._format_table('agent_personal_summaries')}
                    WHERE summary_type = %s AND agent_id IN ({placeholders})
                )
            """
            # Actually, simpler: just use NOT IN with the chunk
            query = f"""
                SELECT t.agent_id
                FROM (
                    SELECT agent_id FROM (
                        SELECT %s as agent_id
                    ) AS ids
                ) AS t
                WHERE t.agent_id NOT IN (
                    SELECT agent_id 
                    FROM {self._format_table('agent_personal_summaries')}
                    WHERE summary_type = %s AND agent_id IN ({placeholders})
                )
            """
            # Even simpler: use a temp table approach or just do NOT IN
            # Let's use the simplest approach that works
            existing = self.bulk_check_existing_summaries(chunk, summary_type)
            missing_ids.extend([aid for aid in chunk if aid not in existing])
        
        return missing_ids

    def bulk_check_existing_summaries(self, agent_ids: List[str], summary_type: str = "llm_personal") -> set:
        """
        Bulk check which agents already have summaries (much faster than individual queries).
        Returns a set of agent_ids that already have the given summary type.
        """
        if not agent_ids:
            return set()
        existing_ids: set = set()
        chunk_size = 1000
        for i in range(0, len(agent_ids), chunk_size):
            chunk = agent_ids[i:i + chunk_size]
            placeholders = ",".join(["%s"] * len(chunk))
            query = f"""
                SELECT DISTINCT agent_id
                FROM {self._format_table('agent_personal_summaries')}
                WHERE agent_id IN ({placeholders}) AND summary_type = %s
            """
            params = tuple(chunk) + (summary_type,)
            result = self.execute_query(query, params, fetch=True)
            if result.success and result.data:
                existing_ids.update(row['agent_id'] for row in result.data)
        return existing_ids
    
    def bulk_get_summaries(self, agent_ids: List[str], summary_type: str = "llm_personal") -> Dict[str, str]:
        """
        Bulk retrieve summaries for multiple agents in a single query (much faster than individual queries).
        
        Args:
            agent_ids: List of agent IDs to retrieve summaries for
            summary_type: Type of summary to retrieve
            
        Returns:
            Dictionary mapping agent_id -> summary content (only includes agents that have summaries)
        """
        if not agent_ids:
            return {}
        
        summaries: Dict[str, str] = {}
        chunk_size = 1000
        
        for i in range(0, len(agent_ids), chunk_size):
            chunk = agent_ids[i:i + chunk_size]
            placeholders = ",".join(["%s"] * len(chunk))
            query = f"""
                SELECT agent_id, content
                FROM {self._format_table('agent_personal_summaries')}
                WHERE agent_id IN ({placeholders}) AND summary_type = %s
                ORDER BY last_updated DESC
            """
            params = tuple(chunk) + (summary_type,)
            result = self.execute_query(query, params, fetch=True)
            
            if result.success and result.data:
                # Use the most recent summary for each agent (ORDER BY last_updated DESC handles this)
                for row in result.data:
                    agent_id = row['agent_id']
                    if agent_id not in summaries:  # Only take first (most recent) summary per agent
                        summaries[agent_id] = row.get('content', '')
        
        return summaries
    
    def bulk_ensure_agents(self, agent_ids: List[str]) -> None:
        """
        Bulk ensure agent records exist using a single INSERT IGNORE query.
        
        Args:
            agent_ids: List of agent IDs to ensure exist
        """
        if not agent_ids:
            return
        
        # Process in chunks to avoid SQL parameter limits
        chunk_size = 1000
        for i in range(0, len(agent_ids), chunk_size):
            chunk = agent_ids[i:i + chunk_size]
            placeholders = ",".join(["(%s,%s)"] * len(chunk))
            query = f"""
                INSERT IGNORE INTO {self._format_table('agents')} (l2_voter_id, name)
                VALUES {placeholders}
            """
            params: List[Any] = []
            for aid in chunk:
                params.extend([aid, None])  # name is None
            self.execute_query(query, tuple(params), fetch=False)
    
    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get agent details by ID.
        
        Args:
            agent_id: Agent identifier (L2 voter ID)
            
        Returns:
            Agent dictionary or None
        """
        query = f"SELECT * FROM {self._format_table('agents')} WHERE l2_voter_id = %s"
        result = self.execute_query(query, (agent_id,), fetch=True)
        
        if result.success and result.data:
            return result.data[0]
        
        return None
    
    def list_agents(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        List agents.
        
        Args:
            limit: Maximum number of agents to return
            
        Returns:
            List of agent dictionaries
        """
        query = f"SELECT * FROM {self._format_table('agents')} ORDER BY created_at DESC LIMIT %s"
        result = self.execute_query(query, (limit,), fetch=True)
        
        if result.success:
            return result.data
        
        return []
    
    def add_agent_experience(self, agent_id: str, simulation_id: Optional[str],
                           experience_type: str, content: str,
                           importance_score: float = 0.0,
                           context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Add an experience record for an agent.
        
        Args:
            agent_id: Agent identifier
            simulation_id: Simulation identifier
            experience_type: Type of experience
            content: Experience content
            importance_score: Importance score (0.0-1.0)
            context: Additional context dictionary
            
        Returns:
            True if successful
        """
        import json
        
        query = f"""
            INSERT INTO {self._format_table('agent_experiences')}
            (agent_id, simulation_id, experience_type, content, importance_score, context)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        
        context_json = json.dumps(context) if context else None
        
        result = self.execute_query(
            query,
            (agent_id, simulation_id, experience_type, content, importance_score, context_json),
            fetch=False
        )
        
        return result.success
    
    def get_simulation_agents(self, simulation_id: str) -> List[Dict[str, Any]]:
        """
        Get all agents initialized for a simulation.
        
        Args:
            simulation_id: Simulation identifier
            
        Returns:
            List of agent dictionaries with initialization info
        """
        query = f"""
            SELECT 
                ia.agent_id,
                ia.created_at as initialized_at,
                a.name,
                a.created_at as agent_created_at
            FROM world_sim_simulations.initialized_agents ia
            LEFT JOIN {self._format_table('agents')} a ON ia.agent_id = a.l2_voter_id
            WHERE ia.simulation_id = %s
            ORDER BY ia.created_at
        """
        
        result = self.execute_query(query, (simulation_id,), fetch=True)
        
        if result.success:
            return result.data
        
        return []
    
    def get_agent_locations_at_time(self, simulation_id: str, datetime_str: str) -> List[Dict[str, Any]]:
        """
        Get most recent location for each agent before specified datetime.
        
        Uses a window function to get the most recent location per agent
        that occurred before or at the specified datetime.
        
        Args:
            simulation_id: Simulation identifier
            datetime_str: ISO datetime string
            
        Returns:
            List of agent location dictionaries
        """
        query = """
            SELECT 
                agent_id,
                latitude,
                longitude,
                simulation_timestamp
            FROM (
                SELECT 
                    agent_id,
                    latitude,
                    longitude,
                    simulation_timestamp,
                    ROW_NUMBER() OVER (
                        PARTITION BY agent_id 
                        ORDER BY simulation_timestamp DESC
                    ) as rn
                FROM world_sim_simulations.agent_locations
                WHERE simulation_id = %s 
                  AND simulation_timestamp <= %s
            ) ranked
            WHERE rn = 1
        """
        
        result = self.execute_query(query, (simulation_id, datetime_str), fetch=True)
        
        if result.success:
            return result.data
        
        return []
    
    def get_agent_full_details(self, agent_id: str, simulation_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get comprehensive agent details including all L2 data and summaries.
        
        Args:
            agent_id: Agent identifier (L2 voter ID)
            simulation_id: Optional simulation context
            
        Returns:
            Dictionary with agent details, L2 data, and summaries
        """
        details = {
            'agent_id': agent_id,
            'agent_data': None,
            'personal_summary': None,
            'l2_data': {},
            'agent_summaries': [],
            'location_history': []
        }
        
        # Get basic agent data
        details['agent_data'] = self.get_agent(agent_id)
        
        # Get personal summary
        details['personal_summary'] = self.get_agent_summary(agent_id)
        # Include all summaries (more robust detail)
        details['agent_summaries'] = self.get_all_agent_summaries(agent_id)
        
        # Get L2 data from l2_data_manager (all tables defined in schema)
        try:
            from Database.l2_data_manager import L2DataManager
            l2_manager = L2DataManager()
            # Returns dict keyed by table names, e.g., l2_agent_core, l2_location, l2_geo,
            # l2_political_part_1/2/3, l2_other_part_1/2/3/4
            voter_data = l2_manager.get_l2_data_by_voter_id(agent_id)
            if voter_data:
                # Per-table data
                details['l2_data'] = voter_data
                # Build a flattened joined view (merge non-null fields across all tables)
                l2_flat: Dict[str, Any] = {}
                for table_name, row in voter_data.items():
                    if not row:
                        continue
                    for k, v in row.items():
                        # Prefer first non-null occurrence; avoid overwriting with None/empty
                        if v is None:
                            continue
                        if k not in l2_flat or l2_flat[k] in (None, ''):
                            l2_flat[k] = v
                details['l2_data_flat'] = l2_flat
        except Exception as e:
            logger.warning(f"Failed to fetch L2 data for agent {agent_id}: {e}")
        
        # Get location history if simulation_id provided
        if simulation_id:
            location_query = """
                SELECT latitude, longitude, simulation_timestamp
                FROM world_sim_simulations.agent_locations
                WHERE simulation_id = %s AND agent_id = %s
                ORDER BY simulation_timestamp DESC
                LIMIT 100
            """
            location_result = self.execute_query(location_query, (simulation_id, agent_id), fetch=True)
            if location_result.success:
                details['location_history'] = location_result.data
        
        return details
    
    def get_agent_household_id(self, agent_id: str) -> Optional[str]:
        """
        Get household ID for an agent from L2 data.
        
        Priority:
        1. Residence_Families_FamilyID
        2. Mailing_Families_FamilyID
        3. Synthetic ID: SYNTH_{agent_id}
        
        Args:
            agent_id: Agent identifier (L2 voter ID)
            
        Returns:
            Household ID string or None
        """
        from Database.l2_data_manager import L2DataManager
        
        try:
            l2_manager = L2DataManager()
            voter_data = l2_manager.get_l2_data_by_voter_id(agent_id)
            
            if not voter_data:
                return f"SYNTH_{agent_id}"
            
            # Try residence family first
            other_part_1 = voter_data.get('l2_other_part_1', {})
            if other_part_1:
                res_fam = other_part_1.get('Residence_Families_FamilyID')
                if res_fam:
                    return str(res_fam)
                
                # Fallback to mailing family
                mail_fam = other_part_1.get('Mailing_Families_FamilyID')
                if mail_fam:
                    return str(mail_fam)
            
            # Synthetic fallback
            return f"SYNTH_{agent_id}"
        except Exception as e:
            logger.warning(f"Failed to get household ID for agent {agent_id}: {e}")
            return f"SYNTH_{agent_id}"
    
    def get_agent_home_location(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get agent's home address and coordinates from L2 data.
        
        Args:
            agent_id: Agent identifier (L2 voter ID)
            
        Returns:
            Dictionary with address fields and coordinates, or None
        """
        from Database.l2_data_manager import L2DataManager
        
        try:
            l2_manager = L2DataManager()
            voter_data = l2_manager.get_l2_data_by_voter_id(agent_id)
            
            if not voter_data:
                return None
            
            location_data = voter_data.get('l2_location', {})
            geo_data = voter_data.get('l2_geo', {})
            
            if not location_data and not geo_data:
                return None
            
            return {
                'address': location_data.get('Residence_Addresses_AddressLine'),
                'city': location_data.get('Residence_Addresses_City'),
                'state': location_data.get('Residence_Addresses_State'),
                'zip': location_data.get('Residence_Addresses_Zip'),
                'latitude': geo_data.get('latitude'),
                'longitude': geo_data.get('longitude'),
            }
        except Exception as e:
            logger.warning(f"Failed to get home location for agent {agent_id}: {e}")
            return None


# Singleton accessor
def get_agents_manager() -> AgentsDatabaseManager:
    """Get the singleton instance of AgentsDatabaseManager."""
    return AgentsDatabaseManager.get_singleton()
