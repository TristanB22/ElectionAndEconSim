import datetime
from typing import List, Dict, Any, Optional
from ..memory_structures import MemoryRecord, MemoryStore
from .embedding_utils import get_text_embedding

def retrieve_relevant_memories(memory_store: MemoryStore,
                             query_context: str,
                             k: int = 10,
                             importance_threshold: float = 0.0,
                             time_window_hours: Optional[int] = None,
                             source_filter: Optional[List[str]] = None) -> List[MemoryRecord]:
    """
    Retrieve the most relevant memories based on the current context.
    
    Args:
        memory_store (MemoryStore): The agent's memory store
        query_context (str): Context to search for relevant memories
        k (int): Number of memories to retrieve
        importance_threshold (float): Minimum importance score
        time_window_hours (Optional[int]): Only consider memories from last N hours
        source_filter (Optional[List[str]]): Only consider memories from these sources
        
    Returns:
        List[MemoryRecord]: Most relevant memories
    """
    # Generate embedding for the query context
    query_embedding = get_text_embedding(query_context, update_corpus=False)
    
    # Set time range if specified
    time_range = None
    if time_window_hours:
        end_time = datetime.datetime.now()
        start_time = end_time - datetime.timedelta(hours=time_window_hours)
        time_range = (start_time, end_time)
    
    # Retrieve memories using the memory store's built-in retrieval
    relevant_memories = memory_store.retrieve_memories(
        query_embedding=query_embedding,
        k=k,
        importance_threshold=importance_threshold,
        source_filter=source_filter,
        time_range=time_range
    )
    
    return relevant_memories

def retrieve_memories_for_planning(memory_store: MemoryStore,
                                 planning_context: str,
                                 agent_goals: List[str] = None) -> List[MemoryRecord]:
    """
    Retrieve memories specifically relevant for planning activities.
    
    Args:
        memory_store (MemoryStore): The agent's memory store
        planning_context (str): Context for planning (e.g., "daily planning", "goal setting")
        agent_goals (List[str]): Current agent goals for additional context
        
    Returns:
        List[MemoryRecord]: Relevant memories for planning
    """
    # Expand query context with goals
    expanded_context = planning_context
    if agent_goals:
        goals_text = " ".join(agent_goals)
        expanded_context += f" considering goals: {goals_text}"
    
    # Get recent important memories and goal-related memories
    recent_memories = retrieve_relevant_memories(
        memory_store=memory_store,
        query_context=expanded_context,
        k=8,
        importance_threshold=5.0,
        time_window_hours=168  # Last week
    )
    
    # Get goal-related and reflection memories
    goal_memories = memory_store.get_memories_by_source("goal_activity")
    reflection_memories = memory_store.get_memories_by_source("reflection")
    
    # Combine and deduplicate
    all_memories = recent_memories + goal_memories[-5:] + reflection_memories[-3:]
    unique_memories = []
    seen_ids = set()
    
    for memory in all_memories:
        if memory.id not in seen_ids:
            unique_memories.append(memory)
            seen_ids.add(memory.id)
    
    # Sort by importance and recency
    unique_memories.sort(key=lambda m: (m.importance, m.timestamp), reverse=True)
    
    return unique_memories[:15]

def retrieve_memories_for_reflection(memory_store: MemoryStore,
                                   reflection_period_hours: int = 24) -> List[MemoryRecord]:
    """
    Retrieve memories for daily/weekly reflection.
    
    Args:
        memory_store (MemoryStore): The agent's memory store
        reflection_period_hours (int): Period to reflect on (default 24 hours)
        
    Returns:
        List[MemoryRecord]: Memories from the reflection period
    """
    end_time = datetime.datetime.now()
    start_time = end_time - datetime.timedelta(hours=reflection_period_hours)
    
    # Get all memories from the period
    period_memories = memory_store.get_memories_by_timeframe(start_time, end_time)
    
    # Filter out low-importance routine memories for reflection
    significant_memories = [m for m in period_memories if m.importance >= 4.0]
    
    # Sort by importance
    significant_memories.sort(key=lambda m: m.importance, reverse=True)
    
    return significant_memories

