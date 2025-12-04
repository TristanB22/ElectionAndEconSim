import datetime
from typing import List, Dict, Any, Optional
from ..prompt_template import (
    run_gpt_prompt_daily_planning,
    run_gpt_prompt_weekly_planning,
    run_gpt_prompt_action_planning,
    run_gpt_prompt_goal_setting
)
from .retrieve import retrieve_memories_for_planning, get_memory_summary_for_context

def create_daily_plan(agent,
                     current_date: datetime.date = None,
                     wake_up_hour: int = 7) -> Optional[Dict[str, Any]]:
    """
    Create a daily plan for the agent.
    
    Args:
        agent: The agent to create a plan for
        current_date (datetime.date): Date to plan for (default: today)
        wake_up_hour (int): Preferred wake up hour
        
    Returns:
        Optional[Dict]: Daily plan with schedule and goals
    """
    if current_date is None:
        current_date = datetime.date.today()
    
    # Get the most recent reflection if available
    recent_reflection = ""
    if hasattr(agent, 'reflection_memory') and agent.reflection_memory.daily_reflections:
        recent_reflection = agent.reflection_memory.daily_reflections[-1].reflection_text
    
    # Get current goals
    current_goals = []
    if hasattr(agent, 'reflection_memory') and agent.reflection_memory.long_term_goals:
        current_goals = agent.reflection_memory.long_term_goals
    
    # Get relevant memories for planning
    relevant_memories = retrieve_memories_for_planning(
        memory_store=agent.memory_stream,
        planning_context="daily planning schedule activities",
        agent_goals=current_goals
    )
    
    # Include memory context in the reflection if we have relevant memories
    if relevant_memories:
        memory_summary = get_memory_summary_for_context(relevant_memories, max_length=300)
        recent_reflection += f"\n\nRelevant recent experiences:\n{memory_summary}"
    
    # Generate the daily plan
    daily_plan = run_gpt_prompt_daily_planning(
        agent_name=agent.name,
        reflection=recent_reflection,
        goals=current_goals,
        current_date=current_date.strftime("%Y-%m-%d"),
        wake_up_hour=wake_up_hour
    )
    
    if daily_plan:
        # Store the plan in the agent's current state
        agent.current_daily_plan = daily_plan
        agent.current_daily_plan['date'] = current_date.isoformat()
    
    return daily_plan

def create_weekly_plan(agent,
                      current_week_start: datetime.date = None) -> Optional[Dict[str, Any]]:
    """
    Create a weekly plan for the agent.
    
    Args:
        agent: The agent to create a plan for
        current_week_start (datetime.date): Start date of the week
        
    Returns:
        Optional[Dict]: Weekly plan with daily themes and goals
    """
    if current_week_start is None:
        today = datetime.date.today()
        current_week_start = today - datetime.timedelta(days=today.weekday())
    
    week_end = current_week_start + datetime.timedelta(days=6)
    week_description = f"{current_week_start.strftime('%Y-%m-%d')} to {week_end.strftime('%Y-%m-%d')}"
    
    # Get recent daily reflections
    daily_reflections = []
    if hasattr(agent, 'reflection_memory'):
        recent_reflections = agent.reflection_memory.get_recent_reflections(days=7)
        daily_reflections = [r.reflection_text for r in recent_reflections 
                           if r.reflection_type == "daily_reflection"]
    
    # Get long-term goals
    long_term_goals = []
    if hasattr(agent, 'reflection_memory') and agent.reflection_memory.long_term_goals:
        long_term_goals = agent.reflection_memory.long_term_goals
    
    # Generate the weekly plan
    weekly_plan = run_gpt_prompt_weekly_planning(
        agent_name=agent.name,
        daily_reflections=daily_reflections,
        long_term_goals=long_term_goals,
        current_week=week_description
    )
    
    if weekly_plan:
        # Store the plan in the agent's current state
        agent.current_weekly_plan = weekly_plan
        agent.current_weekly_plan['week_start'] = current_week_start.isoformat()
    
    return weekly_plan

