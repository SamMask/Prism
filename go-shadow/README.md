# Prism Go Runtime Proof

Phase 18.4 started this as a read-only shadow backend for contract comparison against the Python Flask API.
Phase 19.0 promotes the same binary into a runtime / packaging proof: single executable, embedded frontend, explicit external data directory, explicit DB path, schema check, and health check.
Phase 19.2 promotes it only to a controlled read-only candidate. Python Flask remains the primary runtime and rollback path.
Phase 19.3 adds an opt-in Python-side routing proof for the GET read surface only.
Phase 19.4 is a cutover readiness audit only; it does not authorize replacing `prism.service`.
Phase 19.5 is a plan-only service-level cutover/soak document; live execution remains blocked until explicit approval.
Phase 19.6 executed an approved short Pi read-only soak and rollback drill; it still does not authorize service replacement.
Phase 19.7 executed an approved bounded extended Python-switch read-only soak and rollback drill; it still does not authorize reverse-proxy or service cutover.
Phase 19.8 creates a plan-only reverse-proxy/service cutover contract; it still does not authorize live Caddy changes.
Phase 19.9 executed an approved short Caddy-level read-only routing drill and rollback; it still does not authorize permanent cutover.
Phase 19.10 executed an approved bounded extended Caddy-level read-only soak and rollback; it still does not authorize permanent cutover.
Phase 19.11 creates a proposal-only Caddy cutover candidate decision contract; it still does not authorize permanent cutover.
Phase 19.12 executed an approved permanent read-only Caddy cutover; it retains only the validated GET read surface on Go and still does not authorize a full Go backend replacement.
Phase 19.13 executed an approved post-permanent stabilization review; it keeps the permanent route active without route edits, reloads, or scope expansion.
Phase 19.14 executed approved Caddy matcher hardening; it narrows `/api/notes/*` to exact `/api/notes` plus numeric note-detail IDs without expanding Go ownership.
Phase 19.15 executed approved post-hardening stabilization; it closes Phase 19 read-only promotion as stabilized.
Phase 20.0 is an approved plan-only scope assessment; it does not expand Go ownership after Phase 19 closure.
Phase 20.1 is an approved plan-only write surface inventory; it does not select or implement a Go write candidate.

## Scope

Included endpoints:

- `GET /api/test`
- `GET /api/categories`
- `GET /api/tags`
- `GET /api/notes`
- `GET /api/notes/{id}`

Local/copied-DB candidate endpoints behind explicit flags:

- `POST /api/notes` and `PUT /api/notes/{id}` with `--enable-notes-write`
- `DELETE /api/notes/{id}`, `POST /api/notes/batch/delete`, notes pin/archive/duplicate/reorder, and current batch type/tags with `--enable-notes-write`
- `POST /api/categories`, `PUT /api/categories/{id}`, and `DELETE /api/categories/{id}` with `--enable-category-write`
- `GET /api/attachments/{id}` text JSON with `--enable-attachment-text-read`
- `GET /api/attachments/{id}?raw=true` raw/text/binary serving with `--enable-attachment-raw-read`
- `GET /api/notes/{id}/attachments`, `POST /api/notes/{id}/attachments`, and `DELETE /api/attachments/{id}` metadata/file mutation with `--enable-attachment-write`
- `POST /api/upload` original upload candidate with `--enable-upload-write`
- `POST /api/upload/extract-prompt` prompt metadata extraction with `--enable-upload-write`
- `POST /api/upload` `_thumb.webp` generation and `thumbnail_only` with `--enable-thumbnail-write`
- `POST /api/upload/url` remote image fetch candidate with `--enable-upload-url-write`
- server/system/config candidates with `--enable-server-system`
- embedded SPA and `/static/uploads/<file>` serving from the explicit data dir, with unknown `/api/*` returning JSON 404 instead of SPA fallback
- T046-T050 frontend route coverage closure: long-content `GET /api/notes/{id}/check_separation`, `POST /api/notes/{id}/separate`, and `POST /api/notes/{id}/restore` are handled with `--enable-notes-write`; `GET /api/system/check-update` returns a controlled Go primary response with `--enable-server-system`; PromptBuilder uses `/api/wizard-options`, and `/static/config/*` returns JSON 404 instead of SPA HTML.

Runtime-only endpoint:

- `GET /healthz`

Excluded endpoints remain Python-owned by default/live runtime: live/default notes writes, category/tag writes, files/uploads, upload delete, import/export, cleanup, maintenance, and `/api/server/*` until their explicit local/copied gates are promoted by later cutover work.

## Promotion Gate

The machine-readable Phase 19.2 gate lives at:

- `docs/contracts/phase19-go-readonly-promotion-gate.json`

The gate allows the current GET-only surface to be used for a future controlled read routing proof, but it does not authorize production cutover. The next planned step is Phase 19.3: local-only or sidecar-only read routing behind an explicit reversible switch.

Still excluded: POST/PUT/DELETE, file routes, server maintenance, default frontend cutover, Go migrations, and Python backend removal.

## Controlled Read Routing Proof

The Phase 19.3 contract lives at:

- `docs/contracts/phase19-go-read-routing-proof.json`

Run this Go sidecar on a copied DB, then explicitly enable Python-side routing:

```powershell
$env:PRISM_GO_READ_ROUTING = "1"
$env:PRISM_GO_READ_BASE_URL = "http://127.0.0.1:5001"
python app.py
```

