from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SETTINGS_PATH = ROOT / "frontend" / "src" / "pages" / "SettingsPage.tsx"
HOME_PATH = ROOT / "frontend" / "src" / "pages" / "HomePage.tsx"
DATA_MANAGER_PATH = ROOT / "frontend" / "src" / "components" / "DataManager.tsx"
PORT_CONFIG_PATH = ROOT / "frontend" / "src" / "components" / "settings" / "PortConfigSection.tsx"
UPDATE_PATH = ROOT / "frontend" / "src" / "components" / "settings" / "UpdateSection.tsx"
SERVER_DASHBOARD_PATH = ROOT / "frontend" / "src" / "components" / "settings" / "ServerDashboardSection.tsx"
SYSTEM_MAINTENANCE_PATH = ROOT / "frontend" / "src" / "components" / "SystemMaintenance.tsx"
API_PATH = ROOT / "frontend" / "src" / "services" / "api.ts"
SERVER_ROUTE_PATH = ROOT / "routes" / "server.py"
TODO_PATH = ROOT / "docs" / "development-history" / "todo-archive-pre-go-primary-runtime-migration-20260606.md"


def test_settings_home_followups_are_recorded_in_ui_copy_and_layout():
    settings = SETTINGS_PATH.read_text(encoding="utf-8")
    home = HOME_PATH.read_text(encoding="utf-8")
    maintenance = SYSTEM_MAINTENANCE_PATH.read_text(encoding="utf-8")

    assert "資料庫維護（進階）" in settings
    assert "目前穩定使用路徑是 Source / Dev mode 與 Raspberry Pi 部署" in settings
    assert "本機更新程式時不應覆蓋這些資料目錄" in settings
    assert "進階維護與疑難排解工具" in maintenance
    assert "flex min-w-0 flex-wrap items-baseline gap-x-3 gap-y-1" in home


def test_settings_deploy_controls_explain_port_update_and_hide_local_service_management():
    port_config = PORT_CONFIG_PATH.read_text(encoding="utf-8")
    update = UPDATE_PATH.read_text(encoding="utf-8")
    server_dashboard = SERVER_DASHBOARD_PATH.read_text(encoding="utf-8")
    api = API_PATH.read_text(encoding="utf-8")
    server_route = SERVER_ROUTE_PATH.read_text(encoding="utf-8")

    assert "目前可用網址" in port_config
    assert "若頁面已完全連不上" in port_config
    assert "啟動 console / log" in port_config
    assert "本機版本更新以覆蓋程式檔為主" in update
    assert "不需要另外選補丁檔" in update
    assert "service_management" in api
    assert "const canManageService = hardware?.service_management?.available === true" in server_dashboard
    assert "getattr(sys, 'frozen', False)" in server_route


def test_category_counts_and_backup_delete_controls_are_locked():
    data_manager = DATA_MANAGER_PATH.read_text(encoding="utf-8")
    server_dashboard = SERVER_DASHBOARD_PATH.read_text(encoding="utf-8")
    api = API_PATH.read_text(encoding="utf-8")
    server_route = SERVER_ROUTE_PATH.read_text(encoding="utf-8")

    assert 'data-testid="category-count"' in data_manager
    assert "w-12 shrink-0 rounded bg-bg-elevated px-2 py-0.5 text-right text-xs tabular-nums" in data_manager
    assert 'data-testid="category-actions"' in data_manager
    assert "flex w-16 shrink-0 justify-end gap-1" in data_manager
    assert "一鍵下載與輪換備份都會保留最近 3 份" in server_dashboard
    assert "handleDeleteBackup" in server_dashboard
    assert "api.deleteBackup(backup.filename)" in server_dashboard
    assert "deleteBackup: async (filename: string)" in api
    assert "@server_bp.route('/server/backup/<path:filename>', methods=['DELETE'])" in server_route


def test_todo_records_phase24_settings_home_followup_scope():
    todo = TODO_PATH.read_text(encoding="utf-8")

    assert "Phase 24: Settings and Home Maintenance Follow-up" in todo
    assert "Markdown zip image bundle" in todo
    assert "specific backup delete" in todo
    assert "No Go/Pi runtime expansion" in todo
    assert "Category count column alignment follow-up" in todo

