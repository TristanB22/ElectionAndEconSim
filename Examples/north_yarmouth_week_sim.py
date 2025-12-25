#!/usr/bin/env python3
"""
North Yarmouth Weekly Simulation Runner

Selects N North Yarmouth residents from L2, creates a simulation that
runs one week starting October 31, 2025, and executes 7 day runs with
planning enabled (plans stored to DB under the simulation_id).

Usage:
    python Examples/north_yarmouth_week_sim.py --agents 20

Notes:
    - Requires L2 data in database
    - Requires ATUS precompute tables populated
    - Uses existing day runner (which calls agent.create_day_plan)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import argparse
from typing import List, Dict
import time

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Utils.path_manager import initialize_paths
initialize_paths()

from Database.managers import get_simulations_manager
from Simulation.simulation_manager import create_simulation, init_world_for_simulation
from Agent.factory import AgentFactory
from Simulation.day_runner import run_full_day


# Hardcoded agent IDs to ask questions to (choose 3)
HARDCODED_QUESTION_AGENT_IDS = [
    "LALME175502521",
    "LALME175511870",
    "LALME176380875",
]

def select_north_yarmouth_voter_ids(limit: int) -> List[str]:
    sim_mgr = get_simulations_manager()
    sql = (
        "SELECT l2_location.LALVOTERID, l2_location.*, l2_other_part_1.Residence_Families_FamilyID "
        "FROM l2_location "
        "LEFT JOIN l2_other_part_1 ON l2_location.lalvoterid = l2_other_part_1.lalvoterid "
        "WHERE l2_location.Residence_Addresses_City LIKE %s "
        "ORDER BY l2_other_part_1.Residence_Families_FamilyID ASC "
        f"LIMIT {limit}"
    )
    params = ("%North Yarmouth%",)
    rows = sim_mgr.select_voter_ids_raw_sql(sql, params)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Run North Yarmouth weekly simulation")
    parser.add_argument("--agents", type=int, default=10, help="Number of agents to include")
    parser.add_argument("--start", type=str, default="2025-10-31", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--days", type=int, default=3, help="Number of days to run (default 3)")
    parser.add_argument("--goal", type=str, default="Perform daily activities", help="Default agent daily goal")
    parser.add_argument("--world-context", type=str, default="North Yarmouth, Maine in late 2025. Quiet fall week.", help="World context string")
    parser.add_argument("--clear-simulations", action="store_true", help="Clear simulation tables before starting")
    parser.add_argument("--skip-simulation", action="store_true", help="Skip day-by-day simulation and go straight to asking questions")
    args = parser.parse_args()
    
    # Clear simulations if requested
    if args.clear_simulations:
        print("Clearing simulation tables...")
        try:
            from Database.managers import get_simulations_manager
            mgr = get_simulations_manager()
            success = mgr.reset_simulations()
            if success:
                print("Simulation tables cleared.")
            else:
                print("Warning: Failed to clear simulation tables (continuing anyway)")
        except Exception as e:
            print(f"Warning: Error clearing simulation tables: {e} (continuing anyway)")

    start_date = datetime.strptime(args.start, "%Y-%m-%d")
    end_date = start_date + timedelta(days=args.days)

    # Select voter IDs FIRST (before creating simulation)
    # select_north_yarmouth_voter_ids already returns a list of LALVOTERID strings
    voter_ids = select_north_yarmouth_voter_ids(args.agents)
    if not voter_ids:
        print("No voter IDs found for North Yarmouth selection.")
        return 1

    # Create simulation record WITH agent_ids to trigger automatic initialization and location seeding
    print(f"Creating simulation with {len(voter_ids)} agents...")
    from Database.managers import get_simulations_manager
    mgr = get_simulations_manager()
    
    config = {
        'agent_selection_method': 'north_yarmouth_voters',
        'num_agents': args.agents,
        'planned_end_datetime': end_date.isoformat()
    }
    
    # Use register_simulation directly to pass agent_ids
    # This will automatically call bulk_initialize_agents which seeds locations
    sim_id = mgr.register_simulation(
        started_by="north_yarmouth_week",
        description=f"North Yarmouth weekly sim: {args.agents} agents",
        sim_start=start_date,
        tick_granularity="15m",
        config=config,
        agent_ids=voter_ids  # CRITICAL: This triggers location seeding
    )
    
    print(f"Simulation created: {sim_id}")
    print("Agent locations seeded automatically")

    # Ensure the simulation_end_datetime is persisted so time manager respects overall end
    try:
        mgr.update_simulation_status(sim_id, 'running', end_datetime=end_date)
    except Exception as e:
        print(f"Warning: could not set simulation_end_datetime: {e}")

    # Initialize world
    world = init_world_for_simulation(sim_id)

    # Pre-load summaries in bulk to avoid per-agent database queries during creation
    # This significantly speeds up agent creation and prevents connection pool exhaustion
    print(f"Pre-loading summaries for {len(voter_ids)} agents...")
    verbosity = 0
    try:
        verbosity = int(os.getenv('VERBOSITY', os.getenv('VERBOSITY_LEVEL', '1')))
    except Exception:
        verbosity = 1
    t0 = time.perf_counter()
    from Database.managers import get_agents_manager
    agents_mgr = get_agents_manager()
    summaries_dict = agents_mgr.bulk_get_summaries(voter_ids, summary_type="llm_personal")
    print(f"Loaded {len(summaries_dict)} summaries")
    if verbosity >= 3:
        print(f"[timing] bulk_get_summaries: {time.perf_counter() - t0:.2f}s")

    # Create Agent objects (records already exist from bulk_initialize_agents)
    t0 = time.perf_counter()
    agents = AgentFactory.batch_from_database(voter_ids, simulation_id=sim_id)
    if verbosity >= 3:
        print(f"[timing] AgentFactory.batch_from_database: {time.perf_counter() - t0:.2f}s for {len(voter_ids)} agents")
    
    if not agents:
        print("ERROR: No agents were successfully created. Check L2 data availability.")
        return 1
    
    print(f"Successfully created {len(agents)} agents")

    # Attach agents to world, set simulation date, and inject pre-loaded summaries
    for agent in agents:
        agent.world = world
        agent.simulation_id = sim_id
        # Set pre-loaded summary if available (avoids individual DB queries)
        agent_id_str = str(agent.agent_id)
        if agent_id_str in summaries_dict:
            agent.llm_summary = summaries_dict[agent_id_str]

    # Goals mapping
    goals_by_agent: Dict[str, str] = {str(a.agent_id): args.goal for a in agents}

    # If skip_simulation is enabled, jump straight to asking questions
    if args.skip_simulation:
        print(f"\n=== Skipping simulation, asking questions directly to {len(agents)} agents ===")
        try:
            from Agent.modules.god_given_questions import ask_scheduled_questions
            from Examples.north_yarmouth_questions import NORTH_YARMOUTH_QUESTIONS
            
            # Use start_date as timestamp (simulation start time)
            question_timestamp = start_date
            
            # Use hardcoded agent IDs for questioning
            selected_agent_ids = HARDCODED_QUESTION_AGENT_IDS

            ask_scheduled_questions(
                simulation_id=sim_id,
                agents=agents,
                questions=NORTH_YARMOUTH_QUESTIONS,
                simulation_timestamp=question_timestamp,
                agent_ids=selected_agent_ids,
                skip_existing=False
            )
            print("All questions completed and logged to database")
        except Exception as e:
            print(f"Warning: Failed to ask questions: {e}")
            import traceback
            traceback.print_exc()
        
        print(f"\nCompleted North Yarmouth question session: {sim_id}")
        print(f"Simulation ID: {sim_id}  Start: {start_date}  End: {end_date}")
        return 0
    
    # Execute one day at a time for the requested window
    current = start_date
    
    for i in range(args.days):
        day_number = i + 1
        print(f"\n=== Running day {day_number}/{args.days}: {current.strftime('%Y-%m-%d')} ===")
        # Set current simulation date on agents for planning
        for agent in agents:
            agent.current_simulation_date = current.date()
        
        run_full_day(
            simulation_id=sim_id,
            world=world,
            agents=agents,
            goals_by_agent_id=goals_by_agent,
            world_context=args.world_context,
            base_date=current,
        )
        current += timedelta(days=1)
        
    # Ask questions at the end of the simulation to the hardcoded IDs
    if True:
        print(f"\n=== Asking questions to {len(agents)} agents (at simulation end) ===")
        try:
            from Agent.modules.god_given_questions import ask_scheduled_questions
            from Examples.north_yarmouth_questions import NORTH_YARMOUTH_QUESTIONS
            
            selected_agent_ids = HARDCODED_QUESTION_AGENT_IDS

            ask_scheduled_questions(
                simulation_id=sim_id,
                agents=agents,
                questions=NORTH_YARMOUTH_QUESTIONS,
                simulation_timestamp=end_date,
                agent_ids=selected_agent_ids,
                skip_existing=False
            )
            print("All questions completed and logged to database")
        except Exception as e:
            print(f"Warning: Failed to ask questions: {e}")
            import traceback
            traceback.print_exc()

    # Print example plans for a few agents
    print(f"\n=== Example Plans from Simulation ===")
    try:
        from Agent.modules.plan_manager import PlanManager
        plan_mgr = PlanManager(sim_id)
        
        # Get plans for the first 3 agents
        example_agents = [str(a.agent_id) for a in agents[:3]]
        for agent_id in example_agents:
            plans = plan_mgr.get_agent_plans(agent_id, status=None)
            if plans:
                latest_plan = plans[0]  # Most recent plan
                plan_id = latest_plan.get('id')
                steps = latest_plan.get('steps', [])
                if steps:
                    print(f"\n  Agent {agent_id} - Plan ID {plan_id} ({len(steps)} steps):")
                    for i, step in enumerate(steps[:10], 1):  # Show first 10 steps
                        action = step.get('action', 'Unknown')
                        time_str = step.get('target_time', 'Unknown')
                        location = step.get('location', 'Unknown')
                        travel = step.get('travel_destination')
                        exchange = step.get('exchange_counterparty')
                        wait_min = step.get('wait_minutes')
                        details = []
                        if travel:
                            details.append(f"to={travel}")
                        if exchange:
                            details.append(f"counterparty={exchange}")
                        if wait_min:
                            details.append(f"min={wait_min}")
                        detail_str = f" ({', '.join(details)})" if details else ""
                        print(f"    {i}. {time_str}: {action} at {location}{detail_str}")
                    if len(steps) > 10:
                        print(f"    ... and {len(steps) - 10} more steps")
    except Exception as e:
        print(f"Warning: Could not retrieve example plans: {e}")
        if verbosity >= 2:
            import traceback
            traceback.print_exc()

    print(f"\nCompleted North Yarmouth weekly sim: {sim_id}")
    print(f"Start: {start_date}  End: {end_date}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


