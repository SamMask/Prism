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

Runtime-only endpoint:

- `GET /healthz`

Excluded endpoints remain Python-owned: every write path, file upload/delete, import/export, cleanup, maintenance, and `/api/server/*`.

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

The server requires an explicit DB path and keeps user data outside the binary:

```powershell
go run . --db C:\path\to\knowledge_test.db --data-dir C:\Users\you\AppData\Local\Prism --addr 127.0.0.1:5001
```

By default it refuses to open a file named `knowledge.db`. Use only copied test/dev databases during Phase 19.0 unless `PRISM_GO_ALLOW_PROD_DB=1` is explicitly set for a controlled local smoke test. The SQLite connection also enables and verifies `PRAGMA query_only = ON`, then checks `Schema_Meta.schema_version >= 16`.

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
