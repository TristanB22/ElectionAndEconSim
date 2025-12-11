import datetime
from typing import Optional, List, Any
import numpy as np

class MemoryRecord:
    """
    A single memory record that contains an observation, conversation, or reflection
    with associated metadata and embedding for retrieval.
    """
    
    def __init__(self,
                 text: str,
                 timestamp: Optional[datetime.datetime] = None,
                 importance: float = 5.0,
                 source: str = "observation",
                 embedding: Optional[np.ndarray] = None,
                 associated_event: Optional[str] = None,
                 keywords: Optional[List[str]] = None):
        """
        Initialize a memory record.
        
        Args:
            text (str): The textual content of the memory
            timestamp (datetime): When this memory was created
            importance (float): Importance score 1-10 (10 being most important)
            source (str): Source of memory ('observation', 'conversation', 'reflection', 'plan')
            embedding (np.ndarray): Vector embedding of the text
            associated_event (str): Event this memory is associated with
            keywords (List[str]): Key words/concepts in this memory
        """
        self.text = text
        self.timestamp = timestamp or datetime.datetime.now()
        self.importance = max(1.0, min(10.0, importance))  # Clamp between 1-10
        self.source = source
        self.embedding = embedding
        self.associated_event = associated_event
        self.keywords = keywords or []
        
        # Unique ID for this memory
        self.id = f"{self.timestamp.isoformat()}_{hash(text) % 10000}"
        
        # Access tracking
        self.access_count = 0
        self.last_accessed = None
        
    def mark_accessed(self):
        """Mark this memory as accessed (for recency weighting)"""
        self.access_count += 1
        self.last_accessed = datetime.datetime.now()
    
    def get_recency_score(self, current_time: Optional[datetime.datetime] = None) -> float:
        """
        Calculate recency score (higher = more recent)
        Decays exponentially with time
        """
        if current_time is None:
            current_time = datetime.datetime.now()
            
        time_diff = (current_time - self.timestamp).total_seconds()
        # Decay with half-life of 1 day (86400 seconds)
        recency = np.exp(-time_diff / 86400)
        return recency
    
    def get_composite_score(self, current_time: Optional[datetime.datetime] = None, 
                          query_embedding: Optional[np.ndarray] = None) -> float:
        """
        Calculate composite retrieval score combining importance, recency, and relevance
        """
        # Base importance score (normalized 0-1)
        importance_score = self.importance / 10.0
        
        # Recency score
        recency_score = self.get_recency_score(current_time)
        
        # Relevance score (cosine similarity with query)
        relevance_score = 0.0
        if query_embedding is not None and self.embedding is not None:
            # Cosine similarity
            dot_product = np.dot(self.embedding, query_embedding)
            norm_a = np.linalg.norm(self.embedding)
            norm_b = np.linalg.norm(query_embedding)
            if norm_a > 0 and norm_b > 0:
                relevance_score = dot_product / (norm_a * norm_b)
        
        # Weighted combination (can adjust these weights)
        composite = (0.5 * relevance_score + 0.3 * importance_score + 0.2 * recency_score)
        return composite
    
    def to_dict(self) -> dict:
        """Convert memory record to dictionary for serialization"""
        return {
            'id': self.id,
            'text': self.text,
            'timestamp': self.timestamp.isoformat(),
            'importance': self.importance,
            'source': self.source,
            'embedding': self.embedding.tolist() if self.embedding is not None else None,
            'associated_event': self.associated_event,
            'keywords': self.keywords,
            'access_count': self.access_count,
            'last_accessed': self.last_accessed.isoformat() if self.last_accessed else None
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'MemoryRecord':
        """Create memory record from dictionary"""
        record = cls(
            text=data['text'],
            timestamp=datetime.datetime.fromisoformat(data['timestamp']),
            importance=data['importance'],
            source=data['source'],
            embedding=np.array(data['embedding']) if data['embedding'] else None,
            associated_event=data.get('associated_event'),
            keywords=data.get('keywords', [])
        )
        record.id = data['id']
        record.access_count = data.get('access_count', 0)
        if data.get('last_accessed'):
            record.last_accessed = datetime.datetime.fromisoformat(data['last_accessed'])
        return record
    
    def __str__(self) -> str:
        return f"MemoryRecord({self.timestamp.strftime('%Y-%m-%d %H:%M')}, {self.source}, importance={self.importance:.1f}): {self.text[:100]}..."
    
    def __repr__(self) -> str:
        return self.__str__() 