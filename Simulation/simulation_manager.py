#!/usr/bin/env python3
"""
Simulation management utilities for World_Sim.

Delegates to SimulationsDatabaseManager for all database operations.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List


def create_simulation(started_by: str, description: str = "", 
                     start_datetime: Optional[datetime] = None, 
                     tick_granularity: str = "15m", 
                     duration_hours: Optional[int] = None, 
                     end_datetime: Optional[datetime] = None, 
                     config: Optional[Dict[str, Any]] = None) -> str:
    """
    Create a new simulation record with time parameters.
    Delegates to SimulationsDatabaseManager.
    """
    from Database.managers import get_simulations_manager
    
    # Set default start time to 6:00 AM today if not provided
    if start_datetime is None:
        now = datetime.now()
        start_datetime = now.replace(hour=6, minute=0, second=0, microsecond=0)
    
    # Compute end time: default to 24 hours from start if neither provided
    # Note: SimulationsDatabaseManager.register_simulation doesn't use end_datetime,
    # but we can include it in config for reference
    if end_datetime is None:
        if duration_hours is not None:
            end_datetime = start_datetime + timedelta(hours=duration_hours)
        else:
            end_datetime = start_datetime + timedelta(hours=24)
    
    # Include end_datetime in config if provided
    if config is None:
        config = {}
    if end_datetime:
        config['planned_end_datetime'] = end_datetime.isoformat()
    
    return get_simulations_manager().register_simulation(
        started_by=started_by,
        description=description,
        sim_start=start_datetime,
        tick_granularity=tick_granularity,
        config=config
    )


def init_world_for_simulation(sim_id: str) -> 'World':
    """Initialize a world for the given simulation."""
    from Simulation.core.world import World
    return World(simulation_id=sim_id)


def mark_simulation_completed(sim_id: str) -> None:
    """
    Mark a simulation as completed and set the end time.
    Delegates to SimulationsDatabaseManager.
    """
    from Database.managers import get_simulations_manager
    get_simulations_manager().complete_simulation(
        simulation_id=sim_id,
        results={'completed_at': datetime.now().isoformat()},
        end_dt=datetime.now()
    )


def register_initialized_agents(sim_id: str, agent_ids: List[str]) -> None:
    """
    Insert agents into initialized_agents linking table.
    Delegates to SimulationsDatabaseManager.
    """
    from Database.managers import get_simulations_manager
    get_simulations_manager().register_initialized_agents(sim_id, agent_ids)


def seed_agent_start_locations(sim_id: str) -> None:
    """
    Populate starting locations in agent_locations for initialized agents.
    Delegates to SimulationsDatabaseManager.
    """
    from Database.managers import get_simulations_manager
    get_simulations_manager().seed_agent_start_locations(sim_id)


def get_simulation_info(sim_id: str) -> Optional[Dict[str, Any]]:
    """
    Get simulation information including start and end times.
    Delegates to SimulationsDatabaseManager.
    """
    from Database.managers import get_simulations_manager
    return get_simulations_manager().get_simulation(sim_id)


