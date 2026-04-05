"""
Agent Number Manager
Manages sequential agent numbers for events and provides utilities for creating
events with proper agent number mapping.
"""

from typing import Dict, List, Optional, Tuple, Any
from .events import Event

class AgentNumberManager:
    """
    Manages sequential agent numbers for events.
    
    This class ensures that agent references in event content use sequential
    numbers (e.g., "agent 1", "agent 2") while maintaining a mapping to
    actual agent IDs for proper event processing.
    """
    
    def __init__(self):
        """Initialize the agent number manager."""
        self.agent_id_to_number: Dict[str, str] = {}  # Maps agent ID to agent number
        self.agent_number_to_id: Dict[str, str] = {}  # Maps agent number to agent ID
        self.next_agent_number: int = 1  # Next available agent number
    
    def get_or_create_agent_number(self, agent_id: str) -> str:
        """
        Get existing agent number or create a new one.
        
        Args:
            agent_id: The actual agent ID
            
        Returns:
            Agent number string (e.g., "agent 1")
        """
        if agent_id in self.agent_id_to_number:
            return self.agent_id_to_number[agent_id]
        
        # Create new agent number
        agent_number = f"agent {self.next_agent_number}"
        self.agent_id_to_number[agent_id] = agent_number
        self.agent_number_to_id[agent_number] = agent_id
        self.next_agent_number += 1
        
        return agent_number
    
    def get_agent_id(self, agent_number: str) -> Optional[str]:
        """
        Get agent ID from agent number.
        
        Args:
            agent_number: Agent number (e.g., "agent 1")
            
        Returns:
            Agent ID if found, None otherwise
        """
        return self.agent_number_to_id.get(agent_number)
    
    def get_agent_number(self, agent_id: str) -> Optional[str]:
        """
        Get agent number from agent ID.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Agent number if found, None otherwise
        """
        return self.agent_id_to_number.get(agent_id)
    
    def get_all_mappings(self) -> Dict[str, str]:
        """Get all agent number to agent ID mappings."""
        return self.agent_number_to_id.copy()
    
    def reset(self):
        """Reset the agent number manager."""
        self.agent_id_to_number.clear()
        self.agent_number_to_id.clear()
        self.next_agent_number = 1

def create_event_with_agent_numbers(
    event_id: int,
    event_type: str,
    content: str,
    agent_number_manager: AgentNumberManager,
    agent_ids_in_content: List[str],
    environment: str = "default",
    source: Optional[str] = None,
    target: Optional[str] = None,
    participants: Optional[List[str]] = None,
    timestamp: Optional[float] = None,
    metadata: Optional[Dict[str, Any]] = None,
    location: Optional[List[str]] = None
) -> Event:
    """
    Create an event with proper agent number mapping.
    
    Args:
        event_id: Sequential event ID
        event_type: Type of event
        content: Event content (should use agent numbers like "agent 1", "agent 2")
        agent_number_manager: Manager for agent numbers
        agent_ids_in_content: List of agent IDs referenced in the content
        environment: Environment where event occurred
        source: Source agent ID
        target: Target agent ID
        participants: List of participant agent IDs
        timestamp: Event timestamp
        metadata: Additional metadata
        location: Location hierarchy
        
    Returns:
        Event object with proper agent number mapping
    """
    import time
    
    # Ensure we have all agent numbers mapped
    agent_number_mapping = {}
    for agent_id in agent_ids_in_content:
        agent_number = agent_number_manager.get_or_create_agent_number(agent_id)
        agent_number_mapping[agent_number] = agent_id
    
    # Create the event
    event = Event(
        event_id=event_id,
        event_type=event_type,
        content=content,
        environment=environment,
        source=source,
        target=target,
        participants=participants,
        timestamp=timestamp or time.time(),
        metadata=metadata or {},
        location=location or [],
        agent_number_mapping=agent_number_mapping
    )
    
    return event

def replace_agent_names_with_numbers(
    content: str,
    agent_name_to_id: Dict[str, str],
    agent_number_manager: AgentNumberManager
) -> Tuple[str, List[str]]:
    """
    Replace agent names in content with agent numbers.
    
    Args:
        content: Original content with agent names
        agent_name_to_id: Mapping from agent names to agent IDs
        agent_number_manager: Manager for agent numbers
        
    Returns:
        Tuple of (modified_content, list_of_agent_ids_in_content)
    """
    modified_content = content
    agent_ids_in_content = []
    
    for agent_name, agent_id in agent_name_to_id.items():
        if agent_name in content:
            # Get or create agent number
            agent_number = agent_number_manager.get_or_create_agent_number(agent_id)
            # Replace agent name with agent number
            modified_content = modified_content.replace(agent_name, agent_number)
            agent_ids_in_content.append(agent_id)
    
    return modified_content, agent_ids_in_content

# Global instance for easy access
global_agent_number_manager = AgentNumberManager()

def get_global_agent_number_manager() -> AgentNumberManager:
    """Get the global agent number manager instance."""
    return global_agent_number_manager