def plan_next_action(agent,
                    current_situation: str,
                    time_context: str = None) -> Optional[str]:
    """
    Plan the next action for the agent based on current situation.
    
    Args:
        agent: The agent planning the action
        current_situation (str): Current situation description
        time_context (str): Current time and context
        
    Returns:
        Optional[str]: Planned next action
    """
    if time_context is None:
        time_context = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # Get relevant memories for this situation
    relevant_memories = retrieve_memories_for_planning(
        memory_store=agent.memory_stream,
        planning_context=f"action planning for situation: {current_situation}",
        agent_goals=getattr(agent, 'current_goals', [])
    )
    
    memory_texts = [memory.text for memory in relevant_memories]
    
    # Get current goals
    current_goals = []
    if hasattr(agent, 'reflection_memory') and agent.reflection_memory.long_term_goals:
        current_goals = agent.reflection_memory.long_term_goals
    
    # Plan the action
    planned_action = run_gpt_prompt_action_planning(
        agent_name=agent.name,
        current_situation=current_situation,
        relevant_memories=memory_texts,
        current_goals=current_goals,
        time_context=time_context
    )
    
    if planned_action:
        # Store as current action
        agent.current_planned_action = planned_action
        agent.last_action_planning_time = datetime.datetime.now()
    
    return planned_action

def update_goals(agent,
               life_context: str = "") -> Optional[Dict[str, Any]]:
    """
    Update the agent's goals based on recent reflections and experiences.
    
    Args:
        agent: The agent whose goals to update
        life_context (str): Context about the agent's life situation
        
    Returns:
        Optional[Dict]: Updated goals and principles
    """
    # Get current goals
    current_goals = []
    if hasattr(agent, 'reflection_memory') and agent.reflection_memory.long_term_goals:
        current_goals = agent.reflection_memory.long_term_goals
    
    # Get recent reflections
    recent_reflections = []
    if hasattr(agent, 'reflection_memory'):
        recent_reflection_records = agent.reflection_memory.get_recent_reflections(days=30)
        recent_reflections = [r.reflection_text for r in recent_reflection_records]
    
    # Create life context from L2 data if available
    if not life_context and hasattr(agent, 'l2_object') and agent.l2_object:
        l2_data = agent.l2_object.all_data()
        context_parts = []
        
        # Add demographic information
        if 'GENDER' in l2_data:
            context_parts.append(f"Gender: {l2_data['GENDER']}")
        if 'AGE' in l2_data:
            context_parts.append(f"Age: {l2_data['AGE']}")
        if 'EDUCATION' in l2_data:
            context_parts.append(f"Education: {l2_data['EDUCATION']}")
        if 'INCOME' in l2_data:
            context_parts.append(f"Income level: {l2_data['INCOME']}")
        
        life_context = "; ".join(context_parts)
    
    # Update goals
    updated_goals = run_gpt_prompt_goal_setting(
        agent_name=agent.name,
        current_goals=current_goals,
        reflections=recent_reflections,
        life_context=life_context
    )
    
    if updated_goals and hasattr(agent, 'reflection_memory'):
        # Update the reflection memory with new goals and principles
        if 'long_term_goals' in updated_goals:
            agent.reflection_memory.update_long_term_goals(updated_goals['long_term_goals'])
        
        if 'core_principles' in updated_goals:
            agent.reflection_memory.update_core_principles(updated_goals['core_principles'])
    
    return updated_goals

