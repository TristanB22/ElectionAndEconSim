import datetime
from typing import List, Optional, Dict, Any
import numpy as np
import json
from .memory_record import MemoryRecord

class MemoryStore:
    """
    Manages a collection of memory records with retrieval and persistence capabilities.
    Implements semantic search using embeddings and hybrid scoring.
    """
    
    def __init__(self, max_memories: int = 10000):
        """
        Initialize memory store.
        
        Args:
            max_memories (int): Maximum number of memories to keep
        """
        self.memories: List[MemoryRecord] = []
        self.max_memories = max_memories
        
        # Indices for efficient retrieval
        self.importance_index: Dict[str, List[MemoryRecord]] = {}
        self.source_index: Dict[str, List[MemoryRecord]] = {}
        self.keyword_index: Dict[str, List[MemoryRecord]] = {}
        
    def add_memory(self, memory: MemoryRecord) -> None:
        """
        Add a new memory to the store.
        
        Args:
            memory (MemoryRecord): The memory to add
        """
        self.memories.append(memory)
        
        # Update indices
        self._update_indices(memory)
        
        # Remove oldest memories if we exceed the limit
        if len(self.memories) > self.max_memories:
            self._remove_oldest_memory()
    
    def _update_indices(self, memory: MemoryRecord) -> None:
        """Update internal indices for efficient retrieval"""
        # Importance index (bucketed by importance level)
        importance_level = f"{int(memory.importance)}"
        if importance_level not in self.importance_index:
            self.importance_index[importance_level] = []
        self.importance_index[importance_level].append(memory)
        
        # Source index
        if memory.source not in self.source_index:
            self.source_index[memory.source] = []
        self.source_index[memory.source].append(memory)
        
        # Keyword index
        for keyword in memory.keywords:
            if keyword not in self.keyword_index:
                self.keyword_index[keyword] = []
            self.keyword_index[keyword].append(memory)
    
    def _remove_oldest_memory(self) -> None:
        """Remove the oldest memory and update indices"""
        if not self.memories:
            return
            
        # Find the oldest memory
        oldest_memory = min(self.memories, key=lambda m: m.timestamp)
        self.memories.remove(oldest_memory)
        
        # Remove from indices
        importance_level = f"{int(oldest_memory.importance)}"
        if importance_level in self.importance_index:
            if oldest_memory in self.importance_index[importance_level]:
                self.importance_index[importance_level].remove(oldest_memory)
        
        if oldest_memory.source in self.source_index:
            if oldest_memory in self.source_index[oldest_memory.source]:
                self.source_index[oldest_memory.source].remove(oldest_memory)
        
        for keyword in oldest_memory.keywords:
            if keyword in self.keyword_index:
                if oldest_memory in self.keyword_index[keyword]:
                    self.keyword_index[keyword].remove(oldest_memory)
    
    def retrieve_memories(self, 
                         query: str = None,
                         query_embedding: Optional[np.ndarray] = None,
                         k: int = 10,
                         importance_threshold: float = 0.0,
                         source_filter: Optional[List[str]] = None,
                         time_range: Optional[tuple] = None,
                         keywords: Optional[List[str]] = None) -> List[MemoryRecord]:
        """
        Retrieve the most relevant memories based on various criteria.
        
        Args:
            query (str): Text query for semantic similarity
            query_embedding (np.ndarray): Pre-computed embedding for the query
            k (int): Number of memories to retrieve
            importance_threshold (float): Minimum importance score
            source_filter (List[str]): Only include memories from these sources
            time_range (tuple): (start_time, end_time) to filter by timestamp
            keywords (List[str]): Keywords that must be present
            
        Returns:
            List[MemoryRecord]: Top k most relevant memories
        """
        # Start with all memories
        candidates = list(self.memories)
        
        # Apply filters
        if importance_threshold > 0:
            candidates = [m for m in candidates if m.importance >= importance_threshold]
        
        if source_filter:
            candidates = [m for m in candidates if m.source in source_filter]
        
        if time_range:
            start_time, end_time = time_range
            candidates = [m for m in candidates if start_time <= m.timestamp <= end_time]
        
        if keywords:
            candidates = [m for m in candidates 
                         if any(kw in m.keywords for kw in keywords)]
        
        # If no candidates, return empty list
        if not candidates:
            return []
        
        # Calculate relevance scores if we have a query
        current_time = datetime.datetime.now()
        scored_memories = []
        
        for memory in candidates:
            # Mark as accessed for recency tracking
            memory.mark_accessed()
            
            # Calculate composite score
            score = memory.get_composite_score(current_time, query_embedding)
            scored_memories.append((score, memory))
        
        # Sort by score (descending) and return top k
        scored_memories.sort(key=lambda x: x[0], reverse=True)
        return [memory for _, memory in scored_memories[:k]]
    
    def get_memories_by_timeframe(self, 
                                 start_time: datetime.datetime,
                                 end_time: datetime.datetime) -> List[MemoryRecord]:
        """Get all memories within a specific timeframe"""
        return [m for m in self.memories 
                if start_time <= m.timestamp <= end_time]
    
    def get_memories_by_source(self, source: str) -> List[MemoryRecord]:
        """Get all memories from a specific source"""
        return self.source_index.get(source, [])
    
    def get_recent_memories(self, hours: int = 24) -> List[MemoryRecord]:
        """Get memories from the last N hours"""
        cutoff_time = datetime.datetime.now() - datetime.timedelta(hours=hours)
        return [m for m in self.memories if m.timestamp >= cutoff_time]
    
    def get_important_memories(self, min_importance: float = 7.0) -> List[MemoryRecord]:
        """Get memories above a certain importance threshold"""
        return [m for m in self.memories if m.importance >= min_importance]
    
    def summarize_period(self, 
                        start_time: datetime.datetime,
                        end_time: datetime.datetime) -> str:
        """
        Create a summary of memories from a specific time period.
        
        Args:
            start_time (datetime): Start of the period
            end_time (datetime): End of the period
            
        Returns:
            str: Summary of the period's memories
        """
        period_memories = self.get_memories_by_timeframe(start_time, end_time)
        
        if not period_memories:
            return f"No memories from {start_time.strftime('%Y-%m-%d %H:%M')} to {end_time.strftime('%Y-%m-%d %H:%M')}"
        
        # Group by source
        by_source = {}
        for memory in period_memories:
            if memory.source not in by_source:
                by_source[memory.source] = []
            by_source[memory.source].append(memory)
        
        summary_parts = []
        summary_parts.append(f"Period: {start_time.strftime('%Y-%m-%d %H:%M')} to {end_time.strftime('%Y-%m-%d %H:%M')}")
        summary_parts.append(f"Total memories: {len(period_memories)}")
        
        for source, memories in by_source.items():
            summary_parts.append(f"\n{source.title()} ({len(memories)} memories):")
            # Get the most important memories from this source
            important_memories = sorted(memories, key=lambda m: m.importance, reverse=True)[:3]
            for memory in important_memories:
                summary_parts.append(f"  - {memory.text[:100]}...")
        
        return "\n".join(summary_parts)
    
    def save_to_file(self, filepath: str) -> None:
        """Save all memories to a JSON file"""
        data = {
            'memories': [memory.to_dict() for memory in self.memories],
            'max_memories': self.max_memories,
            'saved_at': datetime.datetime.now().isoformat()
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load_from_file(self, filepath: str) -> None:
        """Load memories from a JSON file"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        self.memories = []
        self.importance_index = {}
        self.source_index = {}
        self.keyword_index = {}
        
        for memory_data in data['memories']:
            memory = MemoryRecord.from_dict(memory_data)
            self.add_memory(memory)
        
        if 'max_memories' in data:
            self.max_memories = data['max_memories']
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the memory store"""
        if not self.memories:
            return {"total_memories": 0}
        
        total_memories = len(self.memories)
        avg_importance = sum(m.importance for m in self.memories) / total_memories
        
        # Memory sources breakdown
        source_counts = {}
        for memory in self.memories:
            source_counts[memory.source] = source_counts.get(memory.source, 0) + 1
        
        # Time range
        oldest = min(self.memories, key=lambda m: m.timestamp)
        newest = max(self.memories, key=lambda m: m.timestamp)
        
        return {
            "total_memories": total_memories,
            "average_importance": avg_importance,
            "source_breakdown": source_counts,
            "oldest_memory": oldest.timestamp.isoformat(),
            "newest_memory": newest.timestamp.isoformat(),
            "time_span_days": (newest.timestamp - oldest.timestamp).days
        }
    
    def __len__(self) -> int:
        return len(self.memories)
    
    def __str__(self) -> str:
        stats = self.get_statistics()
        return f"MemoryStore({stats['total_memories']} memories, avg_importance={stats.get('average_importance', 0):.1f})" 