# Phase 19: Go Runtime / Packaging Promotion

> Scope: Phase 19.0/19.1 proof, Phase 19.2 promotion gate, Phase 19.3 controlled read routing proof, Phase 19.4 cutover readiness audit, Phase 19.5 read-only service-level cutover plan, Phase 19.6 approved short read-only soak execution, Phase 19.7 approved bounded extended read-only soak, and Phase 19.8 reverse-proxy/service cutover plan. This does not replace the Python backend, add product features, or implement write/file/server-maintenance routes.

## Goal

Use Go for Prism runtime and packaging promotion:

- Windows local single executable proof.
- Raspberry Pi Linux ARM64 single binary build proof.
- Embedded React `frontend/dist` inside the Go binary.
- External user data directory for DB, config, uploads, attachments, logs, and backups.
- Python backend remains the parity baseline and rollback path.

## Current Python Runtime Inventory

| Area | Current location / behavior |
|---|---|
| Entry point | `python app.py` creates Flask app via `create_app()`, calls `init_db()`, reads port config, then runs Flask. |
| React dist | Python V2 mode serves `frontend/dist` from `Config.FRONTEND_DIST`. |
| DB path | `DATABASE_PATH` or repo-local `knowledge.db`. Pi deploy excludes `knowledge.db` from sync. |
| Uploads | `UPLOAD_FOLDER` or repo-local `static/uploads`; Pi deploy excludes `static/uploads`. |
| Port config | Repo-local `.port_config`, JSON object with preferred port and fallback settings; Pi deploy excludes it. |
| Pi service | `prism.service` runs `/home/mask070924/prism/linux-venv/bin/python app.py`. |

## Phase 19.0 Go Runtime Layout

| Concern | Proof decision |
|---|---|
| Binary | `go-shadow` remains the proof binary; build output names are `prism-go-runtime.exe` and `prism-go-runtime-linux-arm64`. |
| Frontend | `scripts/build_go_runtime.ps1` builds React and copies `frontend/dist` into `go-shadow/web/dist` before `go build`, so the binary serves embedded assets. |
| Data dir | `--data-dir` / `PRISM_GO_DATA_DIR` points to external user data. The binary may create the directory but does not package user data. |
| DB | `--db` / `PRISM_GO_DB` is mandatory. Phase 19.0 keeps DB explicit and refuses production-like `knowledge.db` unless `PRISM_GO_ALLOW_PROD_DB=1`. |
| Schema check | Startup checks `Schema_Meta.schema_version >= 16`. Older DBs fail closed instead of silently serving stale contracts. |
| Health check | `GET /healthz` reports runtime mode, data dir, DB path, schema version, expected schema version, query-only status, and read-only API surface. |
| API surface | Only `GET /api/test`, `GET /api/categories`, `GET /api/tags`, `GET /api/notes`, and `GET /api/notes/<id>` are implemented. |

## SQLite Driver Spike

| Option | Fit for Phase 19.0 |
|---|---|
| `modernc.org/sqlite` pure Go | Selected. It is a CGo-free SQLite driver and its supported platforms include Windows amd64 and Linux arm64. This matches single Windows exe and Pi ARM64 cross-build goals with `CGO_ENABLED=0`. |
| `github.com/mattn/go-sqlite3` CGO | Not selected for Phase 19.0. It is mature and SQLite-native, but requires `CGO_ENABLED=1` plus a GCC toolchain; ARM/cross builds may also need cross compiler configuration. That conflicts with the low-maintenance Windows/Pi packaging goal. |

Validation added:

- Go unit test creates a Prism-like schema including `Schema_Meta`, `Notes`, `Categories`, and `Notes_FTS`.
- The test verifies FTS5 `MATCH`, `PRAGMA query_only`, and schema version checking through the selected pure Go driver.
- Existing Python vs Go JSON response diff remains the API parity gate.

Reference notes:

- `modernc.org/sqlite` docs describe the package as a CGo-free SQLite driver and list Windows amd64 plus Linux arm64 among supported targets: <https://pkg.go.dev/modernc.org/sqlite>
- `github.com/mattn/go-sqlite3` docs state it is a CGO package requiring `CGO_ENABLED=1` and GCC: <https://pkg.go.dev/github.com/mattn/go-sqlite3>
- SQLite FTS5 is a virtual table module for full-text search: <https://www.sqlite.org/fts5.html>

## Build And Deployment Proof

