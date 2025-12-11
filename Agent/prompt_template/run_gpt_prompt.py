from typing import List, Dict, Optional, Any
import datetime
from .gpt_structure import generate_with_system_prompt, parse_json_response, parse_list_response, extract_importance_score

def run_gpt_prompt_reflection(agent_name: str, 
                            recent_memories: List[str],
                            current_date: str) -> Optional[str]:
    """
    Generate a daily reflection based on recent memories.
    
    Args:
        agent_name (str): Name of the agent
        recent_memories (List[str]): List of recent memory texts
        current_date (str): Current date string
        
    Returns:
        Optional[str]: Generated reflection
    """
    system_prompt = f"""You are {agent_name}, a thoughtful person reflecting on your recent experiences. 
Your task is to create a meaningful reflection that captures the key themes, lessons, and insights from your recent memories.

Focus on:
- Important patterns in your behavior and experiences
- Lessons learned or insights gained
- How your experiences relate to your goals and values
- Areas for improvement or growth
- Meaningful connections or relationships

Keep your reflection personal, authentic, and insightful. Write in first person as {agent_name}."""

    memories_text = "\n".join([f"- {memory}" for memory in recent_memories])
    
    user_prompt = f"""Based on these recent experiences from {current_date}, please write a thoughtful reflection:

Recent Memories:
{memories_text}

Write a reflection that synthesizes these experiences into meaningful insights. What did you learn? What patterns do you notice? How do these experiences shape your understanding of yourself and your goals?"""

    return generate_with_system_prompt(system_prompt, user_prompt, max_tokens=500, temperature=0.7)

def run_gpt_prompt_daily_planning(agent_name: str,
                                reflection: str,
                                goals: List[str],
                                current_date: str,
                                wake_up_hour: int = 7) -> Optional[Dict[str, Any]]:
    """
    Generate a daily plan with hourly schedule.
    
    Args:
        agent_name (str): Name of the agent
        reflection (str): Recent reflection
        goals (List[str]): Current goals
        current_date (str): Current date
        wake_up_hour (int): Hour to wake up
        
    Returns:
        Optional[Dict]: Daily plan with schedule
    """
    system_prompt = f"""You are {agent_name}, planning your day thoughtfully. 
Create a realistic daily schedule that balances your goals, responsibilities, and personal needs.

Your response should be a JSON object with:
- "wake_up_hour": integer (hour to wake up)
- "sleep_hour": integer (hour to go to sleep)
- "schedule": array of objects with "hour", "activity", and "priority" (1-10)
- "main_goals_today": array of strings (3-5 main goals for the day)
- "reflection_notes": string (how today's plan relates to your reflection)

Make the schedule realistic and balanced."""

    goals_text = "\n".join([f"- {goal}" for goal in goals])
    
    user_prompt = f"""Plan your day for {current_date}.

Your recent reflection:
{reflection}

Your current goals:
{goals_text}

Create a detailed hourly schedule from wake up to sleep. Include work, personal time, meals, exercise, social activities, and goal-related tasks. Be specific about activities and assign priority levels."""

    response = generate_with_system_prompt(system_prompt, user_prompt, max_tokens=800, temperature=0.6)
    return parse_json_response(response) if response else None

def run_gpt_prompt_weekly_planning(agent_name: str,
                                 daily_reflections: List[str],
                                 long_term_goals: List[str],
                                 current_week: str) -> Optional[Dict[str, Any]]:
    """
    Generate a weekly plan with daily themes and goals.
    
    Args:
        agent_name (str): Name of the agent
        daily_reflections (List[str]): Recent daily reflections
        long_term_goals (List[str]): Long-term goals
        current_week (str): Current week description
        
    Returns:
        Optional[Dict]: Weekly plan
    """
    system_prompt = f"""You are {agent_name}, planning your week strategically.
Create a weekly plan that moves you toward your long-term goals while maintaining balance.

Your response should be a JSON object with:
- "weekly_theme": string (main focus for the week)
- "daily_plans": object with keys "monday" through "sunday", each containing:
  - "theme": string (daily theme)
  - "main_goals": array of strings (2-3 goals)
  - "focus_areas": array of strings (key areas to focus on)
- "weekly_goals": array of strings (3-5 major goals for the week)
- "challenges_to_address": array of strings (potential challenges and how to handle them)"""

    reflections_text = "\n".join([f"- {reflection}" for reflection in daily_reflections])
    goals_text = "\n".join([f"- {goal}" for goal in long_term_goals])
    
    user_prompt = f"""Plan your week for {current_week}.

Recent daily reflections:
{reflections_text}

Your long-term goals:
{goals_text}

Create a strategic weekly plan that builds on your recent insights and moves you toward your long-term objectives. Consider what you've learned from your daily reflections."""

    response = generate_with_system_prompt(system_prompt, user_prompt, max_tokens=1000, temperature=0.6)
    return parse_json_response(response) if response else None

