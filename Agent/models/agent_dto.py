from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class AgentDTO:
    """
    Lightweight, serialization-friendly representation of an agent.

    Contains just the data required to reconstruct an Agent instance or to
    perform planning/summary work in multiprocessing contexts without holding
    open database connections.
    """

    agent_id: str
    simulation_id: Optional[str]
    l2_data: Optional[Dict[str, Any]]
    llm_summary: Optional[str] = None
    l2_summary: Optional[str] = None
