# -*- coding: utf-8 -*-
"""
Embedding Service - Prism V2 Phase 3.2
Semantic Search using Sentence Transformers

Uses all-MiniLM-L6-v2 model (384 dimensions, ~22MB)
Lightweight and fast for personal knowledge base

Note: First run will download the model (~90MB)
"""

import json
from typing import Optional, List, Tuple, Any

# Lazy loading to avoid slow startup
_model = None
_model_name = "all-MiniLM-L6-v2"
_HAS_DEPS = False

try:
    import numpy as np
    import sentence_transformers
    _HAS_DEPS = True
    NDArray = np.ndarray
except ImportError:
    np = None
    _HAS_DEPS = False
    NDArray = Any


def get_model():
    """Get or initialize the embedding model (singleton)"""
    global _model
    if not _HAS_DEPS:
        raise RuntimeError("Dependencies (numpy/sentence-transformers) not installed")
        
    if _model is None:
        from sentence_transformers import SentenceTransformer
        print(f"[Embedding] Loading model: {_model_name}...")
        _model = SentenceTransformer(_model_name)
        print(f"[Embedding] Model loaded successfully")
    return _model


def is_model_available() -> bool:
    """Check if sentence-transformers is installed"""
    return _HAS_DEPS


def text_to_embedding(text: str) -> Optional[NDArray]:
    """
    Convert text to embedding vector

    Args:
        text: Input text (title + content)

    Returns:
        384-dimensional numpy array or None if failed
    """
    if not _HAS_DEPS:
        return None

    if not text or not text.strip():
        return None

    try:
        model = get_model()
        # Truncate very long text (model max ~256 tokens)
        truncated = text[:2000] if len(text) > 2000 else text
        embedding = model.encode(truncated, convert_to_numpy=True)
        return embedding
    except Exception as e:
        print(f"[Embedding] Error encoding text: {e}")
        return None


def embedding_to_blob(embedding: NDArray) -> bytes:
    """Convert numpy array to bytes for SQLite storage"""
    return embedding.astype(np.float32).tobytes()


def blob_to_embedding(blob: bytes) -> NDArray:
    """Convert bytes from SQLite to numpy array"""
    return np.frombuffer(blob, dtype=np.float32)


def cosine_similarity(a: NDArray, b: NDArray) -> float:
    """Calculate cosine similarity between two vectors"""
    dot = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot / (norm_a * norm_b))


def search_similar(
    query: str,
    note_embeddings: List[Tuple[int, bytes]],  # [(note_id, embedding_blob), ...]
    top_k: int = 10
) -> List[Tuple[int, float]]:
    """
    Search for notes similar to query

    Args:
        query: Search query text
        note_embeddings: List of (note_id, embedding_blob) tuples
        top_k: Number of results to return

    Returns:
        List of (note_id, similarity_score) sorted by similarity
    """
    # Get query embedding
    query_embedding = text_to_embedding(query)
    if query_embedding is None:
        return []

    # Calculate similarities
    similarities = []
    for note_id, blob in note_embeddings:
        if blob is None:
            continue
        try:
            note_embedding = blob_to_embedding(blob)
            similarity = cosine_similarity(query_embedding, note_embedding)
            similarities.append((note_id, similarity))
        except Exception as e:
            print(f"[Embedding] Error comparing note {note_id}: {e}")
            continue

    # Sort by similarity (descending)
    similarities.sort(key=lambda x: x[1], reverse=True)

    # Return top K
    return similarities[:top_k]


def get_embedding_status() -> dict:
    """Get embedding service status"""
    return {
        'available': is_model_available(),
        'model_name': _model_name,
        'dimensions': 384,
        'model_loaded': _model is not None,
    }
