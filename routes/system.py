# -*- coding: utf-8 -*-
"""
System API Routes - Database Maintenance & System Info
Prism v1.5.0
"""

import os
import json
import sqlite3
import subprocess
from flask import jsonify, current_app

from . import system_bp
from db import get_db


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
        # SEC-001 Fix: 使用絕對路徑
        pref_dir = current_app.root_path
        auto_open_yes = os.path.exists(os.path.join(pref_dir, '.auto_open_yes'))
        auto_open_no = os.path.exists(os.path.join(pref_dir, '.auto_open_no'))
        
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
        
        # SEC-001 Fix: 使用絕對路徑確保安全性
        pref_dir = current_app.root_path
        yes_file = os.path.join(pref_dir, '.auto_open_yes')
        no_file = os.path.join(pref_dir, '.auto_open_no')
        
        # 刪除舊的標記檔案
        if os.path.exists(yes_file):
            os.remove(yes_file)
        if os.path.exists(no_file):
            os.remove(no_file)
        
        # 建立新的標記檔案
        if auto_open:
            with open(yes_file, 'w') as f:
                f.write('1')
        else:
            with open(no_file, 'w') as f:
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
    資料一致性檢查（不檢查 type，因為 Notes.type 已於 v12 移除）

    Response: { orphan_note_tags, unused_tags, null_category_id, fk_status, fk_enabled, health }
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
        
        # 3. 缺少 category_id 的筆記
        null_category_id = db.execute('''
            SELECT COUNT(*) FROM Notes WHERE category_id IS NULL
        ''').fetchone()[0]
        
        # 5. Foreign Keys 狀態
        fk_status = db.execute('PRAGMA foreign_keys').fetchone()[0]
        
        # 計算整體健康狀態
        issues = orphan_note_tags
        health = 'healthy' if issues == 0 else 'warning' if issues < 5 else 'critical'

        return jsonify({
            'status': 'success',
            'data': {
                'orphan_note_tags': orphan_note_tags,
                'unused_tags': unused_tags,
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


# ===================================================================
# Update / Migration Status
# ===================================================================

def _normalize_version(version):
    """Convert 'v2.4.3' or '2.4.3-beta' to a comparable tuple."""
    import re
    parts = re.findall(r'\d+', version or '')
    return tuple(int(part) for part in parts[:3])


def _get_release_api_url():
    configured_url = current_app.config.get('PRISM_RELEASE_API_URL')
    if configured_url:
        return configured_url

    github_repository = os.environ.get('GITHUB_REPOSITORY', '').strip()
    if github_repository:
        return f'https://api.github.com/repos/{github_repository}/releases/latest'

    try:
        result = subprocess.run(
            ['git', 'remote', 'get-url', 'origin'],
            cwd=current_app.root_path,
            capture_output=True,
            text=True,
            timeout=2
        )
    except Exception:
        return None

    if result.returncode != 0:
        return None

    remote = result.stdout.strip()
    if 'github.com' not in remote:
        return None

    repo = remote.removesuffix('.git')
    if repo.startswith('git@github.com:'):
        repo = repo.replace('git@github.com:', '', 1)
    elif repo.startswith('https://github.com/'):
        repo = repo.replace('https://github.com/', '', 1)
    else:
        return None

    return f'https://api.github.com/repos/{repo}/releases/latest'


@system_bp.route('/system/check-update', methods=['GET'])
def check_update():
    """
    Check latest release metadata.

    Network failure is returned as a successful API response with error details
    so the settings UI can show a controlled status instead of a 404/500.
    """
    from config import Config

    current_version = Config.PRISM_VERSION
    release_api_url = _get_release_api_url()

    if not release_api_url:
        return jsonify({
            'status': 'success',
            'data': {
                'current_version': current_version,
                'latest_version': None,
                'has_update': False,
                'release_url': '',
                'release_notes': '',
                'message': '未設定更新來源',
            }
        })

    try:
        import requests
        response = requests.get(
            release_api_url,
            timeout=10,
            headers={'Accept': 'application/vnd.github+json'}
        )
        response.raise_for_status()
        release = response.json()
    except Exception as e:
        return jsonify({
            'status': 'success',
            'data': {
                'current_version': current_version,
                'latest_version': None,
                'has_update': False,
                'release_url': '',
                'release_notes': '',
                'message': '無法檢查更新',
                'error': str(e),
            }
        })

    latest_version = release.get('tag_name') or release.get('name')
    has_update = _normalize_version(latest_version) > _normalize_version(current_version)

    return jsonify({
        'status': 'success',
        'data': {
            'current_version': current_version,
            'latest_version': latest_version,
            'has_update': has_update,
            'release_url': release.get('html_url', ''),
            'release_notes': release.get('body', ''),
            'message': '發現新版本' if has_update else '已是最新版本',
        }
    })


@system_bp.route('/system/migration-status', methods=['GET'])
def migration_status():
    """Return current database migration status."""
    try:
        from migrations import get_migration_status
        db = get_db()
        return jsonify({
            'status': 'success',
            'data': get_migration_status(db)
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


# ===================================================================
# Port Configuration (v1.5.0)
# ===================================================================

def _get_port_config_path():
    """Get the port config file path"""
    return os.path.join(current_app.root_path, '.port_config')


@system_bp.route('/system/port-config', methods=['GET'])
def get_port_config():
    """
    取得端口設定
    Response: { 
        preferred_port: int,
        fallback_enabled: bool,
        fallback_range: int,
        current_port: int
    }
    """
    try:
        config_path = _get_port_config_path()
        config = {
            'preferred_port': 5000,
            'fallback_enabled': True,
            'fallback_range': 20
        }
        
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                saved = json.load(f)
                config.update(saved)
        
        # Get current running port from environment or request
        from flask import request
        current_port = request.host.split(':')[-1] if ':' in request.host else '80'
        config['current_port'] = int(current_port)
        
        return jsonify({
            'status': 'success',
            'data': config
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@system_bp.route('/system/port-config', methods=['POST'])
def set_port_config():
    """
    設定端口偏好
    Body: { 
        preferred_port: int,
        fallback_enabled: bool,
        fallback_range: int
    }
    """
    try:
        from flask import request
        data = request.get_json() or {}
        
        config_path = _get_port_config_path()
        
        # Load existing config
        config = {}
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
        
        # Update with new values
        if 'preferred_port' in data:
            port = int(data['preferred_port'])
            if port < 1024 or port > 65535:
                return jsonify({
                    'status': 'error',
                    'message': '端口必須在 1024-65535 之間'
                }), 400
            config['preferred_port'] = port
        
        if 'fallback_enabled' in data:
            config['fallback_enabled'] = bool(data['fallback_enabled'])
        
        if 'fallback_range' in data:
            fb_range = int(data['fallback_range'])
            if fb_range < 1 or fb_range > 100:
                return jsonify({
                    'status': 'error',
                    'message': '備用範圍必須在 1-100 之間'
                }), 400
            config['fallback_range'] = fb_range
        
        # Save config
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        return jsonify({
            'status': 'success',
            'data': config,
            'message': '端口設定已儲存，下次啟動時生效'
        })
        
    except ValueError:
        return jsonify({
            'status': 'error',
            'message': '無效的數值'
        }), 400
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

