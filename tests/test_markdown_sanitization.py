from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
READING_VIEW = ROOT / "frontend" / "src" / "components" / "ReadingView.tsx"
EDITABLE_PREVIEW = ROOT / "frontend" / "src" / "components" / "editor" / "EditablePreview.tsx"
MARKDOWN_UTIL = ROOT / "frontend" / "src" / "utils" / "markdown.ts"
FRONTEND_PACKAGE = ROOT / "frontend" / "package.json"
INDEX_CSS = ROOT / "frontend" / "src" / "index.css"


def test_markdown_render_paths_share_dompurify_sanitizer():
    helper = MARKDOWN_UTIL.read_text(encoding="utf-8")
    package_json = FRONTEND_PACKAGE.read_text(encoding="utf-8")

    assert '"dompurify"' in package_json
    assert "import DOMPurify from 'dompurify'" in helper
    assert "export function renderSafeMarkdown" in helper
    assert "DOMPurify.sanitize" in helper
    assert "FORBID_TAGS" in helper
    for unsafe in ["script", "iframe", "svg", "object", "embed"]:
        assert f"'{unsafe}'" in helper
    for unsafe_uri in ["javascript", "data", "vbscript"]:
        assert unsafe_uri not in helper.replace("javascript", "")


def test_reading_and_editable_preview_never_feed_raw_marked_html_to_inner_html():
    reading = READING_VIEW.read_text(encoding="utf-8")
    preview = EDITABLE_PREVIEW.read_text(encoding="utf-8")

    for source in [reading, preview]:
        assert "import { marked }" not in source
        assert "marked(" not in source
        assert "renderSafeMarkdown" in source
        assert "dangerouslySetInnerHTML" in source

    assert "renderSafeMarkdown(localNote.content || '', t('reading.emptyContent')," in reading
    assert "renderSafeMarkdown(block.source, ''," in preview


def test_markforge_prose_extensions_stay_on_sanitized_local_render_path():
    helper = MARKDOWN_UTIL.read_text(encoding="utf-8")

    for extension in [
        "GITHUB_ALERTS",
        ":::markforge-box",
        ":::markforge-details",
        "prism-footnotes",
        "applyInlineMarkForgeSyntax",
        "<mark>",
    ]:
        assert extension in helper

    assert "DOMPurify.sanitize" in helper
    assert "ALLOW_DATA_ATTR: false" in helper
    assert "ADD_TAGS" in helper
    assert "button" in helper
    for forbidden in ["'script'", "'iframe'", "'object'", "'embed'", "'style'"]:
        assert forbidden in helper


def test_markdown_low_risk_preview_ux_uses_shared_helpers():
    helper = MARKDOWN_UTIL.read_text(encoding="utf-8")
    reading = READING_VIEW.read_text(encoding="utf-8")
    preview = EDITABLE_PREVIEW.read_text(encoding="utf-8")
    css = INDEX_CSS.read_text(encoding="utf-8")

    for helper_symbol in [
        "extractMarkdownHeadings",
        "copyMarkdownCodeFromClick",
        "querySelectorAll('table')",
        "querySelectorAll('pre')",
        "prism-heading-anchor",
        "prism-task-box",
        "prism-table-wrapper",
        "prism-code-copy",
    ]:
        assert helper_symbol in helper

    assert "extractMarkdownHeadings(localNote.content || '')" in reading
    assert "data-testid=\"reading-outline-panel\"" in reading
    assert "copyMarkdownCodeFromClick(target," in reading
    assert "copyMarkdownCodeFromClick(event.target," in preview

    for css_class in [
        ".prism-table-wrapper",
        ".prism-code-copy",
        ".prism-callout",
        ".prism-details",
        ".prism-footnotes",
        ".prism-task-box",
    ]:
        assert css_class in css
