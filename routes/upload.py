# -*- coding: utf-8 -*-
"""
Upload API Routes
Local Insight v1.6
"""

import os
import magic
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import request, jsonify, current_app
from PIL import Image

from . import upload_bp


def allowed_file(filename):
    """檢查檔案副檔名是否允許"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


@upload_bp.route('/upload', methods=['POST'])
def upload_file():
    """
    上傳圖片
    
    Request:
    - file: 圖片檔案 (multipart/form-data)
    - thumbnail_only: (可選) 'true' 時只保存縮圖，不保存原圖 (v1.8.9)
    
    Response:
    - url: 圖片 URL (若 thumbnail_only=true，回傳縮圖 URL)
    - filename: 檔名
    - size: 原始檔案大小
    - thumbnail_only: 是否為僅縮圖模式
    """
    try:
        if 'file' not in request.files:
            return jsonify({
                'status': 'error',
                'message': 'No file part in request'
            }), 400

        file = request.files['file']
        
        # 取得 thumbnail_only 參數 (v1.8.9)
        thumbnail_only = request.form.get('thumbnail_only', 'false').lower() == 'true'

        if file.filename == '':
            return jsonify({
                'status': 'error',
                'message': 'No file selected'
            }), 400

        if not allowed_file(file.filename):
            return jsonify({
                'status': 'error',
                'message': 'Invalid file type. Allowed: jpg, jpeg, png, gif, webp'
            }), 400

        # Magic Numbers 驗證
        file_header = file.read(2048)
        file.seek(0)

        try:
            mime = magic.from_buffer(file_header, mime=True)
            allowed_mimes = ['image/jpeg', 'image/png', 'image/webp', 'image/gif']
            if mime not in allowed_mimes:
                return jsonify({
                    'status': 'error',
                    'message': f'File content validation failed. Detected MIME: {mime}'
                }), 400
        except Exception as magic_error:
            print(f"[Warning] Magic validation failed: {magic_error}")

        # 檔案大小驗證
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)

        max_size = current_app.config.get('MAX_CONTENT_LENGTH', 5 * 1024 * 1024)
        if file_size > max_size:
            return jsonify({
                'status': 'error',
                'message': f'File too large. Maximum size: {max_size // (1024*1024)}MB'
            }), 400

        # 儲存檔案
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        new_filename = f"{timestamp}_{filename}"
        
        upload_folder = current_app.config['UPLOAD_FOLDER']
        file_path = os.path.join(upload_folder, new_filename)
        
        # 用於回傳的 URL (可能是原圖或縮圖)
        return_url = None
        thumb_filename = None
        
        # 生成縮圖 (v1.6 圖片虛擬化)
        try:
            # 讀取圖片到記憶體
            file.seek(0)
            with Image.open(file) as img:
                # 計算縮圖尺寸 (最大寬度 500px)
                max_width = 500
                if img.width > max_width:
                    ratio = max_width / img.width
                    new_height = int(img.height * ratio)
                    img_resized = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
                else:
                    img_resized = img.copy()

                # 轉換並儲存為 WebP
                name_without_ext = os.path.splitext(new_filename)[0]
                thumb_filename = f"{name_without_ext}_thumb.webp"
                thumb_path = os.path.join(upload_folder, thumb_filename)

                if img_resized.mode in ('RGBA', 'LA', 'P'):
                    img_resized = img_resized.convert('RGB')

                img_resized.save(thumb_path, 'WEBP', quality=80)
                
        except Exception as thumb_error:
            print(f"[Warning] Thumbnail generation failed: {thumb_error}")
            thumb_filename = None
        
        # 根據模式決定是否保存原圖
        if thumbnail_only and thumb_filename:
            # 僅縮圖模式：不保存原圖，回傳縮圖 URL
            return_url = f"/static/uploads/{thumb_filename}"
        else:
            # 標準模式：保存原圖
            file.seek(0)
            file.save(file_path)
            return_url = f"/static/uploads/{new_filename}"

        return jsonify({
            'status': 'success',
            'data': {
                'url': return_url,
                'filename': thumb_filename if thumbnail_only else new_filename,
                'size': file_size,
                'thumbnail_only': thumbnail_only
            }
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@upload_bp.route('/upload/delete', methods=['POST'])
def delete_image():
    """刪除圖片（原圖 + 縮圖一起刪除）"""
    try:
        data = request.get_json() or {}
        url = data.get('url', '')
        
        if not url:
            return jsonify({
                'status': 'error',
                'message': 'No URL provided'
            }), 400
        
        # 從 URL 中提取檔名 (v1.8.9: 修正路徑穿越漏洞)
        if '/static/uploads/' in url:
            raw_filename = url.split('/static/uploads/')[-1]
        else:
            raw_filename = url
        
        # 安全過濾：只取檔名部分，移除路徑
        filename = os.path.basename(raw_filename)
        
        # 驗證檔名安全性
        if not filename or '..' in filename or filename.startswith('.'):
            return jsonify({
                'status': 'error',
                'message': 'Invalid filename'
            }), 400
        
        upload_folder = current_app.config['UPLOAD_FOLDER']
        filepath = os.path.join(upload_folder, filename)
        
        # 雙重安全檢查
        if not os.path.abspath(filepath).startswith(os.path.abspath(upload_folder)):
            return jsonify({
                'status': 'error',
                'message': 'Invalid path'
            }), 400
        
        deleted = []
        
        # 刪除原圖
        if os.path.exists(filepath) and os.path.isfile(filepath):
            os.remove(filepath)
            deleted.append(filename)
        
        # 刪除對應的縮圖
        base, ext = os.path.splitext(filename)
        if not base.endswith('_thumb'):
            # 嘗試刪除 webp 縮圖
            thumb_webp = f"{base}_thumb.webp"
            thumb_webp_path = os.path.join(upload_folder, thumb_webp)
            if os.path.exists(thumb_webp_path):
                os.remove(thumb_webp_path)
                deleted.append(thumb_webp)
            
            # 嘗試刪除同格式縮圖
            thumb_same = f"{base}_thumb{ext}"
            thumb_same_path = os.path.join(upload_folder, thumb_same)
            if os.path.exists(thumb_same_path):
                os.remove(thumb_same_path)
                deleted.append(thumb_same)
        
        return jsonify({
            'status': 'success',
            'data': {
                'deleted': deleted,
                'count': len(deleted)
            }
        })
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

