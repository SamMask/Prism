# -*- coding: utf-8 -*-
"""
Export API Routes
Local Insight v1.8.9
"""

import os
import json
from datetime import datetime
from flask import jsonify, send_file, current_app, request

from . import export_bp
from db import get_db  # v1.8.9: 統一資料庫連線層


@export_bp.route('/export/json', methods=['GET'])
def export_json():
    """匯出所有資料為 JSON 格式"""
    try:
        db = get_db()

        # 查詢所有筆記
        notes_query = '''
            SELECT
                n.id,
                n.title,
                n.content,
                n.type,
                n.remarks,
                n.cover_image,
                n.created_at,
                n.updated_at,
                (SELECT GROUP_CONCAT(t2.name, '||')
                 FROM Note_Tags nt2 
                 JOIN Tags t2 ON nt2.tag_id = t2.id 
                 WHERE nt2.note_id = n.id) as tags,
                (SELECT GROUP_CONCAT(s2.url, '||')
                 FROM Source_Urls s2 
                 WHERE s2.note_id = n.id) as urls
            FROM Notes n
            ORDER BY n.updated_at DESC
        '''
        notes_rows = db.execute(notes_query).fetchall()

        notes_list = []
        for row in notes_rows:
            note = {
                'id': row['id'],
                'title': row['title'],
                'content': row['content'],
                'type': row['type'],
                'remarks': row['remarks'],
                'cover_image': row['cover_image'],
                'created_at': row['created_at'],
                'updated_at': row['updated_at'],
                'tags': row['tags'].split('||') if row['tags'] else [],
                'urls': row['urls'].split('||') if row['urls'] else []
            }
            notes_list.append(note)

        # 查詢所有標籤
        tags_rows = db.execute('SELECT id, name FROM Tags ORDER BY name').fetchall()
        tags_list = [{'id': row['id'], 'name': row['name']} for row in tags_rows]

        # 組裝匯出資料
        export_data = {
            'export_info': {
                'version': '1.6',
                'exported_at': datetime.now().isoformat(),
                'notes_count': len(notes_list),
                'tags_count': len(tags_list)
            },
            'notes': notes_list,
            'tags': tags_list
        }

        # 設定回應
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'local_insight_export_{timestamp}.json'

        from flask import Response
        response = Response(
            json.dumps(export_data, ensure_ascii=False, indent=2),
            mimetype='application/json',
            headers={
                'Content-Disposition': f'attachment; filename={filename}'
            }
        )

        return response

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@export_bp.route('/export/db', methods=['GET'])
def export_db():
    """匯出 SQLite 資料庫檔案"""
    try:
        db_path = current_app.config['DATABASE']

        if not os.path.exists(db_path):
            return jsonify({
                'status': 'error',
                'message': 'Database file not found'
            }), 404

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'local_insight_backup_{timestamp}.db'

        return send_file(
            db_path,
            mimetype='application/x-sqlite3',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@export_bp.route('/export/images', methods=['POST'])
def export_images():
    """匯出指定的圖片為 ZIP 檔案"""
    try:
        import zipfile
        import io
        import re
        
        data = request.get_json() or {}
        image_urls = data.get('images', [])
        note_title = data.get('note_title', 'images')
        
        if not image_urls:
            return jsonify({
                'status': 'error',
                'message': 'No images provided'
            }), 400
        
        # v1.8.9: 限制匯出圖片數量防止 OOM
        if len(image_urls) > 100:
            return jsonify({
                'status': 'error',
                'message': 'Maximum 100 images per export'
            }), 400
        
        uploads_dir = os.path.join(current_app.root_path, 'static', 'uploads')
        
        # 創建 ZIP 檔案在記憶體中
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for url in image_urls:
                # 從 URL 提取檔名
                if '/static/uploads/' in url:
                    filename = url.split('/static/uploads/')[-1]
                else:
                    filename = url
                
                filepath = os.path.join(uploads_dir, filename)
                
                # 安全檢查
                if not os.path.abspath(filepath).startswith(os.path.abspath(uploads_dir)):
                    continue
                
                if os.path.exists(filepath) and os.path.isfile(filepath):
                    zf.write(filepath, filename)
        
        memory_file.seek(0)
        
        # 清理檔名
        safe_title = re.sub(r'[^\w\u4e00-\u9fff\-_]', '_', note_title)[:50]
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        zip_filename = f'{safe_title}_images_{timestamp}.zip'
        
        from flask import Response
        return Response(
            memory_file.getvalue(),
            mimetype='application/zip',
            headers={
                'Content-Disposition': f'attachment; filename*=UTF-8\'\'{zip_filename}'
            }
        )
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@export_bp.route('/import/json', methods=['POST'])
def import_json():
    """
    匯入 JSON 資料
    
    Request Body:
    {
        "data": { ... },  // 匯出的 JSON 資料
        "mode": "skip" | "duplicate"  // skip = 略過重複, duplicate = 建立副本
    }
    
    Response:
    {
        "imported": 10,
        "skipped": 5,
        "duplicates": ["標題1", "標題2"]
    }
    """
    try:
        request_data = request.get_json()
        
        if not request_data:
            return jsonify({
                'status': 'error',
                'message': 'No data provided'
            }), 400
        
        import_data = request_data.get('data')
        mode = request_data.get('mode', 'skip')  # 預設略過重複
        
        if not import_data or 'notes' not in import_data:
            return jsonify({
                'status': 'error',
                'message': 'Invalid import data format'
            }), 400
        
        db = get_db()
        
        imported_count = 0
        skipped_count = 0
        duplicate_titles = []
        
        notes = import_data.get('notes', [])
        
        for note in notes:
            title = note.get('title', '').strip()
            content = note.get('content', '').strip()
            
            # 檢查重複 (根據標題 + 內容前 100 字)
            content_preview = content[:100] if content else ''
            existing = db.execute('''
                SELECT id, title FROM Notes 
                WHERE title = ? AND SUBSTR(content, 1, 100) = ?
            ''', (title, content_preview)).fetchone()
            
            if existing:
                if mode == 'skip':
                    skipped_count += 1
                    duplicate_titles.append(title or '無標題')
                    continue
                elif mode == 'duplicate':
                    # 建立副本，標題加上 (Import)
                    title = f"{title} (Import)" if title else "(Imported)"
            
            # 插入新筆記
            try:
                cursor = db.execute('''
                    INSERT INTO Notes (title, content, type, remarks, cover_image, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    title or '無標題',
                    content,
                    note.get('type', 'note'),
                    note.get('remarks', ''),
                    note.get('cover_image', ''),
                    note.get('created_at', datetime.now().isoformat()),
                    note.get('updated_at', datetime.now().isoformat())
                ))
                
                new_note_id = cursor.lastrowid
                
                # 處理標籤
                tags = note.get('tags', [])
                for tag_name in tags:
                    if not tag_name:
                        continue
                    # 確保標籤存在
                    existing_tag = db.execute(
                        'SELECT id FROM Tags WHERE name = ?', 
                        (tag_name,)
                    ).fetchone()
                    
                    if existing_tag:
                        tag_id = existing_tag['id']
                    else:
                        tag_cursor = db.execute(
                            'INSERT INTO Tags (name) VALUES (?)', 
                            (tag_name,)
                        )
                        tag_id = tag_cursor.lastrowid
                    
                    # 建立筆記-標籤關聯
                    db.execute(
                        'INSERT OR IGNORE INTO Note_Tags (note_id, tag_id) VALUES (?, ?)',
                        (new_note_id, tag_id)
                    )
                
                # 處理 URLs
                urls = note.get('urls', [])
                for url in urls:
                    if url:
                        db.execute(
                            'INSERT INTO Source_Urls (note_id, url) VALUES (?, ?)',
                            (new_note_id, url)
                        )
                
                imported_count += 1
                
            except Exception as e:
                print(f"[IMPORT] Error importing note: {e}")
                continue
        
        db.commit()
        
        return jsonify({
            'status': 'success',
            'data': {
                'imported': imported_count,
                'skipped': skipped_count,
                'duplicates': duplicate_titles[:10]  # 最多顯示 10 個
            }
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

