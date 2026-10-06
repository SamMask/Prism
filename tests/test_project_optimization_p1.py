from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend" / "src"


def _read(relative_path: str) -> str:
    return (FRONTEND / relative_path).read_text(encoding="utf-8")


def test_data_recovery_groups_restore_lifecycle_and_db_only_scope():
    settings = _read("pages/SettingsPage.tsx")
    backup = _read("components/settings/BackupImportSection.tsx")
    dashboard = _read("components/settings/ServerDashboardSection.tsx")

    assert 'data-testid="data-recovery-section"' in backup
    assert 'data-testid="db-only-recovery-scope"' in backup
    assert "api.rotateBackups" in backup
    assert "api.deleteBackup" in backup
    assert "api.restoreBackup" in backup
    assert 'data-testid="restore-point-lifecycle"' in backup
    assert 'data-testid="maintenance-advanced"' in settings
    assert "api.rotateBackups" not in dashboard
    assert "api.deleteBackup" not in dashboard


def test_full_snapshot_has_typed_download_and_visible_product_entry():
    api = _read("services/api.ts")
    backup = _read("components/settings/BackupImportSection.tsx")

    assert "export interface FullSnapshotDownload" in api
    assert "downloadFullSnapshot: async" in api
    assert '"/export/full-snapshot"' in api
    assert 'data-testid="full-data-snapshot-export"' in backup
    assert "api.downloadFullSnapshot()" in backup
    assert "fullSnapshotContents" in backup
    assert "fullSnapshotManualRestore" in backup


def test_prompt_save_uses_typed_api_system_identity_and_continuation_actions():
    hook = _read("hooks/usePromptBuilder.ts")
    toast = _read("components/ui/Toast.tsx")

    save_block = hook[hook.index("const saveToLibrary"):hook.index("// Wizard Functions")]
    assert "api.getCategories()" in save_block
    assert "category.system_key === 'prompt'" in save_block
    assert "api.createNote(" in save_block
    assert 'fetch("/api/categories")' not in save_block
    assert 'fetch("/api/notes"' not in save_block
    assert "fetchNotes(true)" in save_block
    assert "fetchCategories()" in save_block
    assert "toast.success" in save_block
    assert "openSavedNote" in save_block
    assert "viewPromptLibrary" in save_block
    assert "ToastAction" in toast


def test_library_only_filter_strip_and_compact_saved_view_empty_state():
    layout = _read("components/Layout.tsx")
    home = _read("pages/HomePage.tsx")

    assert "useLocation" in layout
    assert "location.pathname === '/'" in layout
    assert "isLibraryRoute && <FilterStrip />" in layout
    assert 'data-testid="saved-search-empty-cta"' in home
    assert "savedSearchWorkspaces.length > 0" in home


def test_custom_reorder_requires_unfiltered_fully_loaded_library():
    home = _read("pages/HomePage.tsx")

    assert "const isUnfilteredLibrary" in home
    assert "const isAllNotesLoaded" in home
    assert "const isDragEnabled = sortBy === 'custom' && isUnfilteredLibrary && isAllNotesLoaded" in home
    assert "if (!isDragEnabled) return" in home
    assert 'data-testid="custom-reorder-disabled-reason"' in home


def test_prompt_and_settings_routes_are_lazy_with_recoverable_fallback():
    app = _read("App.tsx")

    assert "lazy(() => import('./pages/PromptBuilder')" in app
    assert "lazy(() => import('./pages/SettingsPage')" in app
    assert "<Suspense fallback={<RouteLoadFallback />}" in app
    assert "RouteLoadErrorBoundary" in app
    assert "window.location.reload()" in app
    assert "lazy(() => import('./pages/HomePage')" not in app


