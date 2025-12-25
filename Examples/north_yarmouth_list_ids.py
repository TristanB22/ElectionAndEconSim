#!/usr/bin/env python3
"""
List LALVOTERIDs for residents of North Yarmouth, ME, up to a specified number (default 10).
"""

import sys
import os
import traceback
from datetime import datetime
from pathlib import Path
import argparse
import logging

# Suppress httpx INFO logs
logging.getLogger("httpx").setLevel(logging.WARNING)

# Ensure project root on path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Load environment and switch to NAS
env_path = project_root / '.env'
try:
    from Utils.env_loader import load_environment
    load_environment(env_path)
except Exception:
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path)
    except Exception:
        pass

# Respect environment; do not force DATABASE_TARGET here


def _now_ts() -> str:
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def log_exception(context: str) -> None:
    print(f"[{_now_ts()}] ERROR in {context}")
    print(traceback.format_exc())


def main(num_agents: int = 10):
    from Database.managers import get_simulations_manager
    sim_mgr = get_simulations_manager()
    import json
    
    # Check verbosity once at the start
    verbosity = int(os.getenv('VERBOSITY', '3'))

    sql = (
        "SELECT l2_location.LALVOTERID, l2_location.*, l2_other_part_1.Residence_Families_FamilyID "
        "FROM l2_location "
        "LEFT JOIN l2_other_part_1 ON l2_location.lalvoterid = l2_other_part_1.lalvoterid "
        "WHERE l2_location.Residence_Addresses_City LIKE %s "
        "ORDER BY l2_other_part_1.Residence_Families_FamilyID ASC "
        f"LIMIT {num_agents}"
    )
    params = ("%North Yarmouth%",)
    try:
        # Use simulation manager's consolidated selection helper
        voter_ids = sim_mgr.select_voter_ids_raw_sql(sql, params)
    except Exception:
        log_exception('select_voter_ids_raw_sql')
        voter_ids = []
    if verbosity > 0:
        print(f"First {num_agents} LALVOTERIDs for North Yarmouth, ME:")
        try:
            for i, vid in enumerate(voter_ids, 1):
                print(f"{i:2d}. {vid}")
            print(f"Found {len(voter_ids)} voter IDs for the query.")
        except Exception:
            log_exception('printing voter_ids')

    # Register simulation in DB
    simulation_id = None
    try:
        started_by = 'north_yarmouth_example'
        description = 'North Yarmouth voter ID listing and simulation registration'
        sim_start = datetime(2025, 11, 1, 5, 0, 0)
        sim_end = None
        tick_granularity = '15m'
        config_json = {
            'agent_selection_method': 'raw_sql',
            'sql': sql,
            'sql_params': params,
            'city': 'North Yarmouth',
            'state': 'ME',
            'limit': num_agents
        }

        # Select N agent ids up front so registration seeds locations automatically
        selected_ids = voter_ids[:num_agents]
        simulation_id = sim_mgr.register_simulation(
            started_by=started_by,
            description=description,
            sim_start=sim_start,
            tick_granularity=tick_granularity,
            config=config_json,
            agent_ids=selected_ids,
        )
        if verbosity > 0:
            print(f"Registered simulation: {simulation_id}")


        # End the simulation now with updated fields
        if simulation_id:
            sim_end_dt = datetime(2025, 11, 1, 23, 59, 59)
            results_json = {
                'agent_count': min(num_agents, len(voter_ids)),
                'note': 'Initialized first N agents',
            }
            try:
                sim_mgr.complete_simulation(simulation_id, results=results_json, end_dt=sim_end_dt)
            except Exception:
                log_exception('complete_simulation_update')
            if verbosity > 0:
                print("Completed simulation and updated records")
    except Exception as e:
        log_exception('main try block')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="List N LALVOTERIDs for North Yarmouth, ME and create a simulation.")
    parser.add_argument(
        "-n", "--num-agents", 
        type=int, 
        default=10, 
        help="Number of LALVOTERIDs/agents to retrieve and use (default: 10)"
    )
    args = parser.parse_args()
    main(args.num_agents)