Only these Python requests may proxy to Go:

- `GET /api/test`
- `GET /api/categories`
- `GET /api/tags`
- `GET /api/notes`
- `GET /api/notes/{id}`

Python remains the fallback and default owner. Invalid base URLs, unavailable Go sidecar, non-GET methods, and non-whitelisted paths stay on Python. Proxied responses include `X-Prism-Go-Read-Routing: hit`; `GET /api/system/go-read-routing` reports switch status and validity.

## Cutover Readiness Audit

The Phase 19.4 audit lives at:

- `docs/contracts/phase19-go-cutover-readiness-audit.json`

Its decision is limited: the repo is ready to write a separate read-only service-level cutover plan. It does not authorize live service replacement, production DB writes, Go migrations, Python removal, or Go ownership of file/write routes.

## Service-level Cutover Plan

The Phase 19.5 plan lives at:

- `docs/contracts/phase19-go-readonly-service-cutover-plan.json`

It defines the planned Python-primary / Go-localhost-sidecar topology, preflight, production DB backup requirement, monitoring evidence, rollback drill, success/failure criteria, and exposure boundary. It is still plan-only: no live Pi service change, Caddy route change, frontend default change, or production DB access is authorized until Phase 19.6 receives explicit user approval.

## Approved Read-only Soak Execution

The Phase 19.6 execution evidence lives at:

- `docs/contracts/phase19-go-readonly-soak-execution.json`

After explicit approval, the Pi target ran `prism-go-readonly.service` on `127.0.0.1:5002` against the production DB with `PRISM_GO_ALLOW_PROD_DB=1`, SQLite `query_only`, and schema v16 health evidence. Python `PRISM_GO_READ_ROUTING=1` temporarily routed only the approved GET read surface to Go; routed responses carried `X-Prism-Go-Read-Routing: hit`. The rollback drill removed the Python service drop-in, restarted `prism.service`, verified routing `enabled=false`, stopped the sidecar, and confirmed port 5002 had no listener.

Phase 19.6 still does not authorize Caddy route changes, frontend default target changes, Go writes/files/migrations, or Python backend removal. Phase 19.7 is a separate approval-gated post-soak decision.

## Bounded Extended Read-only Soak

The Phase 19.7 execution evidence lives at:

- `docs/contracts/phase19-go-readonly-long-soak-decision.json`

After explicit approval, the Pi target started from Python-only state, created a fresh backup, started the localhost Go sidecar, and ran Python opt-in read routing for ten 60-second samples. Each sample verified representative GET reads carried `X-Prism-Go-Read-Routing: hit`, while migration status and a POST method check remained Python-owned without that header. The rollback drill again removed the Python service drop-in, restarted `prism.service`, stopped the sidecar, and confirmed port 5002 had no listener.

Phase 19.7 still does not authorize Caddy route changes, frontend default target changes, unattended long-running production routing, Go writes/files/migrations, or Python backend removal. Phase 19.8 is a separate approval-gated plan-only reverse-proxy/service cutover gate.

## Reverse-proxy / Service Cutover Plan

The Phase 19.8 plan lives at:

- `docs/contracts/phase19-go-reverse-proxy-service-cutover-plan.json`

It defines a plan-only Caddy/service routing shape: only the validated GET read surface may be routed to the localhost Go sidecar, and Python remains owner for writes, files, system/server routes, imports/exports, cleanup, frontend assets, static uploads, and migrations. The plan requires Caddy config backup, `caddy validate`, fresh DB backup, live header/status/log monitoring, and rollback to Python-only before any future 19.9 live drill.

Phase 19.8 still does not authorize live Caddy config changes, Caddy reload, frontend default target changes, unattended long-running production routing, Go writes/files/migrations, or Python backend removal.

## Caddy Read-only Routing Drill

The Phase 19.9 execution evidence lives at:

- `docs/contracts/phase19-go-caddy-readonly-routing-drill.json`

After explicit approval, the Pi target backed up the production DB and Caddyfile, validated Caddy, started the localhost Go sidecar, and briefly reloaded Caddy with a bounded read-only route block. The block routed only the validated GET read surface to Go and added `X-Prism-Go-Read-Routing: hit`; Python-owned system/routing/POST checks did not carry that header. Rollback restored the backed-up Caddyfile, validated and reloaded Caddy, stopped the sidecar, and confirmed port 5002 had no listener.

Phase 19.9 still does not authorize permanent Caddy route changes, frontend default target changes, unattended long-running production routing, Go writes/files/migrations, or Python backend removal. Phase 19.10 is a separate approval-gated post-Caddy decision.

## Bounded Extended Caddy Read-only Soak

The Phase 19.10 execution evidence lives at:

- `docs/contracts/phase19-go-caddy-extended-readonly-soak.json`

After explicit approval, the Pi target started from Python-only state, backed up the production DB and Caddyfile, validated Caddy, started the localhost Go sidecar, and ran a bounded extended Caddy-level read-only soak for ten 60-second samples. Each sample verified representative GET reads carried `X-Prism-Go-Read-Routing: hit`, while system/routing/POST checks remained Python-owned without that header. Rollback restored the backed-up Caddyfile, validated and reloaded Caddy, stopped the sidecar, and confirmed port 5002 had no listener.

