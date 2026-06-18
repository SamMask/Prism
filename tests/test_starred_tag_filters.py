from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HOOK_PATH = ROOT / "frontend" / "src" / "hooks" / "useStarredTags.ts"
FILTER_STRIP_PATH = ROOT / "frontend" / "src" / "components" / "FilterStrip.tsx"
DATA_MANAGER_PATH = ROOT / "frontend" / "src" / "components" / "DataManager.tsx"
I18N_PATH = ROOT / "frontend" / "src" / "i18n" / "index.ts"
CONTRACTS_PATH = ROOT / "docs" / "CONTRACTS.md"
TODO_PATH = ROOT / "docs" / "TODO.md"


def test_starred_tags_storage_contract_is_frontend_only_and_versioned():
    source = HOOK_PATH.read_text(encoding="utf-8")

    assert "STARRED_TAG_IDS_STORAGE_KEY = 'prism.starredTags.v1'" in source
    assert "STARRED_TAGS_CHANGED_EVENT = 'prism:starred-tags-changed'" in source
    assert "window.localStorage.getItem(STARRED_TAG_IDS_STORAGE_KEY)" in source
    assert "window.localStorage.setItem(STARRED_TAG_IDS_STORAGE_KEY, JSON.stringify(normalized))" in source
    assert "window.dispatchEvent(new CustomEvent(STARRED_TAGS_CHANGED_EVENT))" in source
    assert "window.addEventListener('storage', sync)" in source
    assert "new Set(storedTagIds.filter((id) => availableTagIds.has(id)))" in source
    assert "api." not in source


def test_filter_strip_shows_only_starred_tags_or_empty_hint():
    source = FILTER_STRIP_PATH.read_text(encoding="utf-8")

    assert "useStarredTags(tags)" in source
    assert "tags.filter((tag) => starredTagIdSet.has(tag.id))" in source
    assert "data-testid={`filter-tag-${tag.id}`}" in source
    assert 'data-starred-tag="true"' in source
    assert 'data-testid="filter-starred-tags-empty-hint"' in source
    assert "t('filter.starredTagsHint')" in source
    assert "tags.slice(0, 12)" not in source
    assert "+{tags.length - displayTags.length}" not in source


def test_settings_tag_star_control_does_not_trigger_merge_selection():
    source = DATA_MANAGER_PATH.read_text(encoding="utf-8")

    assert "Star" in source
    assert "useStarredTags(tags)" in source
    assert "starredTagIdSet.has(tag.id)" in source
    assert "toggleStarredTag(tag.id)" in source
    assert "onMouseDown={(event) => event.stopPropagation()}" in source
    assert "onClick={(event) => { event.stopPropagation(); toggleStarredTag(tag.id) }}" in source
    assert "data-testid={`settings-star-tag-${tag.id}`}" in source
    assert "settings.organization.starTagShortcut" in source
    assert "settings.organization.unstarTagShortcut" in source


def test_starred_tag_i18n_and_docs_contract_are_recorded():
    i18n = I18N_PATH.read_text(encoding="utf-8")
    contracts = CONTRACTS_PATH.read_text(encoding="utf-8")
    todo = TODO_PATH.read_text(encoding="utf-8")

    assert i18n.count("starredTagsHint:") >= 4
    assert i18n.count("starTagShortcut:") >= 4
    assert i18n.count("unstarTagShortcut:") >= 4

    assert "CONTRACT-STARRED-TAG-FILTERS" in contracts
    assert "`prism.starredTags.v1`" in contracts
    assert "不新增 DB 欄位、不改 tags API、不做跨裝置同步" in contracts

    assert "[x] **01A Frontend state contract**" in todo
    assert "[x] **01B Settings tag star control**" in todo
    assert "[x] **01C Header tag strip integration**" in todo
    assert "[x] **01D Regression and smoke**" in todo