def get_current_priority(agent) -> str:
    """
    Get the current priority based on daily plan and time.
    
    Args:
        agent: The agent to get priority for
        
    Returns:
        str: Current priority or activity
    """
    current_time = datetime.datetime.now()
    current_hour = current_time.hour
    
    # Check if we have a daily plan
    if hasattr(agent, 'current_daily_plan') and agent.current_daily_plan:
        schedule = agent.current_daily_plan.get('schedule', [])
        
        # Find the current activity based on time
        for activity_slot in schedule:
            if activity_slot.get('hour') == current_hour:
                return activity_slot.get('activity', 'No specific activity planned')
        
        # If no specific activity, return a main goal for the day
        main_goals = agent.current_daily_plan.get('main_goals_today', [])
        if main_goals:
            return f"Focus on: {main_goals[0]}"
    
    # Fallback to long-term goals
    if hasattr(agent, 'reflection_memory') and agent.reflection_memory.long_term_goals:
        return f"Working towards: {agent.reflection_memory.long_term_goals[0]}"
    
    return "No specific priority set"

def plan_hourly_schedule(base_schedule: List[Dict], 
                        priorities: List[str],
                        constraints: Dict[str, Any] = None) -> List[Dict]:
    """
    Create a detailed hourly schedule based on priorities and constraints.
    
    Args:
        base_schedule (List[Dict]): Base schedule template
        priorities (List[str]): Priority activities to include
        constraints (Dict): Time and other constraints
        
    Returns:
        List[Dict]: Detailed hourly schedule
    """
    schedule = []
    constraints = constraints or {}
    
    # Default time blocks
    default_blocks = {
        'morning_routine': {'start': 7, 'duration': 1, 'priority': 8},
        'breakfast': {'start': 8, 'duration': 1, 'priority': 7},
        'work_focus': {'start': 9, 'duration': 4, 'priority': 9},
        'lunch': {'start': 13, 'duration': 1, 'priority': 6},
        'afternoon_work': {'start': 14, 'duration': 3, 'priority': 8},
        'personal_time': {'start': 17, 'duration': 2, 'priority': 7},
        'dinner': {'start': 19, 'duration': 1, 'priority': 6},
        'evening_activities': {'start': 20, 'duration': 2, 'priority': 5},
        'wind_down': {'start': 22, 'duration': 1, 'priority': 7},
    }
    
    # Override with custom schedule if provided
    if base_schedule:
        for item in base_schedule:
            schedule.append({
                'hour': item.get('hour'),
                'activity': item.get('activity'),
                'priority': item.get('priority', 5)
            })
    else:
        # Use default blocks and incorporate priorities
        for block_name, block_info in default_blocks.items():
            activity = block_name.replace('_', ' ').title()
            
            # Customize activity based on priorities
            if 'work' in block_name and priorities:
                work_priorities = [p for p in priorities if 'work' in p.lower()]
                if work_priorities:
                    activity = work_priorities[0]
            
            schedule.append({
                'hour': block_info['start'],
                'activity': activity,
                'priority': block_info['priority']
            })
    
    return sorted(schedule, key=lambda x: x['hour'])

def adjust_plan_based_on_feedback(agent, 
                                feedback: str,
                                plan_type: str = "daily") -> bool:
    """
    Adjust existing plans based on feedback or changed circumstances.
    
    Args:
        agent: The agent whose plan to adjust
        feedback (str): Feedback about the current plan
        plan_type (str): Type of plan to adjust ("daily" or "weekly")
        
    Returns:
        bool: True if plan was successfully adjusted
    """
    if plan_type == "daily" and hasattr(agent, 'current_daily_plan'):
        # Simple adjustment - could be enhanced with LLM-based replanning
        current_plan = agent.current_daily_plan
        
        # Add feedback as a note
        if 'feedback' not in current_plan:
            current_plan['feedback'] = []
        current_plan['feedback'].append({
            'timestamp': datetime.datetime.now().isoformat(),
            'feedback': feedback
        })
        
        return True
    
    elif plan_type == "weekly" and hasattr(agent, 'current_weekly_plan'):
        current_plan = agent.current_weekly_plan
        
        # Add feedback
        if 'feedback' not in current_plan:
            current_plan['feedback'] = []
        current_plan['feedback'].append({
            'timestamp': datetime.datetime.now().isoformat(),
            'feedback': feedback
        })
        
        return True
    
    return False 