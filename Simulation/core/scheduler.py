#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Callable, List, Dict, Any

from Environment.reducers import environmental
from Environment.reducers import firm_common


class InMemoryEventBus:
    def __init__(self) -> None:
        self._queue: List[Dict[str, Any]] = []

    def append(self, evt: Dict[str, Any]) -> None:
        self._queue.append(evt)

    def drain(self) -> List[Dict[str, Any]]:
        evts = self._queue
        self._queue = []
        return evts


def advance_to(now: datetime, world, event_bus: InMemoryEventBus) -> None:
    """
    Apply all queued events (deterministic reducer order) to world state.
    """
    events = event_bus.drain()
    if not events:
        return
    
    # Define a deterministic order for reducers
    # This is important for reproducibility if multiple reducers affect the same state
    all_reducers = {
        **environmental.ENVIRONMENTAL_REDUCERS,
        **firm_common.FIRM_COMMON_REDUCERS,
        # Add other reducer modules here
    }
    
    # Sort reducers by name for deterministic application order
    sorted_reducer_keys = sorted(all_reducers.keys())

    for event in events:
        event_type = event.get('event_type')
        if event_type:
            reducer_func = all_reducers.get(event_type)
            if reducer_func:
                try:
                    reducer_func(world, event)
                    # logger.debug(f"Applied reducer for event type: {event_type}")
                except Exception as e:
                    logger.error(f"Error applying reducer for event type {event_type}: {e}", exc_info=True)
            # else:
                # logger.warning(f"No reducer found for event type: {event_type}")


def run_agents(now: datetime, agents: List[Any], step_fn: Callable[[Any, datetime], None]) -> None:
    for agent in agents:
        step_fn(agent, now)


def parse_tick(spec: str) -> timedelta:
    """Parse tick spec like '15m', '1h', '3h', '1d', '1w' into timedelta."""
    s = (spec or '').strip().lower()
    if not s:
        return timedelta(minutes=15)
    try:
        if s.endswith('m'):
            return timedelta(minutes=int(s[:-1]))
        if s.endswith('h'):
            return timedelta(hours=int(s[:-1]))
        if s.endswith('d'):
            return timedelta(days=int(s[:-1]))
        if s.endswith('w'):
            return timedelta(weeks=int(s[:-1]))
        # default assume minutes
        return timedelta(minutes=int(s))
    except Exception:
        return timedelta(minutes=15)


def tick_steps(start: datetime, end: datetime, step: timedelta):
    cur = start
    while cur < end:
        yield cur
        cur += step


