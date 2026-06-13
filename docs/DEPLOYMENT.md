# Prism - 部署指南

## Go primary deployment

目前產品 runtime owner 是 Go primary。產品啟動、Pi live 部署與 package path 不再依賴 Python、venv、Flask 或 PyInstaller。
T051 已將 API / route ownership 文件刷新為 Go primary current truth；T052 已清理 tracked embedded Python / Pillow packaging artifacts 與 root empty package lock，避免 release/package 語義與 T045 衝突。

本機啟動：

```powershell
cd D:/AI/Prism
.\scripts\build_go_runtime.ps1
.\scripts\start_go_primary.ps1
```

批次入口：

```cmd
start_v2.bat
scripts\start.bat
```

Package：

```cmd
scripts\pack.bat
```

---

## Go runtime 環境變數

Go runtime 預設只允許 local bind。不要直接對 public internet 開放。

| 變數 | 用途 |
|---|---|
| `PRISM_GO_DB` | SQLite DB path；也可用 `--db` |
| `PRISM_GO_DATA_DIR` | external data dir；也可用 `--data-dir` |
| `PRISM_GO_ADDR` | listen address；預設 local |
| `PRISM_GO_ALLOW_PROD_DB=1` | 明確允許 `knowledge.db` |
| `PRISM_GO_ALLOW_PROD_UPLOADS=1` | 明確允許 live uploads write flags |
| `PRISM_GO_ALLOW_PROD_IMPORT_EXPORT=1` | 明確允許 live import/export |
| `PRISM_GO_ALLOW_PROD_SERVER_SYSTEM=1` | 明確允許 live server/system routes |

`scripts/start_go_primary.ps1` 與 Pi systemd unit 會為受控 product startup 設定必要 guard。

---

## 安全性提醒

Prism API 目前沒有內建 API Token / Bearer Token / 使用者認證機制。預設適合 `localhost`、trusted LAN、VPN，或 SSH tunnel / 受認證保護的 reverse proxy 使用。不要把 Go runtime 或 Caddy 入口直接暴露到 public internet / 公網。

若需要遠端存取，請先在外層加入 VPN、SSH tunnel、reverse proxy auth（例如 Caddy auth）或等效保護；Prism 內部尚未實作 OAuth、JWT、API key、RBAC 或使用者系統。

---

## 系統需求

- Go toolchain（建置 `go-shadow` runtime）
- Node.js 18+（建置 React SPA 並嵌入 artifact）
- SQLite（runtime 透過 Go SQLite driver 管理）
- Python backend source 已於 T053 移除；Go primary 為唯一 runtime

---

## Raspberry Pi / Headless Server

> **目標**: 在區域網路內以 `https://prism.local` 存取 Prism。
> **詳細操作步驟請見根目錄 [`DEPLOY-PI.md`](../DEPLOY-PI.md)**。

Pi live owner：

- `prism-go-primary.service`
- `127.0.0.1:5004`
- Caddy `https://prism.local` route with `X-Prism-Go-Primary: hit`

部署：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/go_primary_pi_live_ops.ps1 -Mode Cutover
```

完整 cutover / rollback / soak：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/go_primary_pi_live_ops.ps1 -Mode All
```

常用維運：

```bash
ssh PI5Mask24 "sudo systemctl status prism-go-primary.service --no-pager"
ssh PI5Mask24 "sudo journalctl -u prism-go-primary.service -f"
ssh PI5Mask24 "curl -skI https://prism.local/api/server/version | tr -d '\r' | grep -Ei 'HTTP|x-prism'"
```

---

## Legacy Python boundary

T045 移除的是 Python packaged runtime dependency 與 product startup path：

- removed: tracked embedded `python/`
- removed: portable Python launcher / packager
- removed: PyInstaller builder
- replaced: product start/deploy/package scripts now point to Go primary

Removed in T053 (Python backend source):

- `app.py`
- `config.py`
- `db.py`
- `routes/`
- `utils/`
- `migrations/`（`migrations/add_*.py` standalone 腳本封存到 `docs/development-history/`）
- `templates/`

`requirements.txt` / `requirements-pi.txt` 已 prune 成 dev/test tooling（只剩 `pytest`），不再含 Flask backend 相依。

T053 已完成 Python backend source 的物理刪除與最後 API/deploy/release wording cleanup；Go primary 為唯一 runtime。`/api/system/go-read-routing` 是 legacy Phase 19 proof status，已隨 Python source 移除，不存在於任何 runtime。
