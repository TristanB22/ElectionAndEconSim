#!/usr/bin/env python3
from __future__ import annotations

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import pandas as pd
from fastapi.responses import JSONResponse

from ..engine import (
    get_financial_data,
    estimate_column_count,
    verify_invariants,
)
from ..excel_export import create_financial_excel_report
from Firm.financial_transaction_processor import FinancialTransactionProcessor
# No direct DB calls here; engine handles queries via centralized manager


def get_financial_statements(
    firm_id: str,
    start_date: str,
    end_date: str,
    granularity: str = "daily",
    simulation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Get financial statements for a firm."""
    # Call existing engine function
    return get_financial_data(firm_id, start_date, end_date, granularity, simulation_id)


def get_transactions_service(
    firm_id: str,
    start_date: str,
    end_date: str,
    transaction_type: Optional[str] = None,
    limit: int = 1000,
    simulation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Get raw transactions for a firm."""
    # This endpoint would query the journal_entries table
    # For now, return a placeholder
    return {
        "firm_id": firm_id,
        "start_date": start_date,
        "end_date": end_date,
        "simulation_id": simulation_id,
        "transactions": [],
        "message": "Transaction endpoint placeholder - to be implemented"
    }


def estimate_columns_service(
    firm_id: str,
    start_date: str,
    end_date: str,
    granularity: str = "daily",
    simulation_id: Optional[str] = None,
) -> Dict[str, int]:
    """Estimate the number of columns for financial data."""
    return estimate_column_count(firm_id, start_date, end_date, granularity, simulation_id)


def verify_invariants_service(
    firm_id: str,
    start_date: str,
    end_date: str,
    granularity: str = "Monthly",
    tolerance: float = 1e-6,
    simulation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Verify accounting invariants."""
    return verify_invariants(firm_id, start_date, end_date, granularity, tolerance, simulation_id)


def export_excel_service(
    firm_id: str,
    start_date: str,
    end_date: str,
    granularity: str = "monthly",
    simulation_id: Optional[str] = None,
):
    """Export financial statements to Excel."""
    return create_financial_excel_report(firm_id, start_date, end_date, granularity, simulation_id)

