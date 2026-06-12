# 部署更新到樹莓派 (Deploy to Raspberry Pi)

> **目前 live owner**: Go primary runtime
> **Pi 主機名稱**: `PI5Mask24`
> **Pi 路徑**: `/home/mask070924/prism/`
> **存取網址**: `https://prism.local`

> ⚠️ **安全邊界**: Prism API / Go runtime has no built-in auth/token layer，沒有內建 API Token、Bearer Token 或使用者認證。Pi + Caddy 部署預設是 `localhost` / trusted LAN / VPN 用途；不要將 Caddy 或 Go 入口直接 port-forward 到 public internet。遠端存取請放在 VPN、SSH tunnel 或受認證保護的 reverse proxy 後面。

---

## 快速更新（日常使用）

日常 live 部署使用 Go primary ops script；它會建置 linux/arm64 artifact、上傳到 Pi、建立 backup、更新 `prism-go-primary.service`，並讓 Caddy 繼續指向 `127.0.0.1:5004`。

```powershell
# 在 Windows repo root 執行
powershell -ExecutionPolicy Bypass -File scripts/go_primary_pi_live_ops.ps1 -Mode Cutover
```

已確認 artifact 可重用時：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/go_primary_pi_live_ops.ps1 -Mode Cutover -SkipBuild
```

快速驗證：

```bash
ssh PI5Mask24 "systemctl is-active prism-go-primary.service && systemctl is-active prism.service || true"
ssh PI5Mask24 "curl -skI https://prism.local/api/server/version | tr -d '\r' | grep -Ei 'HTTP|x-prism'"
ssh PI5Mask24 "curl -sk https://prism.local/api/system/migration-status"
ssh PI5Mask24 "sudo journalctl -u prism-go-primary.service -n 80 --no-pager"
```

---

## 首次設定（只需執行一次）

首次設定也以 Go primary 為唯一產品啟動路徑。建議優先從 Windows repo root 執行完整 live ops：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/go_primary_pi_live_ops.ps1 -Mode All
```

如需在 Pi 上重新建立 mDNS / Caddy / systemd 範本，可在 artifact 已存在於 `/home/mask070924/prism/go-primary-live/bin/prism-go-runtime-linux-arm64` 後執行：

```bash
ssh PI5Mask24 "cd /home/mask070924/prism && bash deploy/raspberry_pi/setup.sh"
```

`deploy/raspberry_pi/setup.sh` 會：

- 安裝 / 設定 `avahi-daemon`
- 安裝 / 設定 Caddy，將 `https://prism.local` proxy 到 `127.0.0.1:5004`
- 建立並啟用 `prism-go-primary.service`
- 停用 legacy `prism.service`，只保留為 T046 前的 rollback/source context

---

## Go primary staging（T041，不切 live default）

T041 只用 `prism-go-primary-staging.service` 驗證 linux/arm64 Go package 能在 Pi 上以 copied production DB/data 跑 full workflow；它不改 live Caddy route、不寫 live `knowledge.db`。

```powershell
powershell -ExecutionPolicy Bypass -File scripts/stage_go_primary_pi.ps1
```

證據會回收到本機：

- `build/go-primary-staging/pi/evidence.json`
- `build/go-primary-staging/pi/full-workflow.json`

---

## Go primary live（T042-T044）

T042-T044 使用 `scripts/go_primary_pi_live_ops.ps1` 執行 live cutover、rollback drill、再切回 Go primary 並做 bounded soak。

```powershell
# 完整 cutover -> rollback -> cutover/soak
powershell -ExecutionPolicy Bypass -File scripts/go_primary_pi_live_ops.ps1 -Mode All

# 單獨操作
powershell -ExecutionPolicy Bypass -File scripts/go_primary_pi_live_ops.ps1 -Mode Cutover -SkipBuild
powershell -ExecutionPolicy Bypass -File scripts/go_primary_pi_live_ops.ps1 -Mode Rollback -SkipBuild
powershell -ExecutionPolicy Bypass -File scripts/go_primary_pi_live_ops.ps1 -Mode Soak -SkipBuild
```

目前 final live state：

- `prism-go-primary.service`: active/enabled，監聽 `127.0.0.1:5004`
- `prism.service`: inactive，僅為 T046 前的 rollback/source context
- Caddy `https://prism.local`: proxy 到 Go primary，回應帶 `X-Prism-Go-Primary: hit`
- `PRISM_GO_ALLOW_PUBLIC_BIND` 未啟用；仍只適合 trusted LAN/VPN/proxy-auth 邊界
- Python packaged runtime 與 product startup path 已由 T045 移除；Python backend source 是否刪除/封存留給 T046

證據會回收到本機：

