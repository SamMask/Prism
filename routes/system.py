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
    v1.1: 先重建 FTS5 索引，再執行 VACUUM，確保搜尋殘留也被清除
    v1.2: 整合 WAL Checkpoint，一次完成所有資料庫維護
    Response: { size_before, size_after, freed_bytes }
    """
    try:
        db_path = current_app.config['DATABASE']
        
        # 取得 VACUUM 前的檔案大小
        size_before = os.path.getsize(db_path) if os.path.exists(db_path) else 0
        
        # 執行 VACUUM
        # 注意：VACUUM 需要獨立連線，不能在事務中執行
        conn = sqlite3.connect(db_path)
        
        # 0. 先執行 WAL Checkpoint (v1.2: 合併 WAL 日誌)
        try:
            conn.execute('PRAGMA wal_checkpoint(TRUNCATE)')
            print("[Info] WAL checkpoint completed")
        except Exception as wal_error:
            print(f"[Info] WAL checkpoint skipped: {wal_error}")
        
        # 1. 先強制重建 FTS5 索引 (清除搜尋殘留)
        # FTS5 會建立隱藏表格存放索引資料，刪除主表後這些殘影不會自動清除
        try:
            conn.execute("INSERT INTO Notes_FTS(Notes_FTS) VALUES('rebuild');")
            conn.commit()
        except Exception as fts_error:
            # 如果 FTS 表不存在或出錯，忽略繼續執行 VACUUM
            print(f"[Info] FTS rebuild skipped: {fts_error}")
        
        # 2. 執行物理壓縮 (清除空洞)
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


@system_bp.route('/system/clear-history', methods=['POST'])
def clear_history():
    """
    清空所有歷史版本記錄
    Response: { deleted_count }
    """
    try:
        db = get_db()
        
        # 取得刪除前的數量
        count_before = db.execute('SELECT COUNT(*) FROM Note_History').fetchone()[0]
        
        # 清空歷史版本表
        db.execute('DELETE FROM Note_History')
        db.commit()
        
        return jsonify({
            'status': 'success',
            'data': {
                'deleted_count': count_before
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


# ===================================================================
# WAL Checkpoint (v1.2 - 🟡-2 修復)
# ===================================================================

@system_bp.route('/system/wal-checkpoint', methods=['POST'])
def wal_checkpoint():
    """
    手動執行 WAL Checkpoint，將 WAL 日誌合併至主資料庫檔案
    確保備份時資料完整性
    
    Response: { wal_size_before, pages_checkpointed }
    """
    try:
        db_path = current_app.config['DATABASE']
        wal_path = db_path + '-wal'
        
        # 取得 WAL 檔案大小 (合併前)
        wal_size_before = os.path.getsize(wal_path) if os.path.exists(wal_path) else 0
        
        # 執行 TRUNCATE 模式的 checkpoint (最徹底)
        conn = sqlite3.connect(db_path)
        result = conn.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone()
        conn.close()
        
        # result = (blocked, pages_checkpointed, pages_moved)
        wal_size_after = os.path.getsize(wal_path) if os.path.exists(wal_path) else 0
        
        return jsonify({
            'status': 'success',
            'data': {
                'wal_size_before': wal_size_before,
                'wal_size_before_kb': round(wal_size_before / 1024, 2),
                'wal_size_after': wal_size_after,
                'pages_checkpointed': result[1] if result else 0,
                'message': 'WAL 日誌已合併至主資料庫'
            }
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


# ===================================================================
# Data Consistency Check (v1.2 - 🟡-3 修復)
# ===================================================================

@system_bp.route('/system/check-consistency', methods=['GET'])
def check_consistency():
    """
    資料一致性檢查
    檢查 Notes.type 與 category_id 的不一致記錄
    
    Response: { 
        orphan_note_tags, 
        unused_tags, 
        type_category_mismatch, 
        null_category_id,
        fk_status 
    }
    """
    try:
        db = get_db()
        
        # 1. 孤兒標籤關聯 (Note_Tags 引用不存在的 Notes)
        orphan_note_tags = db.execute('''
            SELECT COUNT(*) FROM Note_Tags nt
            LEFT JOIN Notes n ON nt.note_id = n.id
            WHERE n.id IS NULL
        ''').fetchone()[0]
        
        # 2. 未使用的標籤
        unused_tags = db.execute('''
            SELECT COUNT(*) FROM Tags t
            LEFT JOIN Note_Tags nt ON t.id = nt.tag_id
            WHERE nt.tag_id IS NULL
        ''').fetchone()[0]
        
        # 3. type 與 category_id 不一致
        type_category_mismatch = db.execute('''
            SELECT COUNT(*) FROM Notes n
            LEFT JOIN Categories c ON n.category_id = c.id
            WHERE c.name IS NOT NULL AND n.type != c.name
        ''').fetchone()[0]
        
        # 4. 缺少 category_id 的筆記
        null_category_id = db.execute('''
            SELECT COUNT(*) FROM Notes WHERE category_id IS NULL
        ''').fetchone()[0]
        
        # 5. Foreign Keys 狀態
        fk_status = db.execute('PRAGMA foreign_keys').fetchone()[0]
        
        # 計算整體健康狀態
        issues = orphan_note_tags + type_category_mismatch
        health = 'healthy' if issues == 0 else 'warning' if issues < 5 else 'critical'
        
        return jsonify({
            'status': 'success',
            'data': {
                'orphan_note_tags': orphan_note_tags,
                'unused_tags': unused_tags,
                'type_category_mismatch': type_category_mismatch,
                'null_category_id': null_category_id,
                'fk_status': fk_status,
                'fk_enabled': fk_status == 1,
                'health': health
            }
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

