#!/usr/bin/env python3
"""
Reset (wipe) the simulations table.

Deletes all rows from world_sim_simulations.simulations using the
centralized simulations DB manager.
"""

from __future__ import annotations

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def main() -> int:

    try:
        from Database.managers import get_simulations_manager
        mgr = get_simulations_manager()

        # Call the reset method
        success = mgr.reset_simulations()
        
        if success:
            print("Deleted all rows from simulations table.")
            return 0
        else:
            print("Failed to wipe simulations table.")
            return 1
    except Exception as e:
        print(f"Error wiping simulations table: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())


