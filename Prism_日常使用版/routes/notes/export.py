# -*- coding: utf-8 -*-
"""
Notes Export Module
Local Insight v1.0

批量匯出功能 - 將多筆筆記打包為 ZIP (含 Markdown + 圖片)
"""

import os
import re
import io
import zipfile
from flask import jsonify, request, send_file, current_app
from . import notes_bp
from db import get_db


@notes_bp.route('/notes/export/batch', methods=['POST'])
def export_batch():
    """
    批量匯出筆記為 ZIP
    
    Request Body:
        { "note_ids": [1, 2, 3] }
    
    Response:
        ZIP file containing:
        - notes/
          - note_1.md
          - note_2.md
        - assets/
          - image1.jpg
          - image2.png
    """
    try:
        data = request.get_json()
        note_ids = data.get('note_ids', [])
        
        if not note_ids:
            return jsonify({'status': 'error', 'message': 'No notes selected'}), 400
        
        db = get_db()
        
        # 創建 ZIP 緩衝區
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            collected_images = set()
            
            for note_id in note_ids:
                # 取得筆記資料
                note = db.execute(
                    'SELECT id, title, content, type, remarks FROM Notes WHERE id = ?',
                    (note_id,)
                ).fetchone()
                
                if not note:
                    continue
                
                # 取得標籤
                tags = db.execute('''
                    SELECT t.name FROM Tags t
                    JOIN Note_Tags nt ON t.id = nt.tag_id
                    WHERE nt.note_id = ?
                ''', (note_id,)).fetchall()
                tag_names = [t['name'] for t in tags]
                
                # 建立 Markdown 內容 (含 YAML Front Matter)
                md_content = build_markdown(note, tag_names)
                
                # 安全檔名
                safe_title = sanitize_filename(note['title'])
                filename = f"notes/{safe_title}_{note_id}.md"
                
                zf.writestr(filename, md_content.encode('utf-8'))
                
                # 收集圖片路徑
                images = extract_images(note['content'])
                collected_images.update(images)
            
            # 加入圖片到 ZIP
            upload_folder = current_app.config.get('UPLOAD_FOLDER', 'static/uploads')
            for img_path in collected_images:
                # 處理相對路徑
                if img_path.startswith('/static/uploads/'):
                    local_path = img_path.replace('/static/uploads/', '')
                    full_path = os.path.join(upload_folder, local_path)
                    
                    if os.path.exists(full_path):
                        zf.write(full_path, f"assets/{local_path}")
        
        zip_buffer.seek(0)
        
        return send_file(
            zip_buffer,
            mimetype='application/zip',
            as_attachment=True,
            download_name='local_insight_export.zip'
        )
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


def build_markdown(note, tags):
    """建立 Markdown 內容 (含 YAML Front Matter)"""
    frontmatter = f"""---
title: "{note['title']}"
type: {note['type']}
tags: [{', '.join(tags)}]
---

"""
    content = note['content'] or ''
    remarks = note['remarks']
    
    if remarks:
        content += f"\n\n---\n\n> **備註**: {remarks}"
    
    return frontmatter + content


def sanitize_filename(name):
    """將標題轉為安全檔名"""
    # 移除非法字元
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    # 限制長度
    return name[:50].strip() or 'untitled'


def extract_images(content):
    """從 Markdown 內容中提取本地圖片路徑"""
    if not content:
        return []
    
    # 匹配 ![...](/static/uploads/...) 格式
    pattern = r'!\[.*?\]\((/static/uploads/[^)]+)\)'
    matches = re.findall(pattern, content)
    
    return matches
