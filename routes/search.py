# -*- coding: utf-8 -*-
"""
Semantic Search API Routes - Prism V2 Phase 3.2
"""

from flask import Blueprint, request, jsonify
from db import get_db

search_bp = Blueprint('search', __name__)


@search_bp.route('/search/semantic', methods=['GET'])
def semantic_search():
    """
    Semantic search using text embeddings
    
    Query params:
        - q: Search query (required)
        - limit: Max results (default: 20, max: 50)
    
    Returns:
        {
            'status': 'success',
            'data': [
                {
                    'id': int,
                    'title': str,
                    'content_preview': str,
                    'similarity': float,
                    'category': str,
                    'tags': [...]
                }
            ]
        }
    """
    try:
        query = request.args.get('q', '').strip()
        limit = min(int(request.args.get('limit', 20)), 50)
        
        if not query:
            return jsonify({
                'status': 'error',
                'message': 'Search query is required'
            }), 400
        
        # Check if embedding service is available
        try:
            from services.embedding_service import (
                is_model_available, 
                search_similar, 
                get_embedding_status
            )
        except ImportError:
            return jsonify({
                'status': 'error',
                'message': 'Embedding service not available'
            }), 500
        
        if not is_model_available():
            return jsonify({
                'status': 'error',
                'message': 'sentence-transformers not installed. Run: pip install sentence-transformers'
            }), 400
        
        db = get_db()
        
        # Get all notes with embeddings
        rows = db.execute('''
            SELECT id, text_embedding
            FROM Notes
            WHERE text_embedding IS NOT NULL
              AND is_archived = 0
        ''').fetchall()
        
        if not rows:
            return jsonify({
                'status': 'success',
                'data': [],
                'message': 'No indexed notes found. Please rebuild the search index.'
            })
        
        # Convert to list of tuples
        note_embeddings = [(row['id'], row['text_embedding']) for row in rows]
        
        # Search
        results = search_similar(query, note_embeddings, top_k=limit)
        
        if not results:
            return jsonify({
                'status': 'success',
                'data': []
            })
        
        # Get note details
        note_ids = [r[0] for r in results]
        similarity_map = {r[0]: r[1] for r in results}
        
        # Query note details
        placeholders = ','.join('?' * len(note_ids))
        detail_rows = db.execute(f'''
            SELECT 
                n.id, n.title, n.content, n.remarks,
                c.name as category_name, c.icon as category_icon,
                (SELECT GROUP_CONCAT(t.name) FROM Note_Tags nt 
                 JOIN Tags t ON nt.tag_id = t.id WHERE nt.note_id = n.id) as tag_names
            FROM Notes n
            LEFT JOIN Categories c ON n.category_id = c.id
            WHERE n.id IN ({placeholders})
        ''', note_ids).fetchall()
        
        # Build response
        detail_map = {row['id']: row for row in detail_rows}
        data = []
        
        for note_id, similarity in results:
            row = detail_map.get(note_id)
            if not row:
                continue
            
            content = row['content'] or ''
            data.append({
                'id': row['id'],
                'title': row['title'] or '無標題',
                'content_preview': content[:200] + '...' if len(content) > 200 else content,
                'similarity': round(similarity, 3),
                'category': row['category_name'],
                'category_icon': row['category_icon'],
                'tags': row['tag_names'].split(',') if row['tag_names'] else [],
            })
        
        return jsonify({
            'status': 'success',
            'data': data,
            'total': len(data)
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@search_bp.route('/search/hybrid', methods=['GET'])
def hybrid_search_endpoint():
    """
    Hybrid search using RRF (Reciprocal Rank Fusion)
    
    Combines FTS5 keyword search with vector semantic search.
    
    Query params:
        - q: Search query (required)
        - limit: Max results (default: 20, max: 50)
        - mode: 'hybrid' (default), 'fts', or 'vector'
    """
    try:
        query = request.args.get('q', '').strip()
        limit = min(int(request.args.get('limit', 20)), 50)
        mode = request.args.get('mode', 'hybrid')
        
        if not query:
            return jsonify({
                'status': 'error',
                'message': 'Search query is required'
            }), 400
        
        db = get_db()
        
        if mode == 'hybrid':
            # Use RRF Hybrid Search
            try:
                from services.vector_store import hybrid_search, is_available
                
                if not is_available():
                    # Fallback to FTS only
                    mode = 'fts'
                else:
                    results = hybrid_search(query, top_k=limit)
                    note_ids = [r[0] for r in results]
                    score_map = {r[0]: r[1] for r in results}
            except Exception as e:
                print(f"[Hybrid] Error: {e}, falling back to FTS")
                mode = 'fts'
        
        if mode == 'fts':
            # FTS5 only
            try:
                fts_query = query.replace('"', '""')
                cursor = db.execute("""
                    SELECT rowid FROM Notes_FTS 
                    WHERE Notes_FTS MATCH ? 
                    ORDER BY rank LIMIT ?
                """, (fts_query, limit))
                note_ids = [row['rowid'] for row in cursor.fetchall()]
                score_map = {nid: 1.0 for nid in note_ids}
            except Exception as e:
                print(f"[FTS] Error: {e}")
                return jsonify({
                    'status': 'error',
                    'message': f'Search failed: {e}'
                }), 500
        
        elif mode == 'vector':
            # Vector only
            try:
                from services.vector_store import vector_store, is_available
                
                if not is_available():
                    return jsonify({
                        'status': 'error',
                        'message': 'Vector search not available'
                    }), 400
                
                note_ids, scores = vector_store.search(query, top_k=limit)
                score_map = dict(zip(note_ids, scores))
            except Exception as e:
                return jsonify({
                    'status': 'error',
                    'message': f'Vector search failed: {e}'
                }), 500
        
        if not note_ids:
            return jsonify({
                'status': 'success',
                'data': [],
                'mode': mode
            })
        
        # Fetch note details
        placeholders = ','.join('?' * len(note_ids))
        detail_rows = db.execute(f'''
            SELECT 
                n.id, n.title, n.content, n.remarks,
                c.name as category_name, c.icon as category_icon,
                (SELECT GROUP_CONCAT(t.name) FROM Note_Tags nt 
                 JOIN Tags t ON nt.tag_id = t.id WHERE nt.note_id = n.id) as tag_names
            FROM Notes n
            LEFT JOIN Categories c ON n.category_id = c.id
            WHERE n.id IN ({placeholders})
        ''', note_ids).fetchall()
        
        detail_map = {row['id']: row for row in detail_rows}
        data = []
        
        for note_id in note_ids:
            row = detail_map.get(note_id)
            if not row:
                continue
            
            content = row['content'] or ''
            data.append({
                'id': row['id'],
                'title': row['title'] or '無標題',
                'content_preview': content[:200] + '...' if len(content) > 200 else content,
                'score': round(score_map.get(note_id, 0), 4),
                'category': row['category_name'],
                'category_icon': row['category_icon'],
                'tags': row['tag_names'].split(',') if row['tag_names'] else [],
            })
        
        return jsonify({
            'status': 'success',
            'data': data,
            'total': len(data),
            'mode': mode
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@search_bp.route('/search/status', methods=['GET'])
def search_status():
    """Get semantic search service status"""
    try:
        from services.embedding_service import get_embedding_status
        status = get_embedding_status()
        
        db = get_db()
        
        # Count indexed vs total notes
        stats = db.execute('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN text_embedding IS NOT NULL THEN 1 ELSE 0 END) as indexed
            FROM Notes
            WHERE is_archived = 0
        ''').fetchone()
        
        return jsonify({
            'status': 'success',
            'data': {
                **status,
                'total_notes': stats['total'],
                'indexed_notes': stats['indexed'] or 0,
                'index_coverage': f"{(stats['indexed'] or 0) / max(stats['total'], 1) * 100:.1f}%"
            }
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@search_bp.route('/index/rebuild', methods=['POST'])
def rebuild_index():
    """
    Rebuild text embeddings for all notes
    
    This can take a while for large databases.
    Returns progress info.
    """
    try:
        from services.embedding_service import (
            is_model_available,
            text_to_embedding,
            embedding_to_blob
        )
        
        if not is_model_available():
            return jsonify({
                'status': 'error',
                'message': 'sentence-transformers not installed'
            }), 400
        
        db = get_db()
        
        # Get all notes
        rows = db.execute('''
            SELECT id, title, content
            FROM Notes
            WHERE is_archived = 0
        ''').fetchall()
        
        total = len(rows)
        success = 0
        failed = 0
        
        for row in rows:
            try:
                # Combine title and content
                text = f"{row['title'] or ''} {row['content'] or ''}".strip()
                if not text:
                    continue
                
                # Generate embedding
                embedding = text_to_embedding(text)
                if embedding is not None:
                    blob = embedding_to_blob(embedding)
                    db.execute('''
                        UPDATE Notes 
                        SET text_embedding = ?, embedding_updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (blob, row['id']))
                    success += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"[Index] Failed to index note {row['id']}: {e}")
                failed += 1
        
        db.commit()
        
        return jsonify({
            'status': 'success',
            'data': {
                'total': total,
                'success': success,
                'failed': failed
            }
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@search_bp.route('/notes/<int:note_id>/embed', methods=['POST'])
def embed_single_note(note_id):
    """Generate embedding for a single note"""
    try:
        from services.embedding_service import (
            is_model_available,
            text_to_embedding,
            embedding_to_blob
        )
        
        if not is_model_available():
            return jsonify({
                'status': 'error',
                'message': 'sentence-transformers not installed'
            }), 400
        
        db = get_db()
        
        # Get note
        note = db.execute('''
            SELECT id, title, content FROM Notes WHERE id = ?
        ''', (note_id,)).fetchone()
        
        if not note:
            return jsonify({
                'status': 'error',
                'message': 'Note not found'
            }), 404
        
        # Generate embedding
        text = f"{note['title'] or ''} {note['content'] or ''}".strip()
        if not text:
            return jsonify({
                'status': 'error',
                'message': 'Note has no content to embed'
            }), 400
        
        embedding = text_to_embedding(text)
        if embedding is None:
            return jsonify({
                'status': 'error',
                'message': 'Failed to generate embedding'
            }), 500
        
        blob = embedding_to_blob(embedding)
        db.execute('''
            UPDATE Notes 
            SET text_embedding = ?, embedding_updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (blob, note_id))
        db.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Embedding generated successfully'
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