def retrieve_memories_for_social_context(memory_store: MemoryStore,
                                       other_agent_name: str,
                                       interaction_context: str = "") -> List[MemoryRecord]:
    """
    Retrieve memories relevant to interacting with a specific agent.
    
    Args:
        memory_store (MemoryStore): The agent's memory store
        other_agent_name (str): Name of the other agent
        interaction_context (str): Context of the interaction
        
    Returns:
        List[MemoryRecord]: Relevant memories about the other agent
    """
    # Search for memories involving the other agent
    query_context = f"interaction with {other_agent_name} {interaction_context}"
    
    # Get memories with the other agent's name in keywords or text
    relevant_memories = retrieve_relevant_memories(
        memory_store=memory_store,
        query_context=query_context,
        k=10,
        importance_threshold=3.0
    )
    
    # Also get memories with the agent's name as keyword
    agent_memories = []
    for memory in memory_store.memories:
        if other_agent_name.lower() in memory.keywords or other_agent_name.lower() in memory.text.lower():
            agent_memories.append(memory)
    
    # Combine and deduplicate
    all_memories = relevant_memories + agent_memories
    unique_memories = []
    seen_ids = set()
    
    for memory in all_memories:
        if memory.id not in seen_ids:
            unique_memories.append(memory)
            seen_ids.add(memory.id)
    
    # Sort by recency and importance
    unique_memories.sort(key=lambda m: (m.timestamp, m.importance), reverse=True)
    
    return unique_memories[:8]

def retrieve_similar_experiences(memory_store: MemoryStore,
                               current_situation: str,
                               k: int = 5) -> List[MemoryRecord]:
    """
    Retrieve memories of similar past experiences.
    
    Args:
        memory_store (MemoryStore): The agent's memory store
        current_situation (str): Description of current situation
        k (int): Number of similar experiences to retrieve
        
    Returns:
        List[MemoryRecord]: Similar past experiences
    """
    # Get memories with high semantic similarity to current situation
    similar_memories = retrieve_relevant_memories(
        memory_store=memory_store,
        query_context=current_situation,
        k=k,
        importance_threshold=4.0
    )
    
    return similar_memories

def retrieve_contextual_knowledge(memory_store: MemoryStore,
                                topic: str,
                                knowledge_type: str = "general") -> List[MemoryRecord]:
    """
    Retrieve memories that provide contextual knowledge about a topic.
    
    Args:
        memory_store (MemoryStore): The agent's memory store
        topic (str): Topic to get knowledge about
        knowledge_type (str): Type of knowledge needed
        
    Returns:
        List[MemoryRecord]: Relevant knowledge memories
    """
    query_context = f"{knowledge_type} knowledge about {topic}"
    
    # Prioritize reflections and insights for knowledge
    knowledge_memories = retrieve_relevant_memories(
        memory_store=memory_store,
        query_context=query_context,
        k=8,
        importance_threshold=5.0,
        source_filter=["reflection", "insight", "learning", "observation"]
    )
    
    return knowledge_memories

def get_memory_summary_for_context(memories: List[MemoryRecord], 
                                 max_length: int = 500) -> str:
    """
    Create a summary of memories for use in prompts.
    
    Args:
        memories (List[MemoryRecord]): Memories to summarize
        max_length (int): Maximum character length of summary
        
    Returns:
        str: Summary of memories
    """
    if not memories:
        return "No relevant memories found."
    
    # Sort memories by importance and recency
    sorted_memories = sorted(memories, key=lambda m: (m.importance, m.timestamp), reverse=True)
    
    summary_parts = []
    total_length = 0
    
    for memory in sorted_memories:
        memory_text = f"- {memory.text}"
        
        # Check if adding this memory would exceed length limit
        if total_length + len(memory_text) > max_length:
            if not summary_parts:  # If no memories fit, add at least one truncated
                summary_parts.append(memory_text[:max_length-3] + "...")
            break
        
        summary_parts.append(memory_text)
        total_length += len(memory_text)
    
    return "\n".join(summary_parts)

def filter_memories_by_relevance_score(memories: List[MemoryRecord],
                                     query_embedding,
                                     min_relevance: float = 0.1) -> List[MemoryRecord]:
    """
    Filter memories by minimum relevance score to a query.
    
    Args:
        memories (List[MemoryRecord]): Memories to filter
        query_embedding: Embedding of the query
        min_relevance (float): Minimum relevance score
        
    Returns:
        List[MemoryRecord]: Filtered memories
    """
    filtered_memories = []
    
    for memory in memories:
        if memory.embedding is not None:
            relevance_score = memory.get_composite_score(query_embedding=query_embedding)
            if relevance_score >= min_relevance:
                filtered_memories.append(memory)
    
    return filtered_memories 