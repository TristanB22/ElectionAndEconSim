#!/usr/bin/env python3
"""
Context Enums for Memory System
Defines enums and constants used throughout the memory system.
"""

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

class MemoryType(Enum):
    """Types of memories."""
    EPISODIC = "episodic"  # Specific events
    SEMANTIC = "semantic"  # Facts and knowledge
    PROCEDURAL = "procedural"  # Skills and procedures
    EMOTIONAL = "emotional"  # Emotional experiences
    SOCIAL = "social"  # Social interactions
    SPATIAL = "spatial"  # Spatial information
    TEMPORAL = "temporal"  # Time-based information

class AnalysisType(Enum):
    """Types of memory analysis."""
    AUTOMATIC = "automatic"
    MANUAL = "manual"
    AI_ASSISTED = "ai_assisted"
    USER_DEFINED = "user_defined"

# Memory importance thresholds
MIN_IMPORTANCE_TO_SAVE = 1.0
MAX_IMPORTANCE = 10.0
DEFAULT_IMPORTANCE = 5.0

# Impact score thresholds
MIN_IMPACT_SCORE = 0.0
MAX_IMPACT_SCORE = 10.0
DEFAULT_IMPACT_SCORE = 5.0

# Personal significance thresholds
MIN_PERSONAL_SIGNIFICANCE = 0.0
MAX_PERSONAL_SIGNIFICANCE = 10.0
DEFAULT_PERSONAL_SIGNIFICANCE = 5.0

# Memory persistence settings
DEFAULT_MEMORY_PERSIST_TIME = 604800  # 7 days in seconds
MIN_MEMORY_PERSIST_TIME = 3600  # 1 hour in seconds
MAX_MEMORY_PERSIST_TIME = 31536000  # 1 year in seconds

# Vector embedding settings
DEFAULT_EMBEDDING_SIZE = 384
EMBEDDING_TIMEOUT = 10  # seconds
MAX_EMBEDDING_RETRIES = 3

# Qdrant settings
DEFAULT_QDRANT_HOST = "localhost"
DEFAULT_QDRANT_PORT = 1002
DEFAULT_COLLECTION_NAME = "agent_memories"
DEFAULT_VECTOR_DISTANCE = "cosine"

# Memory search settings
DEFAULT_SEARCH_LIMIT = 10
MAX_SEARCH_LIMIT = 100
DEFAULT_SIMILARITY_THRESHOLD = 0.7

# Memory cleanup settings
CLEANUP_INTERVAL = 3600  # 1 hour in seconds
MAX_MEMORIES_PER_AGENT = 10000
MEMORY_CLEANUP_BATCH_SIZE = 100

