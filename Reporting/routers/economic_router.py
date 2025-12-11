#!/usr/bin/env python3
from __future__ import annotations

from fastapi import APIRouter, Query, Request
from typing import Optional

from ..services import economic_service

router = APIRouter(prefix="/gdp", tags=["economic"])


@router.get("/current")
def get_gdp_current(
    request: Request,
    region: Optional[str] = Query(None),
):
    """Get current GDP."""
    simulation_id = getattr(request.state, "simulation_id", None)
    return economic_service.get_current_gdp(simulation_id, region)


@router.get("/periods")
def get_gdp_periods(
    request: Request,
    start_date: str = Query(...),
    end_date: str = Query(...),
    granularity: str = Query("monthly"),
):
    """Get GDP over time periods."""
    simulation_id = getattr(request.state, "simulation_id", None)
    return economic_service.get_gdp_by_period(start_date, end_date, granularity, simulation_id)


@router.get("/sectors")
def get_gdp_sectors(
    request: Request,
    date: Optional[str] = Query(None),
):
    """Get GDP by economic sector."""
    simulation_id = getattr(request.state, "simulation_id", None)
    return economic_service.get_gdp_by_sector(date, simulation_id)

