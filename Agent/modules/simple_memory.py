#!/usr/bin/env python3
"""
Simple Memory System for Agents

Provides a basic, file-based memory system using pickle for storage.
"""

import os
import pickle
import time
import numpy as np
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
import uuid
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer

# Try to import simulation time manager
try:
    from Environment.time_manager import get_current_simulation_datetime, get_current_simulation_timestamp
    SIMULATION_TIME_AVAILABLE = True
except ImportError:
    print("Warning: Simulation time manager not available, using computer time")
    SIMULATION_TIME_AVAILABLE = False


def get_current_timestamp() -> float:
    """Get current timestamp (simulation time if available, computer time as fallback)."""
    if SIMULATION_TIME_AVAILABLE:
        try:
            return get_current_simulation_timestamp()
        except Exception:
            return time.time()
    else:
        return time.time()


def get_current_datetime() -> datetime:
    """Get current datetime (simulation time if available, computer time as fallback)."""
    if SIMULATION_TIME_AVAILABLE:
        try:
            return get_current_simulation_datetime()
        except Exception:
            return datetime.now()
    else:
        return datetime.now()


@dataclass
class SimpleMemory:
    """Represents a single memory entry."""
    id: str
    agent_id: str
    content: str
    timestamp: datetime
    impact_score: int  # Memory salience score (1-10)
    vector: Optional[np.ndarray] = None


