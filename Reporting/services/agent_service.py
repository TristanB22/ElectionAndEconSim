"""
Agent Service

Business logic for agent-related operations including:
- Fetching simulation agents
- Getting agent locations at specific times
- Retrieving comprehensive agent details
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from Database.managers.agents import get_agents_manager
from Database.managers.simulations import get_simulations_manager

logger = logging.getLogger(__name__)


def get_simulation_agent_count(simulation_id: str) -> int:
    """
    Get count of agents in a simulation.
    
    Args:
        simulation_id: Simulation identifier
        
    Returns:
        Number of agents
    """
    try:
        agents_manager = get_agents_manager()
        agents = agents_manager.get_simulation_agents(simulation_id)
        return len(agents)
    except Exception as e:
        logger.error(f"Error getting agent count for simulation {simulation_id}: {e}")
        return 0


def get_simulation_bounds(simulation_id: str) -> Optional[Dict[str, Any]]:
    """
    Get simulation temporal bounds and agent count.
    
    Args:
        simulation_id: Simulation identifier
        
    Returns:
        Dictionary with start_datetime, end_datetime, current_datetime, agent_count
    """
    try:
        sim_manager = get_simulations_manager()
        agents_manager = get_agents_manager()
        
        # Get simulation details
        sim_info = sim_manager.get_simulation(simulation_id)
        if not sim_info:
            return None
        
        # Get agent count
        agents = agents_manager.get_simulation_agents(simulation_id)
        agent_count = len(agents)
        
        return {
            'simulation_id': simulation_id,
            'start_datetime': sim_info.get('simulation_start_datetime'),
            'end_datetime': sim_info.get('simulation_end_datetime'),
            'current_datetime': sim_info.get('current_simulation_datetime'),
            'agent_count': agent_count,
            'status': sim_info.get('status'),
            'tick_granularity': sim_info.get('tick_granularity', '1min')
        }
    except Exception as e:
        logger.error(f"Error getting simulation bounds for {simulation_id}: {e}")
        return None


def get_agents_list(
    simulation_id: str,
    session_id: Optional[str] = None,
    limit: int = 250,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    Get list of all agents in a simulation with basic information.
    
    Args:
        simulation_id: Simulation identifier
        session_id: Optional session identifier for logging
        
    Returns:
        List of agent dictionaries with basic info
    """
    logger.info(f"[SERVICE] get_agents_list called with simulation_id={simulation_id}, session_id={session_id}, limit={limit}, offset={offset}")
    try:
        sim_manager = get_simulations_manager()
        logger.info(f"[SERVICE] Got simulations manager, calling get_agents_list_with_details...")
        agents = sim_manager.get_agents_list_with_details(simulation_id, limit=limit, offset=offset)
        
        logger.info(f"[SERVICE] Retrieved {len(agents)} agents for simulation {simulation_id}")
        
        if len(agents) > 0:
            logger.info(f"[SERVICE] First agent sample: {agents[0]}")
        else:
            logger.warning(f"[SERVICE] No agents returned from database manager")
        
        return agents
    except Exception as e:
        logger.error(f"[SERVICE] Error getting agents list for simulation {simulation_id}: {e}", exc_info=True)
        return []


def get_agents_count(
    simulation_id: str,
    session_id: Optional[str] = None
) -> int:
    """
    Get total number of distinct agents in a simulation.
    """
    logger.info(f"[SERVICE] get_agents_count called with simulation_id={simulation_id}, session_id={session_id}")
    try:
        sim_manager = get_simulations_manager()
        total = sim_manager.get_agents_count(simulation_id)
        logger.info(f"[SERVICE] Total agents in simulation {simulation_id}: {total}")
        return total
    except Exception as e:
        logger.error(f"[SERVICE] Error getting agents count for simulation {simulation_id}: {e}")
        return 0


