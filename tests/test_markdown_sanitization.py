from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
READING_VIEW = ROOT / "frontend" / "src" / "components" / "ReadingView.tsx"
EDITABLE_PREVIEW = ROOT / "frontend" / "src" / "components" / "editor" / "EditablePreview.tsx"
MARKDOWN_UTIL = ROOT / "frontend" / "src" / "utils" / "markdown.ts"
FRONTEND_PACKAGE = ROOT / "frontend" / "package.json"


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

    assert "renderSafeMarkdown(localNote.content || '', t('reading.emptyContent'))" in reading
    assert "dangerouslySetInnerHTML={{ __html: renderSafeMarkdown(block.source) }}" in preview