def test_test_portfolio_and_browser_smoke_use_current_isolated_runtime():
    inventory = (ROOT / "docs" / "TEST_PORTFOLIO.md").read_text(encoding="utf-8")
    conftest = (ROOT / "e2e" / "conftest.py").read_text(encoding="utf-8")
    smoke = (ROOT / "e2e" / "test_note_flow.py").read_text(encoding="utf-8")

    for category in ("Behavior", "Contract", "Governance", "Historical"):
        assert category in inventory
    assert "http://localhost:5000" not in conftest
    assert "tmp_path_factory" in conftest
    assert "prism-go-runtime.exe" in conftest
    assert "if ".casefold() not in smoke.casefold()
    for marker in (
        "test_home_search_and_open_note",
        "test_prompt_builder_direct_load",
        "test_data_recovery_direct_load",
    ):
        assert marker in smoke


# PRISM-OPT-20: governance checks for the separated-notes maintenance action. Behavior is
# covered by go-shadow/notes_inline_test.go and the isolated-runtime smoke.
def _inline_notes_blocks(i18n: str) -> list[str]:
    blocks = []
    start = 0
    while True:
        start = i18n.find("      inlineNotes: {", start)
        if start < 0:
            return blocks
        end = i18n.index("\n      },\n", start)
        blocks.append(i18n[start:end])
        start = end


def _keys(block: str) -> set[str]:
    keys = set()
    for line in block.splitlines()[1:]:
        stripped = line.strip()
        if ":" in stripped and not stripped.startswith("}"):
            keys.add(f"{len(line) - len(line.lstrip())}:{stripped.split(':', 1)[0]}")
    return keys


def test_inline_separated_notes_i18n_keys_match_in_four_locales():
    i18n = _read("i18n/index.ts")
    blocks = _inline_notes_blocks(i18n)
    assert len(blocks) == 4
    reference = _keys(blocks[0])
    assert "8:resultUnknown" in reference and "10:media_unprotected" in reference
    for block in blocks[1:]:
        assert _keys(block) == reference


def test_inline_separated_notes_is_registered_documented_and_explicit():
    main_go = (ROOT / "go-shadow" / "main.go").read_text(encoding="utf-8")
    api_reference = (ROOT / "docs" / "API_REFERENCE.md").read_text(encoding="utf-8")
    contracts = (ROOT / "docs" / "CONTRACTS.md").read_text(encoding="utf-8")
    manifest = (ROOT / "docs" / "contracts" / "go-primary-route-ownership-manifest.json").read_text(encoding="utf-8")
    api = _read("services/api.ts")

    assert 'mux.HandleFunc("/api/system/inline-separated-notes", srv.handleInlineSeparatedNotes)' in main_go
    assert "POST `/api/system/inline-separated-notes`" in api_reference
    assert "CONTRACT-SEPARATED-NOTES-INLINE" in contracts
    assert '"rule": "/api/system/inline-separated-notes"' in manifest
    assert "{ dry_run: dryRun }" in api


def test_note_file_writers_take_the_note_files_lock():
    go = ROOT / "go-shadow"
    sources = {name: (go / name).read_text(encoding="utf-8") for name in (
        "notes_actions.go", "notes_write.go", "attachments.go", "import.go", "media_cleanup.go", "export.go", "notes_inline.go",
    )}

    def body(source: str, signature: str) -> str:
        start = source.index(signature)
        return source[start:source.index("\n}\n", start)]

    locked = [
        ("notes_actions.go", "func (s *server) restoreSeparatedContent("),
        ("notes_actions.go", "func (s *server) separateContent("),
        ("notes_actions.go", "func (s *server) duplicateNote("),
        ("notes_actions.go", "func (s *server) batchDeleteNotes("),
        ("notes_write.go", "func (s *server) deleteNote("),
        ("attachments.go", "func (s *server) deleteAttachment("),
        ("attachments.go", "func (s *server) uploadAttachment("),
        ("import.go", "func (s *server) importJSONNotes("),
        ("media_cleanup.go", "func (s *server) deleteOrphanImages("),
        ("media_cleanup.go", "func (s *server) deleteAllOriginals("),
        ("media_cleanup.go", "func (s *server) fixBrokenImages("),
        ("export.go", "func (s *server) buildFullSnapshot("),
        ("notes_inline.go", "func (s *server) runInlineSeparatedNotes("),
    ]
    for name, signature in locked:
        assert "noteFilesMu" in body(sources[name], signature) or "lockNoteFiles()" in body(sources[name], signature), signature
