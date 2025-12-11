"""
Simulations database manager package.

This module re-exports the primary manager classes and helper functions to
preserve the public interface that previously lived in
`Database.managers.simulations`.
"""

from .manager import SimulationsDatabaseManager, get_simulations_manager

__all__ = ["SimulationsDatabaseManager", "get_simulations_manager"]