Phase 19.10 still does not authorize permanent Caddy route changes, frontend default target changes, unattended or multi-hour production routing, Go writes/files/migrations, or Python backend removal. Phase 19.11 is a separate approval-gated Caddy cutover candidate decision.

## Caddy Cutover Candidate Decision

The Phase 19.11 decision artifact lives at:

- `docs/contracts/phase19-go-caddy-cutover-candidate-decision.json`

After explicit approval, the repo now treats Go as a verified Caddy-routable read-only sidecar candidate and records a proposal-only permanent read-only Caddy cutover contract. The proposal requires an attended operation window, external auth/exposure boundary, fresh DB/Caddy backups, `caddy validate`, header/status/log monitoring, rollback triggers, and a Caddyfile backup restore plan before any future live permanent route.

Phase 19.11 still does not authorize live Caddy changes, Caddy reload, permanent Caddy route changes, frontend default target changes, unattended production routing, Go writes/files/migrations, or Python backend removal. Phase 19.12 is a separate approval-gated permanent read-only Caddy cutover approval gate.

## Permanent Read-only Caddy Cutover

The Phase 19.12 execution evidence lives at:

- `docs/contracts/phase19-go-permanent-caddy-readonly-cutover.json`

After explicit approval, the Pi target retained a permanent Caddy route block for only the validated GET read surface. The route sends `/api/test`, categories, tags, notes list, and note detail/404 to `prism-go-readonly.service` on `127.0.0.1:5002` and adds `X-Prism-Go-Read-Routing: hit`. Python remains owner for system/server routes, writes, files, frontend/static assets, imports/exports, cleanup, and migrations.

Phase 19.12 still does not authorize frontend default target changes, Go writes/files/migrations, Python backend removal, direct public internet exposure, or unreviewed route expansion. Phase 19.13 is a separate approval-gated post-permanent stabilization review.

## Post-permanent Caddy Stabilization

The Phase 19.13 execution evidence lives at:

- `docs/contracts/phase19-go-post-permanent-caddy-stabilization.json`

After explicit approval, the Pi target ran five live monitoring samples at 10-second intervals without editing or reloading Caddy. The permanent read-only route stayed healthy: validated GET reads carried `X-Prism-Go-Read-Routing: hit`, while system/routing/server/version and POST checks stayed Python-owned without that header. The decision is to keep the permanent read-only Caddy route active.

Phase 19.13 still does not authorize route expansion, Caddy route edits, frontend default target changes, Go writes/files/migrations, Python backend removal, or direct public internet exposure. Phase 19.14 is a separate approval-gated matcher/runbook hardening gate.

## Caddy Matcher / Runbook Hardening

The Phase 19.14 execution evidence lives at:

- `docs/contracts/phase19-go-caddy-matcher-runbook-hardening.json`

After explicit approval, the Pi Caddy matcher was narrowed from broad `/api/notes/*` to exact `/api/notes` plus numeric `^/api/notes/[0-9]+$`. This keeps the current validated note list/detail surface on Go but prevents future unreviewed nested or nonnumeric `/api/notes/...` GET routes from silently becoming Go-owned. Live checks verified `/api/notes/not-a-number` and `/api/notes/114/extra` stayed Python-owned without `X-Prism-Go-Read-Routing`.

Phase 19.14 still does not authorize route expansion, frontend default target changes, Go writes/files/migrations, Python backend removal, or direct public internet exposure. Phase 19.15 is a separate approval-gated post-hardening stabilization gate.

## Post-matcher Hardening Stabilization

The Phase 19.15 execution evidence lives at:

- `docs/contracts/phase19-go-post-matcher-hardening-stabilization.json`

After explicit approval, the Pi target ran five monitoring samples at 10-second intervals without editing or reloading Caddy. The narrowed matcher stayed healthy: exact read list and numeric note detail carried `X-Prism-Go-Read-Routing: hit`, while nonnumeric/nested `/api/notes/...`, system/routing/server/version, and POST checks stayed Python-owned without that header.

Phase 19 is now closed as a stabilized read-only promotion. Go owns only the validated GET read surface through the hardened Caddy matcher. Any Phase 20 work must start with a plan-only scope assessment and does not automatically authorize writes, files, migrations, frontend default changes, Python removal, or public exposure.

## Post-readonly Scope Assessment

The Phase 20.0 assessment artifact lives at:

- `docs/contracts/phase20-go-post-readonly-scope-assessment.json`

After explicit approval, Phase 20.0 assessed what could happen after read-only promotion and intentionally stopped before implementation. Notes writes, category/tag writes, file/attachment/cleanup/import/export routes, and system/server/migration routes all remain Python-owned until a separate contract locks side effects, rollback, and parity tests.

## Write Surface Contract Inventory

The Phase 20.1 inventory artifact lives at:

- `docs/contracts/phase20-go-write-surface-contract-inventory.json`

After explicit approval, Phase 20.1 grouped Python-owned mutation/file/system surfaces by route class and side-effect shape. The inventory records DB writes, file writes/deletes, external fetches, service/process actions, security boundaries, rollback requirements, and future parity fixture requirements for notes writes, actions/batch, history, category/tag writes, attachments, uploads, cleanup, import/export, system/server routes, and prompt/wizard config.

Phase 20.1 still does not authorize Go write/file/migration implementation, Caddy expansion, changing the Go sidecar away from SQLite `query_only`, frontend default changes, Python removal, or public exposure. Phase 20.2 is a separate approval-gated candidate selection and fixture planning gate.

