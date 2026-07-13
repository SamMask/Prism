# Go Main Split Completion — 2026-07-13

## Outcome

`GO-MAIN-SPLIT-CANDIDATE-01`（GMS-00..10）完成。`go-shadow/main.go` 從 10,246 physical lines / 312,452 bytes 降到 1,024 physical lines，保留 bootstrap、runtime config / SQLite connection ownership、mux registration、middleware 與 shared declarations。其餘 declarations 依既有責任搬到同一 `package main` 的 bounded-context files。

本次是 source layout maintenance，不是 runtime redesign。沒有新增 package、service、interface、dependency、API、schema、migration、feature、fallback、compatibility layer、desktop/package 行為或 Pi deploy 變更。

## Resulting Source Layout

| File | Physical lines | Responsibility |
|---|---:|---|
| `main.go` | 1,024 | bootstrap, runtime ownership, mux, middleware, shared declarations |
| `attachments.go` | 344 | attachment metadata/text/raw/write and path safety |
| `taxonomy.go` | 647 | categories and tags |
| `migrations.go` | 692 | fresh init, ordered migrations, migration status, backup-before-migrate |
| `backups.go` | 526 | backup, restore, retention and validation |
| `system.go` | 904 | health, system/server administration, CSRF, FTS, port, logs, restart, version |
| `options.go` | 532 | prompt/wizard and data-dir JSON config |
| `import.go` | 750 | JSON/Markdown import, frontmatter, image restore and rollback |
| `export.go` | 816 | JSON/Markdown/DB/images/batch export and ZIP helpers |
| `image_metadata.go` | 243 | prompt metadata and PNG text parsing |
| `uploads.go` | 575 | upload/delete/remote fetch, SSRF, MIME/size and thumbnail helpers |
| `media_cleanup.go` | 873 | orphan/original/broken image and reference-counted cleanup |
| `notes_search.go` | 642 | note reads, list, detail and search |
| `notes_write.go` | 478 | note create/update/delete write paths |
| `notes_media.go` | 205 | note attachment/media coupling |
| `notes_actions.go` | 1,216 | note actions, history, batch and related flows |

All listed files are at or below the 1,500-line stop guard. No further splitting was performed after `main.go` passed the under-4,000-line stop condition.

## Regression Ownership Update

Thirteen static pytest assertions still assumed every Go handler lived in `go-shadow/main.go`. They now use `tests/go_source_assertions.py` to inspect all non-test `.go` files in the package. The Phase 19 route manifest test continues to inspect `main.go` directly for mux registration, while handler/flag/error contracts use package-wide source.

## Verification Evidence

- Pre-split baseline: `cd go-shadow && go test ./...` passed.
- Mechanical equivalence: 425 top-level declarations parsed from pre-split `HEAD:go-shadow/main.go` and current split files produced identical AST-formatted declarations.
- Four targeted Go groups covering migrations/attachments/taxonomy, backup/system/restore, image/uploads, and notes/search/write/actions passed.
- Post-split `cd go-shadow && go test ./...` passed; the release build reran it successfully.
- Static ownership regression set: 13 passed.
- Full Python acceptance net: `python -m pytest tests/ -v` — 379 passed in 254.34s.
- `scripts/build_go_runtime.ps1` passed: frontend production build, Go tests, Windows artifact, and linux/arm64 artifact.
- `scripts/smoke_go_local_artifact.ps1 -SkipBuild` passed; evidence written under `build/go-local-smoke/evidence.json`.
- `scripts/smoke_go_primary_package.ps1 -SkipBuild` passed, including Windows full workflow; evidence written under `build/go-primary-package-smoke/windows/evidence.json` and `evidence/full-workflow.json`.
- Final `git diff --check` passed（only expected Windows LF-to-CRLF notices）；AGENTS/CLAUDE mirror passed；tracked privacy and Go runtime artifact sweeps passed；targeted TODO/governance documentation regression passed（15 tests）。

## Not Performed

- No Pi staging, cutover, reload or live verification.
- No release version bump, commit, tag, push or GitHub release asset.
- No schema/API documentation change because runtime contracts did not change.
