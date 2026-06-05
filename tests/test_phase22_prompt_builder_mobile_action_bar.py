from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROMPT_BUILDER_PATH = ROOT / "frontend" / "src" / "pages" / "PromptBuilder.tsx"
TODO_PATH = ROOT / "docs" / "TODO.md"


def test_prompt_builder_has_mobile_first_action_bar_and_preserves_desktop_bar():
    prompt_builder = PROMPT_BUILDER_PATH.read_text(encoding="utf-8")

    assert 'data-testid="prompt-builder-mobile-actions"' in prompt_builder
    assert "lg:hidden" in prompt_builder
    assert 'data-testid="prompt-builder-actions"' in prompt_builder
    assert "hidden gap-3" in prompt_builder
    assert "lg:flex" in prompt_builder


def test_prompt_builder_action_buttons_reuse_existing_save_and_reset_handlers():
    prompt_builder = PROMPT_BUILDER_PATH.read_text(encoding="utf-8")

    assert "const renderActionButtons = () =>" in prompt_builder
    assert "onClick={saveToLibrary}" in prompt_builder
    assert "onClick={resetForm}" in prompt_builder
    assert "儲存至筆記庫" in prompt_builder
    assert "重置" in prompt_builder


def test_todo_records_prompt_builder_mobile_action_bar_as_p1_completion():
    todo = TODO_PATH.read_text(encoding="utf-8")

    assert "Prompt Builder mobile action bar polish" in todo
    assert "Risk level: `P1 workflow-sensitive`" in todo
    assert "這一步會真的改 Prompt Builder 手機版的操作動線" in todo
    assert "不新增 backend API、資料庫 schema、Pi/Caddy/service、Go runtime 或 public exposure" in todo
    assert "Prompt Builder mobile action bar polish — Risk level `P1 workflow-sensitive`" in todo
