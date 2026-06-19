from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LIGHTBOX_PATH = ROOT / "frontend" / "src" / "components" / "ImageLightbox.tsx"
READING_VIEW_PATH = ROOT / "frontend" / "src" / "components" / "ReadingView.tsx"
EDITABLE_PREVIEW_PATH = ROOT / "frontend" / "src" / "components" / "editor" / "EditablePreview.tsx"
NOTE_EDITOR_PATH = ROOT / "frontend" / "src" / "components" / "NoteEditor.tsx"
NOTE_CARD_PATH = ROOT / "frontend" / "src" / "components" / "NoteCard.tsx"
I18N_PATH = ROOT / "frontend" / "src" / "i18n" / "index.ts"
CONTRACTS_PATH = ROOT / "docs" / "CONTRACTS.md"
TODO_PATH = ROOT / "docs" / "TODO.md"


def test_shared_lightbox_component_stays_frontend_only_and_keyboard_accessible():
    lightbox = LIGHTBOX_PATH.read_text(encoding="utf-8")

    assert "export interface LightboxImage" in lightbox
    assert "images: LightboxImage[]" in lightbox
    assert "onActiveIndexChange: (index: number) => void" in lightbox
    assert "navigator.clipboard.writeText(currentImage.src)" in lightbox
    assert "window.open(currentImage.src, '_blank', 'noopener,noreferrer')" in lightbox
    assert "event.key === 'Escape'" in lightbox
    assert "event.key === 'ArrowLeft'" in lightbox
    assert "event.key === 'ArrowRight'" in lightbox
    assert "event.stopImmediatePropagation()" in lightbox
    assert "document.addEventListener('keydown', handleKeyDown, true)" in lightbox
    assert 'data-testid="image-lightbox"' in lightbox
    assert 'data-testid="image-lightbox-image"' in lightbox
    assert "/api/upload" not in lightbox
    assert "/api/cleanup" not in lightbox


def test_lightbox_zoom_and_backdrop_controls_stay_inside_shared_viewer():
    lightbox = LIGHTBOX_PATH.read_text(encoding="utf-8")

    assert "const MIN_ZOOM = 0.5" in lightbox
    assert "const MAX_ZOOM = 3" in lightbox
    assert "const ZOOM_STEP = 0.25" in lightbox
    assert "const [zoomScale, setZoomScale] = useState(1)" in lightbox
    assert "setZoomScale(1)" in lightbox
    assert "event.key === 'ArrowUp'" in lightbox
    assert "event.key === 'ArrowDown'" in lightbox
    assert 'data-testid="image-lightbox-zoom-out"' in lightbox
    assert 'data-testid="image-lightbox-reset-zoom"' in lightbox
    assert 'data-testid="image-lightbox-zoom-in"' in lightbox
    assert "style={{ transform: `scale(${zoomScale})` }}" in lightbox
    assert "onClick={onClose}" in lightbox
    assert "onClick={(event) => event.stopPropagation()}" in lightbox
    assert "const handlePreviousClick = (event: MouseEvent<HTMLButtonElement>)" in lightbox
    assert "const handleNextClick = (event: MouseEvent<HTMLButtonElement>)" in lightbox


def test_reading_view_collects_cover_and_markdown_images():
    reading_view = READING_VIEW_PATH.read_text(encoding="utf-8")

    assert "collectReadingImages(coverImage, localNote.content || '', localNote.title" in reading_view
    assert "extractImageReferences(content).forEach((src) => addImage(src))" in reading_view
    assert "imageSourceMatches(image.src, src)" in reading_view
    assert "onClick={handleMarkdownImageClick}" in reading_view
    assert 'data-testid="reading-cover-image"' in reading_view
    assert 'data-testid="reading-content"' in reading_view
    assert "prose-img:cursor-zoom-in" in reading_view
    assert "<ImageLightbox" in reading_view
    assert "lightboxIndex === null ? handleClose : () => setLightboxIndex(null)" in reading_view


def test_editor_preview_and_gallery_use_shared_lightbox():
    editable_preview = EDITABLE_PREVIEW_PATH.read_text(encoding="utf-8")
    note_editor = NOTE_EDITOR_PATH.read_text(encoding="utf-8")

    assert "import { ImageLightbox, type LightboxImage } from '../ImageLightbox'" in editable_preview
    assert "const [lightboxIndex, setLightboxIndex] = useState<number | null>(null)" in editable_preview
    assert "const previewImages = useMemo<LightboxImage[]>" in editable_preview
    assert "openLightboxForSource(block.imageUrl as string)" in editable_preview
    assert 'data-testid="preview-image-lightbox-trigger"' in editable_preview
    assert "<ImageLightbox" in editable_preview
    assert "window.open(block.imageUrl" not in editable_preview

    assert "import { ImageLightbox, type LightboxImage } from './ImageLightbox'" in note_editor
    assert "const [galleryLightboxIndex, setGalleryLightboxIndex] = useState<number | null>(null)" in note_editor
    assert "const galleryLightboxImages = useMemo<LightboxImage[]>" in note_editor
    assert 'data-testid="editor-gallery-lightbox-trigger"' in note_editor
    assert "<ImageLightbox" in note_editor
    assert "window.open(src" not in note_editor


def test_note_card_cover_uses_explicit_shared_lightbox_button_without_card_click_hijack():
    note_card = NOTE_CARD_PATH.read_text(encoding="utf-8")

    assert "import { ImageLightbox, type LightboxImage } from './ImageLightbox'" in note_card
    assert "Maximize2" in note_card
    assert "const [isCoverLightboxOpen, setIsCoverLightboxOpen] = useState(false)" in note_card
    assert "event.stopPropagation()" in note_card
    assert "data-testid={`note-card-cover-lightbox-${note.id}`}" in note_card
    assert "aria-label={t('noteCard.openCoverImage')}" in note_card
    assert "<ImageLightbox" in note_card
    assert "openEditorWithDetail(true)" in note_card


def test_lightbox_i18n_and_docs_track_all_subgates():
    i18n = I18N_PATH.read_text(encoding="utf-8")
    contracts = CONTRACTS_PATH.read_text(encoding="utf-8")
    todo = TODO_PATH.read_text(encoding="utf-8")

    for key in [
        "openCoverImage",
        "lightboxTitle",
        "lightboxOpenImage",
        "lightboxCopyPath",
        "lightboxOpenOriginal",
        "lightboxPrevious",
        "lightboxNext",
        "lightboxZoomIn",
        "lightboxZoomOut",
        "lightboxResetZoom",
    ]:
        assert i18n.count(key) == 4

    assert "CONTRACT-IMAGE-VIEWER-LIGHTBOX" in contracts
    assert "CONTRACT-IMAGE-VIEWER-ZOOM" in contracts
    assert "Editor preview / card cover integration" not in contracts
    assert "[x] **01A Shared lightbox component**" in todo
    assert "[x] **01B Reading view integration**" in todo
    assert "[x] **01C Editor preview/card integration**" in todo
    assert "[x] **01A Zoom controls**" in todo
    assert "[x] **01B Backdrop click close**" in todo
    assert "[x] **01C Keyboard zoom shortcuts**" in todo
