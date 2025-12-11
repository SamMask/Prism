# -*- coding: utf-8 -*-
"""
Cleanup API Routes
Local Insight v1.8.9 - 孤兒圖片清理功能
"""

import os
import re
from flask import request, jsonify, current_app

from . import cleanup_bp
from db import get_db  # v1.8.9: 統一資料庫連線層


def get_all_referenced_images():
    """從資料庫取得所有被引用的圖片路徑"""
    db = get_db()
    
    # 查詢所有筆記的 content 和 cover_image
    rows = db.execute('''
        SELECT content, cover_image FROM Notes
    ''').fetchall()
    
    referenced = set()
    
    # 正則表達式匹配圖片路徑
    # 匹配: ![...](/static/uploads/xxx.jpg) 或 src="/static/uploads/xxx.jpg"
    image_pattern = re.compile(r'/static/uploads/([^"\'\)\s]+)')
    
    for row in rows:
        # 從 content 中提取圖片
        content = row['content'] or ''
        matches = image_pattern.findall(content)
        for match in matches:
            referenced.add(match)
        
        # cover_image 可能是完整路徑或只是檔名
        cover = row['cover_image']
        if cover:
            # 提取檔名
            if '/static/uploads/' in cover:
                filename = cover.split('/static/uploads/')[-1]
            else:
                filename = cover
            referenced.add(filename)
    
    return referenced


@cleanup_bp.route('/cleanup/orphan-images', methods=['GET'])
def get_orphan_images():
    """取得所有孤兒圖片列表"""
    try:
        uploads_dir = os.path.join(current_app.root_path, 'static', 'uploads')
        
        if not os.path.exists(uploads_dir):
            return jsonify({
                'status': 'success',
                'data': {
                    'orphan_images': [],
                    'total_count': 0,
                    'total_size_bytes': 0
                }
            })
        
        # 取得目錄中所有檔案
        all_files = []
        for filename in os.listdir(uploads_dir):
            filepath = os.path.join(uploads_dir, filename)
            if os.path.isfile(filepath):
                # 只處理圖片檔案
                ext = os.path.splitext(filename)[1].lower()
                if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg']:
                    all_files.append({
                        'filename': filename,
                        'size': os.path.getsize(filepath),
                        'path': f'/static/uploads/{filename}'
                    })
        
        # 取得被引用的圖片
        referenced = get_all_referenced_images()
        
        # 找出孤兒圖片 (不在引用清單中)
        # 改進邏輯：如果原圖被引用，其縮圖也視為「被引用」
        orphans = []
        total_size = 0
        
        # 擴展 referenced 集合，加入被引用圖片的縮圖
        expanded_referenced = set(referenced)
        for ref in referenced:
            # 為每個被引用的圖片生成對應的縮圖名稱
            base, ext = os.path.splitext(ref)
            if not base.endswith('_thumb'):
                thumb_name = f"{base}_thumb{ext}"
                expanded_referenced.add(thumb_name)
                # 也加入 webp 縮圖
                thumb_webp = f"{base}_thumb.webp"
                expanded_referenced.add(thumb_webp)
        
        for file_info in all_files:
            filename = file_info['filename']
            
            # 如果這個檔案在擴展的引用集合中，跳過
            if filename in expanded_referenced:
                continue
            
            # 如果這是縮圖，檢查其原圖是否被引用
            if '_thumb' in filename:
                # 從縮圖名稱反推原圖名稱
                base_name = filename.replace('_thumb', '')
                # 還原可能的原圖副檔名
                base_no_ext = os.path.splitext(base_name)[0]
                original_ext = os.path.splitext(base_name)[1]
                
                # 檢查各種可能的原圖是否被引用
                possible_originals = [
                    base_name,
                    f"{base_no_ext}.jpg",
                    f"{base_no_ext}.jpeg",
                    f"{base_no_ext}.png",
                    f"{base_no_ext}.gif",
                    f"{base_no_ext}.webp"
                ]
                
                is_thumb_referenced = any(orig in referenced for orig in possible_originals)
                if is_thumb_referenced:
                    continue
            
            orphans.append(file_info)
            total_size += file_info['size']
        
        return jsonify({
            'status': 'success',
            'data': {
                'orphan_images': orphans,
                'total_count': len(orphans),
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2) if total_size > 0 else 0
            }
        })
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@cleanup_bp.route('/cleanup/orphan-images', methods=['DELETE'])
def delete_orphan_images():
    """刪除指定的孤兒圖片"""
    try:
        data = request.get_json() or {}
        filenames = data.get('filenames', [])
        
        if not filenames:
            return jsonify({
                'status': 'error',
                'message': 'No filenames provided'
            }), 400
        
        uploads_dir = os.path.join(current_app.root_path, 'static', 'uploads')
        
        deleted = []
        errors = []
        
        for filename in filenames:
            filepath = os.path.join(uploads_dir, filename)
            
            # 安全檢查：確保路徑在 uploads 目錄內
            if not os.path.abspath(filepath).startswith(os.path.abspath(uploads_dir)):
                errors.append({'filename': filename, 'error': 'Invalid path'})
                continue
            
            if os.path.exists(filepath) and os.path.isfile(filepath):
                try:
                    os.remove(filepath)
                    deleted.append(filename)
                    
                    # 嘗試刪除對應的縮圖
                    base, ext = os.path.splitext(filename)
                    if not base.endswith('_thumb'):
                        thumb_filename = f"{base}_thumb{ext}"
                        thumb_path = os.path.join(uploads_dir, thumb_filename)
                        if os.path.exists(thumb_path):
                            os.remove(thumb_path)
                            deleted.append(thumb_filename)
                except Exception as e:
                    errors.append({'filename': filename, 'error': str(e)})
            else:
                errors.append({'filename': filename, 'error': 'File not found'})
        
        return jsonify({
            'status': 'success',
            'data': {
                'deleted': deleted,
                'deleted_count': len(deleted),
                'errors': errors
            }
        })
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


