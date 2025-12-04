"""
Agent Router

API endpoints for agent-related operations.
"""

from fastapi import APIRouter, HTTPException, Request
from typing import Optional
import logging

from Reporting.services import agent_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.get("/simulation/{simulation_id}/bounds")
async def get_simulation_bounds(
    simulation_id: str,
    request: Request
):
    """
    Get simulation temporal bounds and agent count.
    
    Returns:
        - start_datetime: Simulation start time
        - end_datetime: Simulation end time
        - current_datetime: Current simulation time
        - agent_count: Number of agents in simulation
        - status: Simulation status
        - tick_granularity: Time granularity
    """
    try:
        session_id = getattr(request.state, 'session_id', None)
        
        bounds = agent_service.get_simulation_bounds(simulation_id)
        
        if not bounds:
            raise HTTPException(status_code=404, detail=f"Simulation {simulation_id} not found")
        
        return bounds
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_simulation_bounds: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def get_agents_list(
    simulation_id: str,
    request: Request,
    limit: int = 250,
    offset: int = 0
):
    """
    Get list of all agents in a simulation with basic information.
    
    Query Parameters:
        - simulation_id: Simulation identifier (required)
    
    Returns:
        List of agents with:
        - agent_id: Agent identifier
        - name: Agent full name
        - age: Agent age
        - gender: Agent gender
        - city: City of residence
        - state: State of residence
        - party: Political party affiliation
        - net_worth: Household net worth
        - household_size: Number of people in household
        - home_value: Primary home value
    """
    logger.info(f"[API] GET /api/agents/list called with simulation_id={simulation_id}, limit={limit}, offset={offset}")
    try:
        session_id = getattr(request.state, 'session_id', None)
        logger.info(f"[API] Session ID: {session_id}")
        
        logger.info(f"[API] Calling agent_service.get_agents_list...")
        agents = agent_service.get_agents_list(simulation_id, session_id, limit=limit, offset=offset)
        
        logger.info(f"[API] Service returned {len(agents)} agents")
        if len(agents) > 0:
            logger.info(f"[API] Sample agent: {agents[0]}")
        
        logger.info(f"[API] Returning response with {len(agents)} agents")
        return agents
    except Exception as e:
        logger.error(f"[API] Error in get_agents_list endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/count")
async def get_agents_count(
    simulation_id: str,
    request: Request
):
    """
    Get total number of distinct agents in a simulation.
    """
    try:
        session_id = getattr(request.state, 'session_id', None)
        total = agent_service.get_agents_count(simulation_id, session_id)
        return {"simulation_id": simulation_id, "total": total}
    except Exception as e:
        logger.error(f"[API] Error in get_agents_count endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/simulation/{simulation_id}/locations")
async def get_agent_locations(
    simulation_id: str,
    datetime: str,
    request: Request
):
    """
    Get agent locations at a specific datetime.
    
    Query Parameters:
        - datetime: ISO datetime string (e.g., "2024-01-15T14:30:00")
    
    Returns:
        List of agent locations with:
        - agent_id: Agent identifier
        - latitude: Latitude
        - longitude: Longitude
        - simulation_timestamp: Timestamp of this location
    """
    try:
        session_id = getattr(request.state, 'session_id', None)
        
        locations = agent_service.get_agent_locations_at_datetime(
            simulation_id,
            datetime,
            session_id
        )
        
        return {
            'simulation_id': simulation_id,
            'datetime': datetime,
            'agent_count': len(locations),
            'locations': locations
        }
    except Exception as e:
        logger.error(f"Error in get_agent_locations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{agent_id}/details")
async def get_agent_details(
    agent_id: str,
    simulation_id: Optional[str] = None,
    request: Request = None
):
    """
    Get comprehensive agent details.
    
    Query Parameters:
        - simulation_id: Optional simulation context for location history
    
    Returns:
        Dictionary with:
        - agent_data: Basic agent information
        - personal_summary: Agent personal summary
        - l2_data: All L2 voter data (registration, history, consumer)
        - location_history: Recent location history (if simulation_id provided)
    """
    try:
        session_id = getattr(request.state, 'session_id', None) if request else None
        
        details = agent_service.get_agent_details(agent_id, simulation_id, session_id)
        
        return details
    except Exception as e:
        logger.error(f"Error in get_agent_details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{agent_id}/balance-sheet")
async def get_agent_balance_sheet(
    agent_id: str,
    simulation_id: str,
    request: Request = None
):
    """
    Get agent's household balance sheet.
    
    Query Parameters:
        - simulation_id: Simulation identifier (required)
    
    Returns:
        Dictionary with:
        - household_id: Household identifier
        - balance_sheet: Household balance sheet data
        - household_members: List of all agents in the household
    """
    try:
        session_id = getattr(request.state, 'session_id', None) if request else None
        
        result = agent_service.get_agent_balance_sheet(agent_id, simulation_id, session_id)
        
        if 'error' in result:
            raise HTTPException(status_code=404, detail=result['error'])
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_agent_balance_sheet: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{agent_id}/household-members")
async def get_agent_household_members(
    agent_id: str,
    simulation_id: str,
    request: Request = None
):
    """
    Get all household members for an agent.
    
    Query Parameters:
        - simulation_id: Simulation identifier (required)
    
    Returns:
        Dictionary with:
        - household_id: Household identifier
        - members: List of household members
    """
    try:
        from Database.managers.agents import get_agents_manager
        from Database.managers.simulations import get_simulations_manager
        
        agents_manager = get_agents_manager()
        sim_manager = get_simulations_manager()
        
        # Get household ID
        household_id = agents_manager.get_agent_household_id(agent_id)
        
        if not household_id:
            raise HTTPException(status_code=404, detail="Household ID not found")
        
        # Get household members
        members = sim_manager.get_household_members(simulation_id, household_id)
        
        return {
            'agent_id': agent_id,
            'simulation_id': simulation_id,
            'household_id': household_id,
            'members': members
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_agent_household_members: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{agent_id}/poi-knowledge")
async def get_agent_poi_knowledge(
    agent_id: str,
    simulation_id: str,
    limit: Optional[int] = 200,
    request: Request = None,
):
    """
    Retrieve the POIs an agent knows about, including knowledge strength metrics.
    """
    try:
        data = agent_service.get_agent_poi_knowledge(simulation_id, agent_id, limit)
        if 'error' in data:
            raise HTTPException(status_code=500, detail=data['error'])
        return data
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error in get_agent_poi_knowledge: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{agent_id}/activity")
async def get_agent_activity(
    agent_id: str,
    simulation_id: str,
    limit: int = 100,
    request: Request = None
):
    """
    Get agent's recent activity (actions and transactions).
    
    Query Parameters:
        - simulation_id: Simulation identifier (required)
        - limit: Maximum number of records to return (default: 100)
    
    Returns:
        Dictionary with:
        - actions: List of agent actions
        - transactions: List of agent transactions
    """
    try:
        session_id = getattr(request.state, 'session_id', None) if request else None
        
        result = agent_service.get_agent_activity(agent_id, simulation_id, limit, session_id)
        
        return result
    except Exception as e:
        logger.error(f"Error in get_agent_activity: {e}")
        raise HTTPException(status_code=500, detail=str(e))
