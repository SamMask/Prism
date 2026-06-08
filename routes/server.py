# -*- coding: utf-8 -*-
"""
Server Management API Routes - Phase 8: Headless Server Management
Prism v2.1.0

Endpoints for remote management of headless deployments (e.g., Raspberry Pi):
- Hardware monitoring (CPU temp, memory, disk)
- Log viewer (app.log tail)
- Service restart (systemd)
- Database backup (download + auto-rotate)
- Version info
"""

import os
import sys
import json
import shutil
import sqlite3
import platform
import subprocess
from datetime import datetime

from flask import Blueprint, jsonify, request, current_app, send_file, abort

server_bp = Blueprint('server', __name__)

DEFAULT_BACKUP_KEEP_COUNT = 3
MAX_BACKUP_KEEP_COUNT = 10


@server_bp.before_request
def _require_localhost():
    """Server management API is restricted to localhost connections."""
    if request.remote_addr not in ('127.0.0.1', '::1'):
        abort(403, description='Server management API is accessible from localhost only')


# ===================================================================
# 8.3 Hardware & System Status
# ===================================================================

@server_bp.route('/server/hardware', methods=['GET'])
def get_hardware_status():
    """
    取得硬體與系統狀態
    Response: {
        cpu_temp: float | null,
        memory: { total_mb, used_mb, available_mb, percent },
        disk: { total_gb, used_gb, free_gb, percent },
        database: { size_mb, wal_size_mb },
        platform: { system, machine, hostname },
        uptime_seconds: int | null
    }
    """
    try:
        result = {
            'cpu_temp': _get_cpu_temp(),
            'memory': _get_memory_info(),
            'disk': _get_disk_info(),
            'database': _get_db_sizes(),
            'platform': {
                'system': platform.system(),
                'machine': platform.machine(),
                'hostname': platform.node(),
                'python_version': platform.python_version(),
            },
            'service_management': _get_service_management_status(),
            'uptime_seconds': _get_uptime(),
        }

        return jsonify({'status': 'success', 'data': result})

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


def _get_cpu_temp():
    """讀取 CPU 溫度 (Linux/Raspberry Pi only)"""
    try:
        # Raspberry Pi thermal zone
        thermal_path = '/sys/class/thermal/thermal_zone0/temp'
        if os.path.exists(thermal_path):
            with open(thermal_path, 'r') as f:
                temp_millideg = int(f.read().strip())
                return round(temp_millideg / 1000.0, 1)
    except Exception:
        pass

    try:
        # Try psutil if available
        import psutil
        temps = psutil.sensors_temperatures()
        if temps:
            for name, entries in temps.items():
                if entries:
                    return round(entries[0].current, 1)
    except (ImportError, Exception):
        pass

    return None


def _get_service_management_status():
    """Report whether the UI should expose systemd service controls."""
    is_linux = platform.system() == 'Linux'
    has_systemctl = shutil.which('systemctl') is not None
    available = is_linux and has_systemctl and not getattr(sys, 'frozen', False)

    if available:
        reason = 'systemd service controls available'
    elif getattr(sys, 'frozen', False):
        reason = 'hidden for packaged local executable'
    elif not is_linux:
        reason = 'hidden outside Linux/systemd deployments'
    else:
        reason = 'systemctl not available'

    return {
        'available': available,
        'reason': reason,
    }


def _get_memory_info():
    """取得記憶體使用情況"""
    try:
        import psutil
        mem = psutil.virtual_memory()
        return {
            'total_mb': round(mem.total / 1024 / 1024, 1),
            'used_mb': round(mem.used / 1024 / 1024, 1),
            'available_mb': round(mem.available / 1024 / 1024, 1),
            'percent': mem.percent,
        }
    except ImportError:
        # Fallback for systems without psutil
        if platform.system() == 'Linux':
            try:
                with open('/proc/meminfo', 'r') as f:
                    lines = f.readlines()
                info = {}
                for line in lines:
                    parts = line.split(':')
                    if len(parts) == 2:
                        key = parts[0].strip()
                        val = int(parts[1].strip().split()[0])  # in kB
                        info[key] = val
                total = info.get('MemTotal', 0)
                available = info.get('MemAvailable', info.get('MemFree', 0))
                used = total - available
                return {
                    'total_mb': round(total / 1024, 1),
                    'used_mb': round(used / 1024, 1),
                    'available_mb': round(available / 1024, 1),
                    'percent': round(used / total * 100, 1) if total > 0 else 0,
                }
            except Exception:
                pass
        return None


