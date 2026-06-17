from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NOTE_CARD_PATH = ROOT / "frontend" / "src" / "components" / "NoteCard.tsx"
API_REFERENCE_PATH = ROOT / "docs" / "API_REFERENCE.md"
GO_MAIN_PATH = ROOT / "go-shadow" / "main.go"
GO_TEST_PATH = ROOT / "go-shadow" / "main_test.go"


def test_note_card_variant_action_looks_active_and_lineage_is_rendered():
    note_card = NOTE_CARD_PATH.read_text(encoding="utf-8")

    assert "const parentTitle = note.parent_title?.trim()" in note_card
    assert "const lineageLabel = parentTitle ? t('noteCard.lineageFrom'" in note_card
    assert "title={lineageLabel}" in note_card
    assert "t('noteCard.lineageFrom', { title: parentTitle.substring(0, 20) })" in note_card

    create_variant_block = note_card.split("onClick={handleCreateVariant}", 1)[1].split("</button>", 1)[0]
    assert "text-text-secondary" in create_variant_block
    assert "hover:bg-bg-hover hover:text-text-primary" in create_variant_block
    assert "text-accent" not in create_variant_block
    assert "disabled" not in create_variant_block


def test_notes_list_contract_includes_variant_lineage():
    go_main = GO_MAIN_PATH.read_text(encoding="utf-8")
    go_test = GO_TEST_PATH.read_text(encoding="utf-8")
    api_reference = API_REFERENCE_PATH.read_text(encoding="utf-8")

    assert "n.parent_id, p.title AS parent_title" in go_main
    assert "LEFT JOIN Notes p ON n.parent_id = p.id" in go_main
    assert '"parent_id": nullableIntOrNil(parentID)' in go_main
    assert '"parent_title": nullableStringOrNil(parentTitle)' in go_main

    assert "variant duplicates keep parent lineage visible in the notes list response" in go_test
    assert "ParentID    *int" in go_test
    assert "ParentTitle *string" in go_test

    assert '"parent_id": null' in api_reference
    assert '"parent_title": null' in api_reference
    assert "列表回應包含 `parent_id` / `parent_title`" in api_reference
    assert "列表回應目前不包含 `parent_id`" not in api_reference
