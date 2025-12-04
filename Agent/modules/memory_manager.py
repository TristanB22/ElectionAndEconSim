#!/usr/bin/env python3
"""
Memory Manager for Agent Memory Systems

Handles both simple and advanced vector-based memory storage and retrieval.
"""

import os
import sys
import pickle
import time
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path

from Utils.path_manager import initialize_paths
initialize_paths()

# Load environment variables using centralized loader
try:
    from Utils.env_loader import load_environment
    load_environment()
except ImportError:
    # Fallback to basic dotenv loading if centralized loader not available
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print("Warning: python-dotenv not available. Environment variables may not be loaded from .env file.")

# Add environment variable controls for embeddings and Qdrant connection
USE_EMBEDDINGS = os.getenv("USE_EMBEDDINGS", "1") in ("1", "true", "yes")
EMBEDDING_TIMEOUT = int(os.getenv("EMBEDDING_TIMEOUT", "10"))  # seconds
DISABLE_QDRANT = os.getenv('DISABLE_QDRANT', '0').lower() in ('1', 'true', 'yes')

# Get Qdrant configuration from environment_config (respects QDRANT_TARGET)
try:
    from Utils.environment_config import get_qdrant_config
    qdrant_config = get_qdrant_config()
    QDRANT_HOST = qdrant_config['host']
    QDRANT_PORT = qdrant_config['port']
except Exception as e:
    # Fallback to direct environment variables if config helper fails
    print(f"Warning: Could not load Qdrant config from environment_config: {e}")
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "1002"))

# Add the Setup directory to the path to import qdrant_memory_db
project_root = Path(__file__).resolve().parent.parent.parent
setup_path = project_root / "Setup"
sys.path.insert(0, str(setup_path))

try:
    from qdrant_memory_db import QdrantMemoryDB, Memory as QdrantMemory, create_memory_id as create_qdrant_memory_id
    QDRANT_AVAILABLE = True
except ImportError as e:
    print(f"ERROR: Qdrant memory database not available: {e}")
    print("Qdrant is REQUIRED for agent memory functionality.")
    print("Please ensure Qdrant is running and the qdrant-client package is installed.")
    QdrantMemoryDB = None
    QdrantMemory = None
    create_qdrant_memory_id = None
    QDRANT_AVAILABLE = False

try:
    from .simple_memory import SimpleMemoryDB, SimpleMemory, create_memory_id as create_simple_memory_id
    SIMPLE_MEMORY_AVAILABLE = True
except ImportError:
    try:
        from simple_memory import SimpleMemoryDB, SimpleMemory, create_memory_id as create_simple_memory_id
        SIMPLE_MEMORY_AVAILABLE = True
    except ImportError:
        print("Warning: Simple memory system not available.")
        SimpleMemoryDB = None
        SimpleMemory = None
        create_simple_memory_id = None
        SIMPLE_MEMORY_AVAILABLE = False

try:
    # Try to import from Setup directory first
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'Setup'))
    from embedding_module import get_text_embedding
    EMBEDDING_AVAILABLE = True
except ImportError as e:
    try:
        # Fallback to direct import
        from embedding_module import get_text_embedding
        EMBEDDING_AVAILABLE = True
    except ImportError:
        print(f"ERROR: Embedding module not available: {e}")
        print("Embeddings are REQUIRED for agent memory functionality.")
        print("Please ensure OPENAI_API_KEY is set for OpenAI embeddings.")
        get_text_embedding = None
        EMBEDDING_AVAILABLE = False

# Import structured memory components
try:
    from structured_memory import MemoryBuilder, StructuredMemory
    STRUCTURED_MEMORY_AVAILABLE = True
except ImportError as e:
    print(f"ERROR: Structured memory not available: {e}")
    print("Structured memory is REQUIRED for agent memory functionality.")
    print("Please ensure structured_memory.py is available in the Setup directory.")
    STRUCTURED_MEMORY_AVAILABLE = False

# Try to import simulation time manager
try:
    from Environment.time_manager import get_current_simulation_datetime, get_current_simulation_timestamp
    SIMULATION_TIME_AVAILABLE = True
