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
TODO_PATH = ROOT / "docs" / "development-history" / "todo-archive-pre-go-primary-runtime-migration-20260606.md"


def test_settings_home_followups_are_recorded_in_ui_copy_and_layout():
    settings = SETTINGS_PATH.read_text(encoding="utf-8")
    home = HOME_PATH.read_text(encoding="utf-8")
    maintenance = SYSTEM_MAINTENANCE_PATH.read_text(encoding="utf-8")

    assert "維護與健康檢查" in settings
    assert "後端: Go primary runtime + SQLite FTS5" in settings
    assert "目前穩定使用路徑是 Go primary runtime、SQLite FTS5 純關鍵字搜尋與 Raspberry Pi `prism-go-primary.service` 部署" in settings
    assert "本機更新程式時不應覆蓋這些資料目錄" in settings
    assert "資料健康檢查與進階維護工具" in maintenance
    assert "整理資料庫暫存日誌" in maintenance
    assert "SQLite WAL / checkpoint" in maintenance
    assert "這只會回報狀態，不會自動修改資料" in maintenance
    assert "flex min-w-0 flex-wrap items-baseline gap-x-3 gap-y-1" in home


def test_settings_deploy_controls_explain_port_update_and_hide_local_service_management():
    port_config = PORT_CONFIG_PATH.read_text(encoding="utf-8")
    update = UPDATE_PATH.read_text(encoding="utf-8")
    server_dashboard = SERVER_DASHBOARD_PATH.read_text(encoding="utf-8")
    api = API_PATH.read_text(encoding="utf-8")

    assert "目前可用網址" in port_config
    assert "若頁面已完全連不上" in port_config
    assert "啟動 console / log" in port_config
    assert "本機版本更新以覆蓋程式檔為主" in update
    assert "不需要另外選補丁檔" in update
    assert "service_management" in api
    assert "const canManageService = hardware?.service_management?.available === true" in server_dashboard


def test_category_counts_and_backup_delete_controls_are_locked():
    data_manager = DATA_MANAGER_PATH.read_text(encoding="utf-8")
    server_dashboard = SERVER_DASHBOARD_PATH.read_text(encoding="utf-8")
    api = API_PATH.read_text(encoding="utf-8")

    assert 'data-testid="category-count"' in data_manager
    assert "w-12 shrink-0 rounded bg-bg-elevated px-2 py-0.5 text-right text-xs tabular-nums" in data_manager
    assert 'data-testid="category-actions"' in data_manager
    assert "flex w-16 shrink-0 justify-end gap-1" in data_manager
    assert "Prism 內建還原點" in server_dashboard
    assert "下載目前資料庫是一次性副本；建立還原點會保留最近 3 份供資料庫還原使用" in server_dashboard
    assert "handleDeleteBackup" in server_dashboard
    assert "api.deleteBackup(backup.filename)" in server_dashboard
    assert "deleteBackup: async (filename: string)" in api


def test_core_ux_settings_tabs_and_backup_restore_copy_are_locked():
    settings = SETTINGS_PATH.read_text(encoding="utf-8")
    backup_import = (ROOT / "frontend" / "src" / "components" / "settings" / "BackupImportSection.tsx").read_text(encoding="utf-8")
    server_dashboard = SERVER_DASHBOARD_PATH.read_text(encoding="utf-8")

    for label in ["外觀", "組織", "備份與還原", "維護與健康", "存取與系統", "關於"]:
        assert f"label: '{label}'" in settings

    assert "Flask + SQLite" not in settings
    assert "下載一份可自行保存或帶到其他工具使用的資料副本；這不會建立 Prism 內建還原點" in backup_import
    assert "匯入先前下載的 JSON 副本；這會新增或建立副本，不會覆蓋整個資料庫" in backup_import
    assert "選一個 Prism 內建還原點" in backup_import
    assert "還原前會先把目前資料庫另存一份" in backup_import
    assert "資料庫副本下載失敗" in server_dashboard
    assert "建立還原點失敗" in server_dashboard


def test_todo_records_phase24_settings_home_followup_scope():
    todo = TODO_PATH.read_text(encoding="utf-8")

    assert "Phase 24: Settings and Home Maintenance Follow-up" in todo
    assert "Markdown zip image bundle" in todo
    assert "specific backup delete" in todo
    assert "No Go/Pi runtime expansion" in todo
    assert "Category count column alignment follow-up" in todo
