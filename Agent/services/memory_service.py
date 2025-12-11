from __future__ import annotations

from Agent.agent import Agent


def get_memory_manager(agent: Agent):
    """
    Retrieve the agent's memory manager, ensuring lazy initialization.

    Raises:
        RuntimeError: if the memory subsystem cannot be initialized.
    """
    return agent.memory_manager
