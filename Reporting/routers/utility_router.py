#!/usr/bin/env python3
"""
Utility Router
Handles schema initialization, sample data population, and utility endpoints.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any

# Import from parent api module
from ..engine import ensure_reporting_schema
from ..populate_sample_data import populate_sample_data as populate_samples

router = APIRouter(
    tags=["utility"],
    responses={404: {"description": "Not found"}},
)


@router.post("/init_reporting_schema")
def init_reporting_schema():
    """Initialize reporting database schema."""
    try:
        ensure_reporting_schema()
        return {"status": "schema_initialized"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/populate_sample_data")
def populate_sample_data():
    """Populate the database with sample data for testing."""
    try:
        populate_samples()
        return {"status": "sample_data_populated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