def get_agent_locations_at_datetime(
    simulation_id: str,
    datetime_str: str,
    session_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get agent locations at a specific datetime.
    
    Args:
        simulation_id: Simulation identifier
        datetime_str: ISO datetime string
        session_id: Optional session identifier for logging
        
    Returns:
        List of agent location dictionaries
    """
    try:
        agents_manager = get_agents_manager()
        locations = agents_manager.get_agent_locations_at_time(simulation_id, datetime_str)
        
        logger.info(f"Retrieved {len(locations)} agent locations for simulation {simulation_id} at {datetime_str}")
        
        return locations
    except Exception as e:
        logger.error(f"Error getting agent locations for simulation {simulation_id} at {datetime_str}: {e}")
        return []


def get_agent_details(
    agent_id: str,
    simulation_id: Optional[str] = None,
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get comprehensive agent details.
    
    Args:
        agent_id: Agent identifier (L2 voter ID)
        simulation_id: Optional simulation context
        session_id: Optional session identifier for logging
        
    Returns:
        Dictionary with agent details, L2 data, and summaries
    """
    try:
        agents_manager = get_agents_manager()
        details = agents_manager.get_agent_full_details(agent_id, simulation_id)
        
        logger.info(f"Retrieved details for agent {agent_id}")
        
        return details
    except Exception as e:
        logger.error(f"Error getting details for agent {agent_id}: {e}")
        return {
            'agent_id': agent_id,
            'error': str(e),
            'agent_data': None,
            'personal_summary': None,
            'l2_data': {},
            'location_history': []
        }


def get_agent_balance_sheet(
    agent_id: str,
    simulation_id: str,
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get agent's household balance sheet.
    
    Args:
        agent_id: Agent identifier (L2 voter ID)
        simulation_id: Simulation identifier
        session_id: Optional session identifier for logging
        
    Returns:
        Dictionary with balance sheet data and household info
    """
    try:
        agents_manager = get_agents_manager()
        sim_manager = get_simulations_manager()
        
        # Get household ID for this agent
        household_id = agents_manager.get_agent_household_id(agent_id)
        
        if not household_id:
            return {
                'agent_id': agent_id,
                'simulation_id': simulation_id,
                'error': 'Household ID not found',
                'balance_sheet': None,
                'household_members': []
            }
        
        # Get balance sheet
        balance_sheet = sim_manager.get_household_balance_sheet(simulation_id, household_id)
        
        # Get household members
        household_members = sim_manager.get_household_members(simulation_id, household_id)
        
        logger.info(f"Retrieved balance sheet for agent {agent_id} (household {household_id})")
        
        return {
            'agent_id': agent_id,
            'simulation_id': simulation_id,
            'household_id': household_id,
            'balance_sheet': balance_sheet,
            'household_members': household_members
        }
    except Exception as e:
        logger.error(f"Error getting balance sheet for agent {agent_id}: {e}")
        return {
            'agent_id': agent_id,
            'simulation_id': simulation_id,
            'error': str(e),
            'balance_sheet': None,
            'household_members': []
        }


def get_agent_activity(
    agent_id: str,
    simulation_id: str,
    limit: int = 100,
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get agent's recent activity (actions and transactions).
    
    Args:
        agent_id: Agent identifier (L2 voter ID)
        simulation_id: Simulation identifier
        limit: Maximum number of records to return
        session_id: Optional session identifier for logging
        
    Returns:
        Dictionary with actions and transactions
    """
    try:
        sim_manager = get_simulations_manager()
        
        # Get actions
        actions = sim_manager.get_simulation_actions(simulation_id, agent_id, limit)
        
        # Get transactions
        transactions = sim_manager.get_simulation_transactions(simulation_id, agent_id, limit)
        
        logger.info(f"Retrieved activity for agent {agent_id} in simulation {simulation_id}")
        
        return {
            'agent_id': agent_id,
            'simulation_id': simulation_id,
            'actions': actions,
            'transactions': transactions
        }
    except Exception as e:
        logger.error(f"Error getting activity for agent {agent_id}: {e}")
        return {
            'agent_id': agent_id,
            'simulation_id': simulation_id,
            'error': str(e),
            'actions': [],
            'transactions': []
        }


def get_agent_poi_knowledge(
    simulation_id: str,
    agent_id: str,
    limit: Optional[int] = None
) -> Dict[str, Any]:
    """
    Return POI knowledge records for an agent including derived strength.
    """
    try:
        sim_manager = get_simulations_manager()
        poi_rows = sim_manager.get_agent_poi_knowledge(simulation_id, agent_id, limit)
        return {
            'agent_id': agent_id,
            'simulation_id': simulation_id,
            'count': len(poi_rows),
            'pois': poi_rows,
        }
    except Exception as exc:
        logger.error(f"Error getting POI knowledge for agent {agent_id}: {exc}")
        return {
            'agent_id': agent_id,
            'simulation_id': simulation_id,
            'error': str(exc),
            'pois': [],
        }
