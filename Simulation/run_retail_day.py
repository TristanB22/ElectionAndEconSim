#!/usr/bin/env python3
"""
Test script for running a retail day simulation via the UnifiedSimulationRunner.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add the project root to the path to import modules
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Load environment variables using centralized loader
try:
    from Utils.env_loader import load_environment
    load_environment()
except ImportError:
    from dotenv import load_dotenv
    load_dotenv()

from Simulation.unified_runner import UnifiedSimulationRunner
from Simulation.simulation_config import SimulationConfig
from Api.api_manager import APIManager

def run_retail_day_test():
    """
    Initializes and runs a retail day simulation.
    """
    print("--- Running Retail Day Simulation Test ---")
    
    # Minimal config for a retail day simulation
    config = SimulationConfig(
        name="Retail Day Test",
        description="A test of the retail day simulation with standardized agent creation.",
        simulation_type="retail_day",
        start_datetime=datetime.now(),
        end_datetime=datetime.now(),
        world_context="A typical day in a small town.",
        agent_count=5,
    )

    # The UnifiedSimulationRunner requires an api_manager, but it's not used
    # for config-based runs, so we can pass a mock or None.
    api_manager = APIManager()

    # Create the runner and run from config
    runner = UnifiedSimulationRunner(api_manager=api_manager)
    
    try:
        simulation_id = runner.run_from_config(config)
        print(f"Simulation completed successfully with ID: {simulation_id}")
    except Exception as e:
        print(f"Simulation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_retail_day_test()
