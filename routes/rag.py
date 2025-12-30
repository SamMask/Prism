# -*- coding: utf-8 -*-
"""
RAG API Routes - Prism V2 Phase 3.5
External Knowledge Retrieval Interface for AI Agents
"""

from flask import Blueprint, request, jsonify
from db import get_db
from services.vector_store import hybrid_search, is_available

rag_bp = Blueprint('rag', __name__)

@rag_bp.route('/rag/search', methods=['POST'])
def rag_search():
    """
    RAG Retrieval Endpoint
    
    Expected JSON Payload:
    {
        "query": "search term",
        "limit": 5,      # Optional, default 5
        "threshold": 0.0 # Optional, minimum score
    }
    
    Returns JSON:
    {
        "status": "success",
        "results": [
            {
                "id": 123,
                "title": "Note Title",
                "content": "Full content or chunk...",
                "score": 0.85,
                "source": "Prism Knowledge Base"
            }
        ]
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': 'JSON payload required'}), 400
            
        query = data.get('query', '').strip()
        limit = min(int(data.get('limit', 5)), 20) # Cap at 20 for RAG context window
        threshold = float(data.get('threshold', 0.0))
        
        if not query:
            return jsonify({'status': 'error', 'message': 'Query is required'}), 400
            
        # Check if vector store is ready
        if not is_available():
             return jsonify({
                'status': 'error', 
                'message': 'Vector search service not available'
            }), 503

        # Execute Hybrid Search (Vector + FTS)
        # implementation is in services/vector_store.py
        results = hybrid_search(query, top_k=limit)
        
        note_ids = [r[0] for r in results]
        
        # Hydrate with Content
        if not note_ids:
            return jsonify({'status': 'success', 'results': []})
            
        db = get_db()
        placeholders = ','.join('?' * len(note_ids))
        
        rows = db.execute(f'''
            SELECT id, title, content, updated_at
            FROM Notes
            WHERE id IN ({placeholders})
        ''', note_ids).fetchall()
        
        # Map to ID for sorting preservation
        row_map = {row['id']: row for row in rows}
        
        output = []
        for note_id, score in results:
            if note_id not in row_map:
                continue
            if score < threshold:
                continue
                
            row = row_map[note_id]
            output.append({
                "id": row['id'],
                "title": row['title'],
                "content": row['content'],
                "score": round(score, 6),
                "updated_at": row['updated_at'],
                "source": "Prism"
            })
            
        return jsonify({
            'status': 'success',
            'results': output
        })

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