# ===================================================================
# Delete All Original Images (v1.8.9)
# ===================================================================

@cleanup_bp.route('/cleanup/originals', methods=['GET'])
def get_original_images():
    """
    取得所有原圖 (非縮圖) 的統計信息
    用於預覽刪除前的狀態
    """
    try:
        uploads_dir = os.path.join(current_app.root_path, 'static', 'uploads')
        
        if not os.path.exists(uploads_dir):
            return jsonify({
                'status': 'success',
                'data': {
                    'original_count': 0,
                    'original_size_bytes': 0,
                    'original_size_mb': 0,
                    'thumbnail_count': 0
                }
            })
        
        original_count = 0
        original_size = 0
        thumbnail_count = 0
        
        for filename in os.listdir(uploads_dir):
            filepath = os.path.join(uploads_dir, filename)
            if not os.path.isfile(filepath):
                continue
                
            # 只處理圖片檔案
            ext = os.path.splitext(filename)[1].lower()
            if ext not in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']:
                continue
            
            # 判斷是縮圖還是原圖
            base = os.path.splitext(filename)[0]
            if base.endswith('_thumb'):
                thumbnail_count += 1
            else:
                # 檢查是否有對應的縮圖 (表示這是原圖，可以刪除)
                thumb_webp = f"{base}_thumb.webp"
                thumb_same = f"{base}_thumb{ext}"
                thumb_webp_path = os.path.join(uploads_dir, thumb_webp)
                thumb_same_path = os.path.join(uploads_dir, thumb_same)
                
                if os.path.exists(thumb_webp_path) or os.path.exists(thumb_same_path):
                    original_count += 1
                    original_size += os.path.getsize(filepath)
        
        return jsonify({
            'status': 'success',
            'data': {
                'original_count': original_count,
                'original_size_bytes': original_size,
                'original_size_mb': round(original_size / (1024 * 1024), 2) if original_size > 0 else 0,
                'thumbnail_count': thumbnail_count
            }
        })
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@cleanup_bp.route('/cleanup/originals', methods=['DELETE'])
def delete_all_originals():
    """
    刪除所有原圖並將筆記中的原圖路徑改為對應的縮圖路徑
    
    Response:
    - deleted_count: 刪除的原圖數量
    - saved_bytes: 釋放的空間 (bytes)
    - saved_mb: 釋放的空間 (MB)
    - updated_notes: 更新的筆記數量
    """
    try:
        uploads_dir = os.path.join(current_app.root_path, 'static', 'uploads')
        db = get_db()
        
        if not os.path.exists(uploads_dir):
            return jsonify({
                'status': 'success',
                'data': {
                    'deleted_count': 0,
                    'saved_bytes': 0,
                    'saved_mb': 0,
                    'updated_notes': 0
                }
            })
        
        # Step 1: 找出所有有對應縮圖的原圖
        originals_to_delete = []
        
        for filename in os.listdir(uploads_dir):
            filepath = os.path.join(uploads_dir, filename)
            if not os.path.isfile(filepath):
                continue
            
            ext = os.path.splitext(filename)[1].lower()
            if ext not in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']:
                continue
            
            base = os.path.splitext(filename)[0]
            
            # 跳過縮圖本身
            if base.endswith('_thumb'):
                continue
            
            # 檢查是否有對應的縮圖
            thumb_webp = f"{base}_thumb.webp"
            thumb_same = f"{base}_thumb{ext}"
            thumb_webp_path = os.path.join(uploads_dir, thumb_webp)
            thumb_same_path = os.path.join(uploads_dir, thumb_same)
            
            thumbnail_filename = None
            if os.path.exists(thumb_webp_path):
                thumbnail_filename = thumb_webp
            elif os.path.exists(thumb_same_path):
                thumbnail_filename = thumb_same
            
            if thumbnail_filename:
                originals_to_delete.append({
                    'original': filename,
                    'original_path': filepath,
                    'thumbnail': thumbnail_filename,
                    'size': os.path.getsize(filepath)
                })
        
        # Step 2: 更新筆記內容，將原圖路徑替換為縮圖路徑
        updated_notes = 0
        
        for item in originals_to_delete:
            original_url = f"/static/uploads/{item['original']}"
            thumbnail_url = f"/static/uploads/{item['thumbnail']}"
            
            # 更新 content 中的圖片路徑
            result = db.execute('''
                UPDATE Notes 
                SET content = REPLACE(content, ?, ?),
                    updated_at = CURRENT_TIMESTAMP
                WHERE content LIKE ?
            ''', (original_url, thumbnail_url, f'%{original_url}%'))
            updated_notes += result.rowcount
            
            # 更新 cover_image
            db.execute('''
                UPDATE Notes 
                SET cover_image = ?
                WHERE cover_image = ?
            ''', (thumbnail_url, original_url))
        
        db.commit()
        
        # Step 3: 刪除原圖檔案
        deleted_count = 0
        saved_bytes = 0
        
        for item in originals_to_delete:
            try:
                os.remove(item['original_path'])
                deleted_count += 1
                saved_bytes += item['size']
            except Exception as e:
                print(f"[Warning] Failed to delete {item['original']}: {e}")
        
        return jsonify({
            'status': 'success',
            'data': {
                'deleted_count': deleted_count,
                'saved_bytes': saved_bytes,
                'saved_mb': round(saved_bytes / (1024 * 1024), 2) if saved_bytes > 0 else 0,
                'updated_notes': updated_notes
            }
        })
    
    except Exception as e:
        db.rollback()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


