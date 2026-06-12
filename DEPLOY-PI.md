# 部署更新到樹莓派 (Deploy to Raspberry Pi)

> **適用版本**: v2.4.2+
> **Pi 主機名稱**: `PI5Mask24`（SSH config 設定）
> **Pi 路徑**: `/home/mask070924/prism/`
> **存取網址**: `https://prism.local`

> ⚠️ **安全邊界**: Prism API 目前沒有內建 API Token / Bearer Token / 使用者認證機制；Go runtime 也同樣宣告 no built-in auth/token layer。Pi + Caddy 部署預設是 `localhost` / trusted LAN / VPN 用途；不要將 Caddy、Flask 或 Go 入口直接 port-forward 到 public internet / 公網。若需要遠端存取，請使用 VPN、SSH tunnel、受認證保護的 reverse proxy（例如 Caddy auth）或等效外部保護。`/api/server/*` 仍只允許 localhost。

---

## 快速更新（日常使用）

```bash
# 在 Windows 專案根目錄執行（Git Bash / OpenSSH）

# 1. 建置前端
cd frontend && npm run build && cd ..

# 2. 同步檔案到 Pi（排除資料庫 / 圖片 / Windows venv）
tar -czf - \
  --exclude='.git' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='frontend/node_modules' \
  --exclude='frontend/src' \
  --exclude='frontend/public' \
  --exclude='python' \
  --exclude='knowledge.db' \
  --exclude='static/uploads' \
  --exclude='.port_config' \
  --exclude='*.egg-info' \
  --exclude='.env' \
  --exclude='demo' \
  --exclude='app.log' \
  -C "/d/AI/Prism" . \
  | ssh PI5Mask24 "cd /home/mask070924/prism && tar -xzf - && echo 'EXTRACT OK'"

# 3. 重啟服務
ssh PI5Mask24 "sudo systemctl restart prism && sleep 2 && sudo systemctl status prism --no-pager | grep -E 'Active|Running'"
```

---

## 首次設定（只需執行一次）

> 如果 Pi 上還沒有 `linux-venv/`，請先執行以下步驟。

### 1. 安裝系統依賴

```bash
ssh PI5Mask24 "sudo apt-get install -y libmagic1 python3-venv"
```

### 2. 建立 Linux 專用 venv

```bash
ssh PI5Mask24 "
  cd /home/mask070924/prism
  python3 -m venv linux-venv
  linux-venv/bin/pip install -r requirements-pi.txt -q
  echo 'venv OK'
"
```

> **為什麼不用 `requirements.txt`？**
> `requirements.txt` 包含 `python-magic-bin==0.4.14`（Windows 二進位套件）。
> Pi (Linux) 使用 `requirements-pi.txt`，改用 `python-magic`（依賴系統 `libmagic1`）。

### 3. 更新 systemd service

```bash
ssh PI5Mask24 "
  sudo tee /etc/systemd/system/prism.service > /dev/null <<'EOF'
[Unit]
Description=Prism Knowledge Base Server
After=network.target

[Service]
Type=simple
User=mask070924
WorkingDirectory=/home/mask070924/prism
ExecStart=/home/mask070924/prism/linux-venv/bin/python app.py
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

Environment=FLASK_DEBUG=False
Environment=PRISM_V2=true
Environment=PRISM_PORT=5000

NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF
  sudo systemctl daemon-reload
  sudo systemctl enable prism
  echo 'service OK'
"
```

### 4. 設定 Port 偏好（JSON 格式）

```bash
ssh PI5Mask24 "
  echo '{\"preferred_port\": 5000, \"fallback_enabled\": true, \"fallback_range\": 20}' \
    > /home/mask070924/prism/.port_config
"
```

> **注意**：`.port_config` 必須是 JSON 物件格式，不是純數字。
> 若寫成 `5000`（純文字），app.py 解析失敗會靜默回退，可能導致跳至不正確的 port。

### 5. 首次啟動

```bash
ssh PI5Mask24 "sudo systemctl start prism && sleep 3 && sudo systemctl status prism --no-pager"
```

### 6. 自動備份排程 (v2.4.7+)

> 每週日 03:00 自動下載 DB 備份並輪替（保留最新 3 份，與 Settings UI 一致）。

