import datetime
from typing import List, Dict, Any, Optional
from ..memory_structures import MemoryRecord
from ..prompt_template import run_gpt_prompt_importance_scoring
from .embedding_utils import get_text_embedding

def perceive_environment(agent, 
                        environment_state: Dict[str, Any],
                        social_context: Dict[str, Any] = None) -> List[str]:
    """
    Perceive the current environment and generate observations.
    
    Args:
        agent: The agent doing the perceiving
        environment_state (Dict): Current state of the environment
        social_context (Dict): Information about other agents and social interactions
        
    Returns:
        List[str]: List of observation strings
    """
    observations = []
    
    # Environmental observations
    if environment_state:
        location = environment_state.get('location', 'unknown location')
        time_of_day = environment_state.get('time', 'unknown time')
        weather = environment_state.get('weather', 'clear')
        
        observations.append(f"I am currently at {location} at {time_of_day}")
        if weather != 'clear':
            observations.append(f"The weather is {weather}")
        
        # Objects or features in the environment
        if 'objects' in environment_state:
            for obj in environment_state['objects']:
                observations.append(f"I notice {obj} nearby")
        
        # Events happening in the environment
        if 'events' in environment_state:
            for event in environment_state['events']:
                observations.append(f"I observe that {event}")
    
    # Social observations
    if social_context:
        # Other agents present
        if 'other_agents' in social_context:
            for other_agent in social_context['other_agents']:
                observations.append(f"I see {other_agent['name']} {other_agent.get('activity', 'here')}")
        
        # Conversations or interactions
        if 'interactions' in social_context:
            for interaction in social_context['interactions']:
                observations.append(f"I had an interaction: {interaction}")
        
        # Social events
        if 'social_events' in social_context:
            for event in social_context['social_events']:
                observations.append(f"I noticed a social event: {event}")
    
    # Internal state observations
    if hasattr(agent, 'current_goal'):
        observations.append(f"I am currently focused on: {agent.current_goal}")
    
    if hasattr(agent, 'mood') and agent.mood:
        observations.append(f"I am feeling {agent.mood}")
    
    # Remove empty observations
    observations = [obs for obs in observations if obs.strip()]
    
    return observations

def create_memory_from_observation(agent,
                                 observation: str,
                                 context: str = "",
                                 source: str = "observation",
                                 manual_importance: Optional[float] = None) -> MemoryRecord:
    """
    Create a memory record from an observation.
    
    Args:
        agent: The agent creating the memory
        observation (str): The observation text
        context (str): Additional context about the observation
        source (str): Source type of the memory
        manual_importance (Optional[float]): Manual importance score, if provided
        
    Returns:
        MemoryRecord: Created memory record
    """
    # Score importance if not provided manually
    if manual_importance is None:
        agent_context = f"Agent: {agent.name}"
        if hasattr(agent, 'core_principles') and agent.core_principles:
            agent_context += f", Core principles: {', '.join(agent.core_principles[:3])}"
        if hasattr(agent, 'long_term_goals') and agent.long_term_goals:
            agent_context += f", Goals: {', '.join(agent.long_term_goals[:3])}"
        
        importance = run_gpt_prompt_importance_scoring(observation, agent_context)
    else:
        importance = manual_importance
    
    # Generate embedding for the observation
    embedding = get_text_embedding(observation)
    
    # Extract keywords (simple approach)
    keywords = extract_keywords_from_text(observation)
    
    # Create the memory record
    memory = MemoryRecord(
        text=observation,
        timestamp=datetime.datetime.now(),
        importance=importance,
        source=source,
        embedding=embedding,
        associated_event=context if context else None,
        keywords=keywords
    )
    
    return memory

def extract_keywords_from_text(text: str) -> List[str]:
    """
    Extract keywords from text using simple heuristics.
    
    Args:
        text (str): Text to extract keywords from
        
    Returns:
        List[str]: List of keywords
    """
    import re
    
    # Simple keyword extraction
    # Remove common stop words and punctuation
    stop_words = {
        'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', 'your', 'yours',
        'yourself', 'yourselves', 'he', 'him', 'his', 'himself', 'she', 'her', 'hers',
        'herself', 'it', 'its', 'itself', 'they', 'them', 'their', 'theirs', 'themselves',
        'what', 'which', 'who', 'whom', 'this', 'that', 'these', 'those', 'am', 'is', 'are',
        'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'having', 'do', 'does',
        'did', 'doing', 'a', 'an', 'the', 'and', 'but', 'if', 'or', 'because', 'as', 'until',
        'while', 'of', 'at', 'by', 'for', 'with', 'through', 'during', 'before', 'after',
        'above', 'below', 'up', 'down', 'in', 'out', 'on', 'off', 'over', 'under', 'again',
        'further', 'then', 'once', 'here', 'there', 'when', 'where', 'why', 'how', 'all',
        'any', 'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor',
        'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 'can', 'will', 'just',
        'should', 'now', 'currently', 'notice', 'see', 'observe'
    }
    
    # Extract words
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    
    # Filter out stop words and get unique keywords
    keywords = list(set([word for word in words if word not in stop_words]))
    
    # Limit to most relevant keywords (could be improved with TF-IDF or other methods)
    return keywords[:10]

def create_social_memory(agent,
                        other_agent_name: str,
                        interaction_type: str,
                        interaction_content: str,
                        importance: float = 6.0) -> MemoryRecord:
    """
    Create a memory record for social interactions.
    
    Args:
        agent: The agent creating the memory
        other_agent_name (str): Name of the other agent
        interaction_type (str): Type of interaction (conversation, meeting, etc.)
        interaction_content (str): Content of the interaction
        importance (float): Importance score for this interaction
        
    Returns:
        MemoryRecord: Created memory record
    """
    memory_text = f"I had a {interaction_type} with {other_agent_name}: {interaction_content}"
    
    # Generate embedding
    embedding = get_text_embedding(memory_text)
    
    # Extract keywords
    keywords = extract_keywords_from_text(memory_text)
    keywords.append(other_agent_name.lower())
    keywords.append(interaction_type.lower())
    
    memory = MemoryRecord(
        text=memory_text,
        timestamp=datetime.datetime.now(),
        importance=importance,
        source="social_interaction",
        embedding=embedding,
        associated_event=f"{interaction_type}_with_{other_agent_name}",
        keywords=keywords
    )
    
    return memory

def create_goal_memory(agent,
                      goal_text: str,
                      goal_type: str = "goal_setting",
                      importance: float = 8.0) -> MemoryRecord:
    """
    Create a memory record for goal-related activities.
    
    Args:
        agent: The agent creating the memory
        goal_text (str): Description of the goal or goal-related activity
        goal_type (str): Type of goal activity
        importance (float): Importance score
        
    Returns:
        MemoryRecord: Created memory record
    """
    memory_text = f"Goal activity: {goal_text}"
    
    # Generate embedding
    embedding = get_text_embedding(memory_text)
    
    # Extract keywords
    keywords = extract_keywords_from_text(memory_text)
    keywords.extend(['goal', goal_type.lower()])
    
    memory = MemoryRecord(
        text=memory_text,
        timestamp=datetime.datetime.now(),
        importance=importance,
        source="goal_activity",
        embedding=embedding,
        associated_event=goal_type,
        keywords=keywords
    )
    
    return memory 