# -*- coding: utf-8 -*-
"""
Import API Routes - Markdown Import
Local Insight v1.1
"""

import re
import os
import requests
from datetime import datetime
from flask import request, jsonify, current_app
from werkzeug.utils import secure_filename
from PIL import Image

from . import notes_bp
from db import get_db


def download_and_save_image(image_url, upload_folder, thumbnail_only=False):
    """
    下載或複製圖片並生成縮圖
    Returns: (new_url, success) tuple
    """
    try:
        # 判斷是 URL 還是本地路徑
        is_url = image_url.startswith(('http://', 'https://'))
        
        if is_url:
            # 下載圖片
            response = requests.get(image_url, timeout=10, stream=True)
            response.raise_for_status()
            
            # 從 URL 或 Content-Type 推測副檔名
            content_type = response.headers.get('Content-Type', '')
            ext_map = {
                'image/jpeg': '.jpg',
                'image/png': '.png',
                'image/gif': '.gif',
                'image/webp': '.webp'
            }
            ext = ext_map.get(content_type, '.jpg')
            
            # 生成檔名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S%f')[:-3]
            filename = f"imported_{timestamp}{ext}"
            filepath = os.path.join(upload_folder, filename)
            
            # 儲存圖片
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
        else:
            # 本地路徑 - 不支援
            return None, False
        
        # 生成縮圖
        thumb_filename = None
        try:
            with Image.open(filepath) as img:
                max_width = 500
                if img.width > max_width:
                    ratio = max_width / img.width
                    new_height = int(img.height * ratio)
                    img_resized = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
                else:
                    img_resized = img.copy()
                
                name_without_ext = os.path.splitext(filename)[0]
                thumb_filename = f"{name_without_ext}_thumb.webp"
                thumb_path = os.path.join(upload_folder, thumb_filename)
                
                if img_resized.mode in ('RGBA', 'LA', 'P'):
                    img_resized = img_resized.convert('RGB')
                
                img_resized.save(thumb_path, 'WEBP', quality=80)
        except Exception as e:
            print(f"[Warning] Thumbnail generation failed: {e}")
        
        # 根據設定決定回傳 URL
        if thumbnail_only and thumb_filename:
            # 只保存縮圖，刪除原圖
            if os.path.exists(filepath):
                os.remove(filepath)
            return f"/static/uploads/{thumb_filename}", True
        else:
            # 保存原圖
            return f"/static/uploads/{filename}", True
            
    except Exception as e:
        print(f"[Warning] Failed to download image {image_url}: {e}")
        return None, False


@notes_bp.route('/notes/import/md', methods=['POST'])
def import_markdown():
    """
    匯入單個 Markdown 檔案建立筆記
    Request: multipart/form-data with 'file' field
    Response: { status, data: { note_id } }
    """
    try:
        # 檢查是否有檔案
        if 'file' not in request.files:
            return jsonify({
                'status': 'error',
                'message': 'No file provided'
            }), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({
                'status': 'error',
                'message': 'No file selected'
            }), 400
        
        # 檢查檔案類型
        if not file.filename.endswith('.md'):
            return jsonify({
                'status': 'error',
                'message': 'Only .md files are supported'
            }), 400
        
        # 讀取檔案內容
        content = file.read().decode('utf-8')
        
        # 解析 Markdown 內容
        # 嘗試提取標題（第一個 # 標題）
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if title_match:
            title = title_match.group(1).strip()
            # 移除第一個標題行
            content = re.sub(r'^#\s+.+$\n?', '', content, count=1, flags=re.MULTILINE)
        else:
            # 如果沒有標題，使用檔名
            title = file.filename.replace('.md', '')
        
        # 解析 YAML front matter（如果存在）
        note_type = '筆記'
        tags = []
        thumbnail_only = False
        
        yaml_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
        if yaml_match:
            yaml_content = yaml_match.group(1)
            # 簡單解析 type 和 tags
            type_match = re.search(r'^type:\s*(.+)$', yaml_content, re.MULTILINE)
            if type_match:
                note_type = type_match.group(1).strip()
            
            tags_match = re.search(r'^tags:\s*\[(.+)\]$', yaml_content, re.MULTILINE)
            if tags_match:
                tags = [tag.strip().strip('"').strip("'") for tag in tags_match.group(1).split(',')]
            
            # 移除 YAML front matter
            content = re.sub(r'^---\s*\n.*?\n---\s*\n', '', content, flags=re.DOTALL)
        
        # 處理圖片匯入
        # TODO: 從 localStorage 讀取或使用預設值
        # 這裡簡化為預設 both 模式（保存原圖+縮圖）
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'static/uploads')
        
        # 找出所有圖片鏈結 ![alt](url)
        image_pattern = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')
        images = image_pattern.findall(content)
        
        if images:
            # 處理每個圖片鏈結
            for alt_text, image_url in images:
                # 只處理 http(s) URL
                if image_url.startswith(('http://', 'https://')):
                    new_url, success = download_and_save_image(image_url, upload_folder, thumbnail_only)
                    if success and new_url:
                        # 更新內容中的圖片路徑
                        old_pattern = f'![{alt_text}]({image_url})'
                        new_pattern = f'![{alt_text}]({new_url})'
                        content = content.replace(old_pattern, new_pattern)
        
        content = content.strip()
        
        # 建立筆記
        db = get_db()
        
        cursor = db.execute('''
            INSERT INTO Notes (title, content, type, created_at, updated_at)
            VALUES (?, ?, ?, datetime('now'), datetime('now'))
        ''', (title, content, note_type))
        
        note_id = cursor.lastrowid
        
        # 新增標籤
        if tags:
            for tag_name in tags:
                if not tag_name:
                    continue
                
                # 查找或建立標籤
                tag = db.execute('SELECT id FROM Tags WHERE name = ?', (tag_name,)).fetchone()
                if tag:
                    tag_id = tag['id']
                else:
                    cursor = db.execute('INSERT INTO Tags (name) VALUES (?)', (tag_name,))
                    tag_id = cursor.lastrowid
                
                # 關聯標籤
                db.execute('INSERT INTO Note_Tags (note_id, tag_id) VALUES (?, ?)', (note_id, tag_id))
        
        db.commit()
        
        return jsonify({
            'status': 'success',
            'data': {'note_id': note_id}
        }), 201
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

