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

## Fresh Validation Record - 2026-07-14 (V2.6)

| Check | Result | Evidence / Notes |
|---|---|---|
| `pwsh -NoProfile -ExecutionPolicy Bypass -File .loop/verify-gate.ps1` | Passed | `git diff --check` and AGENTS/CLAUDE mirror passed; pytest 379 passed; Go tests passed. |
| `cd frontend && npm run build` | Passed with warnings | 1,520 modules transformed; existing Browserslist-age and 698.58 kB chunk-size warnings only. |
| Browser e2e | Passed after prerequisite correction | Initial run failed only because localhost:5000 was not running. Started isolated Go runtime under `build/e2e-browser-smoke-v26/`; rerun `python -m pytest e2e -q` passed 9 tests. |
| Go artifact/package smokes | Passed | `build/go-local-smoke/evidence.json`, `build/go-primary-package-smoke/windows/evidence.json`, and `evidence/full-workflow.json`. |
| V2.6 desktop portable build | Passed | `pwsh ... scripts/build_desktop_portable.ps1 -OutputDir build/release -PackageName PrismDesktopPortable-v2.6`. |
| Windows desktop portable smoke | Passed | Clean-unzip smoke evidence: `build/desktop-portable-smoke/run-3032cf1f8b8d445f948b9ad02125a516/evidence.json`. |
| Package version/read-back | Passed | Packaged debug executable served `/api/server/version` = `2.6` against isolated build data. |
| Release package privacy sweep | Passed | Tracked privacy paths empty; zip has 7 allowed entries and no DB/WAL/SHM, PrismData, uploads, attachments, notes, env/key/pem, or log files. |
| V2.6 asset hash | Passed | `PrismDesktopPortable-v2.6.zip`, 21,671,334 bytes, SHA256 `33A23644F664EEE74B9449A19EAA54AEBA758CDE199D2A8E6D22182240D24F74`. |
| GitHub Actions | Passed | Run `29266735767` completed successfully: https://github.com/SamMask/Prism/actions/runs/29266735767. The only annotation was GitHub Actions' Node 20 action-runtime deprecation warning; build/tests passed. |
| GitHub Release / asset read-back | Passed | https://github.com/SamMask/Prism/releases/tag/V2.6; tag targets commit `461421db8d6bb21d0adbd58c081047c45e19010e`; GitHub digest, local hash, and freshly downloaded asset hash match. |
| Pi live deploy | Not-tested | V2.6 GitHub release packaging does not change Pi delivery state. |

## Fresh Validation Record - 2026-07-14 (V2.6.1)

| Check | Result | Evidence / Notes |
|---|---|---|
| `pwsh -NoProfile -ExecutionPolicy Bypass -File .loop/verify-gate.ps1` | Passed | `git diff --check` and AGENTS/CLAUDE mirror passed; pytest 382 passed; Go tests passed. |
| `cd frontend && npm run build` | Passed with warnings | 1,520 modules transformed; existing Browserslist-age and 698.58 kB chunk-size warnings only. |
| Browser e2e | Passed | `python -m pytest e2e -q` passed 9 Chromium tests against an isolated Go runtime. |
| Go artifact/package smokes | Passed | `build/go-local-smoke/evidence.json`, `build/go-primary-package-smoke/windows/evidence.json`, and `evidence/full-workflow.json`. |
| V2.6.1 desktop portable build | Passed | `pwsh ... scripts/build_desktop_portable.ps1 -OutputDir build/release -PackageName PrismDesktopPortable-v2.6.1`. |
| Windows desktop portable smoke | Passed | Clean-unzip smoke evidence: `build/desktop-portable-smoke/run-5c0ba0acf0f64105ac92d95c24ca21d9/evidence.json`. |
| Package version/read-back | Passed | Packaged debug executable served `/api/server/version` = `2.6.1` against isolated build data. |
| Label browser smoke | Passed | Playwright page title `Prism V2.6.1`; sidebar `V2.6.1`; console 0 errors / 0 warnings. |
| Release package privacy sweep | Passed | Tracked privacy paths empty; zip has 7 allowed entries and no DB/WAL/SHM, PrismData, uploads, attachments, notes, env/key/pem, or log files. |
| V2.6.1 asset hash | Passed | `PrismDesktopPortable-v2.6.1.zip`, 21,671,433 bytes, SHA256 `7312213255770862BBFD057C568F70AC2F65DB7662CFDCAFC187552A298BD550`. |
| GitHub Actions / Release read-back | Passed | Run `29274092387` success; annotated tag peels to `80aa35a0d73190c318a78b969b6f51cac74ec3fb`; release asset digest and fresh download SHA256 match `7312213255770862BBFD057C568F70AC2F65DB7662CFDCAFC187552A298BD550`. |
| Pi live deploy | Passed | Cutover artifact SHA256 `7612012cbeb336f15bf9c97d9b162b27541f8f308e31a84245f931e53d0a27e8`; snapshot `/home/mask070924/prism/backups/go-primary-t042-20260714_022829`; runtime 2.6.1/schema v17 clean; full workflow, 5-sample soak, exact label Playwright and console smoke passed. |

## Fresh Validation Record - 2026-07-14 (V2.6.1 About correction reissue)

| Check | Result | Evidence / Notes |
|---|---|---|
| About regression and minimal fix | Passed | New assertions cover title, sidebar, and Settings About fallback; both targeted tests failed before the one-line `2.5` to `2.6.1` correction and passed afterward. |
| `pwsh -NoProfile -ExecutionPolicy Bypass -File .loop/verify-gate.ps1` | Passed | pytest 382 passed in 261.54s; Go tests, mirror, and whitespace gates passed. |
| Frontend / Go production build | Passed with warnings | 1,520 modules transformed; existing Browserslist-age and 698.58 kB chunk-size warnings only; Windows and linux/arm64 artifacts built. |
| Browser e2e / visible labels | Passed | 9 Chromium tests passed; Playwright verified title `Prism V2.6.1`, sidebar `V2.6.1`, About `Version: 2.6.1`, and console 0 errors / 0 warnings. |
| Go artifact/package and desktop smokes | Passed | Local artifact, Windows full-workflow package, and portable clean-unzip smokes passed; packaged runtime returned `2.6.1`. |
| Release package privacy sweep | Passed | Tracked privacy paths empty; zip has 7 allowed entries and no DB/WAL/SHM, PrismData, uploads, attachments, notes, env/key/pem, or log files. |
| Corrected V2.6.1 asset | Passed | `PrismDesktopPortable-v2.6.1.zip`, 21,671,554 bytes, SHA256 `8705C5F5CBCC24A3EEFBBC02E02695B0103CB04E879770A488D2A4429D229F17`. |
| GitHub Actions / replacement tag / Release read-back | Passed | Actions run `29276993209` success; V2.6.1 tag peels to `7f5469c16cac2a8412bb5f2524cc4e9884256db3`; GitHub digest, local hash, and fresh download SHA256 match `8705C5F5CBCC24A3EEFBBC02E02695B0103CB04E879770A488D2A4429D229F17`. Existing V2.6 is unchanged. |
| Pi live cutover / soak / About browser smoke | Passed | Artifact SHA256 `1c1ff025f8653a48e97d87cbb29afa09d09e9ca8e020fef329d1e395e2fce01d`; latest snapshot `/home/mask070924/prism/backups/go-primary-t044-20260714_031146`; runtime 2.6.1/schema v17 clean; full workflow and 5-sample soak passed; live Playwright verified title/sidebar/About and console 0/0. |