Schema note: repo-local Python schema SSOT is migration v16 (`normalize_editor_layout`). Pi Python was deployed to v16 on 2026-06-01 through the existing Python migration flow before the Go real-data canary. Go still does not run migrations.

Windows local:

```powershell
.\scripts\build_go_runtime.ps1
.\build\go-runtime\prism-go-runtime.exe --db D:\path\to\prism_runtime_test.db --data-dir "$env:LOCALAPPDATA\Prism" --addr 127.0.0.1:5001
```

Pi artifact:

```powershell
$env:GOOS="linux"; $env:GOARCH="arm64"; $env:CGO_ENABLED="0"
go build -C go-shadow -o ..\build\go-runtime\prism-go-runtime-linux-arm64 .
```

Systemd plan for a future Pi proof deploy:

```ini
[Unit]
Description=Prism Go Runtime Proof
After=network.target

[Service]
Type=simple
WorkingDirectory=/home/mask070924/prism-go
ExecStart=/home/mask070924/prism-go/prism-go-runtime-linux-arm64 --db /home/mask070924/prism-data/knowledge.db --data-dir /home/mask070924/prism-data --addr 127.0.0.1:5001
Restart=always
RestartSec=5
Environment=PRISM_GO_ALLOW_PROD_DB=1

[Install]
WantedBy=multi-user.target
```

This systemd snippet is a plan only. Phase 19.0 does not replace the live Python `prism.service`.

## Phase 19.1 Real-Data Read-only Canary Run

Canary inputs:

| Item | Value |
|---|---|
| Pi production backup before v16 deploy | `/home/mask070924/prism/backups/prism_pre_v16_20260601_025914.db` |
| Pi canary DB copy | `/home/mask070924/prism/backups/prism_go_canary_v16_20260601_030059.db` |
| Local canary DB copy | `build/go-canary/prism_go_canary_v16.db` |
| Pi Go binary | `/home/mask070924/prism-go-canary/prism-go-runtime-linux-arm64` |
| Pi Go log | `/home/mask070924/prism-go-canary/logs/canary.log` |
| Pi requested addr | `127.0.0.1:5001` |
| Pi actual canary addr | `127.0.0.1:5002` because `127.0.0.1:5001` was already occupied by an unrelated `fava` process; the canary did not stop or replace that process. |

Canary smoke:

- Pi sidecar served `GET /healthz` with `schema_version=16`, `expected_schema_version=16`, and `sqlite_query_only=true`.
- Pi sidecar smoke passed for `GET /api/test`, `/api/categories`, `/api/tags`, `/api/notes?per_page=3&page=1`, `/api/notes/114`, and `/api/notes/999999` returning 404.
- Windows local Go exe served embedded React dist and the same read-only API against `build/go-canary/prism_go_canary_v16.db`.
- Embedded frontend smoke covered Home, `todo.md` search, category filter, tag filter, notes list, and note detail reading panel. Browser request capture showed only GET requests for API calls.

Diff matrix additions:

- `q=todo.md`
- Chinese search (`q=中文搜尋`)
- Empty result
- Pagination edge (`page=999`)
- `per_page` edges (`per_page=1`, `per_page=500`)
- `category_id + tags + tag_mode + sort` combination
- Note detail 404

Runtime metrics:

| Host | Runtime | RSS | Startup readiness |
|---|---:|---:|---:|
| Windows | Python Flask | 46,660 KB | 538 ms to `GET /api/test` |
| Windows | Go runtime | 11,104 KB at API smoke; 19,748 KB after frontend smoke | 513 ms to `GET /healthz` |
| Raspberry Pi | Python Flask | 47,104 KB | 422 ms to `GET /api/test` |
| Raspberry Pi | Go runtime sidecar | 13,488 KB | 278 ms to `GET /healthz` |

Log and write-boundary check:

- Pi canary log contains startup plus GET request logs only.
- Windows browser request capture contains GET API calls only.
- Manual POST smoke to Go `POST /api/test` returned `method not allowed`.
- No Go migration ran, no live production `knowledge.db` was opened, and the Python `prism.service` remained the primary service.

## Phase 19.2 Read-only Promotion Gate

Decision artifact: `docs/contracts/phase19-go-readonly-promotion-gate.json`

Result: Go is promoted only to a controlled read-only candidate. Python Flask remains the primary runtime owner and rollback path.

Allowed Go surface:

- `GET /healthz`
- `GET /api/test`
- `GET /api/categories`
- `GET /api/tags`
- `GET /api/notes`
- `GET /api/notes/<id>`