# ===================================================================
# Fix Broken Image Paths (v1.8.9)
# ===================================================================

def find_thumbnail_for_original(original_filename, uploads_dir):
    """
    為原圖找到對應的縮圖
    返回縮圖檔名，若不存在則返回 None
    """
    base, ext = os.path.splitext(original_filename)
    
    # 可能的縮圖名稱
    thumb_webp = f"{base}_thumb.webp"
    thumb_same = f"{base}_thumb{ext}"
    
    if os.path.exists(os.path.join(uploads_dir, thumb_webp)):
        return thumb_webp
    elif os.path.exists(os.path.join(uploads_dir, thumb_same)):
        return thumb_same
    
    return None


@cleanup_bp.route('/cleanup/broken-images', methods=['GET'])
def get_broken_images():
    """
    掃描筆記中所有圖片路徑，找出原圖不存在但有縮圖可用的情況
    
    Response:
    - broken_paths: 失效路徑列表，每個包含 {note_id, original_path, thumbnail_path}
    - total_count: 總數量
    """
    try:
        db = get_db()
        uploads_dir = os.path.join(current_app.root_path, 'static', 'uploads')
        
        # 正則表達式匹配圖片路徑
        image_pattern = re.compile(r'/static/uploads/([^"\'\)\s]+)')
        
        # 查詢所有筆記
        rows = db.execute('SELECT id, content, cover_image FROM Notes').fetchall()
        
        broken_paths = []
        
        for row in rows:
            note_id = row['id']
            content = row['content'] or ''
            cover = row['cover_image'] or ''
            
            # 檢查 content 中的圖片
            for match in image_pattern.finditer(content):
                filename = match.group(1)
                filepath = os.path.join(uploads_dir, filename)
                
                # 跳過已經是縮圖的
                if '_thumb' in filename:
                    continue
                
                # 如果原圖不存在
                if not os.path.exists(filepath):
                    thumb = find_thumbnail_for_original(filename, uploads_dir)
                    if thumb:
                        broken_paths.append({
                            'note_id': note_id,
                            'original_path': f'/static/uploads/{filename}',
                            'thumbnail_path': f'/static/uploads/{thumb}'
                        })
            
            # 檢查 cover_image
            if cover and '/static/uploads/' in cover:
                filename = cover.split('/static/uploads/')[-1]
                if '_thumb' not in filename:
                    filepath = os.path.join(uploads_dir, filename)
                    if not os.path.exists(filepath):
                        thumb = find_thumbnail_for_original(filename, uploads_dir)
                        if thumb:
                            broken_paths.append({
                                'note_id': note_id,
                                'original_path': cover,
                                'thumbnail_path': f'/static/uploads/{thumb}',
                                'is_cover': True
                            })
        
        return jsonify({
            'status': 'success',
            'data': {
                'broken_paths': broken_paths,
                'total_count': len(broken_paths)
            }
        })
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@cleanup_bp.route('/cleanup/broken-images', methods=['POST'])
def fix_broken_images():
    """
    自動修正所有失效的圖片路徑，將其替換為縮圖路徑
    
    Response:
    - fixed_count: 修正的路徑數量
    - updated_notes: 更新的筆記數量
    """
    try:
        db = get_db()
        uploads_dir = os.path.join(current_app.root_path, 'static', 'uploads')
        
        image_pattern = re.compile(r'/static/uploads/([^"\'\)\s]+)')
        
        rows = db.execute('SELECT id, content, cover_image FROM Notes').fetchall()
        
        fixed_count = 0
        updated_note_ids = set()
        
        for row in rows:
            note_id = row['id']
            content = row['content'] or ''
            cover = row['cover_image'] or ''
            new_content = content
            new_cover = cover
            content_changed = False
            cover_changed = False
            
            # 修正 content 中的圖片
            for match in image_pattern.finditer(content):
                filename = match.group(1)
                
                if '_thumb' in filename:
                    continue
                
                filepath = os.path.join(uploads_dir, filename)
                
                if not os.path.exists(filepath):
                    thumb = find_thumbnail_for_original(filename, uploads_dir)
                    if thumb:
                        old_path = f'/static/uploads/{filename}'
                        new_path = f'/static/uploads/{thumb}'
                        new_content = new_content.replace(old_path, new_path)
                        fixed_count += 1
                        content_changed = True
            
            # 修正 cover_image
            if cover and '/static/uploads/' in cover:
                filename = cover.split('/static/uploads/')[-1]
                if '_thumb' not in filename:
                    filepath = os.path.join(uploads_dir, filename)
                    if not os.path.exists(filepath):
                        thumb = find_thumbnail_for_original(filename, uploads_dir)
                        if thumb:
                            new_cover = f'/static/uploads/{thumb}'
                            fixed_count += 1
                            cover_changed = True
            
            # 更新資料庫
            if content_changed or cover_changed:
                db.execute('''
                    UPDATE Notes 
                    SET content = ?, cover_image = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (new_content, new_cover, note_id))
                updated_note_ids.add(note_id)
        
        db.commit()
        
        return jsonify({
            'status': 'success',
            'data': {
                'fixed_count': fixed_count,
                'updated_notes': len(updated_note_ids)
            }
        })
    
    except Exception as e:
        db.rollback()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