def _get_disk_info():
    """取得磁碟使用情況"""
    try:
        import psutil
        # Get disk usage for the partition where the app resides
        app_path = current_app.root_path
        disk = psutil.disk_usage(app_path)
        return {
            'total_gb': round(disk.total / 1024 / 1024 / 1024, 2),
            'used_gb': round(disk.used / 1024 / 1024 / 1024, 2),
            'free_gb': round(disk.free / 1024 / 1024 / 1024, 2),
            'percent': disk.percent,
        }
    except ImportError:
        # Fallback using shutil
        try:
            total, used, free = shutil.disk_usage(current_app.root_path)
            return {
                'total_gb': round(total / 1024 / 1024 / 1024, 2),
                'used_gb': round(used / 1024 / 1024 / 1024, 2),
                'free_gb': round(free / 1024 / 1024 / 1024, 2),
                'percent': round(used / total * 100, 1) if total > 0 else 0,
            }
        except Exception:
            return None


def _get_db_sizes():
    """取得資料庫檔案大小"""
    try:
        db_path = current_app.config['DATABASE']
        db_size = os.path.getsize(db_path) if os.path.exists(db_path) else 0
        wal_path = db_path + '-wal'
        wal_size = os.path.getsize(wal_path) if os.path.exists(wal_path) else 0
        return {
            'size_mb': round(db_size / 1024 / 1024, 2),
            'wal_size_mb': round(wal_size / 1024 / 1024, 2),
        }
    except Exception:
        return None


def _get_uptime():
    """取得系統運行時間 (seconds)"""
    try:
        import psutil
        boot_time = psutil.boot_time()
        return int(datetime.now().timestamp() - boot_time)
    except ImportError:
        if platform.system() == 'Linux':
            try:
                with open('/proc/uptime', 'r') as f:
                    return int(float(f.read().split()[0]))
            except Exception:
                pass
        return None


# ===================================================================
# 8.4 System Logs
# ===================================================================

@server_bp.route('/server/logs', methods=['GET'])
def get_server_logs():
    """
    讀取系統日誌 (倒數 N 行)
    Query Params:
      - lines: int (default 100, max 500)
      - level: str (optional filter: 'WARNING', 'ERROR', 'ALL')
    Response: { lines: [...], total_lines: int, log_file: str }
    """
    try:
        lines_count = min(int(request.args.get('lines', 100)), 500)
        level_filter = request.args.get('level', 'ALL').upper()

        log_file = os.path.join(current_app.root_path, 'app.log')

        if not os.path.exists(log_file):
            return jsonify({
                'status': 'success',
                'data': {
                    'lines': [],
                    'total_lines': 0,
                    'log_file': 'app.log',
                    'message': '日誌檔案尚未建立',
                }
            })

        # Read last N lines efficiently
        all_lines = []
        with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
            all_lines = f.readlines()

        # Apply level filter
        if level_filter != 'ALL':
            filtered = [l for l in all_lines if f'[{level_filter}]' in l]
        else:
            filtered = all_lines

        # Get last N lines
        tail_lines = filtered[-lines_count:]
        # Strip trailing newlines
        tail_lines = [line.rstrip('\n\r') for line in tail_lines]

        return jsonify({
            'status': 'success',
            'data': {
                'lines': tail_lines,
                'total_lines': len(all_lines),
                'filtered_lines': len(filtered),
                'log_file': 'app.log',
                'log_size_kb': round(os.path.getsize(log_file) / 1024, 1),
            }
        })

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ===================================================================
# 8.4 Service Restart (Systemd)
# ===================================================================

