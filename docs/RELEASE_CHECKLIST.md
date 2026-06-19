# Prism Release Validation Checklist

> Use this before any public GitHub release, tag, or portable package claim.
> A source review is not enough evidence for a release claim.

## Toolchain Contract

| Tool | Version contract | Source |
|---|---|---|
| Go | 1.26.x; `go-shadow/go.mod` declares `go 1.26.1` | `go-shadow/go.mod`, CI `actions/setup-go` |
| Node.js | 22.14.0 | GitHub Actions baseline and local verification record |
| npm | 10.9.2 | Node.js 22.14.0 bundled npm used by local verification |
| Python | 3.11.x | Dev/test-only pytest runner |
| pytest | 9.0.2 | `requirements.txt` / `requirements-pi.txt` |

## Required Evidence

Copy this table into the release notes, release PR, or package handoff. Every
row needs a fresh date, result, and evidence pointer. If a check was not run,
leave the result as `Not-tested` and state why.

| Check | Date | Result | Evidence | Not-tested reason |
|---|---|---|---|---|
| `pwsh -NoProfile -ExecutionPolicy Bypass -File .loop/verify-gate.ps1` | 2026-06-19 | Passed | `git diff --check` passed; `CLAUDE.md` / `AGENTS.md` mirror check passed; `pytest tests/ -v` = 361 passed; `cd go-shadow && go test ./...` = ok. |  |
| `cd frontend && npm run build` | 2026-06-19 | Passed with warnings | Vite build produced `dist/index.html`, `assets/index-DG6Oro5W.css`, `assets/index-DjkCXG_z.js`. Warnings: Browserslist data is 6 months old; chunk size > 500 kB. |  |
| Local browser smoke | 2026-06-19 | Passed | Existing `e2e/` Playwright flow ran against `scripts/start_go_primary.ps1 -Addr 127.0.0.1:5000 -DataDir build/e2e-browser-smoke/data -DbPath prism_e2e_smoke.db`; `python -m pytest e2e -q` passed 9 Chromium tests. |  |
| Windows desktop portable smoke | 2026-06-19 | Passed | `pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/smoke_desktop_portable.ps1`; evidence: `build/desktop-portable-smoke/run-95e5ec99209d41479bdfd08815331e5d/evidence.json`. |  |
| Release package privacy sweep: no DB/WAL/SHM, uploads, attachments, notes, env, key, or log files | 2026-06-19 | Passed | `git ls-files .omx docs/attachments docs/notes static/test_uploads static/uploads knowledge.db app.log logs .env` returned no tracked files; `tar -tf build/release/PrismDesktopPortable-v2.5.zip` found 7 entries and 0 forbidden paths; SHA256 `D7EB53F7927859C224793E4ACD59BD8379A12CBD05450B557B762FB551A80C5E`. |  |
| `AGENTS.md` / `CLAUDE.md` mirror check | 2026-06-19 | Passed | Covered by `.loop/verify-gate.ps1`; `git diff --no-index --exit-code CLAUDE.md AGENTS.md` returned 0. |  |

## Fresh Validation Record - 2026-06-19

### Current Git Status Before Commit

`git status --short --branch` showed `main...origin/main` with expected release
hygiene changes only:

- Modified docs/readme handoff files: `HANDOFF.md`, `README.md`, `README.zh-TW.md`, `docs/CONTRIBUTING.md`, `docs/INDEX.md`, `docs/README.md`, `docs/TODO.md`
- Modified test tooling pins: `requirements.txt`, `requirements-pi.txt`
- New files: `.github/workflows/ci.yml`, `LICENSE`, `docs/RELEASE_CHECKLIST.md`, `tests/test_project_review_hygiene.py`

### Existing Commands Used

Commands were taken from existing repo docs/scripts instead of inventing new
release flow:

- Tests/gate: `.loop/verify-gate.ps1`, `pytest tests/ -v`, `cd go-shadow && go test ./...`
- Runtime startup: `scripts/start_go_primary.ps1`
- Frontend build: `cd frontend && npm run build`
- Go package/API smoke: `scripts/smoke_go_primary_package.ps1`, `scripts/smoke_go_local_artifact.ps1`
- Desktop package/build smoke: `scripts/build_desktop_portable.ps1`, `scripts/smoke_desktop_portable.ps1`
- Browser smoke: `pytest e2e/ -v` per `e2e/conftest.py`

### Additional Validation

| Command | Result | Evidence / Notes |
|---|---|---|
| `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/smoke_go_primary_package.ps1` | Passed | Built Go runtime artifacts, started a fresh Go-created DB, and ran `scripts/go_primary_full_workflow_smoke.py`; evidence: `build/go-primary-package-smoke/windows/evidence.json` and `build/go-primary-package-smoke/windows/evidence/full-workflow.json`. The full workflow covers healthz, note create/update/delete, search, upload, import/export, cleanup, backup download, and migration status. |
| `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/smoke_go_local_artifact.ps1 -SkipBuild` | Passed | Evidence: `build/go-local-smoke/evidence.json`; source `knowledge.db` hash was guarded and not mutated. |
| `pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/build_desktop_portable.ps1 -OutputDir build/release -PackageName PrismDesktopPortable-v2.5` | Passed | Produced `build/release/PrismDesktopPortable-v2.5.zip` and folder; package build again reported only the existing Browserslist/chunk-size warnings. |
| `python -m pytest e2e -q` | Passed after prerequisites | Initial run failed because `pytest-playwright` was not installed. Per `e2e/conftest.py`, installed `pytest-playwright` and ran `python -m playwright install chromium`; rerun passed 9 Chromium tests against fresh local Go runtime. |

### Failures / Attention Items

- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/smoke_desktop_portable.ps1` failed under Windows PowerShell 5.1 because `[System.IO.Path]::GetRelativePath` is unavailable. Rerun with `pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/smoke_desktop_portable.ps1` passed. Use `pwsh` for this smoke.
- Browser smoke prerequisites are not in `requirements.txt`; `pytest-playwright` was installed in the local Python environment for this validation per `e2e/conftest.py`. GitHub CI will not run this browser smoke unless that setup is added to the workflow.
- No Pi deploy or Pi live verification was run in this release validation pass.

## Release Boundary

- Do not treat GitHub CI as Pi live verification. Pi delivery still follows `DEPLOY-PI.md`.
- Do not claim public-internet readiness; Prism still has no built-in auth/token layer.
- Do not publish a portable package until WebView2 behavior and the desktop smoke result are recorded.
- If any required row is `Not-tested`, describe that gap in the release notes instead of implying full validation.
