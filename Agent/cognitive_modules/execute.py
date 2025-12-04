import datetime
from typing import List, Dict, Any, Optional, Tuple
from ..memory_structures import MemoryRecord
from .perceive import create_memory_from_observation, create_goal_memory

def execute_action(agent,
                  planned_action: str,
                  environment_state: Dict[str, Any] = None,
                  social_context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Execute a planned action and update agent state.
    
    Args:
        agent: The agent executing the action
        planned_action (str): The action to execute
        environment_state (Dict): Current environment state
        social_context (Dict): Social context for the action
        
    Returns:
        Dict[str, Any]: Result of the action execution
    """
    execution_result = {
        'action': planned_action,
        'timestamp': datetime.datetime.now(),
        'success': True,
        'outcome': '',
        'state_changes': {},
        'memories_created': []
    }
    
    try:
        # Parse and execute the action
        action_type, action_details = parse_action(planned_action)
        
        if action_type == 'move':
            result = execute_movement_action(agent, action_details, environment_state)
        elif action_type == 'social':
            result = execute_social_action(agent, action_details, social_context)
        elif action_type == 'work':
            result = execute_work_action(agent, action_details)
        elif action_type == 'personal':
            result = execute_personal_action(agent, action_details)
        elif action_type == 'goal':
            result = execute_goal_action(agent, action_details)
        else:
            result = execute_general_action(agent, planned_action)
        
        # Update execution result
        execution_result.update(result)
        
        # Create memory of the action
        action_memory = create_memory_from_observation(
            agent=agent,
            observation=f"I executed action: {planned_action}. Outcome: {result.get('outcome', 'completed successfully')}",
            context=f"action_execution_{action_type}",
            source="action_execution",
            manual_importance=result.get('importance', 5.0)
        )
        
        agent.memory_stream.add_memory(action_memory)
        execution_result['memories_created'].append(action_memory)
        
        # Update agent's current state
        update_agent_state(agent, execution_result)
        
    except Exception as e:
        execution_result['success'] = False
        execution_result['outcome'] = f"Failed to execute action: {str(e)}"
        execution_result['error'] = str(e)
    
    return execution_result

def parse_action(action_text: str) -> Tuple[str, Dict[str, Any]]:
    """
    Parse action text to determine action type and details.
    
    Args:
        action_text (str): The action text to parse
        
    Returns:
        Tuple[str, Dict]: Action type and details
    """
    action_lower = action_text.lower()
    
    # Movement actions
    if any(word in action_lower for word in ['go to', 'move to', 'travel to', 'walk to', 'head to']):
        return 'move', {'description': action_text, 'type': 'movement'}
    
    # Social actions
    elif any(word in action_lower for word in ['talk to', 'meet with', 'call', 'text', 'contact', 'visit']):
        return 'social', {'description': action_text, 'type': 'social_interaction'}
    
    # Work actions
    elif any(word in action_lower for word in ['work on', 'complete', 'finish', 'research', 'analyze', 'write']):
        return 'work', {'description': action_text, 'type': 'work_activity'}
    
    # Personal actions
    elif any(word in action_lower for word in ['eat', 'sleep', 'exercise', 'relax', 'read', 'rest']):
        return 'personal', {'description': action_text, 'type': 'personal_care'}
    
    # Goal actions
    elif any(word in action_lower for word in ['achieve', 'pursue', 'focus on goal', 'work towards']):
        return 'goal', {'description': action_text, 'type': 'goal_pursuit'}
    
    # General action
    else:
        return 'general', {'description': action_text, 'type': 'general_activity'}

def execute_movement_action(agent, action_details: Dict[str, Any], environment_state: Dict[str, Any] = None) -> Dict[str, Any]:
    """Execute a movement action."""
    result = {
        'outcome': f"Successfully moved as planned: {action_details['description']}",
        'importance': 4.0,
        'state_changes': {
            'location_changed': True,
            'last_movement': datetime.datetime.now()
        }
    }
    
    # Update agent location if environment state provides it
    if environment_state and 'new_location' in environment_state:
        agent.current_location = environment_state['new_location']
        result['state_changes']['new_location'] = environment_state['new_location']
    
    return result

def execute_social_action(agent, action_details: Dict[str, Any], social_context: Dict[str, Any] = None) -> Dict[str, Any]:
    """Execute a social interaction action."""
    result = {
        'outcome': f"Successfully completed social action: {action_details['description']}",
        'importance': 6.0,
        'state_changes': {
            'social_interaction_occurred': True,
            'last_social_interaction': datetime.datetime.now()
        }
    }
    
    # If social context provides interaction details, enhance the result
    if social_context:
        if 'other_agents' in social_context:
            result['state_changes']['interacted_with'] = social_context['other_agents']
        
        if 'interaction_outcome' in social_context:
            result['outcome'] += f" Result: {social_context['interaction_outcome']}"
            # Social interactions can be more important if they have significant outcomes
            result['importance'] = 7.0
    
    return result

def execute_work_action(agent, action_details: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a work-related action."""
    result = {
        'outcome': f"Completed work activity: {action_details['description']}",
        'importance': 7.0,
        'state_changes': {
            'work_progress_made': True,
            'last_work_activity': datetime.datetime.now()
        }
    }
    
    # Work actions often relate to goals
    if hasattr(agent, 'reflection_memory') and agent.reflection_memory.long_term_goals:
        work_related_goals = [goal for goal in agent.reflection_memory.long_term_goals 
                            if any(word in goal.lower() for word in ['work', 'career', 'job', 'professional'])]
        if work_related_goals:
            result['importance'] = 8.0
            result['outcome'] += f" (Related to goals: {', '.join(work_related_goals[:2])})"
    
    return result

def execute_personal_action(agent, action_details: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a personal care or self-improvement action."""
    result = {
        'outcome': f"Completed personal activity: {action_details['description']}",
        'importance': 5.0,
        'state_changes': {
            'personal_care_completed': True,
            'last_personal_activity': datetime.datetime.now()
        }
    }
    
    # Some personal actions might be more important (health, learning, etc.)
    description_lower = action_details['description'].lower()
    if any(word in description_lower for word in ['exercise', 'meditation', 'learning', 'study', 'health']):
        result['importance'] = 6.5
    
    return result

def execute_goal_action(agent, action_details: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a goal-related action."""
    result = {
        'outcome': f"Made progress on goals: {action_details['description']}",
        'importance': 8.5,
        'state_changes': {
            'goal_progress_made': True,
            'last_goal_activity': datetime.datetime.now()
        }
    }
    
    # Create a goal memory for this action
    goal_memory = create_goal_memory(
        agent=agent,
        goal_text=action_details['description'],
        goal_type="goal_progress",
        importance=8.5
    )
    
    agent.memory_stream.add_memory(goal_memory)
    
    return result

def execute_general_action(agent, action_description: str) -> Dict[str, Any]:
    """Execute a general action that doesn't fit other categories."""
    result = {
        'outcome': f"Completed activity: {action_description}",
        'importance': 5.0,
        'state_changes': {
            'general_activity_completed': True,
            'last_activity': datetime.datetime.now()
        }
    }
    
    return result

def update_agent_state(agent, execution_result: Dict[str, Any]) -> None:
    """
    Update agent's internal state based on action execution.
    
    Args:
        agent: The agent to update
        execution_result (Dict): Result of the action execution
    """
    # Update last action
    agent.last_action = execution_result['action']
    agent.last_action_time = execution_result['timestamp']
    agent.last_action_success = execution_result['success']
    
    # Update mood based on action success
    if execution_result['success']:
        if hasattr(agent, 'mood'):
            # Simple mood improvement for successful actions
            if agent.mood in ['sad', 'frustrated']:
                agent.mood = 'neutral'
            elif agent.mood == 'neutral':
                agent.mood = 'content'
            elif agent.mood == 'content':
                agent.mood = 'happy'
    else:
        if hasattr(agent, 'mood'):
            # Simple mood degradation for failed actions
            if agent.mood in ['happy', 'content']:
                agent.mood = 'neutral'
            elif agent.mood == 'neutral':
                agent.mood = 'frustrated'
    
    # Apply state changes from the execution result
    state_changes = execution_result.get('state_changes', {})
    for key, value in state_changes.items():
        setattr(agent, key, value)

def simulate_action_consequences(agent,
                               action: str,
                               environment_state: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Simulate the consequences of an action without actually executing it.
    
    Args:
        agent: The agent considering the action
        action (str): The action to simulate
        environment_state (Dict): Current environment state
        
    Returns:
        Dict[str, Any]: Simulated consequences
    """
    consequences = {
        'estimated_duration': 60,  # minutes
        'estimated_importance': 5.0,
        'potential_outcomes': [],
        'risks': [],
        'benefits': []
    }
    
    action_type, action_details = parse_action(action)
    
    # Estimate consequences based on action type
    if action_type == 'social':
        consequences['estimated_importance'] = 6.5
        consequences['potential_outcomes'] = ['strengthened relationship', 'gained information', 'social satisfaction']
        consequences['risks'] = ['social awkwardness', 'time consumption']
        consequences['benefits'] = ['relationship building', 'information exchange']
    
    elif action_type == 'work':
        consequences['estimated_importance'] = 7.5
        consequences['potential_outcomes'] = ['task completion', 'skill development', 'career progress']
        consequences['risks'] = ['stress', 'time pressure']
        consequences['benefits'] = ['goal advancement', 'productivity']
    
    elif action_type == 'goal':
        consequences['estimated_importance'] = 8.0
        consequences['potential_outcomes'] = ['goal progress', 'personal satisfaction', 'skill development']
        consequences['benefits'] = ['long-term benefit', 'personal growth']
    
    elif action_type == 'personal':
        consequences['estimated_importance'] = 5.5
        consequences['potential_outcomes'] = ['improved wellbeing', 'energy restoration', 'self-care']
        consequences['benefits'] = ['health improvement', 'stress reduction']
    
    return consequences

def plan_action_sequence(agent, 
                        goal: str,
                        available_actions: List[str],
                        time_constraint: int = None) -> List[str]:
    """
    Plan a sequence of actions to achieve a goal.
    
    Args:
        agent: The agent planning the sequence
        goal (str): The goal to achieve
        available_actions (List[str]): Available actions to choose from
        time_constraint (int): Time constraint in minutes
        
    Returns:
        List[str]: Ordered sequence of actions
    """
    if not available_actions:
        return []
    
    # Simple prioritization based on relevance to goal
    scored_actions = []
    goal_words = set(goal.lower().split())
    
    for action in available_actions:
        action_words = set(action.lower().split())
        # Calculate overlap with goal
        overlap = len(goal_words.intersection(action_words))
        
        # Simulate consequences to get importance
        consequences = simulate_action_consequences(agent, action)
        importance = consequences['estimated_importance']
        
        # Combined score
        score = overlap * 2 + importance
        scored_actions.append((score, action))
    
    # Sort by score and return top actions
    scored_actions.sort(key=lambda x: x[0], reverse=True)
    
    # If time constraint, consider action durations
    if time_constraint:
        selected_actions = []
        total_time = 0
        
        for score, action in scored_actions:
            consequences = simulate_action_consequences(agent, action)
            duration = consequences['estimated_duration']
            
            if total_time + duration <= time_constraint:
                selected_actions.append(action)
                total_time += duration
            
            if len(selected_actions) >= 5:  # Limit to 5 actions
                break
        
        return selected_actions
    
    return [action for score, action in scored_actions[:5]] 