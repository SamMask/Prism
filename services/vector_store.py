# -*- coding: utf-8 -*-
"""
Vector Store - Prism V2 Phase 3.2
In-Memory Vector Storage with RRF Hybrid Search

Design Philosophy:
- RAM-resident vectors for millisecond search
- L2 Normalization → Cosine Similarity = Dot Product
- RRF (Reciprocal Rank Fusion) for hybrid search

Based on Claude's architecture suggestion (2024-12)
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
import hashlib
import threading

from db import get_db

# Constants
MODEL_NAME = 'all-MiniLM-L6-v2'
EMBEDDING_DIM = 384
RRF_K = 60  # RRF smoothing constant

# Lazy-load model
_model = None
_model_lock = threading.Lock()


def get_model():
    """Get or initialize the embedding model (singleton with thread safety)"""
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:  # Double-check
                try:
                    from sentence_transformers import SentenceTransformer
                    print(f"[VectorStore] Loading model: {MODEL_NAME}...")
                    _model = SentenceTransformer(MODEL_NAME)
                    print(f"[VectorStore] Model loaded successfully")
                except ImportError:
                    raise RuntimeError(
                        "sentence-transformers not installed. "
                        "Run: pip install sentence-transformers"
                    )
    return _model


def is_available() -> bool:
    """Check if sentence-transformers is installed"""
    try:
        import sentence_transformers
        return True
    except ImportError:
        return False


class VectorStore:
    """
    In-Memory Vector Store with SQLite persistence
    
    Core data structures:
    - matrix: (N, 384) numpy array of normalized vectors
    - ids: List mapping matrix row index -> note_id
    - id_map: Dict mapping note_id -> matrix row index
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(VectorStore, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        self.matrix: Optional[np.ndarray] = None
        self.ids: List[int] = []
        self.id_map: Dict[int, int] = {}
        self._initialized = True
        
    def _normalize(self, v: np.ndarray) -> np.ndarray:
        """L2 Normalization - makes Cosine Similarity = Dot Product"""
        norm = np.linalg.norm(v)
        if norm == 0:
            return v
        return v / norm

    def refresh_from_db(self, app=None):
        """Load all vectors from SQLite into RAM (Cold Start)"""
        with self._lock:  # Thread safety
            print("[VectorStore] Loading vectors from DB...")
            
            try:
                if app:
                    with app.app_context():
                        db = get_db()
                        self._load_vectors(db)
                else:
                    db = get_db()
                    self._load_vectors(db)
            except Exception as e:
                print(f"[VectorStore] Failed to load: {e}")
                self.matrix = np.zeros((0, EMBEDDING_DIM), dtype=np.float32)
                self.ids = []
                self.id_map = {}

    def _load_vectors(self, db):
        """Internal: Load vectors from database connection"""
        cursor = db.execute("""
            SELECT id, text_embedding 
            FROM Notes 
            WHERE text_embedding IS NOT NULL AND is_archived = 0
            ORDER BY id ASC
        """)
        rows = cursor.fetchall()

        if not rows:
            self.matrix = np.zeros((0, EMBEDDING_DIM), dtype=np.float32)
            self.ids = []
            self.id_map = {}
            print("[VectorStore] No vectors found in DB")
            return

        vectors = []
        self.ids = []
        self.id_map = {}

        for idx, row in enumerate(rows):
            note_id = row['id']
            blob = row['text_embedding']
            
            try:
                vector = np.frombuffer(blob, dtype=np.float32)
                if len(vector) == EMBEDDING_DIM:
                    vectors.append(self._normalize(vector))
                    self.ids.append(note_id)
                    self.id_map[note_id] = idx
            except Exception as e:
                print(f"[VectorStore] Skipping note {note_id}: {e}")
                continue

        if vectors:
            self.matrix = np.vstack(vectors).astype(np.float32)
        else:
            self.matrix = np.zeros((0, EMBEDDING_DIM), dtype=np.float32)
            
        print(f"[VectorStore] Loaded {len(self.ids)} vectors into RAM")

    def encode_text(self, text: str) -> np.ndarray:
        """Convert text to normalized embedding vector"""
        model = get_model()
        # Truncate for model
        truncated = text[:2000] if len(text) > 2000 else text
        raw_vec = model.encode(truncated, convert_to_numpy=True)
        return self._normalize(raw_vec.astype(np.float32))

    def search(self, query_text: str, top_k: int = 50) -> Tuple[List[int], List[float]]:
        """
        Vector search (dense retrieval)
        
        Returns:
            (note_ids, scores) sorted by similarity descending
        """
        if self.matrix is None or len(self.matrix) == 0:
            return [], []

        query_vec = self.encode_text(query_text)

        # Dot product = Cosine Similarity (because vectors are normalized)
        scores = np.dot(self.matrix, query_vec)

        # Top-K using argpartition (faster than full sort)
        k = min(top_k, len(scores))
        if k == 0:
            return [], []

        top_k_indices = np.argpartition(scores, -k)[-k:]
        top_k_indices = top_k_indices[np.argsort(scores[top_k_indices])][::-1]

        result_ids = [self.ids[i] for i in top_k_indices]
        result_scores = scores[top_k_indices].tolist()

        return result_ids, result_scores

    def get_status(self) -> dict:
        """Get vector store status"""
        return {
            'loaded': self.matrix is not None,
            'count': len(self.ids) if self.ids else 0,
            'memory_mb': (self.matrix.nbytes / 1024 / 1024) if self.matrix is not None else 0,
        }


# Singleton instance
vector_store = VectorStore()


# =============================================================================
# RRF Hybrid Search
# =============================================================================

def hybrid_search(
    query_text: str,
    top_k: int = 20,
    fts_weight: float = 0.3,
    vector_weight: float = 0.7
) -> List[Tuple[int, float]]:
    """
    RRF (Reciprocal Rank Fusion) Hybrid Search
    
    Combines FTS5 keyword search with vector semantic search.
    
    Args:
        query_text: Search query
        top_k: Number of results to return
        fts_weight: Weight for FTS results (not used in RRF, for future)
        vector_weight: Weight for vector results (not used in RRF, for future)
    
    Returns:
        List of (note_id, rrf_score) tuples, sorted by score descending
    """
    from flask import current_app
    
    db = get_db()
    final_scores: Dict[int, float] = {}
    
    # 1. FTS5 Search (Sparse Retrieval)
    fts_results = []
    try:
        # FTS5 MATCH query
        fts_query = query_text.replace('"', '""')  # Escape quotes
        cursor = db.execute("""
            SELECT rowid, rank 
            FROM Notes_FTS 
            WHERE Notes_FTS MATCH ? 
            ORDER BY rank 
            LIMIT 50
        """, (fts_query,))
        fts_results = [(row['rowid'], row['rank']) for row in cursor.fetchall()]
    except Exception as e:
        print(f"[Hybrid] FTS error: {e}")
    
    # 2. Vector Search (Dense Retrieval)
    vector_results = []
    try:
        if is_available() and vector_store.matrix is not None and len(vector_store.ids) > 0:
            note_ids, scores = vector_store.search(query_text, top_k=50)
            vector_results = list(zip(note_ids, scores))
    except Exception as e:
        print(f"[Hybrid] Vector error: {e}")
    
    # 3. RRF Fusion
    # Formula: RRF_score = sum(1 / (k + rank))
    
    for rank, (note_id, _) in enumerate(fts_results):
        if note_id not in final_scores:
            final_scores[note_id] = 0
        final_scores[note_id] += 1 / (RRF_K + rank + 1)
    
    for rank, (note_id, _) in enumerate(vector_results):
        if note_id not in final_scores:
            final_scores[note_id] = 0
        final_scores[note_id] += 1 / (RRF_K + rank + 1)
    
    # 4. Sort by RRF score
    sorted_results = sorted(
        final_scores.items(), 
        key=lambda x: x[1], 
        reverse=True
    )[:top_k]
    
    return sorted_results


def get_content_hash(text: str) -> str:
    """Generate content hash to detect changes"""
    return hashlib.md5(text.encode('utf-8')).hexdigest()[:16]
