from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HOME_PATH = ROOT / "frontend" / "src" / "pages" / "HomePage.tsx"
I18N_PATH = ROOT / "frontend" / "src" / "i18n" / "index.ts"
TODO_PATH = ROOT / "docs" / "development-history" / "todo-archive-pre-go-primary-runtime-migration-20260606.md"


def test_home_empty_state_has_search_specific_copy_and_preserves_default_copy():
    home = HOME_PATH.read_text(encoding="utf-8")
    i18n = I18N_PATH.read_text(encoding="utf-8")

    assert "const emptyStateTitle = searchQuery ? t('home.emptySearchTitle') : t('home.emptyTitle')" in home
    assert "t('home.emptySearchDescription', { query: searchQuery })" in home
    assert "t('home.emptyDescription')" in home
    assert "找不到符合的筆記" in i18n
    assert "還沒有任何筆記" in i18n
    assert "沒有筆記符合" in i18n
    assert "請調整關鍵字或清除搜尋" in i18n
    assert "點擊上方「新增筆記」按鈕開始創作" in i18n
    assert 'data-testid="empty-state-title"' in home
    assert 'data-testid="empty-state-description"' in home


def test_phase22_3_todo_records_p2_low_risk_completion_without_new_contract():
    todo = TODO_PATH.read_text(encoding="utf-8")

    assert "22.3 Home Search Empty State Context Copy" in todo
    assert "Risk level: `P2 low-risk polish`" in todo
    assert "- [x] **22.3.1** Search no-result copy" in todo
    assert "不新增 22.3 contract" in todo
    assert "P2 不再開下一個儀式化 phase" in todo

