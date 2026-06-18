from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAIN_GO = ROOT / "go-shadow" / "main.go"
WINDOWS_SHELL = ROOT / "go-shadow" / "desktop_shell_windows.go"
WINDOWS_TEST = ROOT / "go-shadow" / "desktop_shell_windows_test.go"
BUILD_DESKTOP = ROOT / "scripts" / "build_desktop_shell.ps1"
BUILD_PORTABLE = ROOT / "scripts" / "build_desktop_portable.ps1"
ICON_SCRIPT = ROOT / "scripts" / "generate_prism_icon.ps1"
RESOURCE_SCRIPT = ROOT / "scripts" / "generate_windows_resource.ps1"
FRONTEND_MAIN = ROOT / "frontend" / "src" / "main.tsx"
APPEARANCE = ROOT / "frontend" / "src" / "components" / "settings" / "AppearanceSection.tsx"
NOTE_CARD = ROOT / "frontend" / "src" / "components" / "NoteCard.tsx"
HOME_PAGE = ROOT / "frontend" / "src" / "pages" / "HomePage.tsx"
SERVER_DASHBOARD = ROOT / "frontend" / "src" / "components" / "settings" / "ServerDashboardSection.tsx"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_desktop_default_data_dir_is_exe_neighbor_prismdata_without_picker_or_shortcut():
	main_go = _read(MAIN_GO)
	windows_shell = _read(WINDOWS_SHELL)

	assert "defaultDataDir, err := resolveDesktopDataDir" in main_go
	assert "restartAfterSelection" not in main_go
	assert 'filepath.Join(exeDir, "PrismData")' in windows_shell
	for forbidden in [
		"runDesktopDataDirPicker",
		"CreateShortcut",
		"WScript.Shell",
		"ExecutionPolicy",
		"PrismPortable.json",
		"%LOCALAPPDATA%",
		"selectDataDir",
		"建立桌面捷徑",
		"refreshExistingDesktopShortcutIcon",
	]:
		assert forbidden not in windows_shell
	assert "refreshExistingDesktopShortcutIcon" not in main_go


def test_desktop_shortcut_and_custom_data_dir_are_installer_deferred():
	windows_shell = _read(WINDOWS_SHELL)

	for forbidden in [
		"CreateShortcut bool",
		"createDesktopShortcut()",
		"RefreshShortcutIcon failed",
		"SpecialFolders.Item('Desktop')",
		"Prism.lnk",
		'id="shortcut" type="checkbox" checked',
		"window.selectDataDir",
	]:
		assert forbidden not in windows_shell


def test_desktop_first_run_and_navigation_do_not_leave_blank_webviews():
	windows_shell = _read(WINDOWS_SHELL)

	assert "pickerDestroyed := false" not in windows_shell
	assert "desktopStartupHTML()" in windows_shell
	assert "正在啟動..." in windows_shell
	assert "w.SetHtml(desktopStartupHTML())\n\t\tw.Navigate(opts.targetURL)" in windows_shell


def test_desktop_no_longer_has_first_run_locale_picker():
	windows_shell = _read(WINDOWS_SHELL)
	windows_test = _read(WINDOWS_TEST)

	assert "GetUserDefaultLocaleName" not in windows_shell
	assert "desktopPickerLanguageFromLocale" not in windows_shell
	assert 'locale == "zh-tw"' not in windows_shell
	assert "TestDesktopDataDirPickerHTMLUsesLocalizedLabels" not in windows_test


def test_desktop_package_carries_prompt_builder_seed_config():
    main_go = _read(MAIN_GO)
    desktop_script = _read(BUILD_DESKTOP)
    portable_script = _read(BUILD_PORTABLE)

    assert 'filepath.Join(exeDir, "static", "config", filename)' in main_go
    assert 'filepath.Join(exeDir, "config", filename)' in main_go
    for script in [desktop_script, portable_script]:
        assert "Sync-EmbeddedFrontend" in script
        assert "npm run build" in script
        assert "web/dist" in script
        assert 'static\\config' in script
        assert "prompt_options.json" in script
        assert "wizard_options.json" in script
        assert "Static config source not found" in script


def test_desktop_icon_is_generated_and_loaded_from_package_file():
    icon_script = _read(ICON_SCRIPT)
    resource_script = _read(RESOURCE_SCRIPT)
    windows_shell = _read(WINDOWS_SHELL)
    desktop_script = _read(BUILD_DESKTOP)
    portable_script = _read(BUILD_PORTABLE)

    assert 'DrawString("P"' in icon_script
    assert "System.Drawing.Bitmap" in icon_script
    assert "github.com/akavel/rsrc@v0.10.2" in resource_script
    assert "-ico" in resource_script
    assert "Prism.ico" in windows_shell
    assert "desktopLoadShellIcon" in windows_shell
    assert "desktopLoadImage.Call" in windows_shell
    assert "desktopLRLoadFromFile|desktopLRDefaultSize" in windows_shell
    assert "desktopDestroyIcon.Call" in windows_shell
    for script in [desktop_script, portable_script]:
        assert "generate_prism_icon.ps1" in script
        assert "generate_windows_resource.ps1" in script
        assert "prism_windows_amd64.syso" in script
        assert "Prism.ico" in script
        assert "Windows resource generation failed" in script


def test_new_user_frontend_defaults_are_light_warm_elegant_preview_autoload():
    frontend_main = _read(FRONTEND_MAIN)
    appearance = _read(APPEARANCE)
    note_card = _read(NOTE_CARD)
    home = _read(HOME_PAGE)

    assert "savedAccentColor || 'elegant'" in frontend_main
    assert ": 'warm'" in frontend_main
    assert "localStorage.getItem('theme') || 'light'" in frontend_main
    assert "|| 'light'" in appearance
    assert "? savedAccent : 'elegant'" in appearance
    assert "? savedScheme : 'warm'" in appearance
    assert "type CardOpenMode = 'preview' | 'edit'" in appearance
    assert "readCardOpenMode" in appearance
    assert '<option value="reading">' not in appearance
    assert "localStorage.getItem('autoLoadMore') !== 'false'" in appearance
    assert "localStorage.getItem('autoLoadMore') !== 'false'" in home
    assert "localStorage.getItem('cardOpenMode') === 'edit' ? 'edit' : 'preview'" in note_card
    assert "await openEditorWithDetail(true)" in note_card
    assert "openEditor(fullNote, preview ? { preview: true } : undefined)" in note_card
    card_click_handler = note_card.split("const handleClick = async () => {", 1)[1].split("const handleContextMenu", 1)[0]
    assert "openReading" not in card_click_handler
    assert "openReading(note)" in note_card


def test_windows_dashboard_hides_cpu_temperature_even_if_value_exists():
    dashboard = _read(SERVER_DASHBOARD)

    assert "const hasCpuTemperature = hardware?.cpu_temp != null" in dashboard
    assert "const platformSystem = getPlatformSystem(hardware?.platform)" in dashboard
    assert "const normalizedPlatformSystem = platformSystem.toLowerCase()" in dashboard
    assert "normalizedPlatformSystem === 'windows' || normalizedPlatformSystem.startsWith('windows/')" in dashboard
    assert "const showCpuTemperature = hasCpuTemperature && !isWindowsPlatform" in dashboard
    assert "showCpuTemperature ? (" in dashboard
    assert 'data-testid="data-location-card"' in dashboard
    assert "settings.serverDashboard.dataLocation" in dashboard
    assert "hardware?.data_dir || '-'" in dashboard
    assert "showCpuTemperature ? t('settings.serverDashboard.systemInfo') : t('settings.serverDashboard.databaseStatus')" in dashboard
