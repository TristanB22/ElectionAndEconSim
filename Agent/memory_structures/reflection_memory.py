import datetime
from typing import List, Optional, Dict, Any
import json
from .memory_record import MemoryRecord

class ReflectionRecord:
    """
    A reflection is a higher-level insight derived from multiple memories.
    It represents patterns, learnings, or important realizations.
    """
    
    def __init__(self,
                 reflection_text: str,
                 source_memories: List[MemoryRecord],
                 timestamp: Optional[datetime.datetime] = None,
                 importance: float = 8.0,
                 reflection_type: str = "daily_reflection"):
        """
        Initialize a reflection record.
        
        Args:
            reflection_text (str): The insight or reflection content
            source_memories (List[MemoryRecord]): Memories that led to this reflection
            timestamp (datetime): When this reflection was created
            importance (float): Importance score (reflections are typically important)
            reflection_type (str): Type of reflection ('daily', 'weekly', 'insight', 'goal')
        """
        self.reflection_text = reflection_text
        self.source_memories = source_memories
        self.timestamp = timestamp or datetime.datetime.now()
        self.importance = max(1.0, min(10.0, importance))
        self.reflection_type = reflection_type
        
        # Unique ID for this reflection
        self.id = f"reflection_{self.timestamp.isoformat()}_{hash(reflection_text) % 10000}"
        
        # Track how often this reflection is referenced
        self.reference_count = 0
        self.last_referenced = None
    
    def mark_referenced(self):
        """Mark this reflection as referenced (for tracking relevance)"""
        self.reference_count += 1
        self.last_referenced = datetime.datetime.now()
    
    def to_dict(self) -> dict:
        """Convert reflection to dictionary for serialization"""
        return {
            'id': self.id,
            'reflection_text': self.reflection_text,
            'source_memory_ids': [mem.id for mem in self.source_memories],
            'timestamp': self.timestamp.isoformat(),
            'importance': self.importance,
            'reflection_type': self.reflection_type,
            'reference_count': self.reference_count,
            'last_referenced': self.last_referenced.isoformat() if self.last_referenced else None
        }
    
    def __str__(self) -> str:
        return f"ReflectionRecord({self.timestamp.strftime('%Y-%m-%d')}, {self.reflection_type}): {self.reflection_text[:100]}..."


