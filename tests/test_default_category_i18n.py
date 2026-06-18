from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CATEGORY_DISPLAY = ROOT / "frontend" / "src" / "utils" / "categoryDisplay.ts"
I18N = ROOT / "frontend" / "src" / "i18n" / "index.ts"
DATA_MANAGER = ROOT / "frontend" / "src" / "components" / "DataManager.tsx"
SIDEBAR = ROOT / "frontend" / "src" / "components" / "Sidebar.tsx"
FILTER_STRIP = ROOT / "frontend" / "src" / "components" / "FilterStrip.tsx"
EDITOR_SIDEBAR = ROOT / "frontend" / "src" / "components" / "editor" / "EditorSidebar.tsx"
APPEARANCE = ROOT / "frontend" / "src" / "components" / "settings" / "AppearanceSection.tsx"


def test_default_category_i18n_mapping_is_exact_seed_only():
    source = CATEGORY_DISPLAY.read_text(encoding="utf-8")

    for seed, key in {
        "提示詞 | Prompt": "categoryDefaults.prompt",
        "筆記 | Note": "categoryDefaults.note",
        "教學 | Tutorial": "categoryDefaults.tutorial",
        "資料 | Data": "categoryDefaults.data",
        "靈感 | Inspiration": "categoryDefaults.inspiration",
    }.items():
        assert f"'{seed}': '{key}'" in source

    assert "美食 | Gourmet" not in source
    assert "defaultCategoryLabelKeys[name.trim()] ?? null" in source
    assert "getCategoryEditName" in source
    assert "getCategoryUpdateName" in source
    assert "trimmedName === currentDisplayName" in source


def test_default_category_labels_are_available_in_all_locales():
    source = I18N.read_text(encoding="utf-8")

    for expected in [
        "prompt: '提示詞'",
        "prompt: 'Prompt'",
        "prompt: 'プロンプト'",
        "prompt: '프롬프트'",
        "inspiration: '靈感'",
        "inspiration: 'Inspiration'",
        "inspiration: 'インスピレーション'",
        "inspiration: '영감'",
    ]:
        assert expected in source


def test_default_category_display_helper_is_used_by_visible_category_surfaces():
    files = [
        DATA_MANAGER,
        SIDEBAR,
        FILTER_STRIP,
        EDITOR_SIDEBAR,
        APPEARANCE,
    ]

    for path in files:
        source = path.read_text(encoding="utf-8")
        assert "categoryDisplay" in source

    data_manager = DATA_MANAGER.read_text(encoding="utf-8")
    assert "setEditName(getCategoryEditName(cat.name, t))" in data_manager
    assert "getCategoryDisplayName(cat.name, t)" in data_manager
    assert "getCategoryUpdateName(cat.name, editName, t)" in data_manager
    assert "if (nextName !== undefined)" in data_manager
    assert "updates.name = nextName" in data_manager
