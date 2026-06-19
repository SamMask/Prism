# Prism TODO / HANDOFF Archive - 2026-06-19 V2.5 stabilization

This file archives details moved out of `docs/TODO.md` and `HANDOFF.md` during
the 2026-06-19 slimming pass. Current active entry remains `docs/TODO.md` and
`HANDOFF.md`.

## Current truth archived from active docs

- Go primary is the only current runtime owner. Python Flask backend source was removed in T053; the full migration record remains in `docs/development-history/go-primary-runtime-completion-20260617.md`.
- Windows portable baseline is complete: `Prism.exe` launches the desktop shell with same-process Go runtime and WebView2, and the default data directory is `PrismData\` next to the executable.
- Installer/updater/WebView2 bootstrap/Start Menu/uninstall/update flows remain deferred and require a separate decision gate.
- V2.5 release was aligned to commit `42ce747bc273182b045455de49b8be06fd6c051a`; release notes document unsigned portable SmartScreen behavior, Mark-of-the-Web, SHA256 verification, and `Unblock-File`.
- Pi live deployment remains separate from GitHub release packaging and follows `DEPLOY-PI.md`.
- No built-in auth/token layer was added; Prism remains for localhost, trusted LAN, VPN, SSH tunnel, or an externally protected reverse proxy.

## Completed V2.5 / stabilization items

- Desktop Shell Phase 0-6, post-package follow-up, manual acceptance, README split, and release packaging boundaries were archived in `docs/development-history/desktop-portable-release-handoff-20260618.md`.
- Core UX / Maintenance gates completed: search explainability UX, search integrity diagnostics plus manual FTS rebuild, maintenance health overview, and Windows Server Dashboard card cleanup.
- New-user frontend defaults were stabilized: light theme, warm gray, classic gold, preview card open mode, automatic load-more enabled, and manual language selection persisted in `localStorage`.
- Variant tracking panel completed local + Pi verification: `GET /api/notes?parent_id=<id>`, `variants_count`, ReadingView parent/children panel, NoteCard affordances, and duplicate-as-variant attachment preservation.
- Note list lightweight payload completed local + Pi verification: list payload now uses preview-compatible content plus `content_preview`, `content_truncated`, `content_length`, and `content_first_image`; detail endpoints still return full content.
- Shared image lightbox completed local + Pi verification for ReadingView, EditablePreview, NoteEditor gallery, and NoteCard cover.
- Image viewer zoom follow-up completed local gate: zoom in/out/reset, ArrowUp/ArrowDown zoom shortcuts, backdrop click close, and reset-on-image-change/open.
- Header starred tag shortcuts completed local + Pi verification with frontend-only `prism.starredTags.v1`.
- Batch Markdown/txt import completed local + Pi verification through Settings frontend wrapper over existing single-file APIs.
- Reading list workspace completed Pi delivery with frontend-only `prism.readingWorkspace.v1`, ReadingView panel, NoteCard/Editor/Header entry points, scroll restore, and Appearance sidebar width control.
- Version 2.5 display completed: UI shows `V2.5`, HTML title is `Prism V2.5`, and Go primary fallback version is `2.5`.
- Pi deploy snapshot retention was tightened so pre-cutover data snapshots keep the latest 5 by default; weekly DB backups remain separate DB-only backups.
- Default category identity split completed local + Pi delivery with migration v17, `Categories.system_key`, `name_override`, and localized frontend display semantics.
- Deep scan risk closure `DEEP-SCAN-RISK-CANDIDATE-01` 01A-01G completed local gate:
  - Markdown render path uses DOMPurify sanitizer.
  - Text attachment upload/read limits are aligned to a 1 MiB hard limit.
  - Server backup download/rotate uses SQLite consistent DB snapshots and is documented as DB-only.
  - Category invalid payload/delete-target validation returns 400/404.
  - Bounded attachment body search returns optional partial diagnostics when limits are hit.
  - Local-only/no-auth exposure boundary has runtime/docs regressions.
  - Stability pack covers search sync, Chinese/emoji cases, missing/Windows attachment paths, and bad pending-restore markers.
- `PROJECT-REVIEW-HYGIENE-CANDIDATE-01 01A-01E 已完成 local gate`:
  - [x] **01A LICENSE consistency gate**: root `LICENSE` added for the existing MIT README claim.
  - [x] **01B GitHub CI baseline**: `.github/workflows/ci.yml` validates without secrets, Pi access, production DB, uploads, or attachments.
  - [x] **01C Verification environment alignment**: requirements/docs/CI align on Go 1.26.x, Node.js 22.14.0, npm 10.9.2, Python 3.11.x, and pytest 9.0.2.
  - [x] **01D Release validation checklist**: `docs/RELEASE_CHECKLIST.md` records fresh release evidence requirements and Not-tested reasons.
  - [x] **01E Small docs consistency cleanup**: `CONTRIBUTING` E2E path matches actual `e2e/`, and README release/license wording points to real evidence files.

## Deferred / candidate notes

- `DEEP-SCAN-RISK-CANDIDATE-01` 01H remains low-priority maintenance triage only: frontend bundle/browserslist warning, frozen historical docs/test wording, or small route-local Go cleanup. It must not become a broad code-splitting or Go runtime decomposition task.
- Desktop installer/updater work remains deferred until explicitly requested.
- Hidden/deferred i18n UI such as `PortConfigSection`, `UpdateSection`, and `TagInput` should receive four-language keys only when those surfaces are restored to active rendering.
- Note deletion currently should be treated as note data deletion, not a guarantee that upload image files are deleted. Users can explicitly clean unused images through Settings. A future UX candidate can add clearer copy or an opt-in checkbox for deleting images used only by the selected notes.

## Archived release/package evidence

- V2.5 GitHub Actions CI passed for commit `42ce747bc273182b045455de49b8be06fd6c051a`.
- Local release-doc validation passed with `python -m pytest tests/test_project_review_hygiene.py -q`.
- Portable build and smoke passed before release asset replacement.
- Release package privacy sweep passed: no DB/WAL/SHM, uploads, attachments, notes, env/key/pem, or log files in the zip.
- `build/` was cleaned to keep only the latest `build/release/PrismDesktopPortable-v2.5` folder and zip.