def run_gpt_prompt_importance_scoring(memory_text: str, 
                                    agent_context: str) -> float:
    """
    Score the importance of a memory for the agent.
    
    Args:
        memory_text (str): The memory to score
        agent_context (str): Context about the agent
        
    Returns:
        float: Importance score from 1-10
    """
    system_prompt = f"""You are evaluating the importance of a memory for someone. 
Rate the importance on a scale of 1-10 where:

1-3: Routine, everyday activities with little significance
4-6: Moderately important events, decent social interactions, some learning
7-8: Important conversations, meaningful achievements, significant learning
9-10: Life-changing events, major insights, profound emotional experiences

Consider:
- Emotional impact
- Relevance to goals and values
- Uniqueness or novelty
- Potential for future reference
- Social or relationship significance

Respond with just the number (1-10) and a brief explanation."""

    user_prompt = f"""Agent context: {agent_context}

Memory to evaluate: {memory_text}

Rate the importance of this memory (1-10):"""

    response = generate_with_system_prompt(system_prompt, user_prompt, max_tokens=100, temperature=0.3)
    return extract_importance_score(response) if response else 5.0

def run_gpt_prompt_goal_setting(agent_name: str,
                              current_goals: List[str],
                              reflections: List[str],
                              life_context: str) -> Optional[Dict[str, Any]]:
    """
    Generate or update long-term goals based on reflections.
    
    Args:
        agent_name (str): Name of the agent
        current_goals (List[str]): Current goals
        reflections (List[str]): Recent reflections
        life_context (str): Context about the agent's life
        
    Returns:
        Optional[Dict]: Updated goals and principles
    """
    system_prompt = f"""You are {agent_name}, thoughtfully setting and updating your life goals.
Based on your recent reflections and current situation, refine your goals and principles.

Your response should be a JSON object with:
- "long_term_goals": array of strings (5-7 major life goals)
- "core_principles": array of strings (3-5 fundamental values/principles)
- "short_term_objectives": array of strings (3-5 goals for next few months)
- "areas_for_growth": array of strings (areas you want to develop)
- "goal_changes": string (explanation of what changed and why)

Make goals specific, meaningful, and achievable."""

    current_goals_text = "\n".join([f"- {goal}" for goal in current_goals])
    reflections_text = "\n".join([f"- {reflection}" for reflection in reflections])
    
    user_prompt = f"""Your life context: {life_context}

Your current goals:
{current_goals_text}

Your recent reflections:
{reflections_text}

Based on your reflections and growth, update your goals and principles. What have you learned about what matters most to you? What goals need to be added, modified, or removed?"""

    response = generate_with_system_prompt(system_prompt, user_prompt, max_tokens=800, temperature=0.6)
    return parse_json_response(response) if response else None

def run_gpt_prompt_action_planning(agent_name: str,
                                 current_situation: str,
                                 relevant_memories: List[str],
                                 current_goals: List[str],
                                 time_context: str) -> Optional[str]:
    """
    Plan the next action based on current situation and memories.
    
    Args:
        agent_name (str): Name of the agent
        current_situation (str): Current situation description
        relevant_memories (List[str]): Relevant memories for context
        current_goals (List[str]): Current goals
        time_context (str): Time and context information
        
    Returns:
        Optional[str]: Planned action
    """
    system_prompt = f"""You are {agent_name}, deciding what to do next.
Based on your current situation, relevant memories, and goals, choose your next action.

Consider:
- Your immediate priorities
- Your long-term goals
- What you've learned from past experiences
- The current time and context
- Social obligations and opportunities

Respond with a specific, actionable plan for what you should do next. Be concrete and realistic."""

    memories_text = "\n".join([f"- {memory}" for memory in relevant_memories])
    goals_text = "\n".join([f"- {goal}" for goal in current_goals])
    
    user_prompt = f"""Current situation: {current_situation}
Time context: {time_context}

Relevant memories:
{memories_text}

Your current goals:
{goals_text}

What should you do next? Provide a specific action plan considering your situation, memories, and goals."""

    return generate_with_system_prompt(system_prompt, user_prompt, max_tokens=300, temperature=0.7)

def run_gpt_prompt_memory_synthesis(agent_name: str,
                                  memories_to_synthesize: List[str],
                                  context: str) -> Optional[str]:
    """
    Synthesize multiple memories into a higher-level insight.
    
    Args:
        agent_name (str): Name of the agent
        memories_to_synthesize (List[str]): Memories to combine
        context (str): Context for the synthesis
        
    Returns:
        Optional[str]: Synthesized insight
    """
    system_prompt = f"""You are {agent_name}, looking for patterns and insights across multiple experiences.
Synthesize these related memories into a higher-level understanding or insight.

Focus on:
- Common themes or patterns
- Lessons that emerge when considering them together
- How they relate to each other
- What they reveal about yourself or your situation
- Insights that wouldn't be apparent from individual memories alone

Create a meaningful synthesis that captures the deeper understanding."""

    memories_text = "\n".join([f"- {memory}" for memory in memories_to_synthesize])
    
    user_prompt = f"""Context: {context}

Related memories to synthesize:
{memories_text}

What patterns, themes, or insights emerge when you consider these memories together? What do they collectively tell you that individual memories might not reveal?"""

    return generate_with_system_prompt(system_prompt, user_prompt, max_tokens=400, temperature=0.7) 