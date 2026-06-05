# -*- coding: utf-8 -*-
"""
Categories API Routes
Local Insight v1.8.9
"""

import sqlite3
from flask import request, jsonify

from . import categories_bp
from db import get_db  # v1.8.9: 統一資料庫連線層


@categories_bp.route('/categories', methods=['GET'])
def get_categories():
    """取得所有分類"""
    try:
        db = get_db()

        categories = db.execute('''
            SELECT 
                c.id,
                c.name,
                c.icon,
                c.sort_order,
                c.is_default,
                (SELECT COUNT(*) FROM Notes n WHERE n.category_id = c.id) as count
            FROM Categories c
            ORDER BY c.sort_order ASC
        ''').fetchall()

        categories_list = [{
            'id': row[0],
            'name': row[1],
            'icon': row[2],
            'sort_order': row[3],
            'is_default': bool(row[4]),
            'count': row[5]
        } for row in categories]

        return jsonify({
            'status': 'success',
            'data': categories_list
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@categories_bp.route('/categories', methods=['POST'])
def create_category():
    """新增分類"""
    try:
        data = request.get_json()

        if not data or not data.get('name'):
            return jsonify({
                'status': 'error',
                'message': 'Category name is required'
            }), 400

        name = data.get('name').strip()
        icon = data.get('icon', '📁')
        
        db = get_db()

        existing = db.execute('SELECT id FROM Categories WHERE name = ?', (name,)).fetchone()
        if existing:
            return jsonify({
                'status': 'error',
                'message': 'Category name already exists'
            }), 409

        max_order = db.execute('SELECT MAX(sort_order) FROM Categories').fetchone()[0] or 0
        sort_order = data.get('sort_order', max_order + 1)

        cursor = db.execute('''
            INSERT INTO Categories (name, icon, sort_order, is_default)
            VALUES (?, ?, ?, 0)
        ''', (name, icon, sort_order))
        db.commit()

        return jsonify({
            'status': 'success',
            'data': {'id': cursor.lastrowid}
        }), 201

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@categories_bp.route('/categories/<int:category_id>', methods=['PUT'])
def update_category(category_id):
    """更新分類"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({
                'status': 'error',
                'message': 'Request body is required'
            }), 400

        db = get_db()

        existing = db.execute('SELECT id, name FROM Categories WHERE id = ?', (category_id,)).fetchone()
        if existing is None:
            return jsonify({
                'status': 'error',
                'message': 'Category not found'
            }), 404

        old_name = existing[1]
        new_name = data.get('name', old_name).strip()
        icon = data.get('icon')
        sort_order = data.get('sort_order')

        if not new_name:
            return jsonify({
                'status': 'error',
                'message': 'Category name cannot be empty'
            }), 400

        if new_name != old_name:
            name_exists = db.execute(
                'SELECT id FROM Categories WHERE name = ? AND id != ?',
                (new_name, category_id)
            ).fetchone()
            if name_exists:
                return jsonify({
                    'status': 'error',
                    'message': 'Category name already exists'
                }), 409

        try:
            if icon is not None and sort_order is not None:
                db.execute('''
                    UPDATE Categories SET name = ?, icon = ?, sort_order = ? WHERE id = ?
                ''', (new_name, icon, sort_order, category_id))
            elif icon is not None:
                db.execute('''
                    UPDATE Categories SET name = ?, icon = ? WHERE id = ?
                ''', (new_name, icon, category_id))
            elif sort_order is not None:
                db.execute('''
                    UPDATE Categories SET name = ?, sort_order = ? WHERE id = ?
                ''', (new_name, sort_order, category_id))
            else:
                db.execute('''
                    UPDATE Categories SET name = ? WHERE id = ?
                ''', (new_name, category_id))

            # 注意：Notes 現在使用 category_id，不需要同步 type 欄位
            updated_notes_count = 0

            db.commit()

            return jsonify({
                'status': 'success',
                'data': {'updated_notes_count': updated_notes_count}
            })

        except sqlite3.Error as e:
            db.rollback()
            raise e

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@categories_bp.route('/categories/<int:category_id>', methods=['DELETE'])
def delete_category(category_id):
    """刪除分類"""
    try:
        db = get_db()

        existing = db.execute(
            'SELECT id, name, is_default FROM Categories WHERE id = ?',
            (category_id,)
        ).fetchone()
        
        if existing is None:
            return jsonify({
                'status': 'error',
                'message': 'Category not found'
            }), 404

        if existing[2]:  # is_default
            return jsonify({
                'status': 'error',
                'message': 'Cannot delete the default category'
            }), 400

        old_name = existing[1]
        
        # 檢查該分類下有多少筆記
        notes_count = db.execute(
            'SELECT COUNT(*) FROM Notes WHERE category_id = ?', (category_id,)
        ).fetchone()[0]
        
        # 從請求中取得目標分類
        data = request.get_json() or {}
        target_category_id = data.get('target_category_id')
        
        # 如果有筆記但沒有指定目標分類，返回錯誤
        if notes_count > 0 and not target_category_id:
            return jsonify({
                'status': 'error',
                'message': 'Target category required',
                'notes_count': notes_count
            }), 400
        
        print(f"[Delete Category] 刪除分類 '{old_name}', 目標分類ID: '{target_category_id}', 筆記數: {notes_count}")

        try:
            migrated_count = 0
            if notes_count > 0 and target_category_id:
                cursor = db.execute('''
                    UPDATE Notes SET category_id = ? WHERE category_id = ?
                ''', (target_category_id, category_id))
                migrated_count = cursor.rowcount
                print(f"[Delete Category] 實際遷移的筆記數: {migrated_count}")

            db.execute('DELETE FROM Categories WHERE id = ?', (category_id,))
            db.commit()

            return jsonify({
                'status': 'success',
                'data': {'migrated_notes_count': migrated_count}
            })

        except sqlite3.Error as e:
            db.rollback()
            raise e

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