except ImportError:
    print("Warning: Simulation time manager not available, using computer time")
    SIMULATION_TIME_AVAILABLE = False


def check_qdrant_online():
    """Check if Qdrant is online and accessible."""
    if DISABLE_QDRANT:
        return False
    if not QDRANT_AVAILABLE:
        return False
    
    try:
        # Try to create a test client
        from qdrant_client import QdrantClient
        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        # Try to get collections to test connection
        client.get_collections()
        return True
    except Exception as e:
        print(f"Qdrant is not online: {e}")
        print(f"Full traceback:")
        import traceback
        traceback.print_exc()
        return False


def parse_event_timestamp(event_time_str: str, base_date: Optional[datetime] = None) -> datetime:
    """
    Parse event time string (e.g., "06:45 AM") into a datetime object.
    
    Args:
        event_time_str: Time string in format "HH:MM AM/PM"
        base_date: Base date to use (defaults to simulation time if available, otherwise current date)
        
    Returns:
        datetime object with the parsed time
    """
    if base_date is None:
        if SIMULATION_TIME_AVAILABLE:
            try:
                base_date = get_current_simulation_datetime()
            except Exception:
                base_date = datetime.now()
        else:
            base_date = datetime.now()
    
    try:
        # Parse time string like "06:45 AM"
        time_obj = datetime.strptime(event_time_str, "%I:%M %p").time()
        # Combine with base date
        event_datetime = datetime.combine(base_date.date(), time_obj)
        return event_datetime
    except ValueError as e:
        print(f"Warning: Could not parse event time '{event_time_str}': {e}")
        return get_current_event_time()


def get_current_event_time() -> datetime:
    """
    Get the current event time. This should be overridden by the environment
    to provide the current simulation time instead of computer time.
    
    Returns:
        Current datetime (simulation time if available, computer time as fallback)
    """
    if SIMULATION_TIME_AVAILABLE:
        try:
            return get_current_simulation_datetime()
        except Exception as e:
            print(f"Warning: Failed to get simulation time: {e}, falling back to computer time")
            return datetime.now()
    else:
        # Fallback to computer time if simulation time manager is not available
        return datetime.now()


class MemoryManager:
    """
    Manages agent memories using either simple (numpy-based) or advanced (Qdrant-based) systems.
    """
    
    def __init__(self, agent_id: str, db_path: str = "agent_memory.db"):
        """
        Initialize the memory manager for an agent.
        
        Args:
            agent_id: Unique identifier for the agent
            db_path: Path to the database file (for simple memory)
            
        Raises:
            RuntimeError: If required memory components are not available
        """
        self.agent_id = agent_id
        self.db_path = db_path
        self.db = None
        
        # Determine preference for vector DB early (allow hard-disable via DISABLE_QDRANT)
        use_vector_db_flag = os.getenv('MEMORY_USE_VECTOR_DB', 'True').lower() in ['true', '1', 'yes']
        use_vector_db = use_vector_db_flag and not DISABLE_QDRANT

        # Check if required components are available (only enforce for vector DB mode)
        if use_vector_db and not QDRANT_AVAILABLE:
            raise RuntimeError("Qdrant memory database is REQUIRED but not available when MEMORY_USE_VECTOR_DB is enabled. Please ensure Qdrant is running and qdrant-client is installed, or disable MEMORY_USE_VECTOR_DB.")

        if not EMBEDDING_AVAILABLE:
            print("Warning: Embedding module not available, using fallback embedding method")
            # Don't raise error, let the embedding module handle fallback
        
        if use_vector_db and not STRUCTURED_MEMORY_AVAILABLE:
            raise RuntimeError("Structured memory is REQUIRED when MEMORY_USE_VECTOR_DB is enabled. Please ensure structured_memory.py is available, or disable MEMORY_USE_VECTOR_DB.")
        
        # Determine memory system based on vector DB preference
        if use_vector_db:
            self.memory_system = 'advanced'
        else:
            self.memory_system = 'simple'
        
        # Get memory parameters from environment variables
        try:
            self.memory_top_m_to_return = int(os.getenv('MEMORY_TOP_M_TO_RETURN', '7'))
        except (ValueError, TypeError):
            print("Warning: Invalid MEMORY_TOP_M_TO_RETURN value, using default 7")
            self.memory_top_m_to_return = 7
        
        # Initialize appropriate database based on vector DB preference and availability
        if self.memory_system == 'advanced' and QDRANT_AVAILABLE and not DISABLE_QDRANT:
            if check_qdrant_online():
                try:
                    self.db = QdrantMemoryDB(collection_name=f"agent_{agent_id}", host=QDRANT_HOST, port=QDRANT_PORT)
                    # Using Qdrant database (vector DB enabled)
                except Exception as e:
                    print(f"Warning: Failed to initialize Qdrant database: {e}")
                    print(f"Full traceback:")
                    import traceback
                    traceback.print_exc()
                    self.db = None
                    # Fallback to simple if vector DB fails
                    self.memory_system = 'simple'
            else:
                print("Qdrant is not online, falling back to simple memory system")
                self.memory_system = 'simple'
        
        # Initialize simple memory if vector DB is disabled or failed
        if self.memory_system == 'simple' and SIMPLE_MEMORY_AVAILABLE:
            try:
                self.db = SimpleMemoryDB(agent_id, f"simple_memory_{agent_id}.pkl")
                print(f"Using simple memory system (vector DB disabled) for agent {agent_id}")
            except Exception as e:
                print(f"Warning: Failed to initialize simple memory system: {e}")
                print(f"Full traceback:")
                import traceback
                traceback.print_exc()
                self.db = None
        
        if self.db is None:
            print(f"Warning: No memory system available for agent {agent_id}")
    
    def create_enhanced_memory_content(self, event: 'Event', memory_content: str, impact_score: int) -> str:
        """
        Deprecated: We now store the first-person narrative directly. This helper returns the
        narrative unchanged to preserve compatibility where it's still called.
        """
        return memory_content
    
    def get_similar_memories_for_context(self, event: 'Event', k: int = None) -> str:
        """
        Get similar memories for context when processing new events with high importance scores.
        
        Args:
            event: The current event being processed
            k: Number of similar memories to retrieve (defaults to env setting)
            
        Returns:
            Context string with similar memories
        """
        if k is None:
            k = int(os.getenv('MEMORY_SIMILARITY_SEARCH_K', '3'))
        if self.db is None:
            return ""
        
        try:
            # Create a query based on the event content and context
            query = f"{event.content} {event.event_type} {event.environment} {' '.join(event.location) if isinstance(event.location, list) else str(event.location)}"
            
            # Search for similar memories
            similar_memories = self.search_memories(query, k=k)
            
            if not similar_memories:
                return ""
            
            # Build context string
            context_parts = ["SIMILAR MEMORIES FOR CONTEXT:"]
            for i, (memory_content, score) in enumerate(similar_memories, 1):
                context_parts.append(f"\n{i}. Similarity Score: {score:.3f}")
                context_parts.append(f"Memory: {memory_content[:200]}...")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            print(f"Error getting similar memories for context: {e}")
            print(f"Full traceback:")
            import traceback
            traceback.print_exc()
            return ""
    
    def add_memory(self, content: str, impact_score: int = None, event: Optional[Any] = None) -> bool:
        """
        Add a memory to the memory system.
        
        Args:
            content: The memory content to store
            impact_score: Impact score of the memory (defaults to env setting)
            event: Optional event object containing timestamp information
            
        Returns:
            bool: True if memory was added successfully
        """
        if impact_score is None:
            impact_score = int(os.getenv('DEFAULT_MEMORY_IMPACT_SCORE', '5'))
        
        # Use event timestamp if available, otherwise use current time
        if event and hasattr(event, 'timestamp'):
            if isinstance(event.timestamp, float):
                memory_timestamp = datetime.fromtimestamp(event.timestamp)
            else:
                memory_timestamp = event.timestamp
        else:
            memory_timestamp = get_current_event_time()
        
        if self.db is None:
            return False
        
        try:
            if self.memory_system == 'advanced' and isinstance(self.db, QdrantMemoryDB):
                # Try to create structured memory first
                if STRUCTURED_MEMORY_AVAILABLE and hasattr(self, 'agent') and hasattr(self.agent, 'get_name'):
                    try:
                        # Create structured memory using MemoryBuilder
                        memory_builder = MemoryBuilder(
                            agent_name=self.agent.get_name(),
                            agent_id=self.agent_id
                        )
                        
                        # Create a mock perception result for now
                        perception_result = {
                            'analysis_type': 'historical_context',
                            'reasoning': 'Memory created from direct input'
                        }
                        
                        # Use the provided event or create a mock one
                        if event:
                            event_to_use = event
                        else:
                            # Create a mock event for context
                            class MockEvent:
                                def __init__(self, content: str, timestamp: datetime):
                                    self.event_type = 'memory_creation'
                                    self.environment = 'personal'
                                    self.location = ['World', 'Personal']
                                    self.source = 'agent'
                                    self.timestamp = timestamp.timestamp()
                            
                            event_to_use = MockEvent(content, memory_timestamp)
                        
                        structured_memory = memory_builder.create_memory_from_event(
                            event=event_to_use,
                            perception_result=perception_result,
                            memory_content=content,
                            impact_score=impact_score
                        )
                        
                        # Generate embedding for the structured memory
                        if EMBEDDING_AVAILABLE and USE_EMBEDDINGS:
                            try:
                                # Use the personal narrative for embedding
                                embedding = get_text_embedding(structured_memory.personal_narrative)
                                structured_memory.vector_embedding = embedding
                            except Exception as e:
                                print(f"Warning: Could not generate embedding: {e}")
                                return False
                        elif not USE_EMBEDDINGS:
                            print("Info: Embeddings disabled via USE_EMBEDDINGS environment variable")
                        
                        # Store structured memory
                        return self.db.add_structured_memory(structured_memory)
                        
                    except Exception as e:
                        print(f"Warning: Failed to create structured memory, falling back to legacy: {e}")
                
                # Fallback to legacy memory creation
                memory = QdrantMemory(
                    memory_id=create_qdrant_memory_id(),
                    agent_id=self.agent_id,
                    content=content,
                    memory_type="general",
                    importance=float(impact_score) if impact_score is not None else 0.0,
                    timestamp=memory_timestamp.timestamp() if hasattr(memory_timestamp, 'timestamp') else float(memory_timestamp),
                    created_at=time.time(),
                    impact_score=float(impact_score) if impact_score is not None else 0.0
                )
                
                # Get embedding if available
                if EMBEDDING_AVAILABLE and USE_EMBEDDINGS:
                    try:
                        embedding = get_text_embedding(content)
                        memory.vector = embedding
                    except Exception as e:
                        print(f"Warning: Could not generate embedding: {e}")
                elif not USE_EMBEDDINGS:
                    print("Info: Embeddings disabled via USE_EMBEDDINGS environment variable")
                
                return self.db.add_memory(memory)
            
            elif self.memory_system == 'simple' and isinstance(self.db, SimpleMemoryDB):
                # Create simple memory
                memory = SimpleMemory(
                    id=create_simple_memory_id(),
                    agent_id=self.agent_id,
                    content=content,
                    timestamp=memory_timestamp,
                    impact_score=impact_score
                )
                
                return self.db.add_memory(memory)
            
            return False
            
        except Exception as e:
            print(f"Error adding memory: {e}")
            print(f"Full traceback:")
            import traceback
            traceback.print_exc()
            return False
    
    def search_memories(self, query: str, k: int = None, query_timestamp: Optional[datetime] = None) -> List[Tuple[str, float]]:
        """
        Search for memories using enhanced scoring system.
        
        Args:
            query: Search query string
            k: Number of results to return (defaults to env setting)
            query_timestamp: Timestamp for the query (defaults to current time)
            
        Returns:
            List of tuples containing (memory_content, similarity_score)
        """
        if k is None:
            # Try to get from numerical settings first
            try:
                from Setup.numerical_settings import numerical_settings
                k = numerical_settings.MEMORY_RETRIEVAL_MAX_RESULTS
            except ImportError:
                # Fallback to environment variable
                k = int(os.getenv('MEMORY_RETRIEVAL_MAX_RESULTS', '7'))
        
        # Use provided timestamp or current time
        if query_timestamp is None:
            query_timestamp = get_current_event_time()
        
        if self.db is None:
            return []
        
        try:
            if self.memory_system == 'advanced' and isinstance(self.db, QdrantMemoryDB):
                # Get embedding for query if available
                if EMBEDDING_AVAILABLE and USE_EMBEDDINGS:
                    try:
                        query_vector = get_text_embedding(query)
                        results = self.db.search_memories_enhanced(
                            query_vector,
                            agent_id=self.agent_id,
                            k=k
                        )
                        return [(memory.content, score) for memory, score in results]
                    except Exception as e:
                        print(f"Warning: Could not generate query embedding: {e}")
                        print(f"Full traceback:")
                        import traceback
                        traceback.print_exc()
                        # Fall back to simple text search
                        return self._fallback_text_search(query, k)
                else:
                    print("Warning: Embeddings not available for advanced memory search, using fallback")
                    return self._fallback_text_search(query, k)
            
            elif self.memory_system == 'simple' and isinstance(self.db, SimpleMemoryDB):
                results = self.db.search_memories(query, agent_id=self.agent_id, k=k)
                return [(memory.content, score) for memory, score in results]
            
            return []
            
        except Exception as e:
            print(f"Error searching memories: {e}")
            print(f"Full traceback:")
            import traceback
            traceback.print_exc()
            return []
    
    def get_recent_memories(self, limit: int = None) -> List[str]:
        """
        Get the most recent memories from the memory system.
        
        Args:
            limit: Maximum number of memories to return (defaults to env setting)
            
        Returns:
            List of recent memory contents
        """
        if limit is None:
            limit = int(os.getenv('MEMORY_TOP_M_TO_RETURN', '10'))
        if self.db is None:
            return []
        
        try:
            if self.memory_system == 'advanced' and isinstance(self.db, QdrantMemoryDB):
                memories = self.db.get_memories_by_agent(self.agent_id, limit=limit)
                # Sort by timestamp (most recent first)
                memories.sort(key=lambda m: m.timestamp, reverse=True)
                return [memory.content for memory in memories]
            
            elif self.memory_system == 'simple' and isinstance(self.db, SimpleMemoryDB):
                memories = self.db.get_memories_by_agent(self.agent_id)
                # Sort by timestamp (most recent first)
                memories.sort(key=lambda m: m.timestamp, reverse=True)
                return [memory.content for memory in memories[:limit]]
            
            return []
            
        except Exception as e:
            print(f"Error getting recent memories: {e}")
            print(f"Full traceback:")
            import traceback
            traceback.print_exc()
            return []
    
    def get_memory_count(self) -> int:
        """
        Get the total number of memories for this agent.
        
        Returns:
            Number of memories
        """
        if self.db is None:
            return 0
        
        try:
            if self.memory_system == 'advanced' and isinstance(self.db, QdrantMemoryDB):
                return self.db.get_memory_count()
            
            elif self.memory_system == 'simple' and isinstance(self.db, SimpleMemoryDB):
                return self.db.get_memory_count()
            
            return 0
            
        except Exception as e:
            print(f"Error getting memory count: {e}")
            print(f"Full traceback:")
            import traceback
            traceback.print_exc()
            return 0
    
    def recall_context(self, query: str, k: int = None) -> str:
        """
        Recall relevant context for decision-making.
        
        Args:
            query: Context query
            k: Number of memories to include
            
        Returns:
            Context string combining relevant memories
        """
        if self.db is None:
            return ""
        
        if k is None:
            k = self.memory_top_m_to_return
        
        try:
            # Get scored memories for context
            scored_memories = self.get_scored_memories(query, k=k)
            
            if not scored_memories:
                return ""
            
            # Combine memories into context
            context_parts = []
            for content, score in scored_memories:
                context_parts.append(f"- {content} (relevance: {score:.3f})")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            print(f"Error recalling context: {e}")
            print(f"Full traceback:")
            import traceback
            traceback.print_exc()
            return ""
    
    def add_experience(self, experience: str) -> bool:
        """Add an experience memory."""
        return self.add_memory(f"Experience: {experience}", impact_score=7)
    
    def add_observation(self, observation: str) -> bool:
        """Add an observation memory."""
        return self.add_memory(f"Observation: {observation}", impact_score=5)
    
    def add_interaction(self, interaction: str) -> bool:
        """Add an interaction memory."""
        return self.add_memory(f"Interaction: {interaction}", impact_score=6)
    
    def add_goal(self, goal: str) -> bool:
        """Add a goal memory."""
        return self.add_memory(f"Goal: {goal}", impact_score=8)
    
    def add_decision(self, decision: str) -> bool:
        """Add a decision memory."""
        return self.add_memory(f"Decision: {decision}", impact_score=6)
    
    def get_memory_summary(self) -> str:
        """
        Get a summary of the agent's memories.
        
        Returns:
            Summary string
        """
        if self.db is None:
            return "No memory system available"
        
        try:
            count = self.get_memory_count()
            # Get recent memories for context
            recent_limit = int(os.getenv('MEMORY_TOP_M_TO_RETURN', '3'))
            recent = self.get_recent_memories(limit=recent_limit)
            
            summary = f"Memory Summary for Agent {self.agent_id}:\n"
            summary += f"Total memories: {count}\n"
            summary += f"Memory system: {self.memory_system}\n"
            
            if recent:
                summary += "Recent memories:\n"
                for i, memory in enumerate(recent, 1):
                    summary += f"  {i}. {memory[:100]}{'...' if len(memory) > 100 else ''}\n"
            
            return summary
            
        except Exception as e:
            print(f"Error generating memory summary: {e}")
            print(f"Full traceback:")
            import traceback
            traceback.print_exc()
            return f"Error generating memory summary: {e}"
    
    def get_top_similar_memories(self, k: int = None) -> List[Tuple[str, float]]:
        """
        Get the top k most similar memories.
        
        Args:
            k: Number of memories to return
            
        Returns:
            List of (content, similarity_score) tuples
        """
        if self.db is None:
            return []
        
        if k is None:
            k = self.memory_top_m_to_return
        
        try:
            if self.memory_system == 'advanced' and isinstance(self.db, QdrantMemoryDB):
                results = self.db.get_top_similar_memories(self.agent_id, k=k)
                return [(memory.content, score) for memory, score in results]
            
            elif self.memory_system == 'simple' and isinstance(self.db, SimpleMemoryDB):
                results = self.db.get_top_similar_memories(self.agent_id, k=k)
                return [(memory.content, score) for memory, score in results]
            
            return []
            
        except Exception as e:
            print(f"Error getting top similar memories: {e}")
            print(f"Full traceback:")
            import traceback
            traceback.print_exc()
            return []
    
    def get_scored_memories(self, 
                           current_context: str, 
                           k: int = None,
                           salience_param: float = 1.0,
                           importance_param: float = 0.5,
                           time_decay_param: float = 1.0,
                           context_timestamp: Optional[datetime] = None) -> List[Tuple[str, float]]:
        """
        Get top k memories scored by relevance to current context.
        
        Args:
            current_context: Current context to compare against
            k: Number of results to return
            salience_param: Weight for semantic similarity
            importance_param: Weight for importance
            time_decay_param: Weight for recency decay
            context_timestamp: Timestamp for the context (defaults to current time)
            
        Returns:
            List of (content, score) tuples sorted by score
        """
        if self.db is None:
            return []
        
        # Use provided timestamp or current time
        if context_timestamp is None:
            context_timestamp = get_current_event_time()
        
        if k is None:
            k = self.memory_top_m_to_return
        
        try:
            if self.memory_system == 'advanced' and isinstance(self.db, QdrantMemoryDB):
                if EMBEDDING_AVAILABLE and USE_EMBEDDINGS:
                    try:
                        context_vector = get_text_embedding(current_context)
                        results = self.db.get_scored_memories(
                            context_vector, self.agent_id, k=k,
                            salience_param=salience_param,
                            importance_param=importance_param,
                            time_decay_param=time_decay_param
                        )
                        return [(memory.content, score) for memory, score in results]
                    except Exception as e:
                        print(f"Warning: Could not generate context embedding: {e}")
                        print(f"Full traceback:")
                        import traceback
                        traceback.print_exc()
                        # Fall back to text-based search
                        return self._fallback_text_search(current_context, k)
                else:
                    print("Warning: Embeddings not available for advanced memory scoring, using fallback")
                    return self._fallback_text_search(current_context, k)
            
            elif self.memory_system == 'simple' and isinstance(self.db, SimpleMemoryDB):
                results = self.db.get_scored_memories(
                    current_context, self.agent_id, k=k,
                    salience_param=salience_param,
                    importance_param=importance_param,
                    time_decay_param=time_decay_param
                )
                return [(memory.content, score) for memory, score in results]
            
            return []
            
        except Exception as e:
            print(f"Error getting scored memories: {e}")
            print(f"Full traceback:")
            import traceback
            traceback.print_exc()
            return []
    
    def close(self):
        """Close the database connection."""
        if self.db:
            try:
                self.db.close()
            except Exception as e:
                print(f"Error closing database: {e}")
                print(f"Full traceback:")
                import traceback
                traceback.print_exc()

    def reset_memory_system(self) -> bool:
        """
        Reset the memory system by clearing all memories.
        This is useful for starting fresh between simulation runs.

        Returns:
            bool: True if successful, False otherwise
        """
        if self.db is None:
            print("Warning: No memory database available to reset")
            return False

        try:
            if self.memory_system == 'advanced' and isinstance(self.db, QdrantMemoryDB):
                success = self.db.reset_collection()
                if success:
                    print(f"Reset Qdrant memory system for agent {self.agent_id}")
                return success

            elif self.memory_system == 'simple' and isinstance(self.db, SimpleMemoryDB):
                success = self.db.reset_collection()
                if success:
                    print(f"Reset simple memory system for agent {self.agent_id}")
                return success

            print(f"Warning: Memory system type '{self.memory_system}' doesn't support reset")
            return False

        except Exception as e:
            print(f"Error resetting memory system: {e}")
            print(f"Full traceback:")
            import traceback
            traceback.print_exc()
            return False

    def clear_memories(self) -> bool:
        """
        Clear all memories without recreating the collection structure.
        This is less destructive than reset_memory_system().

        Returns:
            bool: True if successful, False otherwise
        """
        if self.db is None:
            print("Warning: No memory database available to clear")
            return False

        try:
            if self.memory_system == 'advanced' and isinstance(self.db, QdrantMemoryDB):
                success = self.db.clear_collection()
                if success:
                    print(f"Cleared Qdrant memory system for agent {self.agent_id}")
                return success

            elif self.memory_system == 'simple' and isinstance(self.db, SimpleMemoryDB):
                success = self.db.clear_collection()
                if success:
                    print(f"Cleared simple memory system for agent {self.agent_id}")
                return success

            print(f"Warning: Memory system type '{self.memory_system}' doesn't support clear")
            return False

        except Exception as e:
            print(f"Error clearing memory system: {e}")
            print(f"Full traceback:")
            import traceback
            traceback.print_exc()
            return False

    def _fallback_text_search(self, query: str, k: int = 10) -> List[Tuple[str, float]]:
        """
        Fallback text search when embeddings are not available.
        Uses simple keyword matching to find relevant memories.

        Args:
            query: Search query string
            k: Number of results to return

        Returns:
            List of (content, score) tuples
        """
        if self.db is None:
            return []

        try:
            # Get all memories for this agent
            if self.memory_system == 'advanced' and isinstance(self.db, QdrantMemoryDB):
                memories = self.db.get_agent_memories(self.agent_id, limit=k*2)
            elif self.memory_system == 'simple' and isinstance(self.db, SimpleMemoryDB):
                memories = self.db.get_memories_by_agent(self.agent_id, limit=k*2)
            else:
                return []

            # Simple keyword matching
            query_words = set(query.lower().split())
            results = []

            for memory in memories:
                content_words = set(memory.content.lower().split())
                # Calculate simple overlap score
                if query_words and content_words:
                    overlap = len(query_words.intersection(content_words))
                    score = overlap / len(query_words.union(content_words))
                    results.append((memory.content, score))

            # Sort by score and return top k
            results.sort(key=lambda x: x[1], reverse=True)
            return results[:k]

        except Exception as e:
            print(f"Error in fallback text search: {e}")
            return []
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close() 