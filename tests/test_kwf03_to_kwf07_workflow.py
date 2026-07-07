from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_SCRIPT = ROOT / "scripts" / "export_full_data_snapshot.ps1"
API_PATH = ROOT / "frontend" / "src" / "services" / "api.ts"
STORE_PATH = ROOT / "frontend" / "src" / "stores" / "appStore.ts"
HEADER_PATH = ROOT / "frontend" / "src" / "components" / "Header.tsx"
BACKUP_IMPORT_PATH = ROOT / "frontend" / "src" / "components" / "settings" / "BackupImportSection.tsx"
READING_VIEW_PATH = ROOT / "frontend" / "src" / "components" / "ReadingView.tsx"
I18N_PATH = ROOT / "frontend" / "src" / "i18n" / "index.ts"
TODO_PATH = ROOT / "docs" / "TODO.md"
HANDOFF_PATH = ROOT / "HANDOFF.md"
SCHEMA_PATH = ROOT / "docs" / "SCHEMA.md"
API_REFERENCE_PATH = ROOT / "docs" / "API_REFERENCE.md"


def test_kwf03_full_data_snapshot_script_contract_is_local_and_complete():
    script = SNAPSHOT_SCRIPT.read_text(encoding="utf-8")

    assert "[switch]$DryRun" in script
    assert "full_data_snapshot" in script
    assert "Compress-Archive" in script
    assert "snapshot-manifest.json" in script
    for required in [
        "knowledge.db",
        "knowledge.db-wal",
        "knowledge.db-shm",
        "static\\uploads",
        "docs\\attachments",
        "docs\\notes",
        "config",
    ]:
        assert required in script
    assert "Get-FileHash" in script
    assert "Export-CliXml" not in script


def test_kwf04_batch_delete_uses_server_dry_run_preview_before_write():
    api = API_PATH.read_text(encoding="utf-8")
    store = STORE_PATH.read_text(encoding="utf-8")
    header = HEADER_PATH.read_text(encoding="utf-8")
    reference = API_REFERENCE_PATH.read_text(encoding="utf-8")

    assert "export interface BatchDeletePreview" in api
    assert "previewBatchDeleteNotes" in api
    assert 'client.post("/notes/batch/delete", { note_ids: noteIds, dry_run: true })' in api
    assert "batchDeleteNotes: async (noteIds: number[]): Promise" in api
    assert "await api.previewBatchDeleteNotes(selectedNoteIds)" in store
    assert "await api.batchDeleteNotes(selectedNoteIds)" in store
    assert "batchDeletePreview" in header
    assert "header.batchDeletePreview" in header
    assert "`dry_run: true`" in reference
    assert "不是 auth" in reference


def test_kwf05_import_dry_run_preview_is_frontend_only_and_collision_aware():
    backup = BACKUP_IMPORT_PATH.read_text(encoding="utf-8")
    i18n = I18N_PATH.read_text(encoding="utf-8")
    todo = TODO_PATH.read_text(encoding="utf-8")

    assert "type BulkImportPreviewStatus = 'create' | 'duplicate' | 'unsupported'" in backup
    assert "buildBulkImportPreview" in backup
    assert 'data-testid="bulk-import-dry-run-preview"' in backup
    assert "data-creates={bulkPreview.createCount}" in backup
    assert "data-duplicates={bulkPreview.duplicateCount}" in backup
    assert "data-unsupported={bulkPreview.unsupportedCount}" in backup
    assert "api." not in backup.split("function buildBulkImportPreview")[1].split("export function BackupImportSection")[0]
    assert i18n.count("bulkImportDryRun:") >= 4
    assert "KWF-05 Import dry-run / collision preview`（狀態：`Done`）" in todo


def test_kwf06_reading_view_source_url_panel_uses_existing_note_urls():
    reading = READING_VIEW_PATH.read_text(encoding="utf-8")
    i18n = I18N_PATH.read_text(encoding="utf-8")

    assert "function sourceUrlDomain(url: string): string" in reading
    assert "const duplicateSourceUrls" in reading
    assert 'data-testid="reading-source-url-panel"' in reading
    assert "localNote.urls" in reading
    assert "reading.sourceUrlsTitle" in reading
    assert "reading.sourceDuplicate" in reading
    assert i18n.count("sourceUrlsTitle:") >= 4
    assert i18n.count("sourceDuplicate:") >= 4


def test_kwf07_quality_metadata_is_documented_decision_gate_not_schema_change():
    todo = TODO_PATH.read_text(encoding="utf-8")
    handoff = HANDOFF_PATH.read_text(encoding="utf-8")
    schema = SCHEMA_PATH.read_text(encoding="utf-8")

    assert "KWF-07 Knowledge quality metadata decision gate`（狀態：`Done`）" in todo
    assert "schema v18 decision gate" in todo
    assert "status / review_state / last_verified_at" in todo
    assert "KWF-07 Knowledge quality metadata decision gate 已完成" in handoff
    assert "Migration v17" in schema
    assert "| v18+ | （預留） | 下一次 Schema 變更接續此版本號 |" in schema
    assert "review_state" not in schema
