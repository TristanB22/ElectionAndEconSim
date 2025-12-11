#!/usr/bin/env python3
"""
Event System for Environment

Defines the Event class and Experience class for managing events and agent experiences.
"""

import time
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from enum import Enum
from datetime import datetime


class MediumType(Enum):
    """Types of media through which events can be experienced."""
    PHYSICAL = "physical"
    DIGITAL = "digital"


@dataclass
class Event:
    """
    Represents an event that occurs in the environment.
    
    Events are impartial descriptions of what happened, without agent-specific
    interpretation or processing information. Agent references use sequential
    numbers (e.g., "agent 1", "agent 2") for generalization, with a mapping
    to actual agent IDs stored separately.
    """
    
    event_id: int  # Sequential integer ID for the event
    event_type: str  # e.g., "message", "environmental_change", "interaction", "system_notification"
    content: str     # Impartial description using agent numbers (e.g., "agent 1 does x")
    environment: str = "default"  # Environment where the event occurred
    # context: str = "general"      # Context or category of the event
    source: Optional[str] = None  # ID of the agent/system that created this event
    target: Optional[str] = None  # ID of the agent this event is specifically for (None = all agents)
    participants: Optional[List[str]] = None  # List of agent names involved in the event
    timestamp: Optional[float] = None  # Event timestamp (will be set to computer time if not provided)
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional event data
    location: List[str] = field(default_factory=list)  # Ordered list of location specificity (e.g., ["World", "USA", "New York", "Albany"])
    agent_number_mapping: Dict[str, str] = field(default_factory=dict)  # Maps agent numbers in content to actual agent IDs
    
    def __post_init__(self):
        """Validate event data after initialization."""
        if not isinstance(self.event_id, int) or self.event_id < 0:
            raise ValueError("Event ID must be a non-negative integer")
        if not self.event_type:
            raise ValueError("Event type cannot be empty")
        if not self.content:
            raise ValueError("Event content cannot be empty")
        if not isinstance(self.location, list):
            raise ValueError("Location must be a list")
        
        # Set timestamp to current time if not provided (fallback for backward compatibility)
        if self.timestamp is None:
            self.timestamp = time.time()
    
    def get_location_string(self) -> str:
        """Get location as a semicolon-separated string."""
        return "; ".join(self.location) if self.location else "Unknown"
    
    def get_agent_id_from_number(self, agent_number: str) -> Optional[str]:
        """
        Get the actual agent ID from an agent number referenced in content.
        
        Args:
            agent_number: Agent number (e.g., "agent 1", "agent 2")
            
        Returns:
            Actual agent ID if found, None otherwise
        """
        return self.agent_number_mapping.get(agent_number)
    
    def get_agent_number_from_id(self, agent_id: str) -> Optional[str]:
        """
        Get the agent number from an actual agent ID.
        
        Args:
            agent_id: Actual agent ID
            
        Returns:
            Agent number (e.g., "agent 1") if found, None otherwise
        """
        for number, aid in self.agent_number_mapping.items():
            if aid == agent_id:
                return number
        return None
    
    def add_agent_mapping(self, agent_number: str, agent_id: str) -> None:
        """
        Add a mapping between agent number and agent ID.
        
        Args:
            agent_number: Agent number (e.g., "agent 1")
            agent_id: Actual agent ID
        """
        self.agent_number_mapping[agent_number] = agent_id


@dataclass
class Experience:
    """
    Represents an agent's interpretation of an event.
    
    Experiences are agent-specific interpretations of events, including
    how the agent perceived and understood what happened.
    """
    
    experience_id: int  # Sequential integer ID for experiences across the simulation
    event_id: int       # ID of the event being interpreted
    agent_id: str       # ID of the agent having this experience
    interpretation: str # Agent's interpretation of the event
    medium_type: MediumType  # Type of medium through which the event was experienced
    medium: str         # Specific medium (e.g., "phone screen", "direct observation")
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional experience data
    
    def __post_init__(self):
        """Validate experience data after initialization."""
        if not isinstance(self.experience_id, int) or self.experience_id < 0:
            raise ValueError("Experience ID must be a non-negative integer")
        if not isinstance(self.event_id, int) or self.event_id < 0:
            raise ValueError("Event ID must be a non-negative integer")
        if not self.agent_id:
            raise ValueError("Agent ID cannot be empty")
        if not self.interpretation:
            raise ValueError("Interpretation cannot be empty")
        if not isinstance(self.medium_type, MediumType):
            raise ValueError("Medium type must be a MediumType enum value")
        if not self.medium:
            raise ValueError("Medium cannot be empty")


