"""
Agents database manager package.

Re-exports the public manager classes and accessors so existing imports
(`Database.managers import get_agents_manager`) continue to work.
"""

from .manager import AgentsDatabaseManager, get_agents_manager

__all__ = ["AgentsDatabaseManager", "get_agents_manager"]
