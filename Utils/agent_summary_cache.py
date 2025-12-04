#!/usr/bin/env python3
"""
Agent personal summary cache backed by the agents DB.

Delegates to AgentsDatabaseManager for all database operations.
"""

from __future__ import annotations

from typing import Optional
import json

from Utils.path_manager import initialize_paths
initialize_paths()


def ensure_agent(agent_id: str, *, name: str | None = None, l2_voter_id: str | None = None) -> None:
    """
    Public helper to upsert an agent row with optional L2 voter id.
    Delegates to AgentsDatabaseManager.
    """
    try:
        from Database.managers import get_agents_manager
        get_agents_manager().ensure_agent(agent_id, name=name, l2_voter_id=l2_voter_id)
    except Exception:
        # Swallow errors to avoid breaking call sites
        pass


def get_summary(agent_id: str) -> Optional[str]:
    """
    Get agent personal summary.
    Delegates to AgentsDatabaseManager.
    """
    try:
        from Database.managers import get_agents_manager
        return get_agents_manager().get_agent_summary(agent_id, summary_type='llm_personal')
    except Exception:
        return None


def upsert_summary(agent_id: str, summary: str, reasoning: str = "", metadata: dict = None, 
                  model: Optional[str] = None, *, 
                  name: Optional[str] = None, age: Optional[int] = None, 
                  l2_voter_id: Optional[str] = None) -> None:
    """
    Upsert agent personal summary.
    Delegates to AgentsDatabaseManager.
    """
    try:
        from Database.managers import get_agents_manager
        mgr = get_agents_manager()
        # Ensure agent row exists first
        mgr.ensure_agent(agent_id, name=name, l2_voter_id=l2_voter_id)
        # If a summary already exists, do not create a new one
        existing = mgr.get_agent_summary(agent_id, summary_type='llm_personal')
        if existing:
            return
        # Otherwise insert
        mgr.upsert_agent_summary(agent_id, summary, summary_type='llm_personal', 
                                reasoning=reasoning, metadata=metadata)
    except Exception:
        # Swallow errors for robustness
        pass


def get_or_create_summary(agent, model: Optional[str] = None) -> Optional[str]:
    """
    Get or create agent personal summary.
    """
    agent_id = str(getattr(agent, 'agent_id', '') or '')
    if not agent_id:
        return None
    existing = get_summary(agent_id)
    if existing:
        return existing

    # Try to generate using available personal summary generator
    try:
        gen = getattr(agent, 'personal_summary', None)
        if gen is None:
            return None
        if hasattr(gen, 'create_llm_summary'):
            result = gen.create_llm_summary(agent)
            # Handle tuple (summary, reasoning, metadata) returns
            if isinstance(result, tuple) and len(result) == 3:
                summary, reasoning, metadata = result
            else:
                # Backwards compatibility for older return formats
                summary = result
                reasoning = ""
                metadata = {}
        else:
            summary = None
            reasoning = ""
            metadata = {}
        if summary:
            upsert_summary(agent_id, summary, reasoning, metadata, model)
        return summary
    except Exception as e:
        import traceback
        print(f"[ERROR] Exception in get_or_create_summary: {e}")
        print(f"[ERROR] Exception type: {type(e)}")
        traceback.print_exc()
        return None



