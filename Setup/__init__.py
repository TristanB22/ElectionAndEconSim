"""
Setup Package

Keep top-level imports lightweight to avoid side effects when importing
submodules like `Setup.runtime_config`. We expose Database helpers via
lazy wrappers so importing `Setup` does not import `Setup.Database`.
"""

from typing import Any, Optional

def get_database_adapter():
    from .Database import get_database_adapter as _get
    return _get()

def log_action(simulation_id: str, agent_id: str, action_name: str, action_params: Optional[dict] = None) -> None:
    from .Database import log_action as _log_action
    return _log_action(simulation_id, agent_id, action_name, action_params)

def log_experience(simulation_id: str, agent_id: str, experience_type: str, content: str, importance_score: float = 0.0) -> None:
    from .Database import log_experience as _log_experience
    return _log_experience(simulation_id, agent_id, experience_type, content, importance_score)

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
    from .Database import log_transaction as _log_transaction
    return _log_transaction(
        simulation_id,
        firm_id,
        agent_id,
        transaction_type,
        amount,
        description,
        transaction_id,
        metadata,
    )

__all__ = [
    'get_database_adapter',
    'log_action',
    'log_experience',
    'log_transaction',
]
