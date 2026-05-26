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
from flask import request, jsonify, current_app

from . import notes_bp
from ..helpers import parse_tags_json, parse_urls_json
from db import get_db






@notes_bp.route('/notes', methods=['GET'])
def get_notes():
    """
    取得筆記列表 (Phase 0 Step 3: 使用 QueryBuilder 重構)

    支援功能:
    - 分頁 (page, per_page)
    - 關鍵字搜尋 (q) - FTS5 全文檢索
    - 分類過濾 (type/category_id)
    - 標籤過濾 (tags) - AND/OR 模式
    - 封存篩選 (include_archived)
    - 排序 (sort) - updated/custom/created
    """
    try:
        db = get_db()
        from utils.query_builder import NoteQueryBuilder
        from utils.search import find_attachment_content_note_ids

        # 1. 解析並驗證參數
        page = max(1, request.args.get('page', 1, type=int))
        per_page = min(100, max(1, request.args.get('per_page', 20, type=int)))

        keyword = request.args.get('q', '', type=str)[:200]  # 限制長度防 DoS
        note_type = request.args.get('type', '', type=str)
        tag_ids_str = request.args.get('tags', '', type=str)
        tag_mode = request.args.get('tag_mode', 'AND', type=str).upper()
        include_archived = request.args.get('include_archived', 'false', type=str).lower() == 'true'
        archived_only = request.args.get('archived', 'false', type=str).lower() == 'true'
        pinned_only = request.args.get('pinned_only', 'false', type=str).lower() == 'true'
        category_id = request.args.get('category_id', type=int)
        sort_by = request.args.get('sort', 'updated', type=str)

        # 2. 使用 QueryBuilder 建構 WHERE 子句
        builder = NoteQueryBuilder()

        # archived=true 只看封存；include_archived=true 則包含封存與未封存
        if archived_only:
            builder.filter_archived_only()
        else:
            builder.filter_archived(include_archived)

        builder.filter_pinned(pinned_only)

        # 關鍵字搜尋: title/content FTS + remarks/tags/attachments
        if keyword:
            attachment_note_ids = find_attachment_content_note_ids(
                db,
                keyword,
                current_app.root_path
            )
            builder.search_card_fields(keyword, attachment_note_ids)

        # 分類過濾 (Phase 0: type 欄位已移除，但為向後相容保留 API)
        if note_type and note_type.lower() != 'all':
            # 嘗試將 type 名稱轉為 category_id
            category = db.execute(
                'SELECT id FROM Categories WHERE name = ? LIMIT 1',
                (note_type,)
            ).fetchone()
            if category:
                builder.filter_category(category['id'])

        if category_id:
            builder.filter_category(category_id)

        # 標籤過濾
        if tag_ids_str:
            try:
                tag_ids = [int(tid) for tid in tag_ids_str.split(',') if tid.strip()]
                if tag_ids:
                    tag_mode = 'OR' if tag_mode == 'OR' else 'AND'
                    builder.filter_tags(tag_ids, mode=tag_mode)
            except ValueError:
                pass

        # 3. 建構 SQL 查詢
        where_sql, params = builder.build()

        # 查詢總數
        count_query = f'SELECT COUNT(*) as count FROM Notes n {where_sql}'
        total = db.execute(count_query, params).fetchone()['count']

        # 計算分頁
        offset = (page - 1) * per_page
        total_pages = (total + per_page - 1) // per_page

        # 查詢資料 (Phase 0 Step 3: SQLite 直接返回 JSON，無需 Python 解析)
        sort_clause = {
            'custom': 'COALESCE(n.sort_order, n.id) ASC',
            'created': 'n.created_at DESC',
            'updated': 'n.updated_at DESC'
        }.get(sort_by, 'n.updated_at DESC')

        data_query = f'''
            SELECT
                n.id,
                n.title,
                n.content,
                COALESCE(c.name, 'Uncategorized') as category_name,
                n.remarks,
                n.cover_image,
                COALESCE(n.cover_position, 'top') as cover_position,
                COALESCE(n.editor_layout, 'single') as editor_layout,
                COALESCE(n.is_pinned, 0) as is_pinned,
                COALESCE(n.is_archived, 0) as is_archived,
                n.category_id,
                n.created_at,
                n.updated_at,
                COALESCE(
                    (SELECT json_group_array(json_object('id', t2.id, 'name', t2.name))
                     FROM Note_Tags nt2
                     JOIN Tags t2 ON nt2.tag_id = t2.id
                     WHERE nt2.note_id = n.id),
                    json_array()
                ) as tags,
                COALESCE(
                    (SELECT json_group_array(s2.url)
                     FROM Source_Urls s2
                     WHERE s2.note_id = n.id),
                    json_array()
                ) as urls
            FROM Notes n
            LEFT JOIN Categories c ON n.category_id = c.id
            {where_sql}
            ORDER BY COALESCE(n.is_pinned, 0) DESC, {sort_clause}
            LIMIT ? OFFSET ?
        '''

        data_params = params + [per_page, offset]
        rows = db.execute(data_query, data_params).fetchall()

        # 4. 組裝結果 (Phase 0 Step 3: 移除 parse_tags_json)
        notes_list = []
        for row in rows:
            note = {
                'id': row['id'],
                'title': row['title'],
                'content': row['content'],
                'type': row['category_name'],  # 向後相容
                'category_name': row['category_name'],
                'remarks': row['remarks'],
                'cover_image': row['cover_image'],
                'cover_position': row['cover_position'],
                'editor_layout': row['editor_layout'],
                'is_pinned': bool(row['is_pinned']),
                'is_archived': bool(row['is_archived']),
                'category_id': row['category_id'],
                'created_at': row['created_at'],
                'updated_at': row['updated_at'],
                'tags': json.loads(row['tags']) if row['tags'] else [],
                'urls': json.loads(row['urls']) if row['urls'] else [],
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
    """取得單一筆記詳情 (v2.0: 包含卡片譜系 parent_id)"""
    try:
        db = get_db()

        # parent_id is stable since Migration v10; no schema check needed
        parent_cols = ", n.parent_id, p.title as parent_title"
        parent_join = "LEFT JOIN Notes p ON n.parent_id = p.id"

        query = f'''
            SELECT
                n.id,
                n.title,
                n.content,
                COALESCE(c.name, 'Uncategorized') as category_name,
                n.remarks,
                n.cover_image,
                COALESCE(n.cover_position, 'top') as cover_position,
                COALESCE(n.editor_layout, 'single') as editor_layout,
                COALESCE(n.is_pinned, 0) as is_pinned,
                COALESCE(n.is_archived, 0) as is_archived,
                n.category_id,
                n.prompt_params,
                n.created_at,
                n.updated_at
                {parent_cols},
                (SELECT json_group_array(json_object('id', t2.id, 'name', t2.name))
                 FROM Note_Tags nt2 
                 JOIN Tags t2 ON nt2.tag_id = t2.id 
                 WHERE nt2.note_id = n.id) as tags_json,
                (SELECT json_group_array(s2.url)
                 FROM Source_Urls s2 
                 WHERE s2.note_id = n.id) as urls_json
            FROM Notes n
            LEFT JOIN Categories c ON n.category_id = c.id
            {parent_join}
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
            'type': row['category_name'],
            'remarks': row['remarks'],
            'cover_image': row['cover_image'],
            'cover_position': row['cover_position'] if row['cover_position'] else 'top',
            'editor_layout': row['editor_layout'] if row['editor_layout'] else 'single',
            'is_pinned': bool(row['is_pinned']),
            'is_archived': bool(row['is_archived']),
            'category_id': row['category_id'],
            'prompt_params': prompt_params,
            'created_at': row['created_at'],
            'updated_at': row['updated_at'],
            'tags': parse_tags_json(row['tags_json']),
            'urls': parse_urls_json(row['urls_json']),
        }
        
        # parent_id 在現行 schema 為穩定欄位
        parent_id = row['parent_id']
        note['parent_id'] = parent_id
        note['parent_title'] = row['parent_title'] if parent_id else None

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
    """新增筆記 (v1.3: 標題自動生成)"""
    try:
        data = request.get_json()

        # v1.3: 內容必填，標題可選（自動生成）
        if not data or not data.get('content'):
            return jsonify({
                'status': 'error',
                'message': 'Content is required'
            }), 400

        db = get_db()

        try:
            # v1.3: 自動生成標題 - 使用內容第一行前50字元，或建立時間
            title = data.get('title', '').strip()
            if not title:
                content = data.get('content', '')
                # 取第一行（遇到換行就截斷）
                first_line = content.split('\n')[0].strip()
                # 移除 Markdown 符號
                first_line = first_line.lstrip('#').lstrip('>').lstrip('-').lstrip('*').strip()
                if first_line:
                    title = first_line[:50] + ('...' if len(first_line) > 50 else '')
                else:
                    # Fallback: 使用建立時間
                    from datetime import datetime
                    title = f"Note - {datetime.now().strftime('%Y/%m/%d %H:%M')}"
            
            # 處理 prompt_params (v0.6.5 - Prompt Builder)
            prompt_params = data.get('prompt_params')
            if prompt_params and isinstance(prompt_params, dict):
                prompt_params = json.dumps(prompt_params, ensure_ascii=False)

            # Phase 0 Step 0.1.2: 直接使用 category_id，不再支援 type 參數
            category_id = data.get('category_id')
            if category_id is None:
                # 獲取預設分類
                default_cat = db.execute('SELECT id FROM Categories WHERE is_default = 1').fetchone()
                category_id = default_cat[0] if default_cat else None

            cursor = db.execute('''
                INSERT INTO Notes (
                    title, content, category_id, remarks, cover_image,
                    cover_position, editor_layout, prompt_params, is_pinned, is_archived
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                title,
                data.get('content'),
                category_id,
                data.get('remarks', ''),
                data.get('cover_image'),
                data.get('cover_position', 'top'),
                data.get('editor_layout', 'single'),
                prompt_params,
                1 if data.get('is_pinned') else 0,
                1 if data.get('is_archived') else 0
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

        existing = db.execute(
            'SELECT id, content, COALESCE(is_pinned, 0) as is_pinned, COALESCE(is_archived, 0) as is_archived FROM Notes WHERE id = ?',
            (note_id,)
        ).fetchone()
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

            # Phase 0 Step 0.1.2: 直接使用 category_id，不再支援 type 參數
            category_id = data.get('category_id')
            if category_id is None:
                # 保留原有的 category_id（不修改）
                existing_note = db.execute('SELECT category_id FROM Notes WHERE id = ?', (note_id,)).fetchone()
                category_id = existing_note[0] if existing_note else None

            is_pinned = existing['is_pinned'] if 'is_pinned' not in data else 1 if data.get('is_pinned') else 0
            is_archived = existing['is_archived'] if 'is_archived' not in data else 1 if data.get('is_archived') else 0

            # 更新 Notes
            db.execute('''
                UPDATE Notes
                SET title = ?, content = ?, category_id = ?, remarks = ?, cover_image = ?,
                    cover_position = ?, editor_layout = ?, prompt_params = ?,
                    is_pinned = ?, is_archived = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (
                data.get('title'),
                data.get('content'),
                category_id,
                data.get('remarks', ''),
                data.get('cover_image'),
                data.get('cover_position', 'top'),
                data.get('editor_layout', 'single'),
                prompt_params,
                is_pinned,
                is_archived,
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
    """刪除筆記 (v1.1: 同時刪除關聯圖片)"""
    try:
        db = get_db()

        existing = db.execute('SELECT id, content, cover_image FROM Notes WHERE id = ?', (note_id,)).fetchone()
        if existing is None:
            return jsonify({
                'status': 'error',
                'message': 'Note not found'
            }), 404

        # v1.2: 刪除關聯的圖片檔案 (含引用計數檢查)
        _cleanup_note_images(existing['content'], existing['cover_image'], note_id)

        # ON DELETE CASCADE handles Note_History / Note_Tags / Source_Urls
        db.execute('DELETE FROM Notes WHERE id = ?', (note_id,))
        db.commit()

        return jsonify({'status': 'success'})

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


def _cleanup_note_images(content, cover_image, note_id):
    """
    清理筆記關聯的圖片檔案
    - 從 content 中提取 /static/uploads/ 路徑的圖片
    - 刪除 cover_image 和對應的縮圖
    
    v1.2: 新增引用計數檢查，避免刪除其他筆記仍在使用的圖片 (🟡-1 修復)
    """
    import re
    import os
    from flask import current_app
    from db import get_db
    
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'static/uploads')
    deleted_files = []
    skipped_files = []
    
    try:
        db = get_db()
        
        # 收集所有要檢查的圖片路徑
        image_paths = set()
        
        # 1. 處理 cover_image
        if cover_image and cover_image.startswith('/static/uploads/'):
            image_paths.add(cover_image)
        
        # 2. 從 content 中提取所有 /static/uploads/ 的圖片
        if content:
            pattern = r'/static/uploads/([^\s\)\]\"\'\>]+)'
            matches = re.findall(pattern, content)
            for m in matches:
                image_paths.add(f'/static/uploads/{m}')
        
        # 3. 對每個圖片檢查引用計數後再刪除
        for img_path in image_paths:
            # 檢查是否有其他筆記引用此圖片 (在 cover_image 或 content 中)
            ref_count = db.execute('''
                SELECT COUNT(*) FROM Notes
                WHERE id != ? AND (cover_image = ? OR content LIKE ?)
            ''', (note_id, img_path, f'%{img_path}%')).fetchone()[0]
            
            if ref_count > 0:
                # 仍有其他筆記引用，跳過刪除
                skipped_files.append(f"{img_path} (referenced by {ref_count} notes)")
                continue
            
            # 安全刪除圖片
            filename = img_path.replace('/static/uploads/', '')
            filepath = os.path.join(upload_folder, filename)
            
            if os.path.exists(filepath):
                os.remove(filepath)
                deleted_files.append(filename)
            
            # 嘗試刪除對應的縮圖
            name_without_ext = os.path.splitext(filename)[0]
            
            if not filename.endswith('_thumb.webp'):
                # 如果是原圖，刪除 _thumb.webp
                thumb_name = f"{name_without_ext}_thumb.webp"
                thumb_path = os.path.join(upload_folder, thumb_name)
                if os.path.exists(thumb_path):
                    os.remove(thumb_path)
                    deleted_files.append(thumb_name)
            else:
                # 如果是縮圖，嘗試刪除原圖
                original_base = name_without_ext.replace('_thumb', '')
                for ext in ['.jpg', '.png', '.gif', '.webp']:
                    original_path = os.path.join(upload_folder, f"{original_base}{ext}")
                    if os.path.exists(original_path):
                        os.remove(original_path)
                        deleted_files.append(f"{original_base}{ext}")
        
        if deleted_files:
            print(f"[Cleanup] Deleted {len(deleted_files)} files: {deleted_files}")
        if skipped_files:
            print(f"[Cleanup] Skipped {len(skipped_files)} files (still referenced): {skipped_files}")
            
    except Exception as e:
        print(f"[Warning] Image cleanup error: {e}")

