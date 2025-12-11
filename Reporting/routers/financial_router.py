#!/usr/bin/env python3
from __future__ import annotations

from fastapi import APIRouter, Query, Request
from typing import Optional, Dict, Any
from pydantic import BaseModel

from ..services import financial_service

router = APIRouter(tags=["financial"])


class StatementsResponse(BaseModel):
    income: Dict[str, Dict[str, float]]
    balance: Dict[str, Dict[str, float]]
    cash: Dict[str, Dict[str, float]]


@router.get("/statements", response_model=StatementsResponse)
def get_statements(
    request: Request,
    firm_id: str = Query(...),
    start_date: str = Query(...),
    end_date: str = Query(...),
    granularity: str = Query("daily"),
):
    """Get financial statements for a firm."""
    simulation_id = getattr(request.state, "simulation_id", None)
    return financial_service.get_financial_statements(
        firm_id, start_date, end_date, granularity, simulation_id
    )


@router.get("/financial_statements")
def get_financial_statements_alias(
    request: Request,
    firm_id: str = Query(...),
    start_date: str = Query(...),
    end_date: str = Query(...),
    granularity: str = Query("daily"),
):
    """Alias endpoint for financial statements."""
    simulation_id = getattr(request.state, "simulation_id", None)
    return financial_service.get_financial_statements(
        firm_id, start_date, end_date, granularity, simulation_id
    )


@router.get("/transactions")
def get_transactions(
    request: Request,
    firm_id: str = Query(...),
    start_date: str = Query(...),
    end_date: str = Query(...),
    transaction_type: Optional[str] = Query(None),
    limit: int = Query(1000),
):
    """Get raw transactions for a firm."""
    simulation_id = getattr(request.state, "simulation_id", None)
    return financial_service.get_transactions_service(
        firm_id, start_date, end_date, transaction_type, limit, simulation_id
    )


@router.get("/estimate_columns")
def estimate_columns(
    request: Request,
    firm_id: str = Query(...),
    start_date: str = Query(...),
    end_date: str = Query(...),
    granularity: str = Query("daily"),
):
    """Estimate the number of columns for financial data."""
    simulation_id = getattr(request.state, "simulation_id", None)
    return financial_service.estimate_columns_service(
        firm_id, start_date, end_date, granularity, simulation_id
    )


@router.get("/verify")
def verify_invariants(
    request: Request,
    firm_id: str = Query(...),
    start: str = Query(...),
    end: str = Query(...),
    granularity: str = Query("Monthly"),
    tolerance: float = Query(1e-6),
):
    """Verify accounting invariants."""
    simulation_id = getattr(request.state, "simulation_id", None)
    return financial_service.verify_invariants_service(
        firm_id, start, end, granularity, tolerance, simulation_id
    )


@router.get("/export_excel")
def export_excel(
    request: Request,
    firm_id: str = Query(...),
    start_date: str = Query(...),
    end_date: str = Query(...),
    granularity: str = Query("monthly"),
):
    """Export financial statements to Excel."""
    simulation_id = getattr(request.state, "simulation_id", None)
    return financial_service.export_excel_service(
        firm_id, start_date, end_date, granularity, simulation_id
    )

