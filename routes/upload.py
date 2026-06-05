# -*- coding: utf-8 -*-
"""
Upload API Routes
Prism v1.4.1
"""

import os
import socket
import ipaddress
import magic
import requests
import hashlib
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import request, jsonify, current_app
from urllib.parse import urlparse, unquote

from utils.image_tools import (
    extract_prompt_metadata,
    generate_webp_thumbnail,
    thumbnail_name,
)

from . import upload_bp


def _is_ssrf_target(hostname: str) -> bool:
    """Return True if hostname resolves to a private/loopback/link-local IP (SSRF guard)."""
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return True  # unresolvable → block
    for info in infos:
        addr = info[4][0]
        try:
            ip = ipaddress.ip_address(addr)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                return True
        except ValueError:
            continue
    return False


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
        
        file.seek(0)
        file.save(file_path)

        thumb_filename = thumbnail_name(new_filename)
        thumb_path = os.path.join(upload_folder, thumb_filename)
        if not generate_webp_thumbnail(file_path, thumb_path):
            thumb_filename = None
        
        # 根據模式決定是否保存原圖
        if thumbnail_only and thumb_filename:
            # 僅縮圖模式：不保存原圖，回傳縮圖 URL
            if os.path.exists(file_path):
                os.remove(file_path)
            return_url = f"/static/uploads/{thumb_filename}"
        else:
            # 標準模式：保存原圖
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


