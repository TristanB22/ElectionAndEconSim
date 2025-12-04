import datetime
from typing import List, Dict, Any, Optional
from ..memory_structures import MemoryRecord, ReflectionRecord
from ..prompt_template import run_gpt_prompt_reflection, run_gpt_prompt_memory_synthesis
from .retrieve import retrieve_memories_for_reflection

def daily_reflection(agent,
                    reflection_date: datetime.date = None) -> Optional[ReflectionRecord]:
    """
    Create a daily reflection based on the day's experiences.
    
    Args:
        agent: The agent creating the reflection
        reflection_date (datetime.date): Date to reflect on (default: today)
        
    Returns:
        Optional[ReflectionRecord]: Generated reflection record
    """
    if reflection_date is None:
        reflection_date = datetime.date.today()
    
    # Get memories from the day
    day_memories = retrieve_memories_for_reflection(
        memory_store=agent.memory_stream,
        reflection_period_hours=24
    )
    
    if not day_memories:
        return None
    
    # Extract memory texts for the prompt
    memory_texts = [memory.text for memory in day_memories]
    
    # Generate the reflection
    reflection_text = run_gpt_prompt_reflection(
        agent_name=agent.name,
        recent_memories=memory_texts,
        current_date=reflection_date.strftime("%Y-%m-%d")
    )
    
    if reflection_text:
        # Create reflection record
        reflection_record = ReflectionRecord(
            reflection_text=reflection_text,
            source_memories=day_memories,
            timestamp=datetime.datetime.now(),
            importance=8.0,  # Daily reflections are important
            reflection_type="daily_reflection"
        )
        
        # Add to agent's reflection memory
        if hasattr(agent, 'reflection_memory'):
            agent.reflection_memory.add_reflection(reflection_record)
        
        # Also add as a memory to the memory stream
        reflection_memory = MemoryRecord(
            text=f"Daily reflection: {reflection_text}",
            timestamp=datetime.datetime.now(),
            importance=8.0,
            source="reflection",
            keywords=["reflection", "daily", "insights"]
        )
        agent.memory_stream.add_memory(reflection_memory)
        
        return reflection_record
    
    return None

def weekly_reflection(agent,
                     week_start_date: datetime.date = None) -> Optional[ReflectionRecord]:
    """
    Create a weekly reflection based on the week's experiences and daily reflections.
    
    Args:
        agent: The agent creating the reflection
        week_start_date (datetime.date): Start date of the week to reflect on
        
    Returns:
        Optional[ReflectionRecord]: Generated reflection record
    """
    if week_start_date is None:
        today = datetime.date.today()
        week_start_date = today - datetime.timedelta(days=today.weekday())
    
    # Get memories from the week
    week_memories = retrieve_memories_for_reflection(
        memory_store=agent.memory_stream,
        reflection_period_hours=168  # 7 days
    )
    
    # Get daily reflections from the week
    daily_reflections = []
    if hasattr(agent, 'reflection_memory'):
        recent_reflections = agent.reflection_memory.get_recent_reflections(days=7)
        daily_reflections = [r for r in recent_reflections 
                           if r.reflection_type == "daily_reflection"]
    
    if not week_memories and not daily_reflections:
        return None
    
    # Combine memory texts and daily reflection texts
    memory_texts = [memory.text for memory in week_memories]
    reflection_texts = [r.reflection_text for r in daily_reflections]
    
    all_texts = memory_texts + [f"Daily reflection: {text}" for text in reflection_texts]
    
    # Generate the weekly reflection
    reflection_text = run_gpt_prompt_reflection(
        agent_name=agent.name,
        recent_memories=all_texts,
        current_date=f"Week of {week_start_date.strftime('%Y-%m-%d')}"
    )
    
    if reflection_text:
        # Create reflection record
        reflection_record = ReflectionRecord(
            reflection_text=reflection_text,
            source_memories=week_memories,
            timestamp=datetime.datetime.now(),
            importance=9.0,  # Weekly reflections are very important
            reflection_type="weekly_reflection"
        )
        
        # Add to agent's reflection memory
        if hasattr(agent, 'reflection_memory'):
            agent.reflection_memory.add_reflection(reflection_record)
        
        # Also add as a memory to the memory stream
        reflection_memory = MemoryRecord(
            text=f"Weekly reflection: {reflection_text}",
            timestamp=datetime.datetime.now(),
            importance=9.0,
            source="reflection",
            keywords=["reflection", "weekly", "insights", "patterns"]
        )
        agent.memory_stream.add_memory(reflection_memory)
        
        return reflection_record
    
    return None

def create_insight(agent,
                  related_memories: List[MemoryRecord],
                  insight_context: str = "") -> Optional[ReflectionRecord]:
    """
    Create an insight by synthesizing related memories.
    
    Args:
        agent: The agent creating the insight
        related_memories (List[MemoryRecord]): Memories to synthesize
        insight_context (str): Context for the insight generation
        
    Returns:
        Optional[ReflectionRecord]: Generated insight record
    """
    if not related_memories:
        return None
    
    memory_texts = [memory.text for memory in related_memories]
    
    # Generate the insight
    insight_text = run_gpt_prompt_memory_synthesis(
        agent_name=agent.name,
        memories_to_synthesize=memory_texts,
        context=insight_context
    )
    
    if insight_text:
        # Create insight record
        insight_record = ReflectionRecord(
            reflection_text=insight_text,
            source_memories=related_memories,
            timestamp=datetime.datetime.now(),
            importance=7.5,  # Insights are quite important
            reflection_type="insight"
        )
        
        # Add to agent's reflection memory
        if hasattr(agent, 'reflection_memory'):
            agent.reflection_memory.add_reflection(insight_record)
        
        # Also add as a memory to the memory stream
        insight_memory = MemoryRecord(
            text=f"Insight: {insight_text}",
            timestamp=datetime.datetime.now(),
            importance=7.5,
            source="insight",
            keywords=["insight", "synthesis", "pattern", "understanding"]
        )
        agent.memory_stream.add_memory(insight_memory)
        
        return insight_record
    
    return None

