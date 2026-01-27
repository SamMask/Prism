# -*- coding: utf-8 -*-
"""
AI API Routes - Prism V2 Phase 3
Auto-Tagging and AI Analysis Endpoints
"""

import os
from flask import Blueprint, request, jsonify, current_app

ai_bp = Blueprint('ai', __name__)


@ai_bp.route('/ai/status', methods=['GET'])
def get_ai_status():
    """
    Get Ollama server status and available models
    
    Returns:
        {
            'status': 'success',
            'data': {
                'available': bool,
                'models': List[str],
                'vision_ready': bool,
                'text_ready': bool
            }
        }
    """
    try:
        from services.ai_service import get_ollama_status
        status = get_ollama_status()
        return jsonify({
            'status': 'success',
            'data': status
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@ai_bp.route('/ai/tag_image', methods=['POST'])
def tag_image():
    """
    Analyze image and return suggested tags
    
    Request:
        - file: Image file (multipart/form-data)
        - OR image_path: Relative path to existing image (JSON)
        - model: Optional model name (default: llava)
        - language: 'en' or 'zh' (default: en)
    
    Returns:
        {
            'status': 'success',
            'data': {
                'tags': List[str],
                'description': str
            }
        }
    """
    try:
        from services.ai_service import analyze_image_for_tags
        
        # Get optional parameters
        model = request.form.get('model', 'llava')
        language = request.form.get('language', 'en')
        
        # Handle file upload
        if 'file' in request.files:
            file = request.files['file']
            if file.filename:
                # Save temporarily
                upload_folder = current_app.config.get('UPLOAD_FOLDER', 'static/uploads')
                temp_path = os.path.join(upload_folder, f"_temp_ai_{file.filename}")
                file.save(temp_path)
                
                try:
                    result = analyze_image_for_tags(temp_path, model=model, language=language)
                finally:
                    # Clean up temp file
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                
                if result['success']:
                    return jsonify({
                        'status': 'success',
                        'data': {
                            'tags': result['tags'],
                            'description': result['description']
                        }
                    })
                else:
                    return jsonify({
                        'status': 'error',
                        'message': result['error']
                    }), 400
        
        # Handle existing image path
        data = request.get_json() if request.is_json else {}
        image_path = data.get('image_path')
        
        if image_path:
            # Convert relative path to absolute
            if image_path.startswith('/'):
                image_path = image_path[1:]  # Remove leading slash
            
            # Check in static/uploads
            full_path = os.path.join(current_app.root_path, image_path)
            if not os.path.exists(full_path):
                return jsonify({
                    'status': 'error',
                    'message': f'Image not found: {image_path}'
                }), 404
            
            result = analyze_image_for_tags(
                full_path, 
                model=data.get('model', 'llava'),
                language=data.get('language', 'en')
            )
            
            if result['success']:
                return jsonify({
                    'status': 'success',
                    'data': {
                        'tags': result['tags'],
                        'description': result['description']
                    }
                })
            else:
                return jsonify({
                    'status': 'error',
                    'message': result['error']
                }), 400
        
        return jsonify({
            'status': 'error',
            'message': 'No image provided. Use "file" or "image_path".'
        }), 400
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@ai_bp.route('/ai/summarize', methods=['POST'])
def summarize_note():
    """
    Generate AI summary for note content
    
    Request (JSON):
        - content: Note text content
        - model: Optional model name (default: llama3.2)
        - max_length: Optional max summary length (default: 100)
    
    Returns:
        {
            'status': 'success',
            'data': {
                'summary': str
            }
        }
    """
    try:
        from services.ai_service import summarize_note as do_summarize
        
        data = request.get_json()
        if not data or not data.get('content'):
            return jsonify({
                'status': 'error',
                'message': 'Content is required'
            }), 400
        
        result = do_summarize(
            content=data['content'],
            model=data.get('model', 'llama3.2'),
            max_length=data.get('max_length', 100)
        )
        
        if result['success']:
            return jsonify({
                'status': 'success',
                'data': {
                    'summary': result['summary']
                }
            })
        else:
            return jsonify({
                'status': 'error',
                'message': result['error']
            }), 400
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@ai_bp.route('/ai/analyze_note', methods=['POST'])
def analyze_note():
    """
    Analyze note content and images, return suggested tags
    
    Request (JSON):
        - note_id: Note ID to analyze
        - include_images: Whether to analyze embedded images (default: true)
    
    Returns:
        {
            'status': 'success',
            'data': {
                'suggested_tags': List[str],
                'summary': str,
                'image_analyses': List[{tags, description}]
            }
        }
    """
    try:
        from services.ai_service import analyze_image_for_tags, summarize_note as do_summarize
        from db import get_db
        import re
        
        data = request.get_json()
        note_id = data.get('note_id')
        include_images = data.get('include_images', True)
        
        if not note_id:
            return jsonify({
                'status': 'error',
                'message': 'note_id is required'
            }), 400
        
        # Get note content
        db = get_db()
        note = db.execute('SELECT * FROM Notes WHERE id = ?', (note_id,)).fetchone()
        
        if not note:
            return jsonify({
                'status': 'error',
                'message': 'Note not found'
            }), 404
        
        content = note['content'] or ''
        suggested_tags = []
        image_analyses = []
        
        # Analyze images if requested
        if include_images:
            # Extract image paths from markdown
            image_pattern = r'!\[.*?\]\((.*?)\)'
            images = re.findall(image_pattern, content)
            
            for img_path in images[:3]:  # Limit to first 3 images
                if img_path.startswith('/'):
                    img_path = img_path[1:]
                
                full_path = os.path.join(current_app.root_path, img_path)
                if os.path.exists(full_path):
                    result = analyze_image_for_tags(full_path)
                    if result['success']:
                        image_analyses.append({
                            'path': img_path,
                            'tags': result['tags'],
                            'description': result['description']
                        })
                        suggested_tags.extend(result['tags'])
        
        # Generate text summary if content is long enough
        summary = ''
        if len(content) > 100:
            summary_result = do_summarize(content)
            if summary_result['success']:
                summary = summary_result['summary']
        
        # Deduplicate tags
        suggested_tags = list(dict.fromkeys(suggested_tags))[:15]
        
        return jsonify({
            'status': 'success',
            'data': {
                'suggested_tags': suggested_tags,
                'summary': summary,
                'image_analyses': image_analyses
            }
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


# =============================================================================
# Phase 3.1.4: Batch Processing
# =============================================================================

# [P0 Fix 2024-12-17] 使用 OrderedDict + TTL/Max 限制防止記憶體洩漏
from collections import OrderedDict
import time

_batch_tasks = OrderedDict()
_BATCH_TASK_MAX = 100  # 最多保留 100 個任務記錄
_BATCH_TASK_TTL = 3600  # 1 小時過期


def _cleanup_old_tasks():
    """清理過期或超過數量限制的舊任務"""
    global _batch_tasks
    now = time.time()
    
    # 刪除過期任務
    expired_keys = [
        k for k, v in _batch_tasks.items()
        if now - v.get('created_at', now) > _BATCH_TASK_TTL
    ]
    for k in expired_keys:
        del _batch_tasks[k]
    
    # 刪除超過數量限制的舊任務 (FIFO)
    while len(_batch_tasks) > _BATCH_TASK_MAX:
        _batch_tasks.popitem(last=False)


@ai_bp.route('/ai/batch_tag', methods=['POST'])
def batch_tag():
    """
    Start batch AI tagging for multiple notes (Phase 3.1.4)
    
    Request (JSON):
        - scope: 'all' | 'category' | 'untagged'
        - category_id: Required if scope='category'
    
    Returns:
        {
            'status': 'success',
            'data': {
                'task_id': str,
                'total': int,
                'message': str
            }
        }
    """
    import uuid
    import threading
    from db import get_db
    
    try:
        data = request.get_json() or {}
        scope = data.get('scope', 'untagged')  # Default: only untagged notes
        category_id = data.get('category_id')
        
        db = get_db()
        
        # Build query based on scope
        if scope == 'all':
            notes = db.execute('''
                SELECT n.id, n.content, n.cover_image 
                FROM Notes n 
                WHERE COALESCE(n.is_archived, 0) = 0
            ''').fetchall()
        elif scope == 'category' and category_id:
            notes = db.execute('''
                SELECT n.id, n.content, n.cover_image 
                FROM Notes n 
                WHERE n.category_id = ? AND COALESCE(n.is_archived, 0) = 0
            ''', (category_id,)).fetchall()
        else:  # untagged
            notes = db.execute('''
                SELECT n.id, n.content, n.cover_image 
                FROM Notes n 
                WHERE COALESCE(n.is_archived, 0) = 0
                AND NOT EXISTS (SELECT 1 FROM Note_Tags nt WHERE nt.note_id = n.id)
            ''').fetchall()
        
        if not notes:
            return jsonify({
                'status': 'success',
                'data': {
                    'task_id': None,
                    'total': 0,
                    'message': '沒有符合條件的筆記需要處理'
                }
            })
        
        # Create task
        task_id = str(uuid.uuid4())[:8]
        
        # [P0 Fix] 清理舊任務 + 加入時間戳
        _cleanup_old_tasks()
        _batch_tasks[task_id] = {
            'status': 'running',
            'total': len(notes),
            'completed': 0,
            'success': 0,
            'failed': 0,
            'stopped': False,
            'results': [],
            'created_at': time.time()  # TTL 計算用
        }
        
        # Start background thread
        note_data = [(n['id'], n['content'], n['cover_image']) for n in notes]
        thread = threading.Thread(
            target=_run_batch_tagging,
            args=(task_id, note_data),
            daemon=True
        )
        thread.start()
        
        return jsonify({
            'status': 'success',
            'data': {
                'task_id': task_id,
                'total': len(notes),
                'message': f'已開始處理 {len(notes)} 筆筆記'
            }
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@ai_bp.route('/ai/batch_tag/<task_id>', methods=['GET'])
def get_batch_status(task_id):
    """Get batch tagging task status"""
    task = _batch_tasks.get(task_id)
    if not task:
        return jsonify({
            'status': 'error',
            'message': 'Task not found'
        }), 404
    
    return jsonify({
        'status': 'success',
        'data': {
            'task_id': task_id,
            'status': task['status'],
            'total': task['total'],
            'completed': task['completed'],
            'success': task['success'],
            'failed': task['failed'],
            'progress': round(task['completed'] / task['total'] * 100, 1) if task['total'] > 0 else 0
        }
    })


@ai_bp.route('/ai/batch_tag/<task_id>/stop', methods=['POST'])
def stop_batch_task(task_id):
    """Stop a running batch task"""
    task = _batch_tasks.get(task_id)
    if not task:
        return jsonify({
            'status': 'error',
            'message': 'Task not found'
        }), 404
    
    task['stopped'] = True
    task['status'] = 'stopped'
    
    return jsonify({
        'status': 'success',
        'message': '任務已停止'
    })


def _run_batch_tagging(task_id: str, notes: list):
    """Background worker for batch tagging"""
    from flask import Flask
    from services.ai_service import analyze_image_for_tags, extract_tags_from_text
    import re
    import sqlite3
    from config import Config
    
    task = _batch_tasks[task_id]
    
    # Create new DB connection for this thread
    conn = sqlite3.connect(Config.DATABASE)
    conn.row_factory = sqlite3.Row
    
    try:
        for note_id, content, cover_image in notes:
            # Check if stopped
            if task['stopped']:
                break
            
            try:
                all_tags = []
                has_image = False
                
                # Analyze cover image
                if cover_image:
                    img_path = cover_image
                    if img_path.startswith('/'):
                        img_path = img_path[1:]
                    
                    full_path = os.path.join(Config.BASE_DIR, img_path)
                    if os.path.exists(full_path):
                        has_image = True
                        result = analyze_image_for_tags(full_path, language='zh')
                        if result['success']:
                            all_tags.extend(result['tags'])
                
                # Analyze images in content
                if content:
                    image_pattern = r'!\[.*?\]\((.*?)\)'
                    images = re.findall(image_pattern, content)
                    
                    for img_path in images[:2]:  # Limit to 2 per note
                        if task['stopped']:
                            break
                        
                        if img_path.startswith('/'):
                            img_path = img_path[1:]
                        
                        full_path = os.path.join(Config.BASE_DIR, img_path)
                        if os.path.exists(full_path):
                            has_image = True
                            result = analyze_image_for_tags(full_path, language='zh')
                            if result['success']:
                                all_tags.extend(result['tags'])
                
                # If no images, analyze text content for tags
                if not has_image and content and len(content) > 50:
                    text_result = extract_tags_from_text(content)
                    if text_result['success']:
                        all_tags.extend(text_result['tags'])
                
                # Dedupe and apply tags
                all_tags = list(dict.fromkeys(all_tags))[:10]
                
                if all_tags:
                    for tag_name in all_tags:
                        if tag_name.strip():
                            conn.execute('INSERT OR IGNORE INTO Tags (name) VALUES (?)', (tag_name.strip(),))
                            tag_row = conn.execute('SELECT id FROM Tags WHERE name = ?', (tag_name.strip(),)).fetchone()
                            if tag_row:
                                conn.execute(
                                    'INSERT OR IGNORE INTO Note_Tags (note_id, tag_id) VALUES (?, ?)',
                                    (note_id, tag_row[0])
                                )
                    conn.commit()
                    task['success'] += 1
                else:
                    # No tags found - still count as processed but not successful
                    task['failed'] += 1
                    task['results'].append({'note_id': note_id, 'error': 'No tags extracted'})
                
            except Exception as e:
                task['failed'] += 1
                task['results'].append({'note_id': note_id, 'error': str(e)})
            
            task['completed'] += 1
        
        task['status'] = 'completed' if not task['stopped'] else 'stopped'
        
    except Exception as e:
        task['status'] = 'error'
        task['results'].append({'error': str(e)})
    finally:
        conn.close()