@dataclass
class EventQueue:
    """
    Manages a queue of events for processing, scoped to a specific environment.
    """
    environment: str
    events: List[Event] = field(default_factory=list)
    processed_events: List[Event] = field(default_factory=list)
    
    def add_event(self, event: Event) -> None:
        """Add an event to the queue, ensuring it matches the environment."""
        if event.environment != self.environment:
            raise ValueError(f"Event environment '{event.environment}' does not match EventQueue environment '{self.environment}'")
        self.events.append(event)
    
    def get_events_for_agent(self, agent_id: str) -> List[Event]:
        """Get all events for this environment that should be processed by a specific agent."""
        return [
            event for event in self.events 
            if (event.target is None or event.target == agent_id)
            and (event.environment == self.environment)
        ]
    
    def mark_processed(self, event: Event, agent_id: str) -> None:
        """Mark an event as processed by an agent."""
        if event in self.events:
            # Check if all target agents have processed this event
            if event.target is None:
                # Global event - move to processed after any agent processes it
                self.events.remove(event)
                self.processed_events.append(event)
            elif event.target == agent_id:
                # Specific target event - move to processed when target agent processes it
                self.events.remove(event)
                self.processed_events.append(event)
    
    def get_processed_events_for_agent(self, agent_id: str) -> List[Event]:
        """Get events that have been processed by a specific agent."""
        return [
            event for event in self.processed_events 
            if event.environment == self.environment
        ]
    
    def get_all_processed_events(self) -> List[Event]:
        """Get all processed events for this environment."""
        return [event for event in self.processed_events if event.environment == self.environment]
    
    def clear_processed(self) -> None:
        """Clear processed events to free memory."""
        self.processed_events = [event for event in self.processed_events if event.environment != self.environment]
    
    def clear_all(self) -> None:
        """Clear both pending and processed events for this environment."""
        self.events = [event for event in self.events if event.environment != self.environment]
        self.processed_events = [event for event in self.processed_events if event.environment != self.environment]
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get statistics about the event queue for this environment."""
        pending = [event for event in self.events if event.environment == self.environment]
        processed = [event for event in self.processed_events if event.environment == self.environment]
        return {
            'pending_events': len(pending),
            'processed_events': len(processed),
            'total_events': len(pending) + len(processed)
        }


def create_message_event(message: str, source: str, target: Optional[str] = None, environment: str = "default", location: List[str] = None, timestamp: Optional[float] = None) -> Event:
    """Create a message event."""
    return Event(
        event_id=0,  # Will be set by caller
        event_type="message",
        content=message,
        source=source,
        target=target,
        environment=environment,
        # context="communication",
        location=location or [],
        timestamp=timestamp
    )


def create_environmental_event(description: str, environment: str = "default", location: List[str] = None, timestamp: Optional[float] = None) -> Event:
    """Create an environmental change event."""
    return Event(
        event_id=0,  # Will be set by caller
        event_type="environmental_change",
        content=description,
        source="environment",
        environment=environment,
        # context="environment",
        location=location or [],
        timestamp=timestamp
    )


def create_interaction_event(description: str, participants: List[str], environment: str = "default", location: List[str] = None, timestamp: Optional[float] = None) -> Event:
    """Create an interaction event."""
    return Event(
        event_id=0,  # Will be set by caller
        event_type="interaction",
        content=description,
        source="system",
        metadata={'participants': participants},
        environment=environment,
        # context="social",
        location=location or [],
        timestamp=timestamp
    )


def create_system_event(description: str, environment: str = "default", location: List[str] = None, timestamp: Optional[float] = None) -> Event:
    """Create a system notification event."""
    return Event(
        event_id=0,  # Will be set by caller
        event_type="system_notification",
        content=description,
        source="system",
        environment=environment,
        # context="system",
        location=location or [],
        timestamp=timestamp
    )


def parse_clock_time_to_timestamp(clock_time_str: str, base_date: Optional[datetime] = None) -> float:
    """
    Parse clock time string (e.g., "06:45 AM") to a timestamp.
    
    Args:
        clock_time_str: Time string in format "HH:MM AM/PM"
        base_date: Base date to use (defaults to current date)
        
    Returns:
        Unix timestamp for the parsed time
    """
    if base_date is None:
        base_date = datetime.now()
    
    try:
        # Parse time string like "06:45 AM"
        time_obj = datetime.strptime(clock_time_str, "%I:%M %p").time()
        # Combine with base date
        event_datetime = datetime.combine(base_date.date(), time_obj)
        return event_datetime.timestamp()
    except ValueError as e:
        print(f"Warning: Could not parse clock time '{clock_time_str}': {e}")
        return time.time()


def create_event_with_clock_time(event_type: str, content: str, clock_time_str: str, 
                                base_date: Optional[datetime] = None, **kwargs) -> Event:
    """
    Create an event with a specific clock time instead of current time.
    
    Args:
        event_type: Type of event (e.g., "message", "interaction")
        content: Event content description
        clock_time_str: Clock time string (e.g., "06:45 AM")
        base_date: Base date to use (defaults to current date)
        **kwargs: Additional event parameters
        
    Returns:
        Event with the specified clock time
    """
    timestamp = parse_clock_time_to_timestamp(clock_time_str, base_date)
    
    return Event(
        event_id=0,  # Will be set by caller
        event_type=event_type,
        content=content,
        timestamp=timestamp,
        **kwargs
    ) 