# -*- coding: utf-8 -*-
"""
Notes Batch Operations
Prism v1.4.1

Routes:
- POST /api/notes/batch/type   - 批量修改分類
- POST /api/notes/batch/tags   - 批量修改標籤
- POST /api/notes/batch/delete - 批量刪除
"""

import sqlite3
from flask import request, jsonify

from . import notes_bp
from db import get_db


@notes_bp.route('/notes/batch/type', methods=['POST'])
def batch_update_type():
    """
    批量修改筆記分類

    Phase 0 Step 0.1.2: 改用 category_id 參數，不再支援 type 參數
    """
    try:
        data = request.get_json()

        if not data or not data.get('note_ids') or not data.get('category_id'):
            return jsonify({
                'status': 'error',
                'message': 'note_ids and category_id are required'
            }), 400

        note_ids = data.get('note_ids')
        category_id = data.get('category_id')

        if not isinstance(note_ids, list) or len(note_ids) == 0:
            return jsonify({
                'status': 'error',
                'message': 'note_ids must be a non-empty array'
            }), 400
        
        # v0.8.9: 驗證所有 note_ids 都是整數，並限制批量大小
        if len(note_ids) > 500:
            return jsonify({
                'status': 'error',
                'message': 'Maximum 500 notes per batch'
            }), 400
        
        if not all(isinstance(nid, int) for nid in note_ids):
            return jsonify({
                'status': 'error',
                'message': 'All note_ids must be integers'
            }), 400

        db = get_db()

        try:
            # Phase 0 Step 0.1.2: 驗證 category_id 存在
            category_exists = db.execute(
                'SELECT id FROM Categories WHERE id = ?',
                (category_id,)
            ).fetchone()

            if not category_exists:
                return jsonify({
                    'status': 'error',
                    'message': f'Category {category_id} does not exist'
                }), 400

            placeholders = ','.join('?' * len(note_ids))
            cursor = db.execute(f'''
                UPDATE Notes
                SET category_id = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id IN ({placeholders})
            ''', [category_id] + note_ids)
            
            db.commit()

            return jsonify({
                'status': 'success',
                'data': {'updated_count': cursor.rowcount}
            })

        except sqlite3.Error as e:
            db.rollback()
            raise e

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@notes_bp.route('/notes/batch/tags', methods=['POST'])
def batch_update_tags():
    """批量修改筆記標籤"""
    try:
        data = request.get_json()

        if not data or not data.get('note_ids') or not data.get('tags'):
            return jsonify({
                'status': 'error',
                'message': 'note_ids and tags are required'
            }), 400

        note_ids = data.get('note_ids')
        tags = data.get('tags')
        mode = data.get('mode', 'append')

        if not isinstance(note_ids, list) or len(note_ids) == 0:
            return jsonify({
                'status': 'error',
                'message': 'note_ids must be a non-empty array'
            }), 400
        
        # v0.8.9: 驗證所有 note_ids 都是整數，並限制批量大小
        if len(note_ids) > 500:
            return jsonify({
                'status': 'error',
                'message': 'Maximum 500 notes per batch'
            }), 400
        
        if not all(isinstance(nid, int) for nid in note_ids):
            return jsonify({
                'status': 'error',
                'message': 'All note_ids must be integers'
            }), 400

        if mode not in ['append', 'replace']:
            return jsonify({
                'status': 'error',
                'message': 'mode must be "append" or "replace"'
            }), 400

        db = get_db()

        try:
            tags_added = 0
            affected_notes = 0

            for nid in note_ids:
                existing = db.execute('SELECT id FROM Notes WHERE id = ?', (nid,)).fetchone()
                if existing is None:
                    continue

                affected_notes += 1

                if mode == 'replace':
                    db.execute('DELETE FROM Note_Tags WHERE note_id = ?', (nid,))

                for tag_name in tags:
                    if not tag_name or not tag_name.strip():
                        continue

                    tag_name = tag_name.strip()
                    tag_row = db.execute(
                        'SELECT id FROM Tags WHERE name = ? COLLATE NOCASE',
                        (tag_name,)
                    ).fetchone()
                    if tag_row:
                        tag_id = tag_row[0]
                    else:
                        cursor = db.execute('INSERT INTO Tags (name) VALUES (?)', (tag_name,))
                        tag_id = cursor.lastrowid

                    cursor = db.execute('''
                        INSERT OR IGNORE INTO Note_Tags (note_id, tag_id) VALUES (?, ?)
                    ''', (nid, tag_id))
                    if cursor.rowcount > 0:
                        tags_added += 1

                db.execute('UPDATE Notes SET updated_at = CURRENT_TIMESTAMP WHERE id = ?', (nid,))

            db.commit()

            return jsonify({
                'status': 'success',
                'data': {
                    'affected_notes': affected_notes,
                    'tags_added': tags_added,
                    'mode': mode
                }
            })

        except sqlite3.Error as e:
            db.rollback()
            raise e

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@notes_bp.route('/notes/batch/delete', methods=['POST'])
def batch_delete_notes():
    """批量刪除筆記 (v1.1: 同時刪除關聯圖片)"""
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
        
        # v0.8.9: 驗證所有 note_ids 都是整數，並限制批量大小
        if len(note_ids) > 500:
            return jsonify({
                'status': 'error',
                'message': 'Maximum 500 notes per batch'
            }), 400
        
        if not all(isinstance(nid, int) for nid in note_ids):
            return jsonify({
                'status': 'error',
                'message': 'All note_ids must be integers'
            }), 400

        db = get_db()

        try:
            # v1.1: 先取得筆記內容，用於清理圖片
            placeholders = ','.join('?' * len(note_ids))
            notes = db.execute(f'''
                SELECT id, content, cover_image FROM Notes 
                WHERE id IN ({placeholders})
            ''', note_ids).fetchall()
            
            # 清理每個筆記的關聯圖片
            from .crud import _cleanup_note_images
            for note in notes:
                _cleanup_note_images(note['content'], note['cover_image'], note['id'])
            
            # Keep legacy DBs without FK cascades clean before deleting note rows.
            for table in ('Note_Tags', 'Source_Urls', 'Note_History', 'Note_Attachments'):
                db.execute(f'''
                    DELETE FROM {table} WHERE note_id IN ({placeholders})
                ''', note_ids)

            # 刪除資料庫記錄
            cursor = db.execute(f'''
                DELETE FROM Notes WHERE id IN ({placeholders})
            ''', note_ids)
            
            db.commit()

            return jsonify({
                'status': 'success',
                'data': {'deleted_count': cursor.rowcount}
            })

        except sqlite3.Error as e:
            db.rollback()
            raise e

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
