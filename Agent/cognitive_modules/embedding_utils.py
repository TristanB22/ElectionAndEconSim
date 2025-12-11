import numpy as np
from typing import List, Dict, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re
import string

class SimpleTextEmbedder:
    """
    Simple text embedding using TF-IDF.
    In a production system, this would use proper embedding models like OpenAI embeddings.
    """
    
    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            lowercase=True,
            ngram_range=(1, 2)
        )
        self.is_fitted = False
        self.corpus = []
    
    def preprocess_text(self, text: str) -> str:
        """Basic text preprocessing"""
        # Remove punctuation and extra whitespace
        text = re.sub(f'[{string.punctuation}]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip().lower()
    
    def fit(self, texts: List[str]) -> None:
        """Fit the vectorizer on a corpus of texts"""
        if not texts:
            return
        
        processed_texts = [self.preprocess_text(text) for text in texts]
        self.corpus = processed_texts
        
        try:
            self.vectorizer.fit(processed_texts)
            self.is_fitted = True
        except ValueError:
            # If fitting fails, create a basic vectorizer
            self.vectorizer = TfidfVectorizer(max_features=100, stop_words='english')
            self.vectorizer.fit(['default text for fitting'])
            self.is_fitted = True
    
    def get_embedding(self, text: str) -> np.ndarray:
        """Get embedding vector for a text"""
        if not self.is_fitted:
            # If not fitted, fit on this text first
            self.fit([text])
        
        processed_text = self.preprocess_text(text)
        try:
            embedding = self.vectorizer.transform([processed_text]).toarray()[0]
            return embedding
        except:
            # Return zero vector if transformation fails
            return np.zeros(self.vectorizer.max_features if hasattr(self.vectorizer, 'max_features') else 100)
    
    def update_corpus(self, new_texts: List[str]) -> None:
        """Update the corpus and refit if necessary"""
        if not new_texts:
            return
        
        processed_new_texts = [self.preprocess_text(text) for text in new_texts]
        self.corpus.extend(processed_new_texts)
        
        # Refit with updated corpus
        if len(self.corpus) > 10:  # Only refit if we have enough data
            try:
                self.vectorizer.fit(self.corpus)
            except:
                pass  # Keep existing vectorizer if refit fails

# Global embedder instance
_global_embedder = SimpleTextEmbedder()

def get_text_embedding(text: str, update_corpus: bool = True) -> np.ndarray:
    """
    Get embedding for a text string.
    
    Args:
        text (str): Text to embed
        update_corpus (bool): Whether to add this text to the corpus
        
    Returns:
        np.ndarray: Embedding vector
    """
    global _global_embedder
    
    if update_corpus:
        _global_embedder.update_corpus([text])
    
    return _global_embedder.get_embedding(text)

def calculate_similarity(embedding1: np.ndarray, embedding2: np.ndarray) -> float:
    """
    Calculate cosine similarity between two embeddings.
    
    Args:
        embedding1 (np.ndarray): First embedding
        embedding2 (np.ndarray): Second embedding
        
    Returns:
        float: Similarity score between -1 and 1
    """
    if embedding1.size == 0 or embedding2.size == 0:
        return 0.0
    
    # Ensure embeddings are 2D for sklearn
    emb1 = embedding1.reshape(1, -1)
    emb2 = embedding2.reshape(1, -1)
    
    try:
        similarity = cosine_similarity(emb1, emb2)[0][0]
        return float(similarity)
    except:
        return 0.0

def find_most_similar_texts(query_text: str, 
                          candidate_texts: List[str], 
                          k: int = 5) -> List[tuple]:
    """
    Find the k most similar texts to a query.
    
    Args:
        query_text (str): Query text
        candidate_texts (List[str]): List of candidate texts
        k (int): Number of most similar texts to return
        
    Returns:
        List[tuple]: List of (similarity_score, text_index, text) tuples
    """
    if not candidate_texts:
        return []
    
    query_embedding = get_text_embedding(query_text, update_corpus=False)
    similarities = []
    
    for i, text in enumerate(candidate_texts):
        text_embedding = get_text_embedding(text, update_corpus=False)
        similarity = calculate_similarity(query_embedding, text_embedding)
        similarities.append((similarity, i, text))
    
    # Sort by similarity (descending) and return top k
    similarities.sort(key=lambda x: x[0], reverse=True)
    return similarities[:k]

def initialize_embedder_with_corpus(texts: List[str]) -> None:
    """
    Initialize the global embedder with a corpus of texts.
    
    Args:
        texts (List[str]): Corpus of texts to fit the embedder
    """
    global _global_embedder
    _global_embedder.fit(texts)

def batch_embed_texts(texts: List[str]) -> List[np.ndarray]:
    """
    Get embeddings for multiple texts efficiently.
    
    Args:
        texts (List[str]): List of texts to embed
        
    Returns:
        List[np.ndarray]: List of embedding vectors
    """
    embeddings = []
    for text in texts:
        embedding = get_text_embedding(text, update_corpus=False)
        embeddings.append(embedding)
    
    # Update corpus with all texts at once
    _global_embedder.update_corpus(texts)
    
    return embeddings 