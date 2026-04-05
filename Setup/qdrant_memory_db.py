#!/usr/bin/env python3
"""
Qdrant Memory Database Implementation
Handles vector-based memory storage and retrieval for agents.
"""

import os
import time
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, Union, Tuple
from dataclasses import dataclass, asdict
import json

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models
    from qdrant_client.http.models import Distance, VectorParams, PointStruct
    QDRANT_CLIENT_AVAILABLE = True
except ImportError:
    print("Warning: qdrant-client not available. Install with: pip install qdrant-client")
    QdrantClient = None
    models = None
    Distance = None
    VectorParams = None
    PointStruct = None
    QDRANT_CLIENT_AVAILABLE = False

@dataclass
class Memory:
    """Memory object for storing agent memories."""
    memory_id: str
    agent_id: str
    content: str
    memory_type: str
    importance: float
    timestamp: float
    created_at: float
    event_type: str = "general"
    environment: str = "unknown"
    location: str = "unknown"
    source: str = "agent"
    target: str = "self"
    participants: List[str] = None
    emotional_state: str = "neutral"
    impact_score: float = 0.0
    analysis_type: str = "automatic"
    personal_significance: float = 0.0
    personal_narrative: str = ""
    context_description: str = ""
    learning_outcome: str = ""
    future_implications: str = ""
    context_tags: List[str] = None
    vector_embedding: Optional[List[float]] = None

    def __post_init__(self):
        if self.participants is None:
            self.participants = []
        if self.context_tags is None:
            self.context_tags = []

def create_memory_id() -> str:
    """Create a unique memory ID."""
    return str(uuid.uuid4())