## Runtime Safety

The server requires an explicit DB path plus an explicit external data dir and keeps user data outside the binary:

```powershell
go run . --db C:\path\to\knowledge_test.db --data-dir C:\Users\you\AppData\Local\Prism --addr 127.0.0.1:5001
```

`--data-dir` / `PRISM_GO_DATA_DIR` is mandatory. Relative `--db` paths resolve under that data dir and `..` traversal is rejected; absolute copied DB paths remain supported for legacy parity harnesses. Runtime config centralizes `static/uploads`, `docs/attachments`, `logs`, `backups`, and `config` below the data dir, and `/healthz` reports those resolved roots for evidence.

By default it refuses to open a file named `knowledge.db`. Use only copied test/dev databases unless `PRISM_GO_ALLOW_PROD_DB=1` is explicitly set for a controlled local smoke test. The SQLite connection owner uses modernc `_pragma` DSN values so each `database/sql` connection enables WAL, sets `PRAGMA busy_timeout = 5000`, keeps `PRAGMA query_only = ON` by default, and switches query-only off only for explicit DB-write candidate flags. Write-mode transactions go through the owner helper and are covered by commit/rollback tests before any future route promotion.

### Fresh DB Init

For local/package smoke only, a missing DB path inside the explicit data dir can be initialized from Go:

```powershell
go run . --db fresh/prism_runtime_dev.db --data-dir C:\Users\you\AppData\Local\Prism-Go-Smoke --addr 127.0.0.1:5001
```

This creates the current Prism v16 schema, indexes, `Notes_FTS` triggers, default categories, welcome note, and `Schema_Meta schema_version=16`, then returns to default SQLite `query_only = ON` unless an explicit local DB-write candidate flag is enabled. Existing DB migrations remain outside this gate: T008 does not run `ALTER TABLE`, update an existing `Schema_Meta`, perform backup-before-migrate, deploy Pi, or touch production `knowledge.db`.

### Existing DB Migrations

For local/copied DBs, startup now checks `Schema_Meta` and applies pending migrations through the ordered Python-compatible v1-v16 list:

```powershell
go run . --db copied_runtime_dev.db --data-dir C:\Users\you\AppData\Local\Prism-Go-Smoke --addr 127.0.0.1:5001
```

If pending migrations exist, Go first writes a backup under `PRISM_GO_DATA_DIR/backups/prism_go_pre_migrate_*.db`, then runs the migration transaction with duplicate-column and no-such-column skips matching the Python idempotency rules. On success, `/api/system/migration-status` reports `pending: []` and the runtime returns to `query_only = ON` unless an explicit local DB-write flag is enabled. On failure, startup aborts, `Schema_Meta` is not advanced, partial DDL is rolled back, and the pre-migrate backup remains available.

This is still a local/copied-DB proof. Normal/live production migrations remain retained-Python until a separate cutover gate; this does not deploy Pi, edit Caddy/systemd, change frontend defaults, remove Python, or authorize production `knowledge.db` mutation.

### Notes Read/Search/Create/Update/Delete

The active-roadmap T011/T012/T013 gates close local/copied-DB notes read/search/create/update/delete parity:

```powershell
go run . --db copied_runtime_dev.db --data-dir C:\Users\you\AppData\Local\Prism-Go-Smoke --addr 127.0.0.1:5001
go run . --db copied_runtime_dev.db --data-dir C:\Users\you\AppData\Local\Prism-Go-Smoke --addr 127.0.0.1:5001 --enable-notes-write
```

Default mode keeps `GET /api/notes` read-only and matches Python tokenized `Notes_FTS` title/content search, remarks/tag/attachment metadata search, bounded text attachment body search, category/tag filters, type compatibility, and pagination. The explicit `--enable-notes-write` mode opens only local/copied DB create/update parity for `POST /api/notes` and `PUT /api/notes/{id}`: default category fallback, tags, source URLs, prompt params, `Notes_FTS` trigger updates, content history insertion, SQLite `foreign_keys(1)`, and failed update rollback.

The same explicit flag now covers local/copied DB-and-data delete parity for `DELETE /api/notes/{id}` and `POST /api/notes/batch/delete`: not-found and empty-list validation, `Notes_FTS` delete trigger results, Note_Tags / Source_Urls / Note_History / Note_Attachments cleanup, referenced image preservation, original + `_thumb.webp` companion deletion, and `_thumb.webp` reference cleanup of original image candidates. File cleanup is scoped to `PRISM_GO_DATA_DIR/static/uploads`.

#### Notes Actions And Batch Type/Tags

The active-roadmap T014/T015 gates extend the same explicit local/copied-DB candidate mode to `POST /api/notes/{id}/pin`, `POST /api/notes/{id}/archive`, `POST /api/notes/{id}/duplicate`, `PUT /api/notes/reorder`, `POST /api/notes/batch/type`, and `POST /api/notes/batch/tags`. These routes stay behind `--enable-notes-write` / `PRISM_GO_ENABLE_NOTES_WRITE=1` and match Python response shape plus DB state for pin/archive toggles, duplicate variant parent linkage, Note_Tags / Source_Urls duplication, sort_order mutation, batch category/tag updates, invalid category rollback, invalid mode validation, and invalid note_ids handling.

`POST /api/notes/batch/archive` is not a current Python API route, so it remains absent on Go as well. This does not promote live/default notes write ownership and does not cover history restore/delete closure, upload delete, general media cleanup ownership, production DB/files, Pi deploy, Caddy/systemd, frontend defaults, Python removal, or public exposure.

#### Notes History And Categories

The active-roadmap T016/T017 gates close local/copied-DB notes history and category write parity. `GET /api/notes/{id}/history`, `POST /api/notes/{id}/restore/{history_id}`, and `DELETE /api/notes/{id}/history` stay behind `--enable-notes-write` / `PRISM_GO_ENABLE_NOTES_WRITE=1` and match Python response shape plus DB state for history list ordering, restore backup insertion, `Notes.content` restoration, missing history validation, and delete-history counts.

Category writes stay behind `--enable-category-write` / `PRISM_GO_ENABLE_CATEGORY_WRITE=1`. The Go candidate now matches Python `POST /api/categories`, `PUT /api/categories/{id}`, and `DELETE /api/categories/{id}` behavior for create duplicate/missing-name validation, update duplicate/empty-name validation, `sort_order` persistence, default category delete protection, in-use category `target_category_id` migration, empty category delete, and missing category 404s.

This does not promote live/default notes or taxonomy write ownership and does not cover tags write/merge, attachments, uploads, import/export, server/system, cleanup ownership, production DB/files, Pi deploy, Caddy/systemd, frontend defaults, Python removal, or public exposure.

#### Tags Write And Merge

The active-roadmap T018 gate closes local/copied-DB tags write and merge parity. `PUT /api/tags/{id}`, `DELETE /api/tags/{id}`, and `POST /api/tags/merge` stay behind `--enable-tag-write` / `PRISM_GO_ENABLE_TAG_WRITE=1` and match Python response shape plus Tags / Note_Tags DB state for rename trim and duplicate NOCASE validation, in-use tag delete association cleanup, merge target validation, missing-source skip, source tag deletion, and target Note_Tags transfer with `INSERT OR IGNORE`.

`POST /api/tags` is not a current Python API route, so Go does not add a separate tag create endpoint. Tag creation remains through the existing notes create/update/batch tag assignment paths; those paths now use route-level `COLLATE NOCASE` lookup to avoid case-variant duplicate Tags rows on copied legacy DBs.

This does not promote live/default taxonomy write ownership and does not cover attachments, uploads, import/export, server/system, cleanup ownership, production DB/files, Pi deploy, Caddy/systemd, frontend defaults, Python removal, or public exposure.

#### Attachments Metadata Upload/Delete

The active-roadmap T019 gate closes local/copied-DB-and-files attachment metadata parity. `GET /api/notes/{id}/attachments`, `POST /api/notes/{id}/attachments`, and `DELETE /api/attachments/{id}` stay behind `--enable-attachment-write` / `PRISM_GO_ENABLE_ATTACHMENT_WRITE=1` and match Python response shape plus Note_Attachments DB state for list ordering, missing-note validation order, multipart file-required validation, supported `md` / `txt` / `markdown` extensions, copied `docs/attachments` file creation, DB row creation, file delete, and missing-file delete behavior.

`PUT` / `PATCH` attachment metadata update routes are not current Python API routes, so Go does not add a Go-only update endpoint. `GET /api/attachments/{id}` text JSON remains the separate `--enable-attachment-text-read` candidate, while `raw=true` / send_file and broader raw/binary serving stay deferred to T020.

This does not promote live/default files ownership and does not cover raw/binary attachment serving, long-content separate/restore, uploads, import/export, server/system, cleanup ownership, production DB/files, Pi deploy, Caddy/systemd, frontend defaults, Python removal, or public exposure.

#### Attachments Raw Serving And Uploads

The active-roadmap T020-T023 gates close local/copied-data candidates for the next files/uploads surfaces:

```powershell
go run . --db copied_runtime_dev.db --data-dir C:\Users\you\AppData\Local\Prism-Go-Smoke --addr 127.0.0.1:5001 --enable-attachment-raw-read
go run . --db copied_runtime_dev.db --data-dir C:\Users\you\AppData\Local\Prism-Go-Smoke --addr 127.0.0.1:5001 --enable-upload-write --enable-thumbnail-write
go run . --db copied_runtime_dev.db --data-dir C:\Users\you\AppData\Local\Prism-Go-Smoke --addr 127.0.0.1:5001 --enable-upload-url-write
```

`--enable-attachment-raw-read` keeps SQLite `query_only=true` and allows `GET /api/attachments/{id}` plus `raw=true` serving from `PRISM_GO_DATA_DIR/docs/attachments`, including text MIME, binary image MIME, Range requests, missing-file 404s, path traversal rejection, symlink escape rejection, unsupported-extension rejection, and file-size caps.

`--enable-upload-write` and `--enable-thumbnail-write` keep SQLite `query_only=true` and write only under `PRISM_GO_DATA_DIR/static/uploads`. The direct upload candidate validates multipart file presence, safe filename basename, allowed image extension, magic bytes, 5 MiB cap, original write, `_thumb.webp` companion generation, max-width 500 thumbnails, and `thumbnail_only` success behavior.

`--enable-upload-url-write` keeps SQLite `query_only=true` and writes only under `PRISM_GO_DATA_DIR/static/uploads`. It validates http/https scheme, literal-IP/DNS SSRF boundaries, redirect targets, timeout/header policy, image Content-Type, magic bytes, stream cap, sanitized URL basename or md5 hash fallback filename, `_thumb.webp`, and `thumbnail_only` fallback behavior.

These gates do not promote live/default files/uploads ownership and do not cover upload delete, cleanup, import/export, server/system, production DB/files, Pi deploy, Caddy/systemd, frontend defaults, Python removal, or public exposure.

#### Upload Delete And Media Cleanup

The active-roadmap T024-T027 gates close local/copied DB/data candidates for upload delete and media cleanup:

```powershell
go run . --db copied_runtime_dev.db --data-dir C:\Users\you\AppData\Local\Prism-Go-Smoke --addr 127.0.0.1:5001 --enable-upload-delete
go run . --db copied_runtime_dev.db --data-dir C:\Users\you\AppData\Local\Prism-Go-Smoke --addr 127.0.0.1:5001 --enable-media-cleanup
```

`--enable-upload-delete` keeps SQLite `query_only=true` and enables `POST /api/upload/delete` only for copied data. It deletes unreferenced originals plus `_thumb.webp` / same-extension thumbnail companions under `PRISM_GO_DATA_DIR/static/uploads`, while DB/reference scans protect images referenced by `Notes.content`, `Notes.cover_image`, direct static/uploads attachments, and text attachment content.

`--enable-media-cleanup` intentionally disables SQLite `query_only` because originals cleanup and broken image fixes update `Notes.content` / `Notes.cover_image`. It enables `GET` / `DELETE /api/cleanup/orphan-images`, `GET` / `DELETE /api/cleanup/originals`, and `GET` / `POST /api/cleanup/broken-images` for copied DB/data only. File mutation remains confined to `PRISM_GO_DATA_DIR/static/uploads`; production files, Pi/Caddy/systemd routing, frontend defaults, and live/default cleanup ownership remain retained Python.

#### Import And Export

The active-roadmap T028-T031 gates close local/copied DB/data candidates for import/export:

```powershell
go run . --db copied_runtime_dev.db --data-dir C:\Users\you\AppData\Local\Prism-Go-Smoke --addr 127.0.0.1:5001 --enable-import-export
```

`--enable-import-export` intentionally disables SQLite `query_only` because import routes write copied DB rows and may restore files under `PRISM_GO_DATA_DIR/static/uploads` or `PRISM_GO_DATA_DIR/docs/attachments`. It enables `POST /api/notes/import/md`, `POST /api/import/json`, `GET /api/export/json`, `GET /api/export/markdown`, `GET /api/export/db`, `POST /api/export/images`, and `POST /api/notes/export/batch` for copied DB/data only.

Markdown import supports H1 title extraction, simple frontmatter category/type/tags/source_urls mapping, existing `/static/uploads` references, multipart local image bundling, and safe remote image import through the same SSRF-guarded downloader used by upload-url. JSON import supports skip/duplicate semantics, category/tag/url mapping, optional base64 attachment/upload restore, and no-partial-write rollback. Export routes produce JSON metadata, Markdown zip plus bundled images, DB download, images zip, and selected-note markdown/assets zip.

These gates do not promote live/default import/export ownership and do not cover server/system backup management, full workflow E2E, production DB/files, Pi deploy, Caddy/systemd, frontend defaults, Python removal, or public exposure.

#### Server, System, And Options

The active-roadmap T032-T035 gates close local/copied DB/data candidates for server/system/config surfaces:

```powershell
go run . --db copied_runtime_dev.db --data-dir C:\Users\you\AppData\Local\Prism-Go-Smoke --addr 127.0.0.1:5001 --enable-server-system
```

`--enable-server-system` intentionally disables SQLite `query_only` because the candidate includes copied-DB maintenance routes such as WAL checkpoint, VACUUM, and clear-history. It enables `GET /api/server/version`, `GET /api/system/stats`, `GET /api/server/hardware`, `GET /api/server/logs`, backup list/download/rotate/delete, `GET` / `POST /api/system/port-config`, `GET` / `POST /api/system/startup-preference`, safe `POST /api/server/restart` acknowledgement, prompt options CRUD, and wizard options CRUD. File mutations stay under `PRISM_GO_DATA_DIR/backups`, `PRISM_GO_DATA_DIR/config`, and data-root startup marker files.

The Go local candidate does not execute host service restart. These gates do not promote live/default server/system ownership and do not cover full workflow E2E, production DB/files, Pi deploy, Caddy/systemd, frontend defaults, Python removal, or public exposure.

#### Static Serving, Security, Full Workflow

The active-roadmap T036-T038 gates close the local/copied static serving, security, and full workflow proof:

```powershell
go run . --db copied_runtime_dev.db --data-dir C:\Users\you\AppData\Local\Prism-Go-Smoke --addr 127.0.0.1:5001 --enable-notes-write --enable-upload-write --enable-thumbnail-write --enable-upload-url-write --enable-upload-delete --enable-media-cleanup --enable-import-export --enable-server-system
```

The root handler now serves the embedded SPA for `/` and client-side routes, serves `/static/uploads/<file>` only from `PRISM_GO_DATA_DIR/static/uploads`, and returns JSON 404 for unknown `/api/*` routes instead of falling through to `index.html`. Upload static serving rejects traversal, empty paths, directories, and symlink escape outside the uploads root.

The Go runtime has no built-in auth/token layer. It refuses non-local listen addresses by default; `PRISM_GO_ALLOW_PUBLIC_BIND=1` is an explicit escape hatch only for deployments already protected by trusted LAN/VPN/proxy auth. `/healthz` reports this exposure policy, and the T037 fixtures prove private-IP upload-url and bad-MIME upload failures leave copied uploads unchanged.

The T038 full workflow fixture runs create, upload, static serve, search, export, import, delete, cleanup, backup, and migration status against both Python and Go local/copied runtimes. It compares durable invariants rather than generated timestamps or upload filenames. This does not promote live/default Go primary ownership, deploy Pi, edit Caddy/systemd, change frontend defaults, touch production DB/files, remove Python, or expand public exposure.

#### Windows Package and Pi Staging

The active-roadmap T039-T041 gates close package and staging proof without changing the live owner:

```powershell
.\scripts\smoke_go_primary_package.ps1
.\scripts\stage_go_primary_pi.ps1
```

`scripts/smoke_go_primary_package.ps1` builds the Windows and linux/arm64 artifacts, starts `build/go-runtime/prism-go-runtime.exe` from a fresh Go-created DB under `build/go-primary-package-smoke/windows/data/`, removes Python/Flask-related runtime env keys from the child process, and runs `scripts/go_primary_full_workflow_smoke.py` over HTTP. The harness uses Python stdlib only and does not import Flask app code; Python is a test driver, not a package runtime dependency.

`scripts/stage_go_primary_pi.ps1` copies `build/go-runtime/prism-go-runtime-linux-arm64` to `PI5Mask24:/home/mask070924/prism/go-primary-staging/`, installs/restarts only `prism-go-primary-staging.service`, binds it to `127.0.0.1:5003`, copies production `knowledge.db`, `static/uploads`, and `docs/attachments` into the staging data dir, runs the same full workflow smoke, and verifies live DB plus Caddyfile SHA256 remain unchanged. This is not a Caddy/default cutover, rollback drill, soak window, Python service stop, or Python removal.

#### Live Go Primary Cutover, Rollback, and Soak

The active-roadmap T042-T044 gates moved Pi live/default ownership to Go primary:

```powershell
.\scripts\go_primary_pi_live_ops.ps1 -Mode All
```

The live ops script deploys `prism-go-primary.service` on `PI5Mask24`, binds it to `127.0.0.1:5004`, switches Caddy `https://prism.local` to the Go primary target with `X-Prism-Go-Primary: hit`, and runs the HTTP-only full workflow smoke over Caddy. The same script proves rollback to Python `prism.service` with `X-Prism-Python-Rollback: hit`, restores DB/files from the T042 backup set, then cuts back to Go primary and runs a bounded soak.

Final T044 evidence: Go primary active/enabled, Python `prism.service` inactive, Caddy active, schema v16 migration status clean, 5 soak samples at 10-second intervals, no Go/Caddy error journal entries, and Go max RSS below the retained-Python baseline.

#### Python Packaged Runtime Deletion

The active-roadmap T045 gate removes the Python packaged runtime/startup path after the T042-T044 live proof:

- removed tracked embedded `python/`
- removed portable Python launcher/packager and PyInstaller builder
- replaced local start/install/package/deploy entrypoints with Go primary artifact paths
- retained Python backend source and `requirements*.txt` only as legacy source/dev/test context until T053

The machine-readable contract is `docs/contracts/go-primary-python-packaged-runtime-deletion.json`. After the 2026-06-13 closure review, T046 is the frontend-to-Go route coverage and missing-surface audit gate; T053 is the source archival/deletion and final docs/API/release wording cleanup gate.

## Build Proof

```powershell
.\scripts\build_go_runtime.ps1
```

The script builds `frontend/dist`, copies it into the Go embed directory, runs `go test ./...`, and emits:

- `build/go-runtime/prism-go-runtime.exe`
- `build/go-runtime/prism-go-runtime-linux-arm64`

## Verification

