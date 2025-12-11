# -*- coding: utf-8 -*-
"""
Notes CRUD Operations
Local Insight v1.0

Routes:
- GET    /api/notes         - 取得筆記列表
- GET    /api/notes/<id>    - 取得單一筆記
- POST   /api/notes         - 新增筆記
- PUT    /api/notes/<id>    - 更新筆記
- DELETE /api/notes/<id>    - 刪除筆記
"""

import json
import sqlite3
from flask import request, jsonify

from . import notes_bp
from ..helpers import parse_tags_json, parse_urls_json
from db import get_db


@notes_bp.route('/notes', methods=['GET'])
def get_notes():
    """
    取得筆記列表 (包含關聯的 tags 與 urls，支援分頁與篩選)
    """
    try:
        db = get_db()

        # 取得分頁參數
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # 取得篩選參數 (v0.5 新增)
        keyword = request.args.get('q', '', type=str)
        note_type = request.args.get('type', '', type=str)
        tag_ids_str = request.args.get('tags', '', type=str)
        tag_mode = request.args.get('tag_mode', 'AND', type=str).upper()  # 'AND' or 'OR'
        include_archived = request.args.get('include_archived', 'false', type=str).lower() == 'true'  # v0.8.9 封存機制
        sort_by = request.args.get('sort', 'updated', type=str)  # v0.9.0 排序方式: 'updated', 'custom', 'created'

        # 參數驗證
        if page < 1:
            page = 1
        if per_page < 1:
            per_page = 20
        if per_page > 100:
            per_page = 100
        if tag_mode not in ('AND', 'OR'):
            tag_mode = 'AND'

        # 動態組裝 SQL WHERE 子句
        where_clauses = []
        params = []
        
        # v0.8.9: 預設排除已封存筆記
        if not include_archived:
            where_clauses.append("COALESCE(n.is_archived, 0) = 0")

        # 關鍵字搜尋 (FTS5 全文檢索 v0.6, 修正 v0.8.9)
        if keyword:
            # v0.8.9: 限制關鍵字長度防止 DoS
            keyword = keyword[:200]
            
            # v0.8.9: 移除 FTS5 特殊語法字元
            for char in '"()':
                keyword = keyword.replace(char, '')
            
            # 只保留字母數字和空格
            safe_keyword = "".join([c for c in keyword if c.isalnum() or c.isspace()])
            tokens = safe_keyword.split()
            if tokens:
                fts_query = " ".join([f'"{token}"*' for token in tokens])
                where_clauses.append("n.id IN (SELECT rowid FROM Notes_FTS WHERE Notes_FTS MATCH ?)")
                params.append(fts_query)

        # 類型過濾
        if note_type and note_type.lower() != 'all':
            where_clauses.append("n.type = ?")
            params.append(note_type)

        # 標籤過濾 (支援 AND/OR 模式)
        if tag_ids_str:
            try:
                tag_ids = [int(tid) for tid in tag_ids_str.split(',') if tid.strip()]
                if tag_ids:
                    if tag_mode == 'OR':
                        # OR 模式: 筆記只需包含任一選中標籤
                        placeholders = ','.join(['?' for _ in tag_ids])
                        where_clauses.append(f"""
                            EXISTS (SELECT 1 FROM Note_Tags nt WHERE nt.note_id = n.id AND nt.tag_id IN ({placeholders}))
                        """)
                        params.extend(tag_ids)
                    else:
                        # AND 模式 (預設): 筆記必須包含所有選中標籤
                        for tag_id in tag_ids:
                            where_clauses.append("""
                                EXISTS (SELECT 1 FROM Note_Tags nt WHERE nt.note_id = n.id AND nt.tag_id = ?)
                            """)
                            params.append(tag_id)
            except ValueError:
                pass

        # 組合 WHERE 子句
        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)

        # 1. 先查詢符合條件的總筆記數
        count_query = f'SELECT COUNT(*) as count FROM Notes n {where_sql}'
        total = db.execute(count_query, params).fetchone()['count']

        # 計算 OFFSET 與總頁數
        offset = (page - 1) * per_page
        total_pages = (total + per_page - 1) // per_page

        # 2. 使用子查詢取得分頁筆記及其關聯的標籤與網址
        # v1.0: 使用 json_group_array 取代 GROUP_CONCAT 序列化
        data_query = f'''
            SELECT
                n.id,
                n.title,
                n.content,
                n.type,
                n.remarks,
                n.cover_image,
                COALESCE(n.cover_position, 'top') as cover_position,
                COALESCE(n.editor_layout, 'single') as editor_layout,
                COALESCE(n.is_pinned, 0) as is_pinned,
                n.created_at,
                n.updated_at,
                (SELECT json_group_array(json_object('id', t2.id, 'name', t2.name))
                 FROM Note_Tags nt2 
                 JOIN Tags t2 ON nt2.tag_id = t2.id 
                 WHERE nt2.note_id = n.id) as tags_json,
                (SELECT json_group_array(s2.url)
                 FROM Source_Urls s2 
                 WHERE s2.note_id = n.id) as urls_json
            FROM Notes n
            {where_sql}
            ORDER BY COALESCE(n.is_pinned, 0) DESC, 
                     {('COALESCE(n.sort_order, n.id) ASC' if sort_by == 'custom' else 
                       'n.created_at DESC' if sort_by == 'created' else 
                       'n.updated_at DESC')}
            LIMIT ? OFFSET ?
        '''
        
        data_params = params + [per_page, offset]
        rows = db.execute(data_query, data_params).fetchall()


        # 3. 處理結果 (v1.0: 使用 JSON 解析取代字串分割)
        notes_list = []
        for row in rows:
            note = {
                'id': row['id'],
                'title': row['title'],
                'content': row['content'],
                'type': row['type'],
                'remarks': row['remarks'],
                'cover_image': row['cover_image'],
                'cover_position': row['cover_position'] if row['cover_position'] else 'top',
                'editor_layout': row['editor_layout'] if row['editor_layout'] else 'single',
                'is_pinned': bool(row['is_pinned']) if row['is_pinned'] else False,
                'created_at': row['created_at'],
                'updated_at': row['updated_at'],
                'tags': parse_tags_json(row['tags_json']),
                'urls': parse_urls_json(row['urls_json']),
            }
            notes_list.append(note)

        return jsonify({
            'status': 'success',
            'data': notes_list,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'total_pages': total_pages
            }
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@notes_bp.route('/notes/<int:note_id>', methods=['GET'])
def get_note(note_id):
    """取得單一筆記詳情"""
    try:
        db = get_db()

        # v1.0: 使用 json_group_array 取代 GROUP_CONCAT
        query = '''
            SELECT
                n.id,
                n.title,
                n.content,
                n.type,
                n.remarks,
                n.cover_image,
                COALESCE(n.cover_position, 'top') as cover_position,
                COALESCE(n.editor_layout, 'single') as editor_layout,
                n.prompt_params,
                n.created_at,
                n.updated_at,
                (SELECT json_group_array(json_object('id', t2.id, 'name', t2.name))
                 FROM Note_Tags nt2 
                 JOIN Tags t2 ON nt2.tag_id = t2.id 
                 WHERE nt2.note_id = n.id) as tags_json,
                (SELECT json_group_array(s2.url)
                 FROM Source_Urls s2 
                 WHERE s2.note_id = n.id) as urls_json
            FROM Notes n
            WHERE n.id = ?
        '''

        row = db.execute(query, (note_id,)).fetchone()

        if row is None:
            return jsonify({
                'status': 'error',
                'message': 'Note not found'
            }), 404

        # 解析 prompt_params
        prompt_params = None
        if row['prompt_params']:
            try:
                prompt_params = json.loads(row['prompt_params'])
            except (json.JSONDecodeError, TypeError):
                prompt_params = None

        note = {
            'id': row['id'],
            'title': row['title'],
            'content': row['content'],
            'type': row['type'],
            'remarks': row['remarks'],
            'cover_image': row['cover_image'],
            'cover_position': row['cover_position'] if row['cover_position'] else 'top',
            'editor_layout': row['editor_layout'] if row['editor_layout'] else 'single',
            'prompt_params': prompt_params,
            'created_at': row['created_at'],
            'updated_at': row['updated_at'],
            'tags': parse_tags_json(row['tags_json']),
            'urls': parse_urls_json(row['urls_json']),
        }

        return jsonify({
            'status': 'success',
            'data': note
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@notes_bp.route('/notes', methods=['POST'])
def create_note():
    """新增筆記"""
    try:
        data = request.get_json()

        if not data or not data.get('title') or not data.get('content'):
            return jsonify({
                'status': 'error',
                'message': 'Title and content are required'
            }), 400

        db = get_db()

        try:
            # 處理 prompt_params (v0.6.5 - Prompt Builder)
            prompt_params = data.get('prompt_params')
            if prompt_params and isinstance(prompt_params, dict):
                prompt_params = json.dumps(prompt_params, ensure_ascii=False)
            
            cursor = db.execute('''
                INSERT INTO Notes (title, content, type, remarks, cover_image, cover_position, editor_layout, prompt_params)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.get('title'),
                data.get('content'),
                data.get('type', '筆記'),
                data.get('remarks', ''),
                data.get('cover_image'),
                data.get('cover_position', 'top'),
                data.get('editor_layout', 'single'),
                prompt_params
            ))

            note_id = cursor.lastrowid

            # 處理標籤
            tags = data.get('tags', [])
            if tags:
                for tag_name in tags:
                    if tag_name.strip():
                        db.execute('INSERT OR IGNORE INTO Tags (name) VALUES (?)', (tag_name.strip(),))
                        tag_row = db.execute('SELECT id FROM Tags WHERE name = ?', (tag_name.strip(),)).fetchone()
                        tag_id = tag_row[0]
                        db.execute('INSERT INTO Note_Tags (note_id, tag_id) VALUES (?, ?)', (note_id, tag_id))

            # 處理網址
            urls = data.get('urls', [])
            if urls:
                for url in urls:
                    if url.strip():
                        db.execute('INSERT INTO Source_Urls (note_id, url) VALUES (?, ?)', (note_id, url.strip()))

            db.commit()

            return jsonify({
                'status': 'success',
                'data': {'note_id': note_id}
            }), 201

        except sqlite3.Error as e:
            db.rollback()
            raise e

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@notes_bp.route('/notes/<int:note_id>', methods=['PUT'])
def update_note(note_id):
    """更新筆記"""
    try:
        data = request.get_json()

        if not data or not data.get('title') or not data.get('content'):
            return jsonify({
                'status': 'error',
                'message': 'Title and content are required'
            }), 400

        db = get_db()

        existing = db.execute('SELECT id, content FROM Notes WHERE id = ?', (note_id,)).fetchone()
        if existing is None:
            return jsonify({
                'status': 'error',
                'message': 'Note not found'
            }), 404

        try:
            # 儲存舊版本到 Note_History (v0.6 時光機功能)
            old_content = existing[1]
            new_content = data.get('content', '')
            
            if old_content != new_content:
                old_len = len(old_content) if old_content else 0
                new_len = len(new_content) if new_content else 0
                diff_summary = f"字數變化: {old_len} → {new_len}"
                
                db.execute('''
                    INSERT INTO Note_History (note_id, content, diff_summary)
                    VALUES (?, ?, ?)
                ''', (note_id, old_content, diff_summary))
            
            # 處理 prompt_params (v0.6.5 - Prompt Builder)
            prompt_params = data.get('prompt_params')
            if prompt_params and isinstance(prompt_params, dict):
                prompt_params = json.dumps(prompt_params, ensure_ascii=False)
            
            # 更新 Notes
            db.execute('''
                UPDATE Notes
                SET title = ?, content = ?, type = ?, remarks = ?, cover_image = ?,
                    cover_position = ?, editor_layout = ?, prompt_params = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (
                data.get('title'),
                data.get('content'),
                data.get('type', '筆記'),
                data.get('remarks', ''),
                data.get('cover_image'),
                data.get('cover_position', 'top'),
                data.get('editor_layout', 'single'),
                prompt_params,
                note_id
            ))

            # 重新處理標籤
            db.execute('DELETE FROM Note_Tags WHERE note_id = ?', (note_id,))
            tags = data.get('tags', [])
            if tags:
                for tag_name in tags:
                    if tag_name.strip():
                        db.execute('INSERT OR IGNORE INTO Tags (name) VALUES (?)', (tag_name.strip(),))
                        tag_row = db.execute('SELECT id FROM Tags WHERE name = ?', (tag_name.strip(),)).fetchone()
                        tag_id = tag_row[0]
                        db.execute('INSERT INTO Note_Tags (note_id, tag_id) VALUES (?, ?)', (note_id, tag_id))

            # 重新處理網址
            db.execute('DELETE FROM Source_Urls WHERE note_id = ?', (note_id,))
            urls = data.get('urls', [])
            if urls:
                for url in urls:
                    if url.strip():
                        db.execute('INSERT INTO Source_Urls (note_id, url) VALUES (?, ?)', (note_id, url.strip()))

            db.commit()

            return jsonify({'status': 'success'})

        except sqlite3.Error as e:
            db.rollback()
            raise e

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@notes_bp.route('/notes/<int:note_id>', methods=['DELETE'])
def delete_note(note_id):
    """刪除筆記"""
    try:
        db = get_db()

        existing = db.execute('SELECT id FROM Notes WHERE id = ?', (note_id,)).fetchone()
        if existing is None:
            return jsonify({
                'status': 'error',
                'message': 'Note not found'
            }), 404

        # Manually cascade delete related data (since foreign keys might not be enabled)
        db.execute('DELETE FROM Note_History WHERE note_id = ?', (note_id,))
        db.execute('DELETE FROM Note_Tags WHERE note_id = ?', (note_id,))
        db.execute('DELETE FROM Source_Urls WHERE note_id = ?', (note_id,))
        db.execute('DELETE FROM Notes WHERE id = ?', (note_id,))
        db.commit()

        return jsonify({'status': 'success'})

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
