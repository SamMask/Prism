from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HOME_PATH = ROOT / "frontend" / "src" / "pages" / "HomePage.tsx"
STORE_PATH = ROOT / "frontend" / "src" / "stores" / "appStore.ts"
I18N_PATH = ROOT / "frontend" / "src" / "i18n" / "index.ts"
TODO_PATH = ROOT / "docs" / "TODO.md"
HANDOFF_PATH = ROOT / "HANDOFF.md"


def test_kwf02_saved_search_workspace_uses_local_storage_without_backend_contract():
    home = HOME_PATH.read_text(encoding="utf-8")
    store = STORE_PATH.read_text(encoding="utf-8")

    assert "SAVED_SEARCH_WORKSPACES_STORAGE_KEY = 'prism.savedSearchWorkspaces.v1'" in home
    assert "function readSavedSearchWorkspaces(): SavedSearchWorkspace[]" in home
    assert "function writeSavedSearchWorkspaces(workspaces: SavedSearchWorkspace[]): void" in home
    assert "localStorage.getItem(SAVED_SEARCH_WORKSPACES_STORAGE_KEY)" in home
    assert "localStorage.setItem(SAVED_SEARCH_WORKSPACES_STORAGE_KEY, JSON.stringify(workspaces))" in home
    assert "api." not in home.split("function saveCurrentSearchWorkspace")[1].split("const applySavedSearchWorkspace")[0]

    assert "export type SearchWorkspaceFilters = {" in store
    assert "applySearchWorkspace: (filters: SearchWorkspaceFilters) => void" in store
    assert "applySearchWorkspace: (filters) => {" in store
    assert "get().fetchNotes(true)" in store


def test_kwf02_saved_search_workspace_renders_save_restore_and_delete_controls():
    home = HOME_PATH.read_text(encoding="utf-8")
    i18n = I18N_PATH.read_text(encoding="utf-8")

    assert 'data-testid="saved-search-workspace-bar"' in home
    assert 'data-testid="save-search-workspace"' in home
    assert "data-testid={`saved-search-workspace-${workspace.id}`}" in home
    assert "data-testid={`delete-saved-search-workspace-${workspace.id}`}" in home
    assert "saveCurrentSearchWorkspace" in home
    assert "applySavedSearchWorkspace(workspace)" in home
    assert "deleteSavedSearchWorkspace(workspace.id)" in home

    assert i18n.count("savedSearch: {") >= 4
    for key in ["title:", "save:", "empty:", "saved:", "restored:", "removed:"]:
        assert i18n.count(key) >= 4
    for phrase in ["搜尋工作區", "Search workspace", "検索ワークスペース", "검색 작업공간"]:
        assert phrase in i18n


def test_kwf02_docs_close_saved_search_and_recommend_snapshot_next():
    todo = TODO_PATH.read_text(encoding="utf-8")
    handoff = HANDOFF_PATH.read_text(encoding="utf-8")

    assert "`KWF-02 Saved Search / Search Workspace`（狀態：`Done`）" in todo
    assert "localStorage key `prism.savedSearchWorkspaces.v1`" in todo
    assert "沒有新增 DB migration、Go API、semantic search、auth 或 Pi deploy" in todo
    assert "`KWF-03 Full data snapshot export`（狀態：`Todo`）" in todo
    assert "KWF-02 Saved Search / Search Workspace 已完成" in handoff
    assert "下一個建議入口是 `KWF-03 Full data snapshot export`" in handoff
