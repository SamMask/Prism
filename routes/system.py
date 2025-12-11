# -*- coding: utf-8 -*-
"""
System API Routes - Database Maintenance & System Info
Local Insight v1.8.9
"""

import os
import sqlite3
from flask import jsonify, current_app

from . import system_bp
from db import get_db  # v1.8.9: 統一資料庫連線層


# ===================================================================
# Database Maintenance
# ===================================================================

@system_bp.route('/system/vacuum', methods=['POST'])
def vacuum_database():
    """
    執行 VACUUM 緊縮資料庫，釋放碎片空間
    Response: { size_before, size_after, freed_bytes }
    """
    try:
        db_path = current_app.config['DATABASE']
        
        # 取得 VACUUM 前的檔案大小
        size_before = os.path.getsize(db_path) if os.path.exists(db_path) else 0
        
        # 執行 VACUUM
        # 注意：VACUUM 需要獨立連線，不能在事務中執行
        conn = sqlite3.connect(db_path)
        conn.execute('VACUUM')
        conn.close()
        
        # 取得 VACUUM 後的檔案大小
        size_after = os.path.getsize(db_path) if os.path.exists(db_path) else 0
        freed_bytes = size_before - size_after
        
        return jsonify({
            'status': 'success',
            'data': {
                'size_before': size_before,
                'size_after': size_after,
                'freed_bytes': freed_bytes,
                'size_before_mb': round(size_before / 1024 / 1024, 2),
                'size_after_mb': round(size_after / 1024 / 1024, 2),
                'freed_mb': round(freed_bytes / 1024 / 1024, 2)
            }
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@system_bp.route('/system/stats', methods=['GET'])
def get_system_stats():
    """
    取得系統統計資訊
    """
    try:
        db = get_db()
        db_path = current_app.config['DATABASE']
        
        # 資料庫檔案大小
        db_size = os.path.getsize(db_path) if os.path.exists(db_path) else 0
        
        # 各表筆數
        notes_count = db.execute('SELECT COUNT(*) FROM Notes').fetchone()[0]
        tags_count = db.execute('SELECT COUNT(*) FROM Tags').fetchone()[0]
        history_count = db.execute('SELECT COUNT(*) FROM Note_History').fetchone()[0]
        
        # 封存筆記數
        try:
            archived_count = db.execute('SELECT COUNT(*) FROM Notes WHERE is_archived = 1').fetchone()[0]
        except sqlite3.OperationalError:  # v1.8.9: 修正空異常捕捉
            archived_count = 0
        
        # 圖片目錄大小
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'static/uploads')
        upload_size = 0
        if os.path.exists(upload_folder):
            for root, dirs, files in os.walk(upload_folder):
                for f in files:
                    upload_size += os.path.getsize(os.path.join(root, f))
        
        return jsonify({
            'status': 'success',
            'data': {
                'database': {
                    'size_bytes': db_size,
                    'size_mb': round(db_size / 1024 / 1024, 2),
                    'notes_count': notes_count,
                    'archived_count': archived_count,
                    'tags_count': tags_count,
                    'history_count': history_count
                },
                'uploads': {
                    'size_bytes': upload_size,
                    'size_mb': round(upload_size / 1024 / 1024, 2)
                }
            }
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


# ===================================================================
# Startup Preference (v1.1)
# ===================================================================

@system_bp.route('/system/startup-preference', methods=['GET'])
def get_startup_preference():
    """
    取得啟動偏好設定
    Response: { auto_open_browser: true | false | null }
    """
    try:
        auto_open_yes = os.path.exists('.auto_open_yes')
        auto_open_no = os.path.exists('.auto_open_no')
        
        if auto_open_yes:
            return jsonify({'status': 'success', 'data': {'auto_open_browser': True}})
        elif auto_open_no:
            return jsonify({'status': 'success', 'data': {'auto_open_browser': False}})
        else:
            return jsonify({'status': 'success', 'data': {'auto_open_browser': None}})
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@system_bp.route('/system/startup-preference', methods=['POST'])
def set_startup_preference():
    """
    設定啟動偏好
    Body: { auto_open_browser: true | false }
    """
    try:
        from flask import request
        data = request.get_json() or {}
        auto_open = data.get('auto_open_browser')
        
        if auto_open is None:
            return jsonify({'status': 'error', 'message': 'auto_open_browser is required'}), 400
        
        # 刪除舊的標記檔案
        if os.path.exists('.auto_open_yes'):
            os.remove('.auto_open_yes')
        if os.path.exists('.auto_open_no'):
            os.remove('.auto_open_no')
        
        # 建立新的標記檔案
        if auto_open:
            with open('.auto_open_yes', 'w') as f:
                f.write('1')
        else:
            with open('.auto_open_no', 'w') as f:
                f.write('0')
        
        return jsonify({'status': 'success', 'data': {'auto_open_browser': auto_open}})
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