class QdrantMemoryDB:
    """Qdrant-based memory database for agents."""
    
    def __init__(self, host: str = "localhost", port: int = 1002, collection_name: str = "agent_memories"):
        """
        Initialize Qdrant memory database.
        
        Args:
            host: Qdrant server host
            port: Qdrant server port
            collection_name: Name of the collection to use
        """
        if not QDRANT_CLIENT_AVAILABLE:
            raise ImportError("qdrant-client not available. Install with: pip install qdrant-client")
        
        self.host = host
        self.port = port
        self.collection_name = collection_name
        self.client = None
        self.vector_size = 384  # Default embedding size
        
        self._connect()
        self._ensure_collection()
    
    def _connect(self):
        """Connect to Qdrant server."""
        try:
            self.client = QdrantClient(host=self.host, port=self.port)
            # Test connection
            self.client.get_collections()
            # Connection successful (silent)
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Qdrant at {self.host}:{self.port}: {e}")
    
    def _ensure_collection(self):
        """Ensure the collection exists with proper configuration."""
        try:
            collections = self.client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            if self.collection_name not in collection_names:
                # Creating collection (silent)
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=Distance.COSINE
                    )
                )
            # Collection ready (silent)
                
        except Exception as e:
            raise RuntimeError(f"Failed to ensure collection {self.collection_name}: {e}")
    
    def add_memory(self, memory: Memory) -> bool:
        """
        Add a memory to the database.
        
        Args:
            memory: Memory object to add
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if memory.vector_embedding is None:
                print("Warning: Memory has no vector embedding, skipping vector storage")
                return False
            
            vector = memory.vector_embedding
            if len(vector) != self.vector_size:
                print(f"Warning: Vector size {len(vector)} doesn't match expected size {self.vector_size}")
                return False
            
            point = PointStruct(
                id=memory.memory_id,
                vector=vector,
                payload={
                    "agent_id": memory.agent_id,
                    "content": memory.content,
                    "memory_type": memory.memory_type,
                    "importance": memory.importance,
                    "timestamp": memory.timestamp,
                    "created_at": memory.created_at,
                    "event_type": memory.event_type,
                    "environment": memory.environment,
                    "location": memory.location,
                    "source": memory.source,
                    "target": memory.target,
                    "participants": memory.participants,
                    "emotional_state": memory.emotional_state,
                    "impact_score": memory.impact_score,
                    "analysis_type": memory.analysis_type,
                    "personal_significance": memory.personal_significance,
                    "personal_narrative": memory.personal_narrative,
                    "context_description": memory.context_description,
                    "learning_outcome": memory.learning_outcome,
                    "future_implications": memory.future_implications,
                    "context_tags": memory.context_tags,
                    "content": memory.personal_narrative,
                    "created_at": datetime.fromtimestamp(memory.created_at).isoformat()
                }
            )
            
            self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
            
            return True
            
        except Exception as e:
            print(f"Error adding memory: {e}")
            return False
    
    def search_memories(self, agent_id: str, query_vector: List[float], limit: int = 10) -> List[Memory]:
        """
        Search for memories using vector similarity.
        
        Args:
            agent_id: ID of the agent to search memories for
            query_vector: Query vector for similarity search
            limit: Maximum number of results
            
        Returns:
            List of Memory objects
        """
        try:
            if len(query_vector) != self.vector_size:
                print(f"Warning: Query vector size {len(query_vector)} doesn't match expected size {self.vector_size}")
                return []
            
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                query_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="agent_id",
                            match=models.MatchValue(value=agent_id)
                        )
                    ]
                ),
                limit=limit
            )
            
            memories = []
            for result in results:
                payload = result.payload
                memory = Memory(
                    memory_id=result.id,
                    agent_id=payload.get("agent_id", ""),
                    content=payload.get("content", ""),
                    memory_type=payload.get("memory_type", "general"),
                    importance=payload.get("importance", 0.0),
                    timestamp=payload.get("timestamp", 0.0),
                    created_at=payload.get("created_at", 0.0),
                    event_type=payload.get("event_type", "general"),
                    environment=payload.get("environment", "unknown"),
                    location=payload.get("location", "unknown"),
                    source=payload.get("source", "agent"),
                    target=payload.get("target", "self"),
                    participants=payload.get("participants", []),
                    emotional_state=payload.get("emotional_state", "neutral"),
                    impact_score=payload.get("impact_score", 0.0),
                    analysis_type=payload.get("analysis_type", "automatic"),
                    personal_significance=payload.get("personal_significance", 0.0),
                    personal_narrative=payload.get("personal_narrative", ""),
                    context_description=payload.get("context_description", ""),
                    learning_outcome=payload.get("learning_outcome", ""),
                    future_implications=payload.get("future_implications", ""),
                    context_tags=payload.get("context_tags", []),
                    vector_embedding=result.vector
                )
                memories.append(memory)
            
            return memories
            
        except Exception as e:
            print(f"Error searching memories: {e}")
            return []
    
    def get_agent_memories(self, agent_id: str, limit: int = 100) -> List[Memory]:
        """
        Get all memories for a specific agent.
        
        Args:
            agent_id: ID of the agent
            limit: Maximum number of memories to return
            
        Returns:
            List of Memory objects
        """
        try:
            results = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="agent_id",
                            match=models.MatchValue(value=agent_id)
                        )
                    ]
                ),
                limit=limit
            )
            
            memories = []
            for point in results[0]:  # results is a tuple (points, next_page_offset)
                payload = point.payload
                memory = Memory(
                    memory_id=point.id,
                    agent_id=payload.get("agent_id", ""),
                    content=payload.get("content", ""),
                    memory_type=payload.get("memory_type", "general"),
                    importance=payload.get("importance", 0.0),
                    timestamp=payload.get("timestamp", 0.0),
                    created_at=payload.get("created_at", 0.0),
                    event_type=payload.get("event_type", "general"),
                    environment=payload.get("environment", "unknown"),
                    location=payload.get("location", "unknown"),
                    source=payload.get("source", "agent"),
                    target=payload.get("target", "self"),
                    participants=payload.get("participants", []),
                    emotional_state=payload.get("emotional_state", "neutral"),
                    impact_score=payload.get("impact_score", 0.0),
                    analysis_type=payload.get("analysis_type", "automatic"),
                    personal_significance=payload.get("personal_significance", 0.0),
                    personal_narrative=payload.get("personal_narrative", ""),
                    context_description=payload.get("context_description", ""),
                    learning_outcome=payload.get("learning_outcome", ""),
                    future_implications=payload.get("future_implications", ""),
                    context_tags=payload.get("context_tags", []),
                    vector_embedding=point.vector
                )
                memories.append(memory)
            
            return memories
            
        except Exception as e:
            print(f"Error getting agent memories: {e}")
            return []
    
    def delete_memory(self, memory_id: str) -> bool:
        """
        Delete a memory by ID.
        
        Args:
            memory_id: ID of the memory to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.PointIdsList(points=[memory_id])
            )
            return True
        except Exception as e:
            print(f"Error deleting memory: {e}")
            return False
    
    def get_memory_count(self) -> int:
        """
        Get the total number of memories in the database.
        
        Returns:
            int: Number of memories stored
        """
        try:
            collection_info = self.client.get_collection(self.collection_name)
            return collection_info.points_count
        except Exception as e:
            print(f"Error getting memory count: {e}")
            return 0
    
    def health_check(self) -> bool:
        """Check if the database is healthy."""
        try:
            self.client.get_collections()
            return True
        except Exception:
            return False

    def clear_collection(self) -> bool:
        """
        Clear all memories from the current collection.
        This removes all points but keeps the collection structure.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Delete all points in the collection
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[]  # Empty filter matches all points
                    )
                )
            )
            print(f"Cleared all memories from collection '{self.collection_name}'")
            return True
        except Exception as e:
            print(f"Error clearing collection: {e}")
            return False

    def reset_collection(self) -> bool:
        """
        Reset the collection by deleting and recreating it.
        This is useful for starting fresh between simulation runs.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Delete the collection if it exists
            try:
                self.client.delete_collection(self.collection_name)
                print(f"Deleted collection '{self.collection_name}'")
            except Exception:
                # Collection might not exist, that's okay
                pass
            # Recreate the collection
            self._ensure_collection()
            print(f"Reset collection '{self.collection_name}'")
            return True
        except Exception as e:
            print(f"Error resetting collection: {e}")
            return False

    def search_memories_enhanced(self, query_vector: List[float], agent_id: str, k: int = 10) -> List[Memory]:
        """
        Enhanced search for memories using vector similarity with agent filtering.

        Args:
            query_vector: Query vector for similarity search
            agent_id: ID of the agent to search memories for
            k: Maximum number of results

        Returns:
            List of Memory objects
        """
        return self.search_memories(agent_id, query_vector, k)

    def get_scored_memories(self, query_vector: List[float], agent_id: str, k: int = 10,
                          salience_param: float = 1.0, importance_param: float = 0.5,
                          time_decay_param: float = 1.0) -> List[Tuple[Memory, float]]:
        """
        Get memories with enhanced scoring based on multiple factors.

        Args:
            query_vector: Query vector for similarity search
            agent_id: ID of the agent
            k: Number of results to return
            salience_param: Weight for semantic similarity
            importance_param: Weight for importance
            time_decay_param: Weight for recency decay

        Returns:
            List of (Memory, score) tuples
        """
        try:
            # Get basic search results
            memories = self.search_memories(agent_id, query_vector, k)

            # Apply enhanced scoring
            scored_memories = []
            current_time = time.time()

            for memory in memories:
                # Calculate semantic similarity score (from search results)
                semantic_score = 1.0  # Placeholder - would come from search results

                # Calculate importance score
                importance_score = memory.importance

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

    def get_top_similar_memories(self, agent_id: str, k: int = 10) -> List[Tuple[Memory, float]]:
        """
        Get the top k most similar memories for an agent.

        Args:
            agent_id: ID of the agent
            k: Number of results to return

        Returns:
            List of (Memory, similarity_score) tuples
        """
        try:
            # Get all memories for the agent
            memories = self.get_agent_memories(agent_id, limit=k*2)  # Get more to find similar ones

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

    def close(self):
        """Close the database connection."""
        if self.client:
            try:
                self.client.close()
            except Exception as e:
                print(f"Error closing database: {e}")

