#!/usr/bin/env python3
from __future__ import annotations

from typing import Dict, Any, List

from Environment.core.world_state import WorldState


def apply_agent_moved(world: WorldState, event: Dict[str, Any]):
    """Applies the agent_moved event to update agent's position."""
    agent_id = event['metadata']['agent_id']
    new_place_id = event['metadata']['new_place_id']
    world.set_agent_position(agent_id, new_place_id)

def apply_task_scheduled(world: WorldState, event: Dict[str, Any]):
    """Applies the task_scheduled event to add a task to agent's schedule."""
    agent_id = event['metadata']['agent_id']
    task = event['metadata']['task']
    world.add_agent_task(agent_id, task)

def apply_object_state_change(world: WorldState, event: Dict[str, Any]):
    """Applies generic object state changes (e.g., open/close)."""
    # This is a placeholder. Real object state would be more complex.
    object_id = event['metadata']['object_id']
    new_state = event['metadata']['new_state']
    # For now, just log or update a simple object state map if it existed in WorldState
    # print(f"DEBUG: Object {object_id} state changed to {new_state}")
    pass # No direct world state mutation for generic objects yet

def apply_message(world: WorldState, event: Dict[str, Any]):
    """Applies message events (for now, just pass through)."""
    # Messages could be stored in world state for retrieval, but for now just pass
    pass

def apply_object_used(world: WorldState, event: Dict[str, Any]):
    """Applies object_used events."""
    # Generic object use - could update object state or agent state
    pass

# Map event types to their respective reducer functions
ENVIRONMENTAL_REDUCERS = {
    "agent_moved": apply_agent_moved,
    "task_scheduled": apply_task_scheduled,
    "object_open": apply_object_state_change,
    "object_close": apply_object_state_change,
    "object_used": apply_object_used,
    "message": apply_message,
}


