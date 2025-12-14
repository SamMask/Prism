# -*- coding: utf-8 -*-
"""
Tags API Routes
Prism v1.4.1
"""

import sqlite3
from flask import request, jsonify

from . import tags_bp
from db import get_db, transaction  # BUG-002 Fix: 引入 transaction()


@tags_bp.route('/tags', methods=['GET'])
def get_tags():
    """取得所有標籤及其使用次數"""
    try:
        db = get_db()

        rows = db.execute('''
            SELECT 
                t.id,
                t.name,
                COUNT(nt.note_id) as count
            FROM Tags t
            LEFT JOIN Note_Tags nt ON t.id = nt.tag_id
            GROUP BY t.id
            ORDER BY t.name
        ''').fetchall()

        tags_list = [{
            'id': row['id'],
            'name': row['name'],
            'count': row['count']
        } for row in rows]

        return jsonify({
            'status': 'success',
            'data': tags_list
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@tags_bp.route('/tags/<int:tag_id>', methods=['PUT'])
def rename_tag(tag_id):
    """重新命名標籤"""
    try:
        data = request.get_json()

        if not data or not data.get('name'):
            return jsonify({
                'status': 'error',
                'message': 'Tag name is required'
            }), 400

        new_name = data.get('name').strip()
        if not new_name:
            return jsonify({
                'status': 'error',
                'message': 'Tag name cannot be empty'
            }), 400

        db = get_db()

        existing = db.execute('SELECT id FROM Tags WHERE id = ?', (tag_id,)).fetchone()
        if existing is None:
            return jsonify({
                'status': 'error',
                'message': 'Tag not found'
            }), 404

        duplicate = db.execute('SELECT id FROM Tags WHERE name = ? AND id != ?', (new_name, tag_id)).fetchone()
        if duplicate:
            return jsonify({
                'status': 'error',
                'message': 'Tag name already exists'
            }), 409

        db.execute('UPDATE Tags SET name = ? WHERE id = ?', (new_name, tag_id))
        db.commit()

        return jsonify({'status': 'success'})

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@tags_bp.route('/tags/<int:tag_id>', methods=['DELETE'])
def delete_tag(tag_id):
    """刪除標籤"""
    try:
        db = get_db()

        existing = db.execute('SELECT id FROM Tags WHERE id = ?', (tag_id,)).fetchone()
        if existing is None:
            return jsonify({
                'status': 'error',
                'message': 'Tag not found'
            }), 404

        db.execute('DELETE FROM Tags WHERE id = ?', (tag_id,))
        db.commit()

        return jsonify({'status': 'success'})

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@tags_bp.route('/tags/merge', methods=['POST'])
def merge_tags():
    """合併多個標籤到目標標籤"""
    try:
        data = request.get_json()

        if not data or not data.get('source_tag_ids') or not data.get('target_tag_id'):
            return jsonify({
                'status': 'error',
                'message': 'source_tag_ids and target_tag_id are required'
            }), 400

        source_tag_ids = data.get('source_tag_ids')
        target_tag_id = data.get('target_tag_id')

        if not isinstance(source_tag_ids, list) or len(source_tag_ids) == 0:
            return jsonify({
                'status': 'error',
                'message': 'source_tag_ids must be a non-empty array'
            }), 400

        if target_tag_id in source_tag_ids:
            return jsonify({
                'status': 'error',
                'message': 'target_tag_id cannot be in source_tag_ids'
            }), 400

        db = get_db()

        target = db.execute('SELECT id FROM Tags WHERE id = ?', (target_tag_id,)).fetchone()
        if target is None:
            return jsonify({
                'status': 'error',
                'message': 'Target tag not found'
            }), 404

        # BUG-002 Fix: 使用 transaction() context manager 確保原子性
        with transaction() as db:
            merged_count = 0

            for source_id in source_tag_ids:
                source = db.execute('SELECT id FROM Tags WHERE id = ?', (source_id,)).fetchone()
                if source is None:
                    continue

                note_ids = db.execute(
                    'SELECT note_id FROM Note_Tags WHERE tag_id = ?',
                    (source_id,)
                ).fetchall()

                for note_row in note_ids:
                    db.execute(
                        'INSERT OR IGNORE INTO Note_Tags (note_id, tag_id) VALUES (?, ?)',
                        (note_row[0], target_tag_id)
                    )

                db.execute('DELETE FROM Tags WHERE id = ?', (source_id,))
                merged_count += 1

        return jsonify({
            'status': 'success',
            'data': {'merged_count': merged_count}
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
