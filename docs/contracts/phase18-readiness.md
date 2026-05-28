# Phase 18 Contract Readiness

> Updated: 2026-05-27
> Scope: frontend redesign and Go read-only shadow backend preparation.

This pack records the current Python API and UI workflow boundaries before the Phase 18 UI rewrite starts. It is intentionally conservative: no runtime behavior changes, no new schema, no AI/ML dependency, and no Go write path.

## Deliverables

| TODO | Artifact | Status |
|---|---|---|
| 18.0.1 Golden response fixtures | `tests/fixtures/api_golden/*.json` + `tests/test_phase18_api_golden.py` | Locked |
| 18.0.2 Endpoint side-effect map | This document, "Endpoint Side-Effect Map" | Locked |
| 18.0.3 UI route/workflow map | This document, "UI Workflow Map" | Locked |
| 18.0.4 API manifest draft | `docs/contracts/api-readonly-manifest.json` | Locked |

## Endpoint Side-Effect Map

| Class | Endpoints | Rule for Phase 18 |
|---|---|---|
| Read-only core | `GET /api/test`, `GET /api/categories`, `GET /api/tags`, `GET /api/notes`, `GET /api/notes/<id>` | Golden fixtures define the Python baseline. These are the only endpoints eligible for the first Go read shadow. |
| Read-only support | `GET /api/prompt-options`, `GET /api/wizard-options`, `GET /api/system/stats`, `GET /api/system/check-consistency`, `GET /api/system/migration-status`, attachment reads | Keep in Python unless a later task explicitly adds fixtures and contract tests. |
| DB writes | note create/update/delete, pin/archive/duplicate/reorder, batch note actions, category writes, tag writes, prompt/wizard option writes | Keep Python-owned during Phase 18.4. UI redesign must preserve existing request/response contracts. |
| File writes/deletes | upload endpoints, attachment writes/deletes, image cleanup, note delete image cleanup, export image packaging | Excluded from Go read shadow. Do not migrate before a dedicated file contract phase. |
| Maintenance writes | vacuum, clear-history, WAL checkpoint, startup preference, port config, cleanup delete/fix operations | Keep Python-owned and user-confirmed. Do not expose through read-only tool surfaces. |
| Server local-only | `/api/server/*` | Must remain localhost-only. Redesign may reorganize Settings UI but cannot relax access boundaries. |
| Downloads/import/export | JSON/Markdown/DB/images import-export endpoints | Not part of the first Go read shadow. Treat as separate contract area. |

## UI Workflow Map

| Workflow | Existing contract to preserve | Regression points |
|---|---|---|
| Home library | Fetch categories, tags, and paged notes; filters use `category_id`, `tags`, `tag_mode`, `archived`, `include_archived`, `pinned_only`, and `sort`. | Non-Home sidebar filter must navigate Home and apply the filter; repeated active filter click on Home toggles it off. |
| Sidebar filters | Category/tag counts are derived from `GET /api/categories` and `GET /api/tags`; note cards still include legacy `type` plus `category_id`. | Do not reintroduce dependence on renamed category text when `category_id` is available. |
| Note detail / reading | `GET /api/notes/<id>` is the detail source, including `prompt_params`, `parent_id`, tags, urls, cover, archive, and pin fields. | Detail response shape must not drift during layout work. |
| Editor / EditablePreview | Create/update note stays on existing `POST /api/notes` and `PUT /api/notes/<id>` contracts. Preview editing keeps direct text edits, image reference removal, and cover clearing behavior. | Do not replace the editor stack or add a WYSIWYG dependency in Phase 18. |
| Prompt Builder | Existing prompt/wizard option APIs remain the source for option management; note prompt data remains stored in `Notes.prompt_params`. | Redesign can improve density but cannot change generated payload semantics. |
| Settings / maintenance | Settings can be rearranged into tabs, but existing system, export, backup, and local-only server contracts remain intact. | `/api/server/*` must stay local-only; public/API exposure guidance still requires trusted network boundaries. |

## Go Read Shadow Acceptance

The first Go backend work may start only after these stay true:

- `tests/test_phase18_api_golden.py` passes against the Python app.
- `docs/contracts/api-readonly-manifest.json` lists every endpoint included in the shadow surface.
- Go shadow work compares responses against the Python baseline before any traffic switch.
- Write paths, file paths, server ops, import/export, and UI runtime behavior remain Python-owned.

