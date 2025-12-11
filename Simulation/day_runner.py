#!/usr/bin/env python3
"""
Generalized Day Simulation Runner

Sets up a full-day simulation (midnight->midnight), converts agent plans into
scheduled events using ATUS-informed planning, and executes the day using tick-based progression.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Dict, Any, Optional

from Environment.day_simulation_manager import DaySimulationManager
from Environment.plan_to_schedule_converter import (
    convert_plan_to_scheduled_events,
    create_realistic_daily_schedule,
)
from Agent.cognitive_modules.structured_planning import PlanStep


def run_full_day(
    simulation_id: str,
    world: Any,
    agents: List[Any],
    goals_by_agent_id: Dict[str, str],
    world_context: str,
    base_date: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Run a full day simulation for the provided agents using ATUS-informed planning.

    Args:
        simulation_id: Simulation id
        world: Initialized world instance
        agents: List of agent objects
        goals_by_agent_id: Mapping of agent_id -> goal string
        world_context: Context string passed to planners
        base_date: Base date for simulation (defaults to today)

    Returns:
        Results dict from the DaySimulationManager
    """
    # Initialize day manager at provided date's midnight (or today if not provided)
    if base_date is None:
        simulation_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        simulation_date = base_date.replace(hour=0, minute=0, second=0, microsecond=0)
    day_manager = DaySimulationManager(simulation_id, simulation_date)

    from Agent.modules.plan_executor import PlanExecutor
    from Agent.modules.planning.orchestrator import DailyPlanningOrchestrator

    executor = PlanExecutor(world)
    orchestrator = DailyPlanningOrchestrator(simulation_id)

    # Generate plans for all agents using ATUS-informed planning
    wakeup_times: Dict[str, datetime] = {}
    agent_ages: Dict[str, int] = {}
    planning_errors: Dict[str, Exception] = {}
    plan_results: Dict[str, List[PlanStep]] = {}

    print(f"[planning] Generating ATUS-informed plans for {len(agents)} agents")

    # Check verbosity for plan printing
    verbosity = 0
    try:
        import os
        verbosity = int(os.getenv('VERBOSITY', os.getenv('VERBOSITY_LEVEL', '1')))
    except Exception:
        verbosity = 1

    for agent in agents:
        agent_id = str(agent.agent_id)
        goal = goals_by_agent_id.get(agent_id) or "Perform daily activities"
        age = agent.get_age() if hasattr(agent, "get_age") and agent.get_age() is not None else 30
        agent_ages[agent_id] = age

        wake_up = day_manager.generate_realistic_wake_up_time(age)
        wakeup_times[agent_id] = wake_up

        # Set current simulation date on agent for planning
        agent.current_simulation_date = simulation_date.date()

        # Generate plan using ATUS-informed orchestrator
        try:
            plan_id, plan_steps = orchestrator.generate_daily_plan(
                agent=agent,
                target_day=simulation_date.date(),
                goal=goal,
                world_context=world_context,
            )
            if plan_steps:
                plan_results[agent_id] = plan_steps
                print(f"[planning] agent={agent_id} ATUS_plan_generated plan_id={plan_id} steps={len(plan_steps)}")
                # Print example plan if verbosity is high (>= 3)
                if verbosity >= 3 and len(plan_results) <= 2:  # Only print first 2 agents
                    print(f"\n  Example Plan for {agent_id} (plan_id={plan_id}):")
                    for i, step in enumerate(plan_steps[:8], 1):  # Show first 8 steps
                        params_str = ""
                        if hasattr(step, 'parameters') and step.parameters:
                            params_str = f" params={step.parameters}"
                        print(f"    {i}. {step.target_time}: {step.action} at {step.location}{params_str}")
                    if len(plan_steps) > 8:
                        print(f"    ... and {len(plan_steps) - 8} more steps")
            else:
                print(f"[planning] agent={agent_id} ATUS_plan_empty")
        except Exception as exc:
            planning_errors[agent_id] = exc
            print(f"[planning] agent={agent_id} ATUS_planning_failed: {exc}")
            import traceback
            traceback.print_exc()

    # Assemble schedules, falling back to synthetic day plans when necessary
    for agent in agents:
        agent_id = str(agent.agent_id)
        goal = goals_by_agent_id.get(agent_id) or "Perform daily activities"
        wake_up_time = wakeup_times.get(agent_id) or day_manager.generate_realistic_wake_up_time(agent_ages.get(agent_id, 30))
        agent_age = agent_ages.get(agent_id, 30)

        plan_steps = plan_results.get(agent_id)
        scheduled_events: List[Any] = []

        if plan_steps:
            try:
                scheduled_events = convert_plan_to_scheduled_events(agent_id, plan_steps, simulation_date, wake_up_time)
            except Exception as exc:
                planning_errors[agent_id] = exc
                scheduled_events = []

        if not scheduled_events:
            if agent_id in planning_errors:
                error_msg = planning_errors[agent_id]
                print(f"[planning] agent={agent_id} falling_back_to_realistic_schedule: {error_msg}")
            scheduled_events = create_realistic_daily_schedule(
                agent_id,
                agent_age,
                simulation_date,
                [goal],
                world_context,
            )

        day_manager.add_agent_schedule(agent_id, wake_up_time, scheduled_events)

    # Store agents in world for access during execution
    world._agents_cache = agents
    
    # Execute the full day
    return day_manager.run_full_day_simulation(world, executor)