- `build/go-primary-live/pi/evidence.json`
- `build/go-primary-live/pi/t042-full-workflow.json`
- `build/go-primary-live/pi/t043-rollback.json`
- `build/go-primary-live/pi/t044-soak.json`

---

## 自動備份排程

每週日 03:00 透過 Go primary server backup API 下載 DB backup 並輪替。

```bash
ssh PI5Mask24 "sudo tee /home/mask070924/prism/scripts/auto-backup.sh > /dev/null <<'SCRIPT'
#!/bin/bash
set -e
BACKUP_DIR=/home/mask070924/prism/backups
TS=\$(date +%Y%m%d_%H%M%S)
curl -sk --http1.1 --fail -o \"\$BACKUP_DIR/prism_backup_\$TS.db\" https://prism.local/api/server/backup/download
curl -sk --http1.1 --fail -X POST -H 'Content-Type: application/json' -H 'Origin: https://prism.local' -d '{\"keep_count\":3}' https://prism.local/api/server/backup/rotate
SCRIPT
sudo chmod +x /home/mask070924/prism/scripts/auto-backup.sh
sudo chown mask070924:mask070924 /home/mask070924/prism/scripts/auto-backup.sh"

ssh PI5Mask24 "sudo tee /etc/systemd/system/prism-backup.service > /dev/null <<'EOF'
[Unit]
Description=Prism weekly auto-backup (download + rotate)
After=network.target prism-go-primary.service
Wants=prism-go-primary.service

[Service]
Type=oneshot
User=mask070924
WorkingDirectory=/home/mask070924/prism
ExecStart=/home/mask070924/prism/scripts/auto-backup.sh
StandardOutput=journal
StandardError=journal
EOF
sudo tee /etc/systemd/system/prism-backup.timer > /dev/null <<'EOF'
[Unit]
Description=Trigger Prism backup every Sunday 03:00

[Timer]
OnCalendar=Sun *-*-* 03:00:00
Persistent=true
Unit=prism-backup.service

[Install]
WantedBy=timers.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now prism-backup.timer"
```

還原備份：

```bash
ssh PI5Mask24 "sudo systemctl stop prism-go-primary.service"
ssh PI5Mask24 "cp /home/mask070924/prism/backups/prism_backup_YYYYMMDD_HHMMSS.db /home/mask070924/prism/knowledge.db && rm -f /home/mask070924/prism/knowledge.db-wal /home/mask070924/prism/knowledge.db-shm"
ssh PI5Mask24 "sudo systemctl start prism-go-primary.service"
```

---

## 已排除的檔案（不會覆蓋 Pi 上的版本）

| 路徑 | 原因 |
|------|------|
| `knowledge.db` | 使用者資料，絕不以 tar/sync 覆蓋 |
| `static/uploads/` | 使用者上傳圖片，絕不以 tar/sync 覆蓋 |
| `docs/attachments/` | 使用者附件，絕不以 tar/sync 覆蓋 |
| `.port_config` | legacy Python 設定；Go primary 不以它作 live port owner |
| `frontend/node_modules/` | Pi 使用嵌入 Go artifact 的 build 結果 |
| `frontend/src/` | 原始碼，Pi 使用編譯產出 |
| `app.log` | Pi 有自己的 journal/logs |
| `.env` | 機敏設定，不同步 |

---

## 常用維運指令

```bash
# 查看即時日誌
ssh PI5Mask24 "sudo journalctl -u prism-go-primary.service -f"

# 重啟 Go primary
ssh PI5Mask24 "sudo systemctl restart prism-go-primary.service"

# 查看 port 使用狀況
ssh PI5Mask24 "sudo ss -tlnp | grep -E '5000|5001|5002|5003|5004'"

# 查看 Caddy 狀態
ssh PI5Mask24 "sudo systemctl status caddy --no-pager"

# 查看 route header
ssh PI5Mask24 "curl -skI https://prism.local/api/server/version | tr -d '\r' | grep -Ei 'HTTP|x-prism'"
```

---

## 已知問題與解決方案

### `https://prism.local` 沒有 Go header

**症狀**：`curl -skI https://prism.local/api/server/version` 沒有 `X-Prism-Go-Primary: hit`。

**處理**：

```bash
ssh PI5Mask24 "sudo caddy validate --config /etc/caddy/Caddyfile && sudo systemctl reload caddy"
ssh PI5Mask24 "sudo systemctl status prism-go-primary.service --no-pager"
```

### Go primary 無法啟動

先看 service journal，確認 artifact、DB、data dir、prod guard env 都存在：

```bash
ssh PI5Mask24 "sudo journalctl -u prism-go-primary.service -n 120 --no-pager"
ssh PI5Mask24 "ls -l /home/mask070924/prism/go-primary-live/bin/prism-go-runtime-linux-arm64 /home/mask070924/prism/knowledge.db"
```

---

**文件版本**：T045 / 2026-06-13