```bash
# 安裝備份腳本
ssh PI5Mask24 "sudo tee /home/mask070924/prism/scripts/auto-backup.sh > /dev/null <<'SCRIPT'
#!/bin/bash
# 注意：必須用 --http1.1，避開 Caddy → Werkzeug HTTP/2 stream 收尾不乾淨的 curl exit 92
set -e
BACKUP_DIR=/home/mask070924/prism/backups
TS=\$(date +%Y%m%d_%H%M%S)
curl -sk --http1.1 --fail -o \"\$BACKUP_DIR/prism_backup_\$TS.db\" https://prism.local/api/server/backup/download
curl -sk --http1.1 --fail -X POST -H 'Content-Type: application/json' -H 'Origin: https://prism.local' -d '{\"keep_count\":3}' https://prism.local/api/server/backup/rotate
SCRIPT
sudo chmod +x /home/mask070924/prism/scripts/auto-backup.sh
sudo chown mask070924:mask070924 /home/mask070924/prism/scripts/auto-backup.sh"

# 安裝 systemd service + timer
ssh PI5Mask24 "sudo tee /etc/systemd/system/prism-backup.service > /dev/null <<'EOF'
[Unit]
Description=Prism weekly auto-backup (download + rotate)
After=network.target prism.service
Wants=prism.service

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

# 驗證 + 立即跑一次
ssh PI5Mask24 "systemctl list-timers --no-pager | grep prism && sudo systemctl start prism-backup.service && ls -lt /home/mask070924/prism/backups/ | head -3"
```

**還原備份**：

```bash
# 在 Pi 上
sudo systemctl stop prism
cp /home/mask070924/prism/backups/prism_backup_YYYYMMDD_HHMMSS.db /home/mask070924/prism/knowledge.db
# 清掉 WAL（避免半寫狀態）
rm -f /home/mask070924/prism/knowledge.db-wal /home/mask070924/prism/knowledge.db-shm
sudo systemctl start prism
```

---

## 驗證

```bash
# 確認服務正常、port 正確
ssh PI5Mask24 "sudo systemctl status prism --no-pager | grep -E 'Active|Port'"

# 確認 API 回應（需通過 Caddy HTTPS）
ssh PI5Mask24 "curl -sk https://prism.local/api/system/stats | python3 -c 'import sys,json; d=json.load(sys.stdin); print(\"notes:\", d[\"data\"][\"database\"][\"notes_count\"])'"
```

---

## 已排除的檔案（不會覆蓋 Pi 上的版本）

| 路徑 | 原因 |
|------|------|
| `knowledge.db` | 使用者資料，絕不覆蓋 |
| `static/uploads/` | 使用者上傳圖片，絕不覆蓋 |
| `.port_config` | Pi 獨立設定，不同步 |
| `python/` | Windows venv，與 Pi 不相容 |
| `frontend/node_modules/` | 不需要（Pi 使用 build 後的 `frontend/dist/`） |
| `frontend/src/` | 原始碼，Pi 使用編譯產出 |
| `app.log` | Pi 有自己的日誌 |
| `.env` | 機敏設定，不同步 |

---

## 常用維運指令

```bash
# 查看即時日誌
ssh PI5Mask24 "sudo journalctl -u prism -f"

# 重啟服務
ssh PI5Mask24 "sudo systemctl restart prism"

# 查看 port 使用狀況
ssh PI5Mask24 "sudo ss -tlnp | grep -E '5000|5001|5002'"

# 查看 Caddy 狀態
ssh PI5Mask24 "sudo systemctl status caddy --no-pager"

# 手動安裝新套件到 Pi venv
ssh PI5Mask24 "cd /home/mask070924/prism && linux-venv/bin/pip install -r requirements-pi.txt"
```

---

## 已知問題與解決方案

### Port 重啟後跳到錯誤號碼

**症狀**：重啟後 Prism 用 5002 而非 5000，Caddy 無法代理。

**根因**：`find_available_port()` 的 test socket 未設 `SO_REUSEADDR`，服務剛停止時 port 在 TIME_WAIT 狀態，誤判為被佔用。

**修法**（已在 v2.4.2 修正）：`app.py` 的測試 socket 加入 `s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)`。

**臨時解法**（舊版）：等待 60 秒讓 TIME_WAIT 消退，再重啟。

---

### `python-magic-bin` 安裝失敗

**症狀**：`pip install -r requirements.txt` 在 Pi 上報錯 `No matching distribution`。

**原因**：`requirements.txt` 含 Windows 專用二進位套件 `python-magic-bin`。

**解法**：Pi 上改用 `requirements-pi.txt`（使用 `python-magic`，依賴 `apt install libmagic1`）。

---

**文件版本**：v2.4.7 / 2026-05-13
