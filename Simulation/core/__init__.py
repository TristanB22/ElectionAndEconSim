"""
Simulation Core Module

Contains fundamental simulation primitives:
- World: Central state container and coordination
- Scheduler: Event scheduling and time progression utilities
"""

from .world import World
from .scheduler import (
    InMemoryEventBus,
    advance_to,
    run_agents,
    parse_tick,
    tick_steps
)

__all__ = [
    'World',
    'InMemoryEventBus',
    'advance_to',
    'run_agents',
    'parse_tick',
    'tick_steps'
]

