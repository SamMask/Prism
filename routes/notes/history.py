# -*- coding: utf-8 -*-
"""
Notes History Operations
Local Insight v1.0

Routes:
- GET  /api/notes/<id>/history               - 取得版本歷史
- POST /api/notes/<id>/restore/<history_id>  - 還原至指定版本
"""

import sqlite3
from flask import jsonify

from . import notes_bp
from db import get_db


@notes_bp.route('/notes/<int:note_id>/history', methods=['GET'])
def get_note_history(note_id):
    """取得筆記的版本歷史"""
    try:
        db = get_db()

        existing = db.execute('SELECT id, title FROM Notes WHERE id = ?', (note_id,)).fetchone()
        if existing is None:
            return jsonify({
                'status': 'error',
                'message': 'Note not found'
            }), 404

        history = db.execute('''
            SELECT id, content, diff_summary, created_at
            FROM Note_History
            WHERE note_id = ?
            ORDER BY created_at DESC
            LIMIT 50
        ''', (note_id,)).fetchall()

        history_list = [{
            'id': row[0],
            'content': row[1],
            'diff_summary': row[2],
            'created_at': row[3]
        } for row in history]

        return jsonify({
            'status': 'success',
            'data': {
                'note_id': note_id,
                'note_title': existing[1],
                'history': history_list,
                'total': len(history_list)
            }
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@notes_bp.route('/notes/<int:note_id>/restore/<int:history_id>', methods=['POST'])
def restore_note_version(note_id, history_id):
    """還原筆記至指定的歷史版本"""
    try:
        db = get_db()

        existing = db.execute('SELECT id, content FROM Notes WHERE id = ?', (note_id,)).fetchone()
        if existing is None:
            return jsonify({
                'status': 'error',
                'message': 'Note not found'
            }), 404

        history = db.execute('''
            SELECT id, content FROM Note_History
            WHERE id = ? AND note_id = ?
        ''', (history_id, note_id)).fetchone()
        
        if history is None:
            return jsonify({
                'status': 'error',
                'message': 'History version not found'
            }), 404

        try:
            # 先保存當前版本
            db.execute('''
                INSERT INTO Note_History (note_id, content, diff_summary)
                VALUES (?, ?, ?)
            ''', (note_id, existing[1], '還原前自動備份'))

            # 還原
            db.execute('''
                UPDATE Notes
                SET content = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (history[1], note_id))

            db.commit()

            return jsonify({
                'status': 'success',
                'message': 'Note restored successfully'
            })

        except sqlite3.Error as e:
            db.rollback()
            raise e

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@notes_bp.route('/notes/<int:note_id>/history', methods=['DELETE'])
def delete_note_history(note_id):
    """清空指定筆記的所有歷史版本"""
    try:
        db = get_db()
        
        # Check note existing
        existing = db.execute('SELECT id FROM Notes WHERE id = ?', (note_id,)).fetchone()
        if existing is None:
            return jsonify({
                'status': 'error',
                'message': 'Note not found'
            }), 404
            
        # Delete history
        cursor = db.execute('DELETE FROM Note_History WHERE note_id = ?', (note_id,))
        deleted_count = cursor.rowcount
        db.commit()
        
        return jsonify({
            'status': 'success',
            'message': f'Deleted {deleted_count} history records',
            'data': {'deleted_count': deleted_count}
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