class ReflectionMemory:
    """
    Manages long-term reflections and insights derived from daily experiences.
    These are higher-level patterns and learnings that inform future behavior.
    """
    
    def __init__(self, max_reflections: int = 1000):
        """
        Initialize reflection memory store.
        
        Args:
            max_reflections (int): Maximum number of reflections to keep
        """
        self.reflections: List[ReflectionRecord] = []
        self.max_reflections = max_reflections
        
        # Categorized reflections
        self.daily_reflections: List[ReflectionRecord] = []
        self.weekly_reflections: List[ReflectionRecord] = []
        self.insights: List[ReflectionRecord] = []
        self.goal_reflections: List[ReflectionRecord] = []
        
        # Core principles and values (most stable reflections)
        self.core_principles: List[str] = []
        self.long_term_goals: List[str] = []
        
    def add_reflection(self, reflection: ReflectionRecord) -> None:
        """
        Add a new reflection to the store.
        
        Args:
            reflection (ReflectionRecord): The reflection to add
        """
        self.reflections.append(reflection)
        
        # Categorize by type
        if reflection.reflection_type == "daily_reflection":
            self.daily_reflections.append(reflection)
        elif reflection.reflection_type == "weekly_reflection":
            self.weekly_reflections.append(reflection)
        elif reflection.reflection_type == "insight":
            self.insights.append(reflection)
        elif reflection.reflection_type == "goal":
            self.goal_reflections.append(reflection)
        
        # Remove oldest reflections if we exceed the limit
        if len(self.reflections) > self.max_reflections:
            self._remove_oldest_reflection()
    
    def _remove_oldest_reflection(self) -> None:
        """Remove the oldest reflection"""
        if not self.reflections:
            return
            
        oldest_reflection = min(self.reflections, key=lambda r: r.timestamp)
        self.reflections.remove(oldest_reflection)
        
        # Remove from categorized lists
        for reflection_list in [self.daily_reflections, self.weekly_reflections, 
                              self.insights, self.goal_reflections]:
            if oldest_reflection in reflection_list:
                reflection_list.remove(oldest_reflection)
                break
    
    def get_recent_reflections(self, days: int = 7) -> List[ReflectionRecord]:
        """Get reflections from the last N days"""
        cutoff_time = datetime.datetime.now() - datetime.timedelta(days=days)
        return [r for r in self.reflections if r.timestamp >= cutoff_time]
    
    def get_reflections_by_type(self, reflection_type: str) -> List[ReflectionRecord]:
        """Get all reflections of a specific type"""
        return [r for r in self.reflections if r.reflection_type == reflection_type]
    
    def get_most_important_reflections(self, k: int = 10) -> List[ReflectionRecord]:
        """Get the k most important reflections"""
        sorted_reflections = sorted(self.reflections, key=lambda r: r.importance, reverse=True)
        return sorted_reflections[:k]
    
    def add_core_principle(self, principle: str) -> None:
        """Add a core principle or value"""
        if principle not in self.core_principles:
            self.core_principles.append(principle)
    
    def add_long_term_goal(self, goal: str) -> None:
        """Add a long-term goal"""
        if goal not in self.long_term_goals:
            self.long_term_goals.append(goal)
    
    def update_core_principles(self, principles: List[str]) -> None:
        """Update the list of core principles"""
        self.core_principles = principles
    
    def update_long_term_goals(self, goals: List[str]) -> None:
        """Update the list of long-term goals"""
        self.long_term_goals = goals
    
    def get_reflection_summary(self, days: int = 30) -> str:
        """
        Create a summary of recent reflections and core insights.
        
        Args:
            days (int): Number of days to look back
            
        Returns:
            str: Summary of reflections
        """
        recent_reflections = self.get_recent_reflections(days)
        
        summary_parts = []
        summary_parts.append(f"Reflection Summary (Last {days} days)")
        summary_parts.append(f"Total reflections: {len(recent_reflections)}")
        
        # Core principles
        if self.core_principles:
            summary_parts.append("\nCore Principles:")
            for i, principle in enumerate(self.core_principles, 1):
                summary_parts.append(f"  {i}. {principle}")
        
        # Long-term goals
        if self.long_term_goals:
            summary_parts.append("\nLong-term Goals:")
            for i, goal in enumerate(self.long_term_goals, 1):
                summary_parts.append(f"  {i}. {goal}")
        
        # Recent insights
        recent_insights = [r for r in recent_reflections if r.reflection_type == "insight"]
        if recent_insights:
            summary_parts.append(f"\nRecent Insights ({len(recent_insights)}):")
            for insight in recent_insights[-3:]:  # Last 3 insights
                summary_parts.append(f"  - {insight.reflection_text}")
        
        # Recent daily reflections
        recent_daily = [r for r in recent_reflections if r.reflection_type == "daily_reflection"]
        if recent_daily:
            summary_parts.append(f"\nRecent Daily Reflections ({len(recent_daily)}):")
            for reflection in recent_daily[-3:]:  # Last 3 daily reflections
                summary_parts.append(f"  - {reflection.reflection_text}")
        
        return "\n".join(summary_parts)
    
    def find_relevant_reflections(self, context: str, k: int = 5) -> List[ReflectionRecord]:
        """
        Find reflections relevant to a given context.
        This is a simple keyword-based search for now.
        
        Args:
            context (str): Context to search for
            k (int): Number of reflections to return
            
        Returns:
            List[ReflectionRecord]: Relevant reflections
        """
        # Simple keyword matching (could be enhanced with embeddings)
        context_words = context.lower().split()
        scored_reflections = []
        
        for reflection in self.reflections:
            reflection_words = reflection.reflection_text.lower().split()
            # Count matching words
            matches = sum(1 for word in context_words if word in reflection_words)
            if matches > 0:
                # Score based on matches and importance
                score = matches * reflection.importance
                scored_reflections.append((score, reflection))
        
        # Sort by score and return top k
        scored_reflections.sort(key=lambda x: x[0], reverse=True)
        return [reflection for _, reflection in scored_reflections[:k]]
    
    def save_to_file(self, filepath: str) -> None:
        """Save reflections to a JSON file"""
        data = {
            'reflections': [reflection.to_dict() for reflection in self.reflections],
            'core_principles': self.core_principles,
            'long_term_goals': self.long_term_goals,
            'max_reflections': self.max_reflections,
            'saved_at': datetime.datetime.now().isoformat()
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load_from_file(self, filepath: str, memory_store=None) -> None:
        """
        Load reflections from a JSON file.
        
        Args:
            filepath (str): Path to the JSON file
            memory_store: MemoryStore instance to reconstruct source memories
        """
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        self.reflections = []
        self.daily_reflections = []
        self.weekly_reflections = []
        self.insights = []
        self.goal_reflections = []
        
        # Reconstruct reflections
        for reflection_data in data['reflections']:
            # Reconstruct source memories if memory_store is provided
            source_memories = []
            if memory_store:
                for mem_id in reflection_data.get('source_memory_ids', []):
                    # Find memory by ID (simplified lookup)
                    for memory in memory_store.memories:
                        if memory.id == mem_id:
                            source_memories.append(memory)
                            break
            
            reflection = ReflectionRecord(
                reflection_text=reflection_data['reflection_text'],
                source_memories=source_memories,
                timestamp=datetime.datetime.fromisoformat(reflection_data['timestamp']),
                importance=reflection_data['importance'],
                reflection_type=reflection_data['reflection_type']
            )
            reflection.id = reflection_data['id']
            reflection.reference_count = reflection_data.get('reference_count', 0)
            if reflection_data.get('last_referenced'):
                reflection.last_referenced = datetime.datetime.fromisoformat(reflection_data['last_referenced'])
            
            self.add_reflection(reflection)
        
        # Load core principles and goals
        self.core_principles = data.get('core_principles', [])
        self.long_term_goals = data.get('long_term_goals', [])
        
        if 'max_reflections' in data:
            self.max_reflections = data['max_reflections']
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the reflection memory"""
        if not self.reflections:
            return {"total_reflections": 0}
        
        total_reflections = len(self.reflections)
        avg_importance = sum(r.importance for r in self.reflections) / total_reflections
        
        # Reflection type breakdown
        type_counts = {}
        for reflection in self.reflections:
            type_counts[reflection.reflection_type] = type_counts.get(reflection.reflection_type, 0) + 1
        
        # Time range
        oldest = min(self.reflections, key=lambda r: r.timestamp)
        newest = max(self.reflections, key=lambda r: r.timestamp)
        
        return {
            "total_reflections": total_reflections,
            "average_importance": avg_importance,
            "type_breakdown": type_counts,
            "core_principles_count": len(self.core_principles),
            "long_term_goals_count": len(self.long_term_goals),
            "oldest_reflection": oldest.timestamp.isoformat(),
            "newest_reflection": newest.timestamp.isoformat(),
            "time_span_days": (newest.timestamp - oldest.timestamp).days
        }
    
    def __len__(self) -> int:
        return len(self.reflections)
    
    def __str__(self) -> str:
        stats = self.get_statistics()
        return f"ReflectionMemory({stats['total_reflections']} reflections, {stats['core_principles_count']} principles, {stats['long_term_goals_count']} goals)" 