#!/usr/bin/env python3
from __future__ import annotations

from fastapi import APIRouter, Query, Request
from typing import Optional

from ..services import simulation_service

router = APIRouter(tags=["simulation"])


@router.get("/simulations")
def get_simulations(request: Request):
    """Get all simulations sorted by start time."""
    simulation_id = getattr(request.state, "simulation_id", None)
    return simulation_service.get_all_simulations(simulation_id)


@router.post("/simulations")
def create_simulation(
    request: Request,
    name: str = Query(...),
    description: str = Query(""),
    started_by: str = Query(...),
):
    """Create a new simulation."""
    simulation_id = getattr(request.state, "simulation_id", None)
    return simulation_service.create_simulation_service(name, description, started_by, simulation_id)


@router.get("/simulations/{simulation_id}")
def get_simulation_details(simulation_id: str, request: Request):
    """Get simulation details by ID."""
    parent_sim_id = getattr(request.state, "simulation_id", None)
    return simulation_service.get_simulation_by_id(simulation_id, parent_sim_id)


@router.put("/simulations/{simulation_id}/status")
def update_simulation_status(
    simulation_id: str,
    request: Request,
    status: str = Query(...),
):
    """Update simulation status."""
    parent_sim_id = getattr(request.state, "simulation_id", None)
    return simulation_service.update_simulation_status_service(simulation_id, status, parent_sim_id)


@router.post("/simulations/{simulation_id}/complete")
def complete_simulation(simulation_id: str, request: Request):
    """Mark a simulation as complete."""
    parent_sim_id = getattr(request.state, "simulation_id", None)
    return simulation_service.complete_simulation_service(simulation_id, parent_sim_id)


@router.get("/firms")
def get_firms(request: Request, limit: int = Query(100)):
    """List all firms."""
    simulation_id = getattr(request.state, "simulation_id", None)
    return simulation_service.get_firms_service(limit, simulation_id)


@router.get("/firms/{firm_id}/defaults")
def get_firm_defaults(firm_id: str, request: Request):
    """Get default account mappings for a firm."""
    simulation_id = getattr(request.state, "simulation_id", None)
    return simulation_service.get_firm_defaults_service(firm_id, simulation_id)

