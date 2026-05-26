# -*- coding: utf-8 -*-
"""
Notes Action Operations
Local Insight v1.0

Routes:
- POST /api/notes/<id>/pin       - 切換釘選狀態
- POST /api/notes/<id>/archive   - 切換封存狀態
- POST /api/notes/<id>/duplicate - 複製筆記
- PUT  /api/notes/reorder        - 重新排序筆記
"""

import sqlite3
from flask import request, jsonify

from . import notes_bp
from db import get_db


@notes_bp.route('/notes/<int:note_id>/pin', methods=['POST'])
def toggle_pin_note(note_id):
    """
    切換筆記的釘選狀態
    Request: { pinned: true/false } 或無 body (toggle)
    """
    try:
        db = get_db()

        # 檢查筆記是否存在 - 使用安全查詢
        try:
            existing = db.execute('SELECT id, COALESCE(is_pinned, 0) as is_pinned FROM Notes WHERE id = ?', (note_id,)).fetchone()
        except sqlite3.OperationalError:
            existing = db.execute('SELECT id FROM Notes WHERE id = ?', (note_id,)).fetchone()
            if existing:
                existing = {'id': existing['id'], 'is_pinned': 0}
        
        if existing is None:
            return jsonify({
                'status': 'error',
                'message': 'Note not found'
            }), 404

        data = request.get_json(silent=True) or {}
        
        # 決定新的 pinned 狀態
        if 'pinned' in data:
            new_pinned = 1 if data['pinned'] else 0
        else:
            # Toggle 模式
            current_pinned = existing['is_pinned'] if 'is_pinned' in existing.keys() else 0
            new_pinned = 0 if current_pinned else 1

        db.execute('UPDATE Notes SET is_pinned = ? WHERE id = ?', (new_pinned, note_id))
        db.commit()

        return jsonify({
            'status': 'success',
            'data': {
                'id': note_id,
                'is_pinned': bool(new_pinned)
            }
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@notes_bp.route('/notes/<int:note_id>/archive', methods=['POST'])
def toggle_archive_note(note_id):
    """
    切換筆記的封存狀態
    Request: { archived: true/false } 或無 body (toggle)
    """
    try:
        db = get_db()

        # 檢查筆記是否存在
        try:
            existing = db.execute('SELECT id, COALESCE(is_archived, 0) as is_archived FROM Notes WHERE id = ?', (note_id,)).fetchone()
        except sqlite3.OperationalError:
            existing = db.execute('SELECT id FROM Notes WHERE id = ?', (note_id,)).fetchone()
            if existing:
                existing = {'id': existing['id'], 'is_archived': 0}
        
        if existing is None:
            return jsonify({
                'status': 'error',
                'message': 'Note not found'
            }), 404

        data = request.get_json(silent=True) or {}
        
        # 決定新的 archived 狀態
        if 'archived' in data:
            new_archived = 1 if data['archived'] else 0
        else:
            # Toggle 模式
            current_archived = existing['is_archived'] if 'is_archived' in existing.keys() else 0
            new_archived = 0 if current_archived else 1

        db.execute('UPDATE Notes SET is_archived = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', (new_archived, note_id))
        db.commit()

        return jsonify({
            'status': 'success',
            'data': {
                'id': note_id,
                'is_archived': bool(new_archived)
            }
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@notes_bp.route('/notes/<int:note_id>/duplicate', methods=['POST'])
def duplicate_note(note_id):
    """
    複製筆記 / 建立變體 (Fork)
    
    Phase 3.7: 卡片譜系 (Card Lineage)
    - 當 as_variant=true 時，設定 parent_id 建立父子關係
    - 變體不複製圖片 (僅引用 cover_image 路徑)
    
    Request Body (optional):
    {
        "as_variant": true,          # 是否作為變體 (設定 parent_id)
        "title_suffix": " (v2)"      # 標題後綴 (預設 " (Copy)" 或 " (Variant)")
    }
    """
    try:
        db = get_db()
        data = request.get_json(silent=True) or {}
        
        as_variant = data.get('as_variant', False)
        title_suffix = data.get('title_suffix', ' (Variant)' if as_variant else ' (Copy)')

        original = db.execute('''
            SELECT
                id,
                title,
                content,
                remarks,
                cover_image,
                cover_position,
                editor_layout,
                category_id,
                prompt_params
            FROM Notes
            WHERE id = ?
        ''', (note_id,)).fetchone()
        if original is None:
            return jsonify({
                'status': 'error',
                'message': 'Note not found'
            }), 404

        try:
            new_title = original['title'] + title_suffix

            if as_variant:
                # 變體模式: 設定 parent_id，不重複複製圖片
                cursor = db.execute('''
                    INSERT INTO Notes (
                        title, content, remarks, cover_image, cover_position,
                        editor_layout, category_id, prompt_params, parent_id
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    new_title,
                    original['content'],
                    original['remarks'],
                    original['cover_image'],  # 引用，不複製
                    original['cover_position'],
                    original['editor_layout'],
                    original['category_id'],
                    original['prompt_params'],
                    note_id
                ))
            else:
                # 傳統複製模式
                cursor = db.execute('''
                    INSERT INTO Notes (
                        title, content, remarks, cover_image, cover_position,
                        editor_layout, category_id, prompt_params
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    new_title,
                    original['content'],
                    original['remarks'],
                    original['cover_image'],
                    original['cover_position'],
                    original['editor_layout'],
                    original['category_id'],
                    original['prompt_params'],
                ))

            new_note_id = cursor.lastrowid

            # 複製標籤關聯
            db.execute('''
                INSERT INTO Note_Tags (note_id, tag_id)
                SELECT ?, tag_id FROM Note_Tags WHERE note_id = ?
            ''', (new_note_id, note_id))

            # 複製網址
            db.execute('''
                INSERT INTO Source_Urls (note_id, url)
                SELECT ?, url FROM Source_Urls WHERE note_id = ?
            ''', (new_note_id, note_id))

            db.commit()

            return jsonify({
                'status': 'success',
                'data': {
                    'note_id': new_note_id,
                    'parent_id': note_id if as_variant else None,
                    'is_variant': as_variant
                }
            }), 201

        except sqlite3.Error as e:
            db.rollback()
            raise e

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@notes_bp.route('/notes/reorder', methods=['PUT'])
def reorder_notes():
    """
    重新排序筆記 (拖放排序功能)
    Request: { note_ids: [id1, id2, id3, ...] }
    note_ids 陣列中的順序即為新的排序 (index 0 = sort_order 0)
    """
    try:
        data = request.get_json()

        if not data or not data.get('note_ids'):
            return jsonify({
                'status': 'error',
                'message': 'note_ids is required'
            }), 400

        note_ids = data.get('note_ids')

        if not isinstance(note_ids, list) or len(note_ids) == 0:
            return jsonify({
                'status': 'error',
                'message': 'note_ids must be a non-empty array'
            }), 400
        
        # 限制批量大小
        if len(note_ids) > 500:
            return jsonify({
                'status': 'error',
                'message': 'Maximum 500 notes per reorder'
            }), 400
        
        # 驗證所有 note_ids 都是整數
        if not all(isinstance(nid, int) for nid in note_ids):
            return jsonify({
                'status': 'error',
                'message': 'All note_ids must be integers'
            }), 400

        db = get_db()

        try:
            # 更新每個筆記的 sort_order
            for index, note_id in enumerate(note_ids):
                db.execute(
                    'UPDATE Notes SET sort_order = ? WHERE id = ?',
                    (index, note_id)
                )
            
            db.commit()

            return jsonify({
                'status': 'success',
                'data': {'reordered_count': len(note_ids)}
            })

        except sqlite3.Error as e:
            db.rollback()
            raise e

    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        print(f"[ERROR] reorder_notes failed: {error_msg}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'traceback': error_msg
        }), 500
