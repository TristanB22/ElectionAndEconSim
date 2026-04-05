#!/usr/bin/env python3
"""
Structured Memory System
Handles structured memory creation and management for agents.
"""

import time
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum

class EventType(Enum):
    """Types of events that can be stored as memories."""
    INTERACTION = "interaction"
    OBSERVATION = "observation"
    DECISION = "decision"
    EMOTIONAL = "emotional"
    LEARNING = "learning"
    GOAL_ACHIEVEMENT = "goal_achievement"
    FAILURE = "failure"
    SOCIAL = "social"
    ECONOMIC = "economic"
    POLITICAL = "political"
    GENERAL = "general"

class Environment(Enum):
    """Environment types for memories."""
    HOME = "home"
    WORK = "work"
    SOCIAL = "social"
    PUBLIC = "public"
    VIRTUAL = "virtual"
    UNKNOWN = "unknown"

class EmotionalState(Enum):
    """Emotional states for memories."""
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    FEARFUL = "fearful"
    SURPRISED = "surprised"
    DISGUSTED = "disgusted"
    NEUTRAL = "neutral"
    EXCITED = "excited"
    ANXIOUS = "anxious"
    CONTENT = "content"
    FRUSTRATED = "frustrated"
    HOPEFUL = "hopeful"
    DISAPPOINTED = "disappointed"
    PROUD = "proud"
    ASHAMED = "ashamed"

@dataclass
class StructuredMemory:
    """Structured memory object for agents."""
    memory_id: str
    agent_id: str
    timestamp: float
    created_at: float
    event_type: str
    environment: str
    location: str
    source: str
    target: str
    participants: List[str]
    emotional_state: str
    impact_score: float
    analysis_type: str
    personal_significance: float
    personal_narrative: str
    context_description: str
    learning_outcome: str
    future_implications: str
    context_tags: List[str]
    vector_embedding: Optional[List[float]] = None

class MemoryBuilder:
    """Builder for creating structured memories."""
    
    def __init__(self, agent_id: str):
        """
        Initialize memory builder.
        
        Args:
            agent_id: ID of the agent creating memories
        """
        self.agent_id = agent_id
    
    def create_memory_from_event(self, 
                                event_description: str,
                                event_type: Union[str, EventType] = EventType.GENERAL,
                                environment: Union[str, Environment] = Environment.UNKNOWN,
                                location: str = "unknown",
                                source: str = "agent",
                                target: str = "self",
                                participants: List[str] = None,
                                emotional_state: Union[str, EmotionalState] = EmotionalState.NEUTRAL,
                                impact_score: float = 0.0,
                                personal_significance: float = 0.0,
                                context_description: str = "",
                                learning_outcome: str = "",
                                future_implications: str = "",
                                context_tags: List[str] = None) -> StructuredMemory:
        """
        Create a structured memory from an event.
        
        Args:
            event_description: Description of the event
            event_type: Type of event
            environment: Environment where event occurred
            location: Specific location
            source: Source of the event
            target: Target of the event
            participants: List of participants
            emotional_state: Emotional state during event
            impact_score: Impact score (0-10)
            personal_significance: Personal significance (0-10)
            context_description: Additional context
            learning_outcome: What was learned
            future_implications: Future implications
            context_tags: Tags for categorization
            
        Returns:
            StructuredMemory object
        """
        if participants is None:
            participants = []
        if context_tags is None:
            context_tags = []
        
        # Convert enums to strings
        if isinstance(event_type, EventType):
            event_type = event_type.value
        if isinstance(environment, Environment):
            environment = environment.value
        if isinstance(emotional_state, EmotionalState):
            emotional_state = emotional_state.value
        
        # Generate personal narrative
        personal_narrative = self._generate_personal_narrative(
            event_description, event_type, emotional_state, impact_score
        )
        
        memory = StructuredMemory(
            memory_id=str(uuid.uuid4()),
            agent_id=self.agent_id,
            timestamp=time.time(),
            created_at=time.time(),
            event_type=event_type,
            environment=environment,
            location=location,
            source=source,
            target=target,
            participants=participants,
            emotional_state=emotional_state,
            impact_score=impact_score,
            analysis_type="automatic",
            personal_significance=personal_significance,
            personal_narrative=personal_narrative,
            context_description=context_description,
            learning_outcome=learning_outcome,
            future_implications=future_implications,
            context_tags=context_tags
        )
        
        return memory
    
    def _generate_personal_narrative(self, 
                                   event_description: str, 
                                   event_type: str, 
                                   emotional_state: str, 
                                   impact_score: float) -> str:
        """Generate a personal narrative for the memory."""
        narrative_parts = []
        
        # Add emotional context
        if emotional_state != "neutral":
            narrative_parts.append(f"I felt {emotional_state} during this event.")
        
        # Add impact context
        if impact_score > 7:
            narrative_parts.append("This was a highly significant event for me.")
        elif impact_score > 4:
            narrative_parts.append("This was a moderately important event.")
        else:
            narrative_parts.append("This was a routine event.")
        
        # Add event description
        narrative_parts.append(f"The event involved: {event_description}")
        
        # Add type-specific context
        if event_type == "interaction":
            narrative_parts.append("I interacted with others during this event.")
        elif event_type == "decision":
            narrative_parts.append("I made an important decision.")
        elif event_type == "learning":
            narrative_parts.append("I learned something new from this experience.")
        elif event_type == "emotional":
            narrative_parts.append("This event had a strong emotional impact on me.")
        
        return " ".join(narrative_parts)
    
    def create_memory_from_interaction(self, 
                                     other_agent_id: str,
                                     interaction_type: str,
                                     description: str,
                                     emotional_state: str = "neutral",
                                     impact_score: float = 0.0) -> StructuredMemory:
        """Create a memory from an agent interaction."""
        return self.create_memory_from_event(
            event_description=f"Interaction with {other_agent_id}: {description}",
            event_type=EventType.INTERACTION,
            environment=Environment.SOCIAL,
            source="agent",
            target=other_agent_id,
            participants=[other_agent_id],
            emotional_state=emotional_state,
            impact_score=impact_score,
            context_tags=["interaction", "social"]
        )
    
    def create_memory_from_decision(self, 
                                   decision_description: str,
                                   decision_context: str = "",
                                   emotional_state: str = "neutral",
                                   impact_score: float = 0.0) -> StructuredMemory:
        """Create a memory from a decision made."""
        return self.create_memory_from_event(
            event_description=f"Decision: {decision_description}",
            event_type=EventType.DECISION,
            environment=Environment.UNKNOWN,
            source="agent",
            target="self",
            participants=[],
            emotional_state=emotional_state,
            impact_score=impact_score,
            context_description=decision_context,
            context_tags=["decision", "cognitive"]
        )
    
    def create_memory_from_observation(self, 
                                     observation: str,
                                     environment: str = "unknown",
                                     location: str = "unknown",
                                     emotional_state: str = "neutral",
                                     impact_score: float = 0.0) -> StructuredMemory:
        """Create a memory from an observation."""
        return self.create_memory_from_event(
            event_description=f"Observation: {observation}",
            event_type=EventType.OBSERVATION,
            environment=environment,
            location=location,
            emotional_state=emotional_state,
            impact_score=impact_score,
            context_tags=["observation", "perception"]
        )

