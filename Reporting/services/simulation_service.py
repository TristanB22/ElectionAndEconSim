#!/usr/bin/env python3
from __future__ import annotations

from typing import List, Dict, Any, Optional
from datetime import datetime

from ..engine import list_firms, list_simulations


def get_all_simulations(simulation_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get all simulations sorted by start time."""
    try:
        from Database.managers import get_simulations_manager
        dm = get_simulations_manager()
        simulations = dm.list_simulations(limit=100)
    except Exception:
        # Fallback: use centralized query directly
        from Database.database_manager import execute_query as dm_execute_query
        import os
        sim_db = os.getenv('DB_SIM_NAME', 'world_sim_simulations')
        res = dm_execute_query("SELECT * FROM simulations ORDER BY start_time DESC LIMIT 100", None, sim_db, True)
        simulations = res.data if getattr(res, 'success', False) else []
    
    result = []
    for sim in simulations:
        status = "unknown"
        if sim.get("simulation_end_datetime") and sim.get("current_simulation_datetime"):
            if sim["current_simulation_datetime"] >= sim["simulation_end_datetime"]:
                status = "completed"
            elif sim["current_simulation_datetime"] > sim["simulation_start_datetime"]:
                status = "running"
            else:
                status = "pending"
        elif sim.get("end_time"):
            status = "completed"
        else:
            status = "running"
        
        result.append({
            "id": sim["simulation_id"],
            "name": sim.get("started_by", "Unknown"),
            "created_at": sim["start_time"].isoformat() if sim["start_time"] else None,
            "status": status,
            "description": sim["description"],
            "end_time": sim["end_time"].isoformat() if sim["end_time"] else None,
            "start_datetime": sim.get("simulation_start_datetime").isoformat() if sim.get("simulation_start_datetime") else None,
            "current_datetime": sim.get("current_simulation_datetime").isoformat() if sim.get("current_simulation_datetime") else None,
            "end_datetime": sim.get("simulation_end_datetime").isoformat() if sim.get("simulation_end_datetime") else None,
            "tick_granularity": sim.get("tick_granularity", "15m")
        })
    
    return result


def create_simulation_service(
    name: str,
    description: str,
    started_by: str,
    simulation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a new simulation."""
    from Simulation.simulation_manager import create_new_simulation
    sim_id = create_new_simulation(started_by, description)
    return {"simulation_id": sim_id, "status": "created"}


def get_simulation_by_id(sim_id: str, simulation_id: Optional[str] = None) -> Dict[str, Any]:
    """Get simulation details by ID."""
    from Database.managers import get_simulations_manager
    dm = get_simulations_manager()
    sim = dm.get_simulation(sim_id)
    if not sim:
        return {"error": "Simulation not found"}
    return sim


def update_simulation_status_service(
    sim_id: str,
    status: str,
    simulation_id: Optional[str] = None,
) -> Dict[str, str]:
    """Update simulation status."""
    # Placeholder - implement based on SimulationDataManager
    return {"simulation_id": sim_id, "status": status, "message": "Status updated"}


def complete_simulation_service(sim_id: str, simulation_id: Optional[str] = None) -> Dict[str, str]:
    """Mark a simulation as complete."""
    from Simulation.simulation_manager import mark_simulation_completed
    mark_simulation_completed(sim_id)
    return {"simulation_id": sim_id, "status": "completed"}


def get_firms_service(limit: int = 100, simulation_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all firms."""
    return list_firms(limit=limit)


def get_firm_defaults_service(firm_id: str, simulation_id: Optional[str] = None) -> Dict[str, Any]:
    """Get default account mappings for a firm."""
    # Placeholder
    return {
        "firm_id": firm_id,
        "defaults": {},
        "message": "Firm defaults endpoint placeholder"
    }

