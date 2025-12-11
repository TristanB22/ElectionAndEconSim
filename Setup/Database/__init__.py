"""
Setup Database integrations

Provides lightweight adapter functions used by legacy code paths for logging
actions, experiences, and transactions, backed by the split-database
connection manager.
"""

from __future__ import annotations
import sys
import os
from pathlib import Path
from typing import Any, Optional

"""
IMPORTANT: This module should not import live database connection code at import time.
It only provides thin wrappers that defer to Database when explicitly called.
This avoids masking the top-level 'Database' package and prevents import-time side-effects.
"""

def _get_execs():
    """Resolve execute_* functions at call time to avoid side-effects."""
    from Database.connection_manager import (
        execute_sim_query,
        execute_agents_query,
        execute_firms_query,
    )
    return execute_sim_query, execute_agents_query, execute_firms_query


def log_action(simulation_id: str, agent_id: str, action_name: str, action_params: Optional[dict] = None) -> None:
    # Get simulation time instead of using NOW()
    try:
        from Environment.simulation_time_manager import get_simulation_time_manager
        time_manager = get_simulation_time_manager(simulation_id)
        sim_time = time_manager.get_current_datetime()
    except Exception:
        # Fallback to real time if simulation time not available
        from datetime import datetime
        sim_time = datetime.now()
    
    _esq, _eaq, _efq = _get_execs()
    _esq(
        """
        INSERT INTO action_log (simulation_id, agent_id, action_name, action_params, timestamp)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (simulation_id, agent_id, action_name, (action_params or {}), sim_time),
        fetch=False,
    )


def log_experience(simulation_id: str, agent_id: str, experience_type: str, content: str, importance_score: float = 0.0) -> None:
    # Get simulation time instead of using NOW()
    try:
        from Environment.simulation_time_manager import get_simulation_time_manager
        time_manager = get_simulation_time_manager(simulation_id)
        sim_time = time_manager.get_current_datetime()
    except Exception:
        # Fallback to real time if simulation time not available
        from datetime import datetime
        sim_time = datetime.now()
    
    _esq, _eaq, _efq = _get_execs()
    _eaq(
        """
        INSERT INTO agent_experiences (simulation_id, agent_id, experience_type, content, importance_score, timestamp)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (simulation_id, agent_id, experience_type, content, importance_score, sim_time),
        fetch=False,
    )


def log_transaction(
    simulation_id: str,
    firm_id: Optional[str],
    agent_id: Optional[str],
    transaction_type: str,
    amount: float,
    description: Optional[str] = None,
    transaction_id: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> None:
    # Get simulation time instead of using NOW()
    try:
        from Environment.simulation_time_manager import get_simulation_time_manager
        time_manager = get_simulation_time_manager(simulation_id)
        sim_time = time_manager.get_current_datetime()
    except Exception:
        # Fallback to real time if simulation time not available
        from datetime import datetime
        sim_time = datetime.now()
    
    _esq, _eaq, _efq = _get_execs()
    _efq(
        """
        INSERT INTO transactions (simulation_id, transaction_id, firm_id, agent_id, transaction_type, amount, description, metadata, timestamp)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            simulation_id,
            transaction_id,
            firm_id,
            agent_id,
            transaction_type,
            amount,
            description,
            (metadata or {}),
            sim_time,
        ),
        fetch=False,
    )


class _DBAdapter:
    def log_action(self, *args, **kwargs) -> None:
        log_action(*args, **kwargs)

    def log_experience(self, *args, **kwargs) -> None:
        log_experience(*args, **kwargs)

    def log_transaction(self, *args, **kwargs) -> None:
        log_transaction(*args, **kwargs)


def get_database_adapter() -> _DBAdapter:
    return _DBAdapter()


__all__ = [
    'get_database_adapter',
    'log_action',
    'log_experience',
    'log_transaction',
]