@server_bp.route('/server/restart', methods=['POST'])
def restart_service():
    """
    透過 Systemd 觸發服務重啟 (僅限 Linux)
    Body (optional): { service_name: str }  (default: 'prism')
    
    安全性: 
    - 僅允許在 Linux 系統上執行
    - 服務名稱經過清洗，防止注入攻擊
    """
    try:
        if platform.system() != 'Linux':
            return jsonify({
                'status': 'error',
                'message': '服務重啟僅支援 Linux 系統 (Systemd)'
            }), 400

        data = request.get_json(silent=True) or {}
        service_name = data.get('service_name', 'prism')

        # Sanitize service name (only allow alphanumeric, dash, underscore)
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', service_name):
            return jsonify({
                'status': 'error',
                'message': '無效的服務名稱'
            }), 400

        # Execute systemctl restart
        result = subprocess.run(
            ['sudo', 'systemctl', 'restart', service_name],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            return jsonify({
                'status': 'success',
                'message': f'服務 {service_name} 正在重啟...',
            })
        else:
            return jsonify({
                'status': 'error',
                'message': f'重啟失敗: {result.stderr.strip()}',
            }), 500

    except subprocess.TimeoutExpired:
        return jsonify({
            'status': 'error',
            'message': '重啟命令逾時 (30秒)'
        }), 500
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ===================================================================
# 8.5 Database Backup
# ===================================================================

def _get_backup_dir():
    """Get or create backup directory"""
    backup_dir = current_app.config.get('PRISM_BACKUP_DIR') or os.path.join(current_app.root_path, 'backups')
    os.makedirs(backup_dir, exist_ok=True)
    return backup_dir


def _is_managed_backup_filename(filename):
    return (
        filename
        and filename == os.path.basename(filename)
        and filename.startswith('prism_backup_')
        and filename.endswith('.db')
    )


def _parse_backup_keep_count(data, default=DEFAULT_BACKUP_KEEP_COUNT):
    """Read backup retention count from keep_count or legacy keep."""
    raw_keep = data.get('keep_count', data.get('keep', default))
    try:
        keep_count = int(raw_keep)
    except (TypeError, ValueError):
        keep_count = default
    return max(1, min(keep_count, MAX_BACKUP_KEEP_COUNT))


def _list_managed_backups(backup_dir):
    backups = []
    for filename in os.listdir(backup_dir):
        if not _is_managed_backup_filename(filename):
            continue
        path = os.path.join(backup_dir, filename)
        if not os.path.isfile(path):
            continue
        modified_at = os.path.getmtime(path)
        backups.append({
            'filename': filename,
            'path': path,
            'size_bytes': os.path.getsize(path),
            'created_at': datetime.fromtimestamp(modified_at).isoformat(),
            'modified_at': modified_at,
        })

    backups.sort(key=lambda item: (item['modified_at'], item['filename']), reverse=True)
    return backups


def _enforce_backup_retention(backup_dir, keep_count, protected_filename=None):
    backups = _list_managed_backups(backup_dir)
    protected = None
    if protected_filename:
        protected = next(
            (backup for backup in backups if backup['filename'] == protected_filename),
            None
        )

    if protected:
        newest_without_protected = [
            backup for backup in backups
            if backup['filename'] != protected_filename
        ]
        kept = [protected] + newest_without_protected[:keep_count - 1]
    else:
        kept = backups[:keep_count]

    kept_names = {backup['filename'] for backup in kept}
    to_delete = [
        backup for backup in backups
        if backup['filename'] not in kept_names
    ]

    deleted_names = []
    for backup in to_delete:
        try:
            os.remove(backup['path'])
            deleted_names.append(backup['filename'])
        except Exception as e:
            print(f"[WARNING] Failed to delete backup {backup['filename']}: {e}")

    total_size = sum(backup['size_bytes'] for backup in kept)
    return kept, deleted_names, total_size


def _backup_response_item(backup):
    return {
        'filename': backup['filename'],
        'size_bytes': backup['size_bytes'],
        'size_mb': round(backup['size_bytes'] / 1024 / 1024, 2),
        'created_at': backup['created_at'],
    }


def _resolve_backup_path(filename):
    """Resolve a managed Prism backup filename inside the backup directory."""
    if not _is_managed_backup_filename(filename):
        return None

    backup_dir = _get_backup_dir()
    backup_path = os.path.abspath(os.path.join(backup_dir, filename))
    backup_dir_abs = os.path.abspath(backup_dir)
    if not backup_path.startswith(backup_dir_abs + os.sep):
        return None
    return backup_path


@server_bp.route('/server/backup/download', methods=['GET'])
def download_backup():
    """
    一鍵打包下載當前資料庫
    先執行 WAL Checkpoint 確保資料完整，再打包 .db 檔案提供下載
    """
    try:
        db_path = current_app.config['DATABASE']

        if not os.path.exists(db_path):
            return jsonify({
                'status': 'error',
                'message': '資料庫檔案不存在'
            }), 404

        # Execute WAL checkpoint first for data integrity
        try:
            conn = sqlite3.connect(db_path)
            conn.execute('PRAGMA wal_checkpoint(TRUNCATE)')
            conn.close()
        except Exception as wal_err:
            print(f"[WARNING] WAL checkpoint before backup failed: {wal_err}")

        # Create a temporary backup copy
        backup_dir = _get_backup_dir()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'prism_backup_{timestamp}.db'
        backup_path = os.path.join(backup_dir, backup_filename)

        shutil.copy2(db_path, backup_path)
        _enforce_backup_retention(
            backup_dir,
            _parse_backup_keep_count(request.args, DEFAULT_BACKUP_KEEP_COUNT),
            protected_filename=backup_filename,
        )

        return send_file(
            backup_path,
            as_attachment=True,
            download_name=backup_filename,
            mimetype='application/x-sqlite3'
        )

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@server_bp.route('/server/backup/rotate', methods=['POST'])
def rotate_backups():
    """
    自動輪換備份 - 保留最近 N 份 (預設 3)
    1. 先建立當前資料庫的新備份
    2. 清理舊備份，只保留最近 N 份

    Body (optional): { keep_count: int }  (default: 3)
    Response: {
        new_backup: str,
        kept_backups: [...],
        deleted_backups: [...],
        total_size_mb: float
    }
    """
    try:
        data = request.get_json(silent=True) or {}
        keep_count = _parse_backup_keep_count(data)

        db_path = current_app.config['DATABASE']
        backup_dir = _get_backup_dir()

        # WAL Checkpoint first
        try:
            conn = sqlite3.connect(db_path)
            conn.execute('PRAGMA wal_checkpoint(TRUNCATE)')
            conn.close()
        except Exception:
            pass

        # Create new backup
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        new_backup_name = f'prism_backup_{timestamp}.db'
        new_backup_path = os.path.join(backup_dir, new_backup_name)
        shutil.copy2(db_path, new_backup_path)

        kept, deleted_names, total_size = _enforce_backup_retention(
            backup_dir,
            keep_count,
            protected_filename=new_backup_name,
        )

        return jsonify({
            'status': 'success',
            'data': {
                'new_backup': new_backup_name,
                'kept_backups': [
                    _backup_response_item(b)
                    for b in kept
                ],
                'deleted_backups': deleted_names,
                'total_size_mb': round(total_size / 1024 / 1024, 2),
            }
        })

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@server_bp.route('/server/backup/list', methods=['GET'])
def list_backups():
    """
    列出所有備份檔案
    Response: { backups: [...], total_size_mb: float }
    """
    try:
        backup_dir = _get_backup_dir()
        backups = _list_managed_backups(backup_dir)
        total_size = sum(b['size_bytes'] for b in backups)

        return jsonify({
            'status': 'success',
            'data': {
                'backups': [_backup_response_item(b) for b in backups],
                'count': len(backups),
                'total_size_mb': round(total_size / 1024 / 1024, 2),
            }
        })

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@server_bp.route('/server/backup/<path:filename>', methods=['DELETE'])
def delete_backup(filename):
    """Delete a specific managed Prism database backup."""
    try:
        backup_path = _resolve_backup_path(filename)
        if backup_path is None:
            return jsonify({
                'status': 'error',
                'message': '無效的備份檔名'
            }), 400

        if not os.path.exists(backup_path):
            return jsonify({
                'status': 'error',
                'message': '備份檔案不存在'
            }), 404

        os.remove(backup_path)

        return jsonify({
            'status': 'success',
            'data': {
                'deleted': filename
            }
        })

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ===================================================================
# 8.6 Version Info
# ===================================================================

@server_bp.route('/server/version', methods=['GET'])
def get_version():
    """
    取得當前版本號與更新日誌
    Response: {
        version: str,
        changelog: [...],
        is_frozen: bool,
        v2_mode: bool
    }
    """
    try:
        from config import Config
        version = Config.PRISM_VERSION

        # Try to read CHANGELOG or release notes
        changelog = _read_changelog()

        return jsonify({
            'status': 'success',
            'data': {
                'version': version,
                'changelog': changelog,
                'is_frozen': getattr(sys, 'frozen', False),
                'v2_mode': current_app.config.get('V2_MODE', False),
                'platform': platform.system(),
            }
        })

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


def _read_changelog():
    """讀取更新日誌 (從 TODO-V2.md 的更新記錄段落)"""
    changelog = []

    # Try reading from TODO-V2.md (Update Log section)
    todo_path = os.path.join(current_app.root_path, 'docs', 'TODO-V2.md')
    if os.path.exists(todo_path):
        try:
            with open(todo_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Extract the "更新記錄" section
            import re
            # Find the update log section
            match = re.search(
                r'## 📝 更新記錄 \(Update Log\)(.*?)(?=\n## |\n---\n## |\Z)',
                content,
                re.DOTALL
            )
            if match:
                log_section = match.group(1)
                # Parse individual entries
                entries = re.findall(
                    r'### ✅ (\d{4}-\d{2}-\d{2}): (.+?)(?=\n### |\Z)',
                    log_section,
                    re.DOTALL
                )
                for date, body in entries:
                    title_line = body.split('\n')[0].strip()
                    changelog.append({
                        'date': date,
                        'title': title_line,
                        'body': body.strip()[:500],  # Limit body length
                    })
        except Exception as e:
            print(f"[WARNING] Failed to read changelog: {e}")

    return changelog