@upload_bp.route('/upload/url', methods=['POST'])
def download_from_url():
    """
    下載遠端圖片 URL 並存到本機
    
    用於從網頁複製文章時，自動下載其中的圖片。
    
    Request (JSON):
    - url: 遠端圖片 URL
    - thumbnail_only: (可選) 只保存縮圖
    
    Response:
    - url: 本機圖片 URL
    - filename: 本機檔名
    - original_url: 原始遠端 URL
    """
    try:
        data = request.get_json() or {}
        image_url = data.get('url', '').strip()
        thumbnail_only = data.get('thumbnail_only', False)
        
        if not image_url:
            return jsonify({
                'status': 'error',
                'message': 'No URL provided'
            }), 400
        
        # 驗證 URL 格式
        parsed = urlparse(image_url)
        if parsed.scheme not in ('http', 'https'):
            return jsonify({
                'status': 'error',
                'message': 'Invalid URL scheme. Only http/https allowed.'
            }), 400

        # SSRF 防護：拒絕解析到內網 / loopback / link-local 的主機名稱
        if _is_ssrf_target(parsed.hostname or ''):
            return jsonify({
                'status': 'error',
                'message': 'URL resolves to a private or reserved IP address.'
            }), 400

        # 下載圖片 (設定 timeout 和 headers)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': f'{parsed.scheme}://{parsed.netloc}/'
        }
        
        try:
            response = requests.get(image_url, headers=headers, timeout=30, stream=True)
            response.raise_for_status()
        except requests.RequestException as req_err:
            return jsonify({
                'status': 'error',
                'message': f'Failed to download image: {str(req_err)}'
            }), 400
        
        # 檢查 Content-Type
        content_type = response.headers.get('Content-Type', '')
        if not content_type.startswith('image/'):
            return jsonify({
                'status': 'error',
                'message': f'URL does not point to an image. Content-Type: {content_type}'
            }), 400
        
        # 讀取圖片內容
        image_data = response.content
        file_size = len(image_data)
        
        # 檔案大小驗證
        max_size = current_app.config.get('MAX_CONTENT_LENGTH', 5 * 1024 * 1024)
        if file_size > max_size:
            return jsonify({
                'status': 'error',
                'message': f'Image too large. Maximum size: {max_size // (1024*1024)}MB'
            }), 400
        
        # Magic Numbers 驗證
        try:
            mime = magic.from_buffer(image_data[:2048], mime=True)
            allowed_mimes = ['image/jpeg', 'image/png', 'image/webp', 'image/gif']
            if mime not in allowed_mimes:
                return jsonify({
                    'status': 'error',
                    'message': f'Invalid image type. Detected: {mime}'
                }), 400
        except Exception as magic_error:
            print(f"[Warning] Magic validation failed: {magic_error}")
        
        # 生成檔名
        # 嘗試從 URL 提取原始檔名，否則使用 hash
        url_path = unquote(parsed.path)
        original_name = os.path.basename(url_path) if url_path else ''
        
        # 確保有副檔名
        ext_map = {
            'image/jpeg': '.jpg',
            'image/png': '.png',
            'image/webp': '.webp',
            'image/gif': '.gif'
        }
        
        if original_name and '.' in original_name:
            base_name = secure_filename(original_name)
        else:
            # 使用 URL hash 作為檔名
            url_hash = hashlib.md5(image_url.encode()).hexdigest()[:8]
            ext = ext_map.get(mime, '.jpg')
            base_name = f"remote_{url_hash}{ext}"
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        new_filename = f"{timestamp}_{base_name}"
        
        upload_folder = current_app.config['UPLOAD_FOLDER']
        file_path = os.path.join(upload_folder, new_filename)
        
        # 保存原圖後用 Go helper 生成縮圖；驗證失敗不會走到這裡，所以 failure
        # fallback 只保留已驗證的本機圖片。
        with open(file_path, 'wb') as f:
            f.write(image_data)

        return_url = None
        thumb_filename = thumbnail_name(new_filename)
        thumb_path = os.path.join(upload_folder, thumb_filename)
        if not generate_webp_thumbnail(file_path, thumb_path):
            thumb_filename = None
        
        # 根據模式決定是否保存原圖
        if thumbnail_only and thumb_filename:
            if os.path.exists(file_path):
                os.remove(file_path)
            return_url = f"/static/uploads/{thumb_filename}"
        else:
            return_url = f"/static/uploads/{new_filename}"
        
        return jsonify({
            'status': 'success',
            'data': {
                'url': return_url,
                'filename': thumb_filename if thumbnail_only else new_filename,
                'size': file_size,
                'original_url': image_url,
                'thumbnail_only': thumbnail_only
            }
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@upload_bp.route('/upload/extract-prompt', methods=['POST'])
def extract_prompt():
    """
    從圖片中提取 AI 生成的提示詞
    
    支援格式:
    - Stable Diffusion (PNG parameters)
    - ComfyUI (PNG workflow)
    - NovelAI (PNG Comment)
    - EXIF UserComment
    
    Request:
    {
        "image_path": "/static/uploads/xxx.png"
    }
    
    Response:
    {
        "status": "success",
        "data": {
            "prompt": "...",
            "negative_prompt": "...",
            "source": "stable_diffusion"
        }
    }
    """
    try:
        data = request.get_json() or {}
        image_path = data.get('image_path', '')
        
        if not image_path:
            return jsonify({
                'status': 'error',
                'message': 'image_path is required'
            }), 400
        
        # Convert URL path to file path
        if image_path.startswith('/static/'):
            file_path = os.path.join(current_app.root_path, image_path[1:])
        else:
            file_path = image_path
        
        if not os.path.exists(file_path):
            return jsonify({
                'status': 'error',
                'message': 'Image file not found'
            }), 404
        
        # Read image metadata
        prompt_data = {
            'prompt': None,
            'negative_prompt': None,
            'source': None,
            'raw_metadata': None
        }
        
        try:
            prompt_data = extract_prompt_metadata(file_path)
        except Exception as e:
            print(f"[Extract Prompt] Error reading image: {e}")
            return jsonify({
                'status': 'error',
                'message': f'Failed to read image metadata: {str(e)}'
            }), 500
        
        if not prompt_data['prompt']:
            return jsonify({
                'status': 'success',
                'data': {
                    'prompt': None,
                    'has_prompt': False
                }
            })
        
        return jsonify({
            'status': 'success',
            'data': {
                'prompt': prompt_data['prompt'],
                'negative_prompt': prompt_data['negative_prompt'],
                'source': prompt_data['source'],
                'has_prompt': True
            }
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