Promotion constraints:

- Python `prism.service` remains primary.
- Go does not run migrations.
- Go does not replace the frontend default API target.
- Production-like `knowledge.db` remains refused unless explicitly allowed for a controlled local smoke.
- POST/PUT/DELETE, file routes, export/cleanup, and `/api/server/*` stay Python-owned.

Validation added:

- `tests/test_phase19_go_readonly_promotion_gate.py` checks the machine-readable gate.
- The test verifies the gate matches `go-shadow/main.go` route registration.
- The test fails if Go runtime code adds POST/PUT/DELETE/PATCH method ownership.

Next planned step: Phase 19.3 Controlled Read Routing Proof. It may only test local-only or sidecar-only routing behind an explicit reversible switch. It must not include write routes, file routes, server maintenance, default frontend cutover, production cutover, or Python backend removal.

## Phase 19.3 Controlled Read Routing Proof

Decision artifact: `docs/contracts/phase19-go-read-routing-proof.json`

Implementation:

- Python Flask remains the default owner.
- `PRISM_GO_READ_ROUTING=1` enables the proof switch.
- `PRISM_GO_READ_BASE_URL` must be an explicit `http://localhost:<port>`, `http://127.0.0.1:<port>`, or `http://[::1]:<port>` sidecar URL.
- Flask `before_request` proxies only the already validated GET read surface to the Go sidecar.
- Invalid base URL, disabled switch, non-GET method, non-whitelisted path, or unavailable Go sidecar all keep the request on Python.

Allowed proxied surface:

- `GET /api/test`
- `GET /api/categories`
- `GET /api/tags`
- `GET /api/notes`
- `GET /api/notes/<id>`

Python-owned evidence and fallback:

- `GET /api/system/go-read-routing` reports enabled state, base URL validity, default owner, fallback owner, allowed surface, and blocked methods.
- Proxied responses include `X-Prism-Go-Read-Routing: hit`.
- Sidecar failure is fail-open to Python; this is a proof-stage availability guard, not a cutover behavior guarantee.

Still Python-owned:

- POST/PUT/DELETE/PATCH.
- Attachments, export, cleanup, server maintenance, and migrations.
- Frontend default API target.
- Production service ownership and rollback.

Next planned step: Phase 19.4 Cutover Readiness Audit. It is an audit and decision checkpoint only; it must not perform production cutover, add Go writes, add file routes, run Go migrations, replace `prism.service`, or remove Python.

## Phase 19.4 Cutover Readiness Audit

Decision artifact: `docs/contracts/phase19-go-cutover-readiness-audit.json`

Result: the repo is ready to write a separate read-only service-level cutover plan, but Phase 19.4 does not authorize runtime cutover.

Evidence accepted:

- Phase 19.0 proved Windows and Linux ARM64 Go runtime packaging, embedded frontend serving, external data dir, explicit DB path, schema check, and `/healthz`.
- Phase 19.1 proved real-data read-only canary behavior against copied v16 DB, including Pi sidecar smoke, GET-only browser capture, runtime metrics, and log/write-boundary checks.
- Phase 19.2 locked Go as a controlled read-only candidate with Python as runtime owner and rollback path.
- Phase 19.3 proved an opt-in localhost-only Python-side routing switch with Python fallback and status/header evidence.

Blocking gaps before any live cutover:

- No production service-level cutover plan exists.
- No long-running read-routing soak has been recorded.
- No Caddy/systemd read-routing deployment contract exists.
- No rollback drill from Go-routed reads back to Python service has been recorded.
- Go still does not own POST/PUT/DELETE, attachments, export, cleanup, server maintenance, migrations, production DB writes, or Python rollback.

Not authorized by Phase 19.4:

- Replacing `prism.service`.
- Changing the production frontend default API target.
- Writing to production `knowledge.db` from Go.
- Running migrations from Go.
- Removing Python runtime or venv.
- Promoting Go file/write routes.

Next planned step: Phase 19.5 Read-only Service-level Cutover Plan. This is a plan-only stage unless the user separately approves live execution. It must define deployment topology, Caddy/systemd routing, rollback drill, monitoring/log evidence, duration, success/failure criteria, and production DB backup requirements while preserving Python rollback and excluding Go writes/files/migrations.

## Phase 19.5 Read-only Service-level Cutover Plan

Plan artifact: `docs/contracts/phase19-go-readonly-service-cutover-plan.json`

Result: a plan-only service-level path exists. It is not live execution approval.

Planned topology:

- Python `prism.service` remains the primary runtime, write/file/maintenance owner, and rollback target.
- Go sidecar service name is planned as `prism-go-readonly.service`.
- Go sidecar binds `127.0.0.1:5002`.
- Go sidecar may only serve the validated GET read surface.
- Python-side `PRISM_GO_READ_ROUTING` remains the first routing control point.
- Caddy or reverse-proxy read routing is only a future option after a successful Python-switch soak and separate approval.

Required preflight before any execution:

- Verify Python `prism.service` health.
- Verify representative Python read endpoints and migration status.
- Create and verify a timestamped production DB backup.
- Verify Go sidecar `/healthz` reports schema version >= 16 and `sqlite_query_only=true`.
- Verify Go sidecar binds localhost only.
- Verify Go does not serve POST/PUT/DELETE/PATCH.
- Verify no public-internet exposure is introduced.

Rollback drill:

- Disable `PRISM_GO_READ_ROUTING`.
- Restart Python `prism.service`.
- Verify `GET /api/system/go-read-routing` reports `enabled=false`.
- Verify representative GET reads work without `X-Prism-Go-Read-Routing`.
- Stop Go sidecar if needed.

Not authorized by Phase 19.5:

- Live Pi service changes.
- Caddy route changes.
- Frontend default API target changes.
- Production DB access or writes.
- Go migrations.
- Python runtime or venv removal.
- Go ownership of write/file/maintenance routes.

Next executed step: Phase 19.6 Approved Read-only Soak Execution. It was performed only after explicit user authorization and ended with rollback to Python-only routing.

## Phase 19.6 Approved Read-only Soak Execution

Execution artifact: `docs/contracts/phase19-go-readonly-soak-execution.json`

Result: the approved short Pi read-only soak completed and was rolled back to Python-only routing. This is not production cutover approval.

Live evidence:

- Pi Python `prism.service` was active before execution.
- Production DB backup was created and verified at `/home/mask070924/prism/backups/prism_pre_go_readonly_soak_20260604_032653.db`.
- Migration status stayed at current/latest v16 with pending `[]`.
- Go sidecar `prism-go-readonly.service` served `127.0.0.1:5002` with `/healthz` reporting schema version 16 and `sqlite_query_only=true`.
- Stage 0 direct sidecar smoke covered `/healthz`, `/api/test`, categories, tags, notes list, note detail, note 404, and method boundary.
- Stage 1 Python opt-in routing used `PRISM_GO_READ_ROUTING=1` and `PRISM_GO_READ_BASE_URL=http://127.0.0.1:5002`; approved GET read surface responses carried `X-Prism-Go-Read-Routing: hit`.
- Python-owned `/api/system/migration-status` and a POST method check did not carry the Go routing header.
- Rollback removed the systemd drop-in, restarted `prism.service`, verified routing `enabled=false`, verified representative reads without the Go header, stopped `prism-go-readonly.service`, and confirmed no 5002 listener remained.

Not authorized by Phase 19.6:

- Long-running production read routing.
- Caddy or reverse-proxy route changes.
- Frontend default API target changes.
- Go writes, file routes, maintenance routes, exports, or migrations.
- Python backend removal.

Next executed step: Phase 19.7 Post-soak Decision Gate. It was performed only after separate explicit user authorization and chose a bounded extended Python-switch read-only soak, followed by rollback to Python-only routing.

## Phase 19.7 Post-soak Decision Gate

Execution artifact: `docs/contracts/phase19-go-readonly-long-soak-decision.json`

Result: the approved bounded extended Pi read-only soak completed and was rolled back to Python-only routing. Go is now a verified bounded Python-switch read-only sidecar candidate for the approved GET surface. This is still not production cutover approval.

Live evidence:

- Started from Python-only state: `prism.service` active, routing disabled, `prism-go-readonly.service` inactive, and no 5002 listener.
- Fresh production DB backup was created and verified at `/home/mask070924/prism/backups/prism_pre_go_readonly_long_soak_20260604_034124.db`.
- Go sidecar `prism-go-readonly.service` served `127.0.0.1:5002` with `/healthz` reporting schema version 16 and `sqlite_query_only=true`.
- Python opt-in routing ran from `2026-06-04T03:42:31+08:00` to `2026-06-04T03:51:36+08:00`.
- Ten samples ran at 60-second intervals. Every sample verified `prism.service` active, Go sidecar active, `GET /api/test`, notes list, and note detail with `X-Prism-Go-Read-Routing: hit`.
- Every sample verified Python-owned `/api/system/migration-status` and `POST /api/test` did not carry the Go routing header.
- Go journal had no POST/PUT/DELETE/PATCH request logs since the 19.7 start timestamp.
- Rollback removed the systemd drop-in, restarted `prism.service`, verified routing `enabled=false`, verified `/api/test` without the Go header, stopped `prism-go-readonly.service`, and confirmed no 5002 listener remained.

Not authorized by Phase 19.7:

- Caddy or reverse-proxy route changes.
- Frontend default API target changes.
- Unattended long-running production read routing.
- Go writes, file routes, maintenance routes, exports, or migrations.
- Python backend removal.
- Direct public internet exposure.

Next executed step: Phase 19.8 Reverse-proxy / Service Cutover Planning Gate. It was performed only after separate explicit user authorization and stopped at a plan-only contract.

## Phase 19.8 Reverse-proxy / Service Cutover Planning Gate

Plan artifact: `docs/contracts/phase19-go-reverse-proxy-service-cutover-plan.json`

Result: the reverse-proxy/service cutover planning gap is closed. This is not live Caddy or frontend routing approval.

Planned topology:

- Python `prism.service` remains the primary runtime, write/file/maintenance/migration owner, and required final fallback.
- Go sidecar `prism-go-readonly.service` remains localhost-only at `127.0.0.1:5002`, read-only, `sqlite_query_only`, and schema >= 16.
- Caddy may only be planned to route the validated GET read surface to the localhost Go sidecar.
- All writes, files, server/system routes, imports/exports, cleanup, frontend SPA assets, static uploads, and migrations remain Python-owned.
- Frontend default API target must not change.
- Prism still has no built-in API token, Bearer token, or user auth layer; any broader exposure requires external protection before any live routing change is considered.

Required before any 19.9 live drill:

- Separate explicit user approval.
- Python and Caddy health checks.
- Caddy config backup or rollback copy.
- `caddy validate` before reload.
- Fresh timestamped production DB backup.
- Go sidecar localhost/query_only/schema health.
- Header/status/log monitoring plan.
- Immediate rollback criteria.

Not authorized by Phase 19.8:

- Live Caddy config changes or reload.
- Frontend default API target changes.
- Direct public internet exposure.
- Go writes, file routes, maintenance routes, exports, or migrations.
- Python backend removal.
- Unattended long-running production routing.

Next planned step: Phase 19.9 Approved Caddy Read-only Routing Drill. It is blocked until separate explicit user approval and must execute only a short, reversible Caddy-level read-only routing drill using the 19.8 plan, with fresh backup, `caddy validate`, live evidence, and rollback to Python-only.

## Stop Conditions

Phase 19.8 stops at proof, canary evidence, promotion-gate evidence, controlled routing evidence, cutover-readiness audit evidence, plan-only cutover evidence, approved short-soak evidence, approved bounded extended-soak evidence, reverse-proxy/service cutover plan evidence, and rollback evidence:

- `go test ./...`
- Python vs Go response diff tests
- `pytest tests/ -v`
- Windows local executable smoke test
- Linux ARM64 build artifact and Pi sidecar smoke
- `tests/test_phase19_go_readonly_promotion_gate.py`
- `tests/test_phase19_go_read_routing.py`
- `tests/test_phase19_go_cutover_readiness_audit.py`
- `tests/test_phase19_go_readonly_service_cutover_plan.py`
- `tests/test_phase19_go_readonly_soak_execution.py`
- `tests/test_phase19_go_readonly_long_soak_decision.py`
- `tests/test_phase19_go_reverse_proxy_service_cutover_plan.py`
- This document, `docs/TODO.md`, `docs/contracts/phase19-go-readonly-promotion-gate.json`, `docs/contracts/phase19-go-read-routing-proof.json`, `docs/contracts/phase19-go-cutover-readiness-audit.json`, `docs/contracts/phase19-go-readonly-service-cutover-plan.json`, `docs/contracts/phase19-go-readonly-soak-execution.json`, `docs/contracts/phase19-go-readonly-long-soak-decision.json`, and `docs/contracts/phase19-go-reverse-proxy-service-cutover-plan.json` updated

Still out of scope:

- POST/PUT/DELETE
- Long-running production cutover or read routing without separate explicit approval
- Caddy/frontend routing changes without explicit approval
- Attachments, export, cleanup, server maintenance
- Removing or weakening the Python backend
- Writing to the production DB