The pytest diff harness in `tests/test_phase18_go_shadow_contract.py` starts this server against the same temporary DB used by Flask and compares the core read responses. `tests/test_phase19_go_runtime_packaging.py` builds a local executable, smoke-tests `/healthz` and embedded frontend serving, then cross-builds the Linux ARM64 artifact with `CGO_ENABLED=0`.
`tests/test_phase19_go_readonly_promotion_gate.py` locks the Phase 19.2 gate against the registered Go route surface and forbidden write methods.
`tests/test_phase19_go_read_routing.py` locks the Phase 19.3 Python-side switch, fallback behavior, and status evidence.
`tests/test_phase19_go_cutover_readiness_audit.py` locks the Phase 19.4 audit-only boundary and 19.5 approval requirement.
`tests/test_phase19_go_readonly_service_cutover_plan.py` locks the Phase 19.5 plan-only boundary and 19.6 approval gate.
`tests/test_phase19_go_readonly_soak_execution.py` locks the Phase 19.6 execution evidence, rollback final state, and 19.7 approval gate.
`tests/test_phase19_go_readonly_long_soak_decision.py` locks the Phase 19.7 extended-soak evidence, rollback final state, and 19.8 approval gate.
`tests/test_phase19_go_reverse_proxy_service_cutover_plan.py` locks the Phase 19.8 plan-only Caddy/service boundary and 19.9 approval gate.
`tests/test_phase19_go_caddy_readonly_routing_drill.py` locks the Phase 19.9 Caddy drill evidence, rollback final state, and 19.10 approval gate.
`tests/test_phase19_go_caddy_extended_readonly_soak.py` locks the Phase 19.10 extended Caddy soak evidence, rollback final state, and 19.11 approval gate.
`tests/test_phase19_go_caddy_cutover_candidate_decision.py` locks the Phase 19.11 proposal-only cutover candidate decision and 19.12 approval gate.
`tests/test_phase19_go_permanent_caddy_readonly_cutover.py` locks the Phase 19.12 permanent read-only Caddy cutover evidence, final state, rollback plan, and 19.13 approval gate.
`tests/test_phase19_go_post_permanent_caddy_stabilization.py` locks the Phase 19.13 stabilization evidence, keep decision, and 19.14 approval gate.
`tests/test_phase19_go_caddy_matcher_runbook_hardening.py` locks the Phase 19.14 matcher narrowing evidence, rollback plan, and 19.15 approval gate.
`tests/test_phase19_go_post_matcher_hardening_stabilization.py` locks the Phase 19.15 post-hardening stabilization evidence, read-only promotion closure, and 20.0 plan-only gate.
`tests/test_phase20_go_post_readonly_scope_assessment.py` locks the Phase 20.0 plan-only scope assessment and 20.1 inventory gate.
`tests/test_phase20_go_write_surface_contract_inventory.py` locks the Phase 20.1 plan-only inventory, Python-owned route classes, side-effect coverage, and 20.2 approval gate.
`tests/test_go_primary_t007_sqlite_owner.py` locks the active-roadmap T007 SQLite owner contract, WAL/busy-timeout/write-mode source shape, docs status, and non-promotion boundary.
`tests/test_go_primary_t008_fresh_db_init.py` locks the active-roadmap T008 fresh DB init contract, empty data-dir runtime smoke, v16 schema/seed evidence, docs status, and existing-migration-runner boundary.
`tests/test_go_primary_t009_t010_migrations.py` locks the active-roadmap T009/T010 existing DB migration runner, backup-before-migrate, failed rollback, docs status, and non-production boundary.
`tests/test_go_primary_t011_t012_notes.py` locks the active-roadmap T011/T012 notes read/search/create/update parity, FTS/default-category/history/rollback evidence, docs status, and non-live-promotion boundary.
`tests/test_go_primary_t013_notes_delete.py` locks the active-roadmap T013 notes delete/batch-delete parity, DB/FTS association cleanup, static/uploads original + `_thumb.webp` cleanup, docs status, and non-live-promotion boundary.
`tests/test_go_primary_t014_t015_notes_actions_batch.py` locks the active-roadmap T014/T015 notes actions and batch type/tags parity, batch/archive absence boundary, docs status, and non-live-promotion boundary.
`tests/test_go_primary_t016_t017_history_categories.py` locks the active-roadmap T016/T017 notes history and categories parity, default-disabled write boundary, docs status, and non-live-promotion boundary.
`tests/test_go_primary_t018_tags.py` locks the active-roadmap T018 tags write/merge parity, NOCASE tag lookup boundary, `POST /api/tags` absence boundary, docs status, and non-live-promotion boundary.
`tests/test_go_primary_t019_attachments_metadata.py` locks the active-roadmap T019 attachments metadata upload/delete parity, update-route absence boundary, docs status, and non-live-promotion boundary.
`tests/test_go_primary_t020_t023_files_uploads.py` locks the active-roadmap T020-T023 attachment raw serving, upload, thumbnail, upload-url safety fixtures, docs status, and non-live-promotion boundary.
`tests/test_go_primary_t024_t027_media_cleanup.py` locks the active-roadmap T024-T027 upload delete, orphan images, originals cleanup, broken images cleanup fixtures, docs status, and non-live-promotion boundary.
`tests/test_go_primary_t028_t031_import_export.py` locks the active-roadmap T028-T031 Markdown import, JSON import, JSON/Markdown export, DB/images export, batch export fixtures, docs status, and non-live-promotion boundary.
`tests/test_go_primary_t032_t035_server_system.py` locks the active-roadmap T032-T035 server status, backup management, port/startup config, prompt/wizard options fixtures, docs status, and non-live-promotion boundary.
`tests/test_go_primary_t036_t038_static_security_workflow.py` locks the active-roadmap T036-T038 embedded SPA/static uploads serving, security no-mutation/public-bind boundary, full workflow E2E invariants, docs status, and non-live-promotion boundary.
`tests/test_go_primary_t039_t041_package_staging.py` locks the active-roadmap T039-T041 Windows package smoke, linux/arm64 Pi staging smoke, staging unit/live-hash guard scripts, docs status, and non-live-cutover boundary.
`tests/test_go_primary_t042_t044_live_cutover.py` locks the active-roadmap T042-T044 live Go primary cutover, rollback drill, soak evidence, script boundaries, docs status, and non-deletion boundary.
`tests/test_go_primary_t045_python_packaged_runtime_deletion.py` locks the active-roadmap T045 embedded Python runtime deletion, Go primary product starter paths, legacy source retention, docs status, T046 route-coverage handoff, and T053 final source cleanup boundary.
