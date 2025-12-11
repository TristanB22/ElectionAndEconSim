#!/usr/bin/env python3
"""
Embedding Module for Text Vectorization
Handles text embedding generation for memory storage and retrieval.
"""

import os
import time
from typing import List, Optional, Union
import numpy as np

# Sentence transformers is no longer used - we use OpenAI embeddings only
SENTENCE_TRANSFORMERS_AVAILABLE = False
SentenceTransformer = None

# Try to import OpenAI for embeddings
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    print("Warning: openai not available. Install with: pip install openai")
    openai = None
    OPENAI_AVAILABLE = False

class EmbeddingModule:
    """Handles text embedding generation."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", use_openai: bool = False):
        """
        Initialize embedding module.

        Args:
            model_name: Name of the sentence transformer model to use
            use_openai: Whether to use OpenAI embeddings instead of sentence transformers
        """
        self.model_name = model_name
        self.use_openai = use_openai
        self.model = None
        self.openai_client = None

        if use_openai and OPENAI_AVAILABLE:
            self._init_openai()
        # If not using OpenAI, that's fine - we'll use the fallback simple embeddings
    
    def _init_openai(self):
        """Initialize OpenAI client."""
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        self.openai_client = openai.OpenAI(api_key=api_key)
        print("OpenAI embedding client initialized")
    
    
    def get_embedding(self, text: str) -> Optional[List[float]]:
        """
        Get embedding for a text string.
        
        Args:
            text: Text to embed
            
        Returns:
            List of float values representing the embedding, or None if failed
        """
        if not text or not text.strip():
            return None
        
        try:
            if self.use_openai and self.openai_client:
                return self._get_openai_embedding(text)
            else:
                # Fallback to simple hash-based embedding
                return self._get_simple_embedding(text)
        except Exception as e:
            print(f"Error generating embedding: {e}")
            return self._get_simple_embedding(text)
    
    def _get_openai_embedding(self, text: str) -> Optional[List[float]]:
        """Get embedding using OpenAI API."""
        try:
            response = self.openai_client.embeddings.create(
                model="text-embedding-ada-002",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"OpenAI embedding error: {e}")
            return None
    
    
    def _get_simple_embedding(self, text: str) -> List[float]:
        """Get a simple hash-based embedding as fallback."""
        import hashlib
        import struct
        
        # Create a hash of the text
        text_hash = hashlib.sha256(text.encode('utf-8')).digest()
        
        # Convert to float values
        embedding = []
        for i in range(0, len(text_hash), 4):
            if i + 4 <= len(text_hash):
                # Convert 4 bytes to float
                value = struct.unpack('>f', text_hash[i:i+4])[0]
                embedding.append(value)
        
        # Pad or truncate to desired size
        target_size = 384
        if len(embedding) < target_size:
            # Pad with zeros
            embedding.extend([0.0] * (target_size - len(embedding)))
        elif len(embedding) > target_size:
            # Truncate
            embedding = embedding[:target_size]
        
        return embedding
    
    def get_embeddings_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        Get embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embeddings (or None for failed texts)
        """
        embeddings = []
        for text in texts:
            embedding = self.get_embedding(text)
            embeddings.append(embedding)
        return embeddings

def get_text_embedding(text: str) -> Optional[List[float]]:
    """
    Get embedding for a single text string.
    Now uses centralized APIManager for consistency.
    """
    try:
        from Utils.api_manager import APIManager
        api_manager = APIManager.get_instance()
        return api_manager.get_text_embedding(text)
    except Exception as e:
        # Fallback to simple hash-based embeddings if APIManager fails
        print(f"Warning: APIManager embedding failed ({e}), using local embedding module")
        module = EmbeddingModule(use_openai=False)
        return module.get_embedding(text)

def get_text_embeddings(texts: List[str]) -> List[Optional[List[float]]]:
    """
    Get embeddings for multiple text strings.
    Now uses centralized APIManager for consistency.
    """
    try:
        from Utils.api_manager import APIManager
        api_manager = APIManager.get_instance()
        return [api_manager.get_text_embedding(text) for text in texts]
    except Exception as e:
        # Fallback to simple hash-based embeddings if APIManager fails
        print(f"Warning: APIManager embedding failed ({e}), using local embedding module")
        module = EmbeddingModule(use_openai=False)
        return module.get_embeddings_batch(texts)
