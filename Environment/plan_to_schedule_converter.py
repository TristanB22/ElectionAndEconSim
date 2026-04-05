#!/usr/bin/env python3
"""
Plan to Schedule Converter

Converts agent day plans into scheduled events for the day simulation manager.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from Environment.day_simulation_manager import ScheduledEvent


def parse_time_string(time_str: str, base_date: datetime) -> datetime:
    """
    Parse a time string like "09:00 AM" or "1015 AM" and return a datetime object.
    
    Args:
        time_str: Time string in format "HH:MM AM/PM" or "HHMM AM/PM"
        base_date: Base date to use for the datetime
        
    Returns:
        datetime object representing the parsed time on the base date
    """
    try:
        # Normalize the time string: handle formats like "1015 AM" -> "10:15 AM"
        normalized = time_str.strip()
        
        # If the string doesn't contain a colon, try to insert one
        if ':' not in normalized:
            # Look for pattern like "1015 AM" or "915 AM"
            import re
            # Match pattern: digits followed by AM/PM
            match = re.match(r'(\d{1,2})(\d{2})\s*(AM|PM)', normalized, re.IGNORECASE)
            if match:
                hour = match.group(1)
                minute = match.group(2)
                am_pm = match.group(3).upper()
                normalized = f"{hour}:{minute} {am_pm}"
        
        # Parse time string like "09:00 AM"
        time_obj = datetime.strptime(normalized, "%I:%M %p").time()
        # Combine with base date
        return datetime.combine(base_date.date(), time_obj)
    except (ValueError, AttributeError) as e:
        print(f"Warning: Could not parse time '{time_str}': {e}")
        # Return a default time (9:00 AM) if parsing fails
        return base_date.replace(hour=9, minute=0, second=0, microsecond=0)


def convert_plan_to_scheduled_events(
    agent_id: str, 
    plan_steps: List[Any], 
    base_date: datetime,
    wake_up_time: datetime
) -> List[ScheduledEvent]:
    """
    Convert agent plan steps to scheduled events.
    
    Args:
        agent_id: ID of the agent
        plan_steps: List of plan steps from the agent's planner
        base_date: Base date for the simulation
        wake_up_time: When the agent wakes up
        
    Returns:
        List of ScheduledEvent objects
    """
    scheduled_events = []
    
    for i, step in enumerate(plan_steps):
        try:
            # Parse the target time from the plan step (PlanStep objects have direct attributes)
            target_time = parse_time_string(getattr(step, 'target_time', ''), base_date)
            
            # Ensure the time is after wake-up time
            if target_time < wake_up_time:
                # Adjust time to be after wake-up, with some buffer
                target_time = wake_up_time + timedelta(minutes=15 + (i * 5))
            
            # Create scheduled event
            event = ScheduledEvent(
                simulation_time=target_time,
                agent_id=agent_id,
                action_name=getattr(step, 'action', 'Unknown'),
                action_params=getattr(step, 'parameters', {}),
                location=getattr(step, 'location', 'unknown'),
                priority=i  # Lower index = higher priority
            )
            
            scheduled_events.append(event)
            
        except Exception as e:
            print(f"Warning: Could not convert plan step {i} for agent {agent_id}: {e}")
            continue
    
    return scheduled_events


def create_realistic_daily_schedule(
    agent_id: str,
    agent_age: int,
    base_date: datetime,
    goals: List[str],
    world_context: str
) -> List[ScheduledEvent]:
    """
    Create a realistic daily schedule for an agent based on their characteristics.
    
    Args:
        agent_id: ID of the agent
        agent_age: Age of the agent
        base_date: Base date for the simulation
        goals: List of goals for the day
        world_context: Context about the world (stores, etc.)
        
    Returns:
        List of ScheduledEvent objects representing the agent's day
    """
    from Environment.day_simulation_manager import DaySimulationManager
    
    # Generate realistic wake-up time
    day_manager = DaySimulationManager("temp", base_date)
    wake_up_time = day_manager.generate_realistic_wake_up_time(agent_age)
    
    # Create basic daily structure based on age and goals
    scheduled_events = []
    
    # Morning routine (after wake-up)
    morning_start = wake_up_time + timedelta(minutes=30)
    
    # Add morning routine events
    scheduled_events.append(ScheduledEvent(
        simulation_time=morning_start,
        agent_id=agent_id,
        action_name="MorningRoutine",
        action_params={"duration_minutes": 45},
        location="home",
        priority=1
    ))
    
    # Add goal-related events throughout the day
    for i, goal in enumerate(goals):
        # Space out goals throughout the day
        goal_time = morning_start + timedelta(hours=2 + (i * 2))
        
        if "grocery" in goal.lower() or "store" in goal.lower():
            # Shopping trip - determine specific item from goal
            item_sku = "MILK_GAL"  # Default fallback
            if "milk" in goal.lower():
                item_sku = "MILK_GAL"
            elif "eggs" in goal.lower():
                item_sku = "EGGS_12"
            elif "bread" in goal.lower():
                item_sku = "BREAD_WHT"
            
            scheduled_events.append(ScheduledEvent(
                simulation_time=goal_time,
                agent_id=agent_id,
                action_name="Travel",
                action_params={"to": "store"},
                location="in_transit",
                priority=2 + i
            ))
            
            scheduled_events.append(ScheduledEvent(
                simulation_time=goal_time + timedelta(minutes=15),
                agent_id=agent_id,
                action_name="Exchange",
                action_params={"counterparty": "test_firm_001", "receive": {item_sku: 1}},
                location="store",
                priority=2 + i
            ))
            
            scheduled_events.append(ScheduledEvent(
                simulation_time=goal_time + timedelta(minutes=30),
                agent_id=agent_id,
                action_name="Travel",
                action_params={"to": "home"},
                location="in_transit",
                priority=2 + i
            ))
        
        elif "work" in goal.lower() or "job" in goal.lower():
            # Work-related activity
            scheduled_events.append(ScheduledEvent(
                simulation_time=goal_time,
                agent_id=agent_id,
                action_name="Work",
                action_params={"duration_hours": 8},
                location="workplace",
                priority=2 + i
            ))
    
    # Evening routine
    evening_time = base_date.replace(hour=18, minute=0, second=0, microsecond=0)
    scheduled_events.append(ScheduledEvent(
        simulation_time=evening_time,
        agent_id=agent_id,
        action_name="EveningRoutine",
        action_params={"duration_minutes": 60},
        location="home",
        priority=10
    ))
    
    # Bedtime
    bedtime = base_date.replace(hour=22, minute=0, second=0, microsecond=0)
    scheduled_events.append(ScheduledEvent(
        simulation_time=bedtime,
        agent_id=agent_id,
        action_name="Sleep",
        action_params={"duration_hours": 8},
        location="home",
        priority=11
    ))
    
    return scheduled_events


def validate_schedule(scheduled_events: List[ScheduledEvent]) -> Dict[str, Any]:
    """
    Validate a schedule for logical consistency.
    
    Args:
        scheduled_events: List of scheduled events to validate
        
    Returns:
        Dictionary with validation results
    """
    validation_results = {
        'is_valid': True,
        'warnings': [],
        'errors': []
    }
    
    if not scheduled_events:
        validation_results['is_valid'] = False
        validation_results['errors'].append("No events scheduled")
        return validation_results
    
    # Check for time conflicts
    sorted_events = sorted(scheduled_events, key=lambda x: x.simulation_time)
    
    for i in range(len(sorted_events) - 1):
        current_event = sorted_events[i]
        next_event = sorted_events[i + 1]
        
        # Check if events are too close together (less than 5 minutes apart)
        time_diff = (next_event.simulation_time - current_event.simulation_time).total_seconds() / 60
        
        if time_diff < 5:
            validation_results['warnings'].append(
                f"Events {current_event.action_name} and {next_event.action_name} "
                f"are very close together ({time_diff:.1f} minutes apart)"
            )
    
    # Check for reasonable time distribution
    if len(sorted_events) > 1:
        total_duration = (sorted_events[-1].simulation_time - sorted_events[0].simulation_time).total_seconds() / 3600
        
        if total_duration > 24:
            validation_results['errors'].append("Schedule spans more than 24 hours")
            validation_results['is_valid'] = False
    
    return validation_results
