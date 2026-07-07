from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HEADER_PATH = ROOT / "frontend" / "src" / "components" / "Header.tsx"
NOTE_CARD_PATH = ROOT / "frontend" / "src" / "components" / "NoteCard.tsx"
DANGER_ZONE_PATH = ROOT / "frontend" / "src" / "components" / "settings" / "DangerZoneSection.tsx"
I18N_PATH = ROOT / "frontend" / "src" / "i18n" / "index.ts"
TODO_PATH = ROOT / "docs" / "TODO.md"
HANDOFF_PATH = ROOT / "HANDOFF.md"


def test_note_delete_confirmation_mentions_reference_counted_media_cleanup():
    note_card = NOTE_CARD_PATH.read_text(encoding="utf-8")
    header = HEADER_PATH.read_text(encoding="utf-8")
    i18n = I18N_PATH.read_text(encoding="utf-8")

    assert "t('noteCard.deleteMediaHint')" in note_card
    assert "`${t('noteCard.deleteMessage')}\\n\\n${t('noteCard.deleteMediaHint')}`" in note_card
    assert "t('header.batchDeleteMediaHint')" in header
    assert "`${t('header.batchDeleteMessage', { count: selectedNoteIds.length })}\\n\\n${t('header.batchDeleteMediaHint')}`" in header

    assert i18n.count("deleteMediaHint:") >= 4
    assert i18n.count("batchDeleteMediaHint:") >= 4
    for phrase in [
        "已偵測且沒有其他筆記引用的圖片會一併清理",
        "Detected images that no other note references will be cleaned up",
        "検出済みで他のノートから参照されていない画像は一緒に整理されます",
        "감지되었고 다른 노트가 참조하지 않는 이미지는 함께 정리됩니다",
    ]:
        assert phrase in i18n


def test_settings_orphan_image_cleanup_copy_mentions_leftovers_after_note_delete():
    danger_zone = DANGER_ZONE_PATH.read_text(encoding="utf-8")
    i18n = I18N_PATH.read_text(encoding="utf-8")

    assert 'data-testid="orphan-image-cleanup-description"' in danger_zone
    assert "t('settings.dangerZone.orphanDescription')" in danger_zone
    assert "刪除筆記後仍留下的未引用圖片" in i18n
    assert "unreferenced images left after deleting notes" in i18n
    assert "ノート削除後に残った未参照画像" in i18n
    assert "노트 삭제 후 남은 미참조 이미지" in i18n


def test_note_delete_media_ux_docs_close_without_runtime_semantics_change():
    todo = TODO_PATH.read_text(encoding="utf-8")
    handoff = HANDOFF_PATH.read_text(encoding="utf-8")

    assert "`NOTE-DELETE-MEDIA-UX-CANDIDATE-01`（狀態：`Done`）" in todo
    assert "只補 confirmation / Settings copy" in todo
    assert "未改 Go delete/media cleanup runtime" in todo
    assert "NOTE-DELETE-MEDIA-UX-CANDIDATE-01 已完成" in handoff
