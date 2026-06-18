from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
API_PATH = ROOT / "frontend" / "src" / "services" / "api.ts"
BACKUP_IMPORT_PATH = ROOT / "frontend" / "src" / "components" / "settings" / "BackupImportSection.tsx"
I18N_PATH = ROOT / "frontend" / "src" / "i18n" / "index.ts"
CONTRACTS_PATH = ROOT / "docs" / "CONTRACTS.md"
API_REFERENCE_PATH = ROOT / "docs" / "API_REFERENCE.md"
TODO_PATH = ROOT / "docs" / "TODO.md"


def test_markdown_import_wrapper_stays_single_file_endpoint():
    source = API_PATH.read_text(encoding="utf-8")

    assert "importMarkdown: async (file: File): Promise<{ note_id: number }>" in source
    assert 'formData.append("file", file)' in source
    assert 'client.post("/notes/import/md", formData' in source
    assert 'headers: { "Content-Type": "multipart/form-data" }' in source
    assert "/notes/import/batch" not in source
    assert "/notes/import/txt" not in source


def test_settings_bulk_import_uses_markdown_import_and_txt_create_note_paths():
    source = BACKUP_IMPORT_PATH.read_text(encoding="utf-8")

    assert 'accept=".md,.txt"' in source
    assert "multiple" in source
    assert 'data-testid="bulk-import-file-input"' in source
    assert 'data-testid="bulk-import-start"' in source
    assert 'data-testid="bulk-import-clear"' in source
    assert 'data-testid="bulk-import-summary"' in source
    assert 'data-testid="bulk-import-file-row"' in source
    assert 'data-testid="bulk-import-remove-file"' in source
    assert "function bulkFileKey(file: File): string" in source
    assert "setBulkFiles((current) => {" in source
    assert "new Set(current.map(bulkFileKey))" in source
    assert "next.push(file)" in source
    assert "removeBulkFile" in source
    assert "for (const file of bulkFiles)" in source
    assert "if (extension === '.md')" in source
    assert "await api.importMarkdown(file)" in source
    assert "else if (extension === '.txt')" in source
    assert "const content = await file.text()" in source
    assert "await api.createNote({" in source
    assert "title: fileStem(file.name)" in source
    assert "content," in source
    assert "status: 'skipped'" in source
    assert "} catch (error) {" in source
    assert "message: errorMessage(error)" in source
    assert "data-created={bulkCreatedCount}" in source
    assert "data-skipped={bulkSkippedCount}" in source
    assert "data-failed={bulkFailedCount}" in source
    assert "await Promise.all([fetchNotes(true), fetchCategories(), fetchTags()])" in source
    assert "setBulkFiles([])" in source


def test_bulk_import_i18n_and_docs_lock_no_batch_api_contract():
    i18n = I18N_PATH.read_text(encoding="utf-8")
    contracts = CONTRACTS_PATH.read_text(encoding="utf-8")
    api_reference = API_REFERENCE_PATH.read_text(encoding="utf-8")
    todo = TODO_PATH.read_text(encoding="utf-8")

    for key in [
        "bulkImportTitle",
        "bulkImportDescription",
        "bulkImportChooseFiles",
        "bulkImportClear",
        "bulkImportRemoveFile",
        "bulkImportSummary",
        "bulkImportCompleteToast",
    ]:
        assert i18n.count(f"{key}:") == 4

    assert "CONTRACT-BULK-MARKDOWN-TXT-IMPORT" in contracts
    assert "不新增 server-side batch API" in contracts
    assert "`.txt` 只可由前端讀檔後走既有 `POST /api/notes`" in contracts
    assert "允許多次選擇不同資料夾的檔案" in contracts
    assert "匯入後清空待匯入清單但保留結果摘要" in contracts

    assert "Settings 的批次 Markdown/TXT 匯入是前端逐檔 wrapper" in api_reference
    assert "沒有 server-side batch import API" in api_reference
    assert "`.txt` 檔不走 `/api/notes/import/md`" in api_reference
    assert "使用者可多次從不同資料夾選檔後一次匯入" in api_reference

    assert "[x] **01A Import path lock**" in todo
    assert "[x] **01B Settings import UI**" in todo
    assert "[x] **01C Contract/docs cleanup**" in todo
    assert "[x] **01D Regression and smoke**" in todo
    assert "跨批選檔累加" in todo