def identify_patterns_and_create_insights(agent,
                                        pattern_search_days: int = 7) -> List[ReflectionRecord]:
    """
    Automatically identify patterns in recent memories and create insights.
    
    Args:
        agent: The agent to analyze
        pattern_search_days (int): Number of days to look back for patterns
        
    Returns:
        List[ReflectionRecord]: Generated insights
    """
    insights = []
    
    # Get recent memories
    recent_memories = agent.memory_stream.get_recent_memories(hours=pattern_search_days * 24)
    
    if len(recent_memories) < 3:
        return insights
    
    # Group memories by keywords to find patterns
    keyword_groups = {}
    for memory in recent_memories:
        for keyword in memory.keywords:
            if keyword not in keyword_groups:
                keyword_groups[keyword] = []
            keyword_groups[keyword].append(memory)
    
    # Look for keyword groups with multiple memories (patterns)
    for keyword, memories in keyword_groups.items():
        if len(memories) >= 3:  # At least 3 related memories
            insight = create_insight(
                agent=agent,
                related_memories=memories,
                insight_context=f"Pattern related to {keyword}"
            )
            if insight:
                insights.append(insight)
    
    # Look for temporal patterns (similar activities at similar times)
    time_groups = {}
    for memory in recent_memories:
        hour = memory.timestamp.hour
        time_period = get_time_period(hour)
        if time_period not in time_groups:
            time_groups[time_period] = []
        time_groups[time_period].append(memory)
    
    for time_period, memories in time_groups.items():
        if len(memories) >= 3:
            insight = create_insight(
                agent=agent,
                related_memories=memories,
                insight_context=f"Pattern in {time_period} activities"
            )
            if insight:
                insights.append(insight)
    
    return insights

def get_time_period(hour: int) -> str:
    """Get time period string from hour"""
    if 6 <= hour < 12:
        return "morning"
    elif 12 <= hour < 17:
        return "afternoon"
    elif 17 <= hour < 21:
        return "evening"
    else:
        return "night"

def reflect_on_goals_progress(agent) -> Optional[ReflectionRecord]:
    """
    Reflect on progress towards long-term goals.
    
    Args:
        agent: The agent to reflect on
        
    Returns:
        Optional[ReflectionRecord]: Reflection on goal progress
    """
    if not hasattr(agent, 'reflection_memory') or not agent.reflection_memory.long_term_goals:
        return None
    
    # Get goal-related memories
    goal_memories = agent.memory_stream.get_memories_by_source("goal_activity")
    recent_goal_memories = [m for m in goal_memories 
                          if (datetime.datetime.now() - m.timestamp).days <= 14]
    
    if not recent_goal_memories:
        return None
    
    # Get current goals
    current_goals = agent.reflection_memory.long_term_goals
    
    # Create context for reflection
    goals_text = "; ".join(current_goals)
    context = f"Progress towards goals: {goals_text}"
    
    # Create insight about goal progress
    goal_reflection = create_insight(
        agent=agent,
        related_memories=recent_goal_memories,
        insight_context=context
    )
    
    if goal_reflection:
        goal_reflection.reflection_type = "goal_reflection"
    
    return goal_reflection

def monthly_deep_reflection(agent,
                          month_year: str = None) -> Optional[ReflectionRecord]:
    """
    Create a deep monthly reflection synthesizing all experiences.
    
    Args:
        agent: The agent creating the reflection
        month_year (str): Month and year to reflect on (e.g., "2023-12")
        
    Returns:
        Optional[ReflectionRecord]: Deep monthly reflection
    """
    if month_year is None:
        current_date = datetime.date.today()
        month_year = current_date.strftime("%Y-%m")
    
    # Get all memories from the month
    month_memories = retrieve_memories_for_reflection(
        memory_store=agent.memory_stream,
        reflection_period_hours=30 * 24  # ~30 days
    )
    
    # Get all reflections from the month
    monthly_reflections = []
    if hasattr(agent, 'reflection_memory'):
        recent_reflections = agent.reflection_memory.get_recent_reflections(days=30)
        monthly_reflections = [r.reflection_text for r in recent_reflections]
    
    if not month_memories and not monthly_reflections:
        return None
    
    # Combine high-level memories and all reflections
    important_memories = [m for m in month_memories if m.importance >= 6.0]
    memory_texts = [memory.text for memory in important_memories]
    
    all_texts = memory_texts + [f"Previous reflection: {text}" for text in monthly_reflections]
    
    # Generate deep reflection
    reflection_text = run_gpt_prompt_reflection(
        agent_name=agent.name,
        recent_memories=all_texts[:20],  # Limit to avoid overwhelming the prompt
        current_date=f"Month of {month_year}"
    )
    
    if reflection_text:
        # Create deep reflection record
        reflection_record = ReflectionRecord(
            reflection_text=reflection_text,
            source_memories=important_memories,
            timestamp=datetime.datetime.now(),
            importance=10.0,  # Monthly deep reflections are the most important
            reflection_type="monthly_reflection"
        )
        
        # Add to agent's reflection memory
        if hasattr(agent, 'reflection_memory'):
            agent.reflection_memory.add_reflection(reflection_record)
        
        return reflection_record
    
    return None 