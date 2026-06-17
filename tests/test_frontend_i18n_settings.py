from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
I18N_PATH = ROOT / "frontend" / "src" / "i18n" / "index.ts"
STORE_PATH = ROOT / "frontend" / "src" / "stores" / "appStore.ts"
HOOK_PATH = ROOT / "frontend" / "src" / "hooks" / "useTranslation.ts"
APPEARANCE_PATH = ROOT / "frontend" / "src" / "components" / "settings" / "AppearanceSection.tsx"
SETTINGS_PATH = ROOT / "frontend" / "src" / "pages" / "SettingsPage.tsx"
HEADER_PATH = ROOT / "frontend" / "src" / "components" / "Header.tsx"
SIDEBAR_PATH = ROOT / "frontend" / "src" / "components" / "Sidebar.tsx"
FILTER_STRIP_PATH = ROOT / "frontend" / "src" / "components" / "FilterStrip.tsx"
HOME_PATH = ROOT / "frontend" / "src" / "pages" / "HomePage.tsx"
NOTE_CARD_PATH = ROOT / "frontend" / "src" / "components" / "NoteCard.tsx"
LAYOUT_PATH = ROOT / "frontend" / "src" / "components" / "Layout.tsx"
READING_VIEW_PATH = ROOT / "frontend" / "src" / "components" / "ReadingView.tsx"
NOTE_EDITOR_PATH = ROOT / "frontend" / "src" / "components" / "NoteEditor.tsx"
EDITOR_DIR = ROOT / "frontend" / "src" / "components" / "editor"
EDITOR_HOOKS_DIR = ROOT / "frontend" / "src" / "hooks" / "editor"
PROMPT_BUILDER_PATH = ROOT / "frontend" / "src" / "pages" / "PromptBuilder.tsx"
PROMPT_BUILDER_HOOK_PATH = ROOT / "frontend" / "src" / "hooks" / "usePromptBuilder.ts"
PROMPT_BUILDER_DIR = ROOT / "frontend" / "src" / "components" / "prompt-builder"
BACKUP_IMPORT_PATH = ROOT / "frontend" / "src" / "components" / "settings" / "BackupImportSection.tsx"
SERVER_DASHBOARD_PATH = ROOT / "frontend" / "src" / "components" / "settings" / "ServerDashboardSection.tsx"
SYSTEM_MAINTENANCE_PATH = ROOT / "frontend" / "src" / "components" / "SystemMaintenance.tsx"
SYSTEM_STATS_PATH = ROOT / "frontend" / "src" / "components" / "settings" / "SystemStatsSection.tsx"
DATA_MANAGER_PATH = ROOT / "frontend" / "src" / "components" / "DataManager.tsx"
API_SERVICE_PATH = ROOT / "frontend" / "src" / "services" / "api.ts"
COMMAND_PALETTE_PATH = ROOT / "frontend" / "src" / "components" / "CommandPalette.tsx"
SECURITY_SECTION_PATH = ROOT / "frontend" / "src" / "components" / "settings" / "SecuritySection.tsx"
DANGER_ZONE_PATH = ROOT / "frontend" / "src" / "components" / "settings" / "DangerZoneSection.tsx"
CONFIRM_DIALOG_PATH = ROOT / "frontend" / "src" / "components" / "ui" / "ConfirmDialog.tsx"
TOAST_PATH = ROOT / "frontend" / "src" / "components" / "ui" / "Toast.tsx"
MODAL_PATH = ROOT / "frontend" / "src" / "components" / "ui" / "Modal.tsx"
TODO_PATH = ROOT / "docs" / "TODO.md"
HANDOFF_PATH = ROOT / "HANDOFF.md"
DESKTOP_I18N_ARCHIVE_PATH = (
    ROOT
    / "docs"
    / "development-history"
    / "desktop-backup-i18n-handoff-20260617.md"
)


def test_i18n_exposes_four_locales_and_pure_translate_api():
    i18n = I18N_PATH.read_text(encoding="utf-8")

    assert "export type Locale = 'zh-TW' | 'en' | 'ja' | 'ko'" in i18n
    assert "type TranslationNamespace = Extract<keyof typeof zhTW, string>" in i18n
    assert "export type TranslationKey = TranslationNamespace | `${TranslationNamespace}.${string}`" in i18n
    assert "export type TranslationParams = Record<string, string | number>" in i18n
    for locale in ["'zh-TW'", "'en'", "'ja'", "'ko'"]:
        assert f"code: {locale}" in i18n
    assert "export function translate(" in i18n
    assert "export function t(" in i18n
    assert "readTranslation(translations['zh-TW'], key)" in i18n
    assert "params[name]?.toString() ?? ''" in i18n
    assert "settings.appearance.language.changed" not in i18n
    assert "language: {" in i18n


def test_locale_is_reactive_zustand_state_for_component_rerender():
    store = STORE_PATH.read_text(encoding="utf-8")
    hook = HOOK_PATH.read_text(encoding="utf-8")

    assert "locale: Locale" in store
    assert "locale: readStoredLocale()" in store
    assert "setLocale: (locale: Locale) => void" in store
    assert "persistLocale(locale)" in store
    assert "set({ locale })" in store
    assert "useAppStore((state) => state.locale)" in hook
    assert "useCallback(" in hook
    assert "translate(locale, key, params)" in hook
    assert "type TranslateFunction" in hook
    assert "TranslationKey" in hook


def test_settings_appearance_renders_language_switcher_and_translated_tabs():
    appearance = APPEARANCE_PATH.read_text(encoding="utf-8")
    settings = SETTINGS_PATH.read_text(encoding="utf-8")

    assert "data-testid=\"language-select\"" in appearance
    assert "availableLocales.map" in appearance
    assert "setLocale(nextLocale)" in appearance
    assert "t('settings.appearance.language.title')" in appearance
    assert "labelKey: 'settings.tabs.appearance'" in settings
    assert "{t(tab.labelKey)}" in settings
    assert "label: '外觀'" in settings


def test_home_shell_namespace_is_translated_for_four_locales():
    i18n = I18N_PATH.read_text(encoding="utf-8")

    for namespace in ["shell", "sidebar", "filter", "header", "home", "noteCard"]:
        assert i18n.count(f"{namespace}: {{") >= 4
    for phrase in ["Navigation", "ナビゲーション", "탐색"]:
        assert phrase in i18n
    for phrase in ["Search results", "検索結果", "검색 결과"]:
        assert phrase in i18n
    for phrase in ["Untitled", "無題", "제목 없음"]:
        assert phrase in i18n


def test_home_shell_components_use_i18n_for_extracted_strings():
    files = {
        "Header.tsx": HEADER_PATH.read_text(encoding="utf-8"),
        "Sidebar.tsx": SIDEBAR_PATH.read_text(encoding="utf-8"),
        "FilterStrip.tsx": FILTER_STRIP_PATH.read_text(encoding="utf-8"),
        "HomePage.tsx": HOME_PATH.read_text(encoding="utf-8"),
        "NoteCard.tsx": NOTE_CARD_PATH.read_text(encoding="utf-8"),
        "Layout.tsx": LAYOUT_PATH.read_text(encoding="utf-8"),
    }

    for source in files.values():
        assert "useTranslation" in source
    assert "t('header.searchPlaceholder')" in files["Header.tsx"]
    assert "t('sidebar.showAllTags'" in files["Sidebar.tsx"]
    assert "t('filter.archive')" in files["FilterStrip.tsx"]
    assert "t('home.emptySearchDescription'" in files["HomePage.tsx"]
    assert "t('noteCard.untitled')" in files["NoteCard.tsx"]
    assert "t('shell.notesCount'" in files["Layout.tsx"]

    extracted_literals = [
        "搜尋筆記... (按 Enter)",
        "找不到符合的筆記",
        "還沒有任何筆記",
        "更多操作",
        "內容已複製",
        "本地連線",
    ]
    for name, source in files.items():
        for literal in extracted_literals:
            assert literal not in source, f"{literal} should stay in i18n, not {name}"


def test_editor_reading_namespace_is_translated_for_four_locales():
    i18n = I18N_PATH.read_text(encoding="utf-8")

    for namespace in ["reading", "editor"]:
        assert i18n.count(f"{namespace}: {{") >= 4
    for phrase in ["Edit note", "ノートを編集", "노트 편집"]:
        assert phrase in i18n
    for phrase in ["Close reading panel", "読書パネルを閉じる", "읽기 패널 닫기"]:
        assert phrase in i18n
    for phrase in ["Image management", "画像管理", "이미지 관리"]:
        assert phrase in i18n


def test_editor_reading_components_use_i18n_for_extracted_strings():
    files = {
        "ReadingView.tsx": READING_VIEW_PATH.read_text(encoding="utf-8"),
        "NoteEditor.tsx": NOTE_EDITOR_PATH.read_text(encoding="utf-8"),
    }
    for path in EDITOR_DIR.glob("*.tsx"):
      files[path.name] = path.read_text(encoding="utf-8")
    for path in EDITOR_HOOKS_DIR.glob("*.ts"):
      files[path.name] = path.read_text(encoding="utf-8")

    assert "t('reading.closePanel')" in files["ReadingView.tsx"]
    assert "t('editor.noteEditor.contentPlaceholder')" in files["NoteEditor.tsx"]
    assert "t('editor.toolbar.editNote')" in files["EditorToolbar.tsx"]
    assert "t('editor.sidebar.chooseCategory')" in files["EditorSidebar.tsx"]
    assert "t('editor.attachment.uploadMd')" in files["AttachmentPanel.tsx"]
    assert "t('editor.imagePanel.deleteMessage'" in files["ImageManagementPanel.tsx"]
    assert "t('editor.form.unsavedTitle')" in files["useNoteForm.ts"]
    assert "t('editor.attachmentsToast.uploading'" in files["useNoteAttachments.ts"]
    assert "t('editor.uploadToast.imageUploading')" in files["useDragDrop.ts"]

    extracted_literals = [
        "編輯筆記",
        "開始輸入內容",
        "歷史版本",
        "圖片管理",
        "刪除附件",
        "上傳圖片中",
        "讀取筆記內容失敗",
        "關閉閱讀面板",
    ]
    for name, source in files.items():
        for literal in extracted_literals:
            assert literal not in source, f"{literal} should stay in i18n, not {name}"


def test_prompt_builder_namespace_is_translated_for_four_locales():
    i18n = I18N_PATH.read_text(encoding="utf-8")

    assert i18n.count("promptBuilder: {") >= 4
    for phrase in ["Structured prompt composer", "構造化プロンプト作成ツール", "구조화 프롬프트 작성 도구"]:
        assert phrase in i18n
    for phrase in ["Output preview", "出力プレビュー", "출력 미리보기"]:
        assert phrase in i18n
    for phrase in ["Inspiration Guide Wizard", "インスピレーションガイド Wizard", "영감 가이드 Wizard"]:
        assert phrase in i18n


def test_prompt_builder_components_use_i18n_for_extracted_strings():
    files = {
        "PromptBuilder.tsx": PROMPT_BUILDER_PATH.read_text(encoding="utf-8"),
        "usePromptBuilder.ts": PROMPT_BUILDER_HOOK_PATH.read_text(encoding="utf-8"),
    }
    for path in PROMPT_BUILDER_DIR.glob("*.tsx"):
        files[path.name] = path.read_text(encoding="utf-8")

    assert "t('promptBuilder.actions.saveToLibrary')" in files["PromptBuilder.tsx"]
    assert "t('promptBuilder.camera.title')" in files["PromptBuilder.tsx"]
    assert "t('promptBuilder.output.title')" in files["OutputPreview.tsx"]
    assert "t('promptBuilder.selectPlaceholder')" in files["ParameterSelect.tsx"]
    assert "t('promptBuilder.quickTemplates')" in files["QuickTemplates.tsx"]
    assert "t('promptBuilder.wizard.subject')" in files["WizardModal.tsx"]
    assert 't("promptBuilder.alerts.llmCopied")' in files["usePromptBuilder.ts"]
    assert 't("promptBuilder.llmPrompt"' in files["usePromptBuilder.ts"]

    extracted_literals = [
        "儲存至筆記庫",
        "結構化提示詞組裝器",
        "權重模式",
        "主要描述",
        "鏡頭設定",
        "風格設定",
        "輸出預覽",
        "尚無輸出",
        "快速模板",
        "靈感引導 Wizard",
        "確認並填入",
        "已複製 LLM 優化指令",
    ]
    allowed_data_literals = ["提示詞 | Prompt", 'cat.name.includes("提示")']
    for name, source in files.items():
        source_without_data_literals = source
        for literal in allowed_data_literals:
            source_without_data_literals = source_without_data_literals.replace(literal, "")
        for literal in extracted_literals:
            assert literal not in source_without_data_literals, f"{literal} should stay in i18n, not {name}"


def test_settings_deep_namespace_is_translated_for_four_locales():
    i18n = I18N_PATH.read_text(encoding="utf-8")

    for namespace in ["backup", "serverDashboard", "systemStats"]:
        assert i18n.count(f"{namespace}: {{") >= 4
    assert i18n.count("maintenance: {") >= 4
    for phrase in ["Restore database", "データベースを復元", "데이터베이스 복원"]:
        assert phrase in i18n
    for phrase in ["Server dashboard", "サーバーダッシュボード", "서버 대시보드"]:
        assert phrase in i18n
    for phrase in ["Data consistency check", "データ整合性チェック", "데이터 일관성 점검"]:
        assert phrase in i18n


def test_settings_deep_components_use_i18n_for_extracted_strings():
    files = {
        "BackupImportSection.tsx": BACKUP_IMPORT_PATH.read_text(encoding="utf-8"),
        "ServerDashboardSection.tsx": SERVER_DASHBOARD_PATH.read_text(encoding="utf-8"),
        "SystemMaintenance.tsx": SYSTEM_MAINTENANCE_PATH.read_text(encoding="utf-8"),
        "SystemStatsSection.tsx": SYSTEM_STATS_PATH.read_text(encoding="utf-8"),
    }

    for source in files.values():
        assert "useTranslation" in source
    assert "t('settings.backup.exportTitle')" in files["BackupImportSection.tsx"]
    assert "t('settings.backup.confirmRestoreTitle')" in files["BackupImportSection.tsx"]
    assert "t('settings.serverDashboard.title')" in files["ServerDashboardSection.tsx"]
    assert "t('settings.serverDashboard.deleteRestorePointMessage'" in files["ServerDashboardSection.tsx"]
    assert "t('settings.maintenance.consistencyDescription')" in files["SystemMaintenance.tsx"]
    assert "t('settings.systemStats.title')" in files["SystemStatsSection.tsx"]

    extracted_literals = [
        "匯出副本",
        "還原資料庫",
        "確認還原資料庫",
        "伺服器儀表板",
        "Prism 內建還原點",
        "資料庫副本下載失敗",
        "資料健康檢查與進階維護工具",
        "資料一致性檢查",
        "資料庫統計",
    ]
    allowed_dynamic_literals = ["Prism", "WAL", "SQLite", "Systemd", "localhost", "trusted internal access"]
    for name, source in files.items():
        source_without_allowed = source
        for literal in allowed_dynamic_literals:
            source_without_allowed = source_without_allowed.replace(literal, "")
        for literal in extracted_literals:
            assert literal not in source_without_allowed, f"{literal} should stay in i18n, not {name}"


def test_settings_organization_namespace_is_translated_for_four_locales():
    i18n = I18N_PATH.read_text(encoding="utf-8")

    assert i18n.count("organization: {") >= 4
    for phrase in ["Category management", "カテゴリ管理", "분류 관리"]:
        assert phrase in i18n
    for phrase in ["Tag management", "タグ管理", "태그 관리"]:
        assert phrase in i18n
    for phrase in ["Choose target tag", "統合先タグを選択", "대상 태그 선택"]:
        assert phrase in i18n


def test_data_manager_uses_i18n_for_extracted_strings():
    source = DATA_MANAGER_PATH.read_text(encoding="utf-8")

    assert "useTranslation" in source
    assert "t('settings.organization.categoryManagement')" in source
    assert "t('settings.organization.deleteCategoryMessage'" in source
    assert "t('settings.organization.tagManagement'" in source
    assert "t('settings.organization.mergeAction'" in source
    assert "t('settings.organization.noTags')" in source

    extracted_literals = [
        "分類管理",
        "分類名稱",
        "請輸入分類名稱",
        "刪除分類",
        "標籤管理",
        "請輸入標籤名稱",
        "刪除標籤",
        "選擇目標標籤",
        "尚無標籤",
        "重新命名",
    ]
    for literal in extracted_literals:
        assert literal not in source, f"{literal} should stay in i18n, not DataManager.tsx"


def test_api_error_adapter_namespace_is_translated_for_four_locales():
    i18n = I18N_PATH.read_text(encoding="utf-8")

    assert i18n.count("apiErrors: {") >= 4
    for phrase in [
        "Could not connect to the server",
        "サーバーに接続できません",
        "서버에 연결할 수 없습니다",
    ]:
        assert phrase in i18n
    for phrase in ["Server error ({status})", "サーバーエラー ({status})", "서버 오류 ({status})"]:
        assert phrase in i18n


def test_api_service_global_error_toasts_use_i18n_fallbacks():
    source = API_SERVICE_PATH.read_text(encoding="utf-8")

    assert 'import { t } from "../i18n";' in source
    assert 't("apiErrors.networkUnavailable")' in source
    assert 't("apiErrors.serverError", { status })' in source
    assert "data?.message || data?.error" in source

    extracted_literals = [
        "無法連線到伺服器",
        "請檢查網路或服務狀態",
        "伺服器錯誤",
    ]
    for literal in extracted_literals:
        assert literal not in source, f"{literal} should stay in i18n, not api.ts"


def test_i18n_remaining_hardcoded_ui_audit_triages_active_hidden_and_allowed_literals():
    todo = DESKTOP_I18N_ARCHIVE_PATH.read_text(encoding="utf-8")
    handoff = HANDOFF_PATH.read_text(encoding="utf-8")
    settings = SETTINGS_PATH.read_text(encoding="utf-8")

    assert "desktop-backup-i18n-handoff-20260617.md" in handoff
    assert "remaining hardcoded UI string audit / hidden legacy settings triage" in todo
    assert "CommandPalette" in todo
    assert "SecuritySection" in todo or "Security" in todo
    assert "DangerZoneSection" in todo or "DangerZone" in todo
    assert "ConfirmDialog" in todo or "shared UI fallback" in todo
    assert "PortConfigSection" in todo
    assert "UpdateSection" in todo
    assert "TagInput" in todo
    assert "Allowed non-UI/data literals" in todo
    assert "階段 5 收尾" in todo or "進階段 5 收尾" in todo

    assert "PortConfigSection" in settings
    assert "UpdateSection" in settings
    assert "<PortConfigSection" not in settings
    assert "<UpdateSection" not in settings


def test_active_ui_final_i18n_namespaces_are_translated_for_four_locales():
    i18n = I18N_PATH.read_text(encoding="utf-8")

    for namespace in ["ui", "commandPalette"]:
        assert i18n.count(f"{namespace}: {{") >= 4
    assert i18n.count("security: {") >= 4
    assert i18n.count("dangerZone: {") >= 4

    for phrase in ["Recent notes", "最近のノート", "최근 노트"]:
        assert phrase in i18n
    for phrase in ["CSRF protection", "CSRF 保護", "CSRF 보호"]:
        assert phrase in i18n
    for phrase in ["Danger zone", "危険ゾーン", "위험 영역"]:
        assert phrase in i18n
    for phrase in ["Close notification", "通知を閉じる", "알림 닫기"]:
        assert phrase in i18n


def test_active_ui_final_components_use_i18n_for_extracted_strings():
    files = {
        "CommandPalette.tsx": COMMAND_PALETTE_PATH.read_text(encoding="utf-8"),
        "SecuritySection.tsx": SECURITY_SECTION_PATH.read_text(encoding="utf-8"),
        "DangerZoneSection.tsx": DANGER_ZONE_PATH.read_text(encoding="utf-8"),
        "ConfirmDialog.tsx": CONFIRM_DIALOG_PATH.read_text(encoding="utf-8"),
        "Toast.tsx": TOAST_PATH.read_text(encoding="utf-8"),
        "Modal.tsx": MODAL_PATH.read_text(encoding="utf-8"),
    }

    assert "useTranslation" in files["CommandPalette.tsx"]
    assert "t('commandPalette.placeholder')" in files["CommandPalette.tsx"]
    assert "commandPalette.groups.${group}" in files["CommandPalette.tsx"]
    assert "useTranslation" in files["SecuritySection.tsx"]
    assert "t('settings.security.title')" in files["SecuritySection.tsx"]
    assert "useTranslation" in files["DangerZoneSection.tsx"]
    assert "t('settings.dangerZone.title')" in files["DangerZoneSection.tsx"]
    assert "t('settings.dangerZone.deleteOrphanMessage'" in files["DangerZoneSection.tsx"]
    assert "t('ui.confirm.cancel')" in files["ConfirmDialog.tsx"]
    assert "translate('ui.toast.region')" in files["Toast.tsx"]
    assert "t('ui.modal.close')" in files["Modal.tsx"]

    extracted_literals = [
        "導覽",
        "最近筆記",
        "動作",
        "未知時間",
        "沒有內容預覽",
        "搜尋命令、最近筆記、設定",
        "找不到符合的命令",
        "CSRF 防護已開啟",
        "驗證 Origin",
        "危險區域",
        "清理未使用的圖片",
        "掃描中",
        "全部刪除",
        "修復失效圖片路徑",
        "取消",
        "確定",
        "通知",
        "關閉通知",
    ]
    allowed_literals = ["Prompt Builder", "CSRF", "Origin", "Referer", "POST", "PUT", "DELETE"]
    for name, source in files.items():
        source_without_allowed = source
        for literal in allowed_literals:
            source_without_allowed = source_without_allowed.replace(literal, "")
        for literal in extracted_literals:
            assert literal not in source_without_allowed, f"{literal} should stay in i18n, not {name}"


def test_todo_records_i18n_scope_and_frontend_only_boundary():
    todo = DESKTOP_I18N_ARCHIVE_PATH.read_text(encoding="utf-8")

    assert "i18n（多語系）還原" in todo
    assert "中(zh-TW)/英(en)/日(ja)/韓(ko) 四語" in todo
    assert "設定 > 外觀" in todo
    assert "純前端、不動後端/schema" in todo
    assert "Home shell / Header / Sidebar / FilterStrip / HomePage / NoteCard" in todo
    assert "ReadingView / NoteEditor / editor 子元件與 hooks" in todo
    assert "Prompt Builder" in todo
    assert "Settings 維護深層 section / server dashboard / backup-restore" in todo
    assert "Settings 組織管理（DataManager）" in todo
    assert "global API/toast error adapter" in todo
    assert "remaining hardcoded UI string audit / hidden legacy settings triage" in todo
    assert "階段 5 — 收尾" in todo
    assert "缺漏 key 先回 zh-TW fallback" in todo
    assert "TranslationKey" in todo
    assert "{count} 參數替換" in todo
