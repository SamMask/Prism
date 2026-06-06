from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SETTINGS_PATH = ROOT / "frontend" / "src" / "pages" / "SettingsPage.tsx"
TODO_PATH = ROOT / "docs" / "development-history" / "todo-archive-pre-go-primary-runtime-migration-20260606.md"


def test_settings_tabs_are_driven_by_url_search_params():
    settings_page = SETTINGS_PATH.read_text(encoding="utf-8")

    assert "useSearchParams" in settings_page
    assert "const tabParam = searchParams.get('tab')" in settings_page
    assert "const activeTab: SettingsTab = isSettingsTab(tabParam) ? tabParam : 'appearance'" in settings_page
    assert "nextParams.set('tab', tab)" in settings_page
    assert "setSearchParams(nextParams, { replace: true })" in settings_page


def test_settings_tabs_accept_only_known_tab_ids_and_preserve_default_appearance():
    settings_page = SETTINGS_PATH.read_text(encoding="utf-8")

    assert "type SettingsTab = 'appearance' | 'data' | 'search' | 'deploy' | 'about'" in settings_page
    assert "function isSettingsTab(value: string | null): value is SettingsTab" in settings_page
    assert "SETTINGS_TAB_IDS.includes(value as SettingsTab)" in settings_page
    assert ": 'appearance'" in settings_page
    assert "data-testid={`settings-panel-${activeTab}`}" in settings_page


def test_todo_records_settings_tab_deep_linking_as_p1_single_task():
    todo = TODO_PATH.read_text(encoding="utf-8")

    assert "Settings tab deep linking" in todo
    assert "Risk level: `P1 workflow-sensitive`" in todo
    assert "這一步會真的改 Settings 分頁的使用流程" in todo
    assert "最多 plan gate + implementation gate" in todo
    assert "不新增 backend API、資料庫 schema、Pi/Caddy/service、Go runtime 或 public exposure" in todo

