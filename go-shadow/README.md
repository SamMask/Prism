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
