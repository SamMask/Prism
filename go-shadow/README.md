# Prism Go Shadow Backend

Phase 18.4 read-only shadow backend for contract comparison against the Python Flask API.

## Scope

Included endpoints:

- `GET /api/test`
- `GET /api/categories`
- `GET /api/tags`
- `GET /api/notes`
- `GET /api/notes/{id}`

Excluded endpoints remain Python-owned: every write path, file upload/delete, import/export, maintenance, and `/api/server/*`.

## Runtime Safety

The server requires an explicit DB path:

```powershell
go run . --db C:\path\to\knowledge_test.db --addr 127.0.0.1:5001
```

By default it refuses to open a file named `knowledge.db`. Use only copied test/dev databases during Phase 18.4. The SQLite connection also enables `PRAGMA query_only = ON`.

## Verification

The pytest diff harness in `tests/test_phase18_go_shadow_contract.py` starts this server against the same temporary DB used by Flask and compares the core read responses.