class SimpleMemoryDB:
    """
    Simple memory database using numpy arrays and cosine similarity.
    """
    
    def __init__(self, agent_id: str, db_path: str = "simple_memory.pkl"):
        """
        Initialize the simple memory database.
        
        Args:
            agent_id: Unique identifier for the agent
            db_path: Path to save/load memory data
        """
        self.agent_id = agent_id
        self.db_path = db_path
        self.memories: List[SimpleMemory] = []
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2)
        )
        self.vectors: Optional[np.ndarray] = None
        self.is_fitted = False
        
        # Load existing memories if available
        self._load_memories()
    
    def _load_memories(self):
        """Load memories from disk if available."""
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, 'rb') as f:
                    data = pickle.load(f)
                    self.memories = data.get('memories', [])
                    # Re-fit vectorizer with existing memories
                    if self.memories:
                        self._fit_vectorizer()
                print(f"Loaded {len(self.memories)} existing memories")
            except Exception as e:
                print(f"Warning: Could not load existing memories: {e}")
                print(f"Full traceback:")
                import traceback
                traceback.print_exc()
                self.memories = []
    
    def _save_memories(self):
        """Save memories to disk."""
        try:
            data = {
                'memories': self.memories,
                'agent_id': self.agent_id,
                'timestamp': get_current_datetime()
            }
            with open(self.db_path, 'wb') as f:
                pickle.dump(data, f)
        except Exception as e:
            print(f"Warning: Could not save memories: {e}")
            print(f"Full traceback:")
            import traceback
            traceback.print_exc()
    
    def _fit_vectorizer(self):
        """Fit the vectorizer with all memory contents."""
        if not self.memories:
            return
        
        contents = [memory.content for memory in self.memories]
        self.vectors = self.vectorizer.fit_transform(contents).toarray()
        self.is_fitted = True
    
    def _update_vectors(self):
        """Update vectors when new memories are added."""
        if not self.memories:
            return
        
        contents = [memory.content for memory in self.memories]
        self.vectors = self.vectorizer.fit_transform(contents).toarray()
        self.is_fitted = True
    
    def add_memory(self, memory: SimpleMemory) -> bool:
        """
        Add a memory to the database.
        
        Args:
            memory: Memory object to add
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Add memory to list
            self.memories.append(memory)
            
            # Update vectors
            self._update_vectors()
            
            # Save to disk
            self._save_memories()
            
            return True
            
        except Exception as e:
            print(f"Error adding memory: {e}")
            print(f"Full traceback:")
            import traceback
            traceback.print_exc()
            return False
    
    def search_memories(self, 
                       query: str, 
                       agent_id: Optional[str] = None,
                       k: int = 10) -> List[Tuple[SimpleMemory, float]]:
        """
        Search for memories similar to the query.
        
        Args:
            query: Search query
            agent_id: Filter by agent ID (optional)
            k: Number of results to return
            
        Returns:
            List of (Memory, similarity_score) tuples
        """
        if not self.is_fitted or self.vectors is None:
            return []
        
        try:
            # Vectorize query
            query_vector = self.vectorizer.transform([query]).toarray()
            
            # Calculate cosine similarities
            similarities = cosine_similarity(query_vector, self.vectors)[0]
            
            # Create memory-similarity pairs
            memory_similarities = list(zip(self.memories, similarities))
            
            # Filter by agent_id if specified
            if agent_id:
                memory_similarities = [
                    (memory, sim) for memory, sim in memory_similarities 
                    if memory.agent_id == agent_id
                ]
            
            # Sort by similarity and return top k
            memory_similarities.sort(key=lambda x: x[1], reverse=True)
            return memory_similarities[:k]
            
        except Exception as e:
            print(f"Error searching memories: {e}")
            return []
    
    def get_top_similar_memories(self, agent_id: str, k: int = 7) -> List[Tuple[SimpleMemory, float]]:
        """
        Get the top k most similar memories for an agent.
        
        Args:
            agent_id: The agent ID
            k: Number of results to return
            
        Returns:
            List of (Memory, similarity_score) tuples
        """
        if not self.is_fitted or self.vectors is None:
            return []
        
        try:
            # Get agent's memories
            agent_memories = [memory for memory in self.memories if memory.agent_id == agent_id]
            
            if len(agent_memories) < 2:
                return [(memory, 1.0) for memory in agent_memories]
            
            # Calculate similarities between all agent memories
            agent_indices = [i for i, memory in enumerate(self.memories) if memory.agent_id == agent_id]
            agent_vectors = self.vectors[agent_indices]
            
            # Calculate average similarity to other memories
            similarities = []
            for i, memory in enumerate(agent_memories):
                # Calculate similarity to all other agent memories
                other_vectors = np.vstack([agent_vectors[:i], agent_vectors[i+1:]])
                if len(other_vectors) > 0:
                    sims = cosine_similarity([agent_vectors[i]], other_vectors)[0]
                    avg_sim = np.mean(sims)
                else:
                    avg_sim = 0.0
                similarities.append((memory, avg_sim))
            
            # Sort by similarity and return top k
            similarities.sort(key=lambda x: x[1], reverse=True)
            return similarities[:k]
            
        except Exception as e:
            print(f"Error getting top similar memories: {e}")
            return []
    
    def get_scored_memories(self, 
                           current_context: str, 
                           agent_id: str, 
                           k: int = 7,
                           salience_param: float = 1.0,
                           importance_param: float = 0.5,
                           time_decay_param: float = 1.0) -> List[Tuple[SimpleMemory, float]]:
        """
        Get top k memories scored by the equation:
        score(m) = salience_param⋅semantic_similarity(m,current_context) + 
                   time_decay_param⋅recency_decay(m) + 
                   importance_param⋅importance(m)
        
        Args:
            current_context: The current context to compare against
            agent_id: The agent ID to search for
            k: Number of results to return
            salience_param: Weight for semantic similarity
            importance_param: Weight for importance
            time_decay_param: Weight for recency decay
            
        Returns:
            List of (Memory, score) tuples sorted by score
        """
        if not self.is_fitted or self.vectors is None:
            return []
        
        try:
            # Get agent's memories
            agent_memories = [memory for memory in self.memories if memory.agent_id == agent_id]
            
            if not agent_memories:
                return []
            
            # Vectorize current context
            context_vector = self.vectorizer.transform([current_context]).toarray()
            
            # Get agent memory indices and vectors
            agent_indices = [i for i, memory in enumerate(self.memories) if memory.agent_id == agent_id]
            agent_vectors = self.vectors[agent_indices]
            
            current_time = get_current_datetime()
            scored_memories = []
            
            for memory, memory_vector in zip(agent_memories, agent_vectors):
                # 1. Semantic similarity
                semantic_sim = cosine_similarity([context_vector[0]], [memory_vector])[0][0]
                
                # 2. Recency decay (exponential decay with time_decay_param)
                time_diff = (current_time - memory.timestamp).total_seconds()
                recency_decay = np.exp(-time_diff / time_decay_param)
                
                # 3. Importance (normalized impact score)
                importance = memory.impact_score / 10.0
                
                # Calculate final score
                score = salience_param * semantic_sim + time_decay_param * recency_decay + importance_param * importance
                
                scored_memories.append((memory, score))
            
            # Sort by score and return top k
            scored_memories.sort(key=lambda x: x[1], reverse=True)
            return scored_memories[:k]
            
        except Exception as e:
            print(f"Error getting scored memories: {e}")
            return []
    
    def get_memories_by_agent(self, agent_id: str) -> List[SimpleMemory]:
        """
        Get all memories for a specific agent.
        
        Args:
            agent_id: The agent ID
            
        Returns:
            List of memories for the agent
        """
        return [memory for memory in self.memories if memory.agent_id == agent_id]
    
    def get_memory_count(self) -> int:
        """Get the total number of memories."""
        return len(self.memories)
    
    def clear_agent_memories(self, agent_id: str) -> bool:
        """
        Clear all memories for a specific agent.
        
        Args:
            agent_id: ID of the agent whose memories to clear
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Filter out memories for the specified agent
            original_count = len(self.memories)
            self.memories = [m for m in self.memories if m.agent_id != agent_id]
            cleared_count = original_count - len(self.memories)
            
            if cleared_count > 0:
                # Re-fit vectorizer with remaining memories
                self._fit_vectorizer()
                # Save updated memories
                self._save_memories()
                print(f"Cleared {cleared_count} memories for agent {agent_id}")
            
            return True
            
        except Exception as e:
            print(f"Error clearing memories for agent {agent_id}: {e}")
            return False
    
    def close(self):
        """Close the database and save memories."""
        self._save_memories()

    def clear_collection(self) -> bool:
        """
        Clear all memories from the database.
        This removes all memories but keeps the database file.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.memories = []
            self.vectors = None
            self.is_fitted = False
            self._save_memories()
            print("Cleared all memories from simple memory database")
            return True
        except Exception as e:
            print(f"Error clearing collection: {e}")
            return False

    def reset_collection(self) -> bool:
        """
        Reset the database by clearing all memories and recreating the file.
        This is useful for starting fresh between simulation runs.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Remove the database file if it exists
            if os.path.exists(self.db_path):
                os.remove(self.db_path)
                print(f"Deleted memory database file '{self.db_path}'")

            # Reset in-memory state
            self.memories = []
            self.vectors = None
            self.is_fitted = False

            print("Reset simple memory database")
            return True
        except Exception as e:
            print(f"Error resetting collection: {e}")
            return False

    def search_memories_enhanced(self, query_vector: List[float], agent_id: str, k: int = 10) -> List[SimpleMemory]:
        """
        Enhanced search for memories (alias for regular search for compatibility).

        Args:
            query_vector: Query vector for similarity search
            agent_id: ID of the agent to search memories for
            k: Maximum number of results

        Returns:
            List of SimpleMemory objects
        """
        return self.search_memories(query_vector, agent_id, k)

    def get_scored_memories(self, query_text: str, agent_id: str, k: int = 10,
                           salience_param: float = 1.0, importance_param: float = 0.5,
                           time_decay_param: float = 1.0) -> List[Tuple[SimpleMemory, float]]:
        """
        Get memories with enhanced scoring based on multiple factors.

        Args:
            query_text: Query text for similarity search
            agent_id: ID of the agent
            k: Number of results to return
            salience_param: Weight for semantic similarity
            importance_param: Weight for importance
            time_decay_param: Weight for recency decay

        Returns:
            List of (SimpleMemory, score) tuples
        """
        try:
            # Get basic search results
            memories_scores = self.search_memories(query_text, agent_id, k)

            # Apply enhanced scoring
            scored_memories = []
            current_time = get_current_timestamp()

            for memory, similarity_score in memories_scores:
                # Use the similarity score as semantic score
                semantic_score = similarity_score

                # Calculate importance score
                importance_score = memory.impact_score

                # Calculate time decay score (more recent = higher score)
                time_diff = current_time - memory.timestamp
                time_decay_score = max(0, 1.0 - (time_diff / 86400))  # Decay over 24 hours

                # Combined score
                total_score = (salience_param * semantic_score +
                             importance_param * importance_score +
                             time_decay_param * time_decay_score)

                scored_memories.append((memory, total_score))

            # Sort by score (descending)
            scored_memories.sort(key=lambda x: x[1], reverse=True)

            return scored_memories[:k]

        except Exception as e:
            print(f"Error getting scored memories: {e}")
            return []

    def get_top_similar_memories(self, agent_id: str, k: int = 10) -> List[Tuple[SimpleMemory, float]]:
        """
        Get the top k most similar memories for an agent.

        Args:
            agent_id: ID of the agent
            k: Number of results to return

        Returns:
            List of (SimpleMemory, similarity_score) tuples
        """
        try:
            # Get all memories for the agent
            memories = self.get_memories_by_agent(agent_id, limit=k*2)  # Get more to find similar ones

            if len(memories) < 2:
                return []

            # Find similar memories by comparing content
            scored_memories = []
            for i, memory1 in enumerate(memories):
                for memory2 in memories[i+1:]:
                    # Simple similarity based on content overlap
                    content1 = memory1.content.lower()
                    content2 = memory2.content.lower()

                    # Calculate simple similarity score
                    words1 = set(content1.split())
                    words2 = set(content2.split())

                    if words1 or words2:
                        similarity = len(words1.intersection(words2)) / len(words1.union(words2))
                        scored_memories.append((memory1, similarity))

            # Sort by similarity and return top k
            scored_memories.sort(key=lambda x: x[1], reverse=True)
            return scored_memories[:k]

        except Exception as e:
            print(f"Error getting top similar memories: {e}")
            return []


def create_memory_id() -> str:
    """Create a unique memory ID."""
    return str(uuid.uuid4()) 