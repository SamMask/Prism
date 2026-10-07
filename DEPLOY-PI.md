# 部署更新到樹莓派 (Deploy to Raspberry Pi)

> **目前 live owner**: Go primary runtime
> **Pi 主機名稱**: `PI5Mask24`
> **Pi 路徑**: `/home/mask0709/prism/`
> **存取網址**: `https://prism.local`

> ⚠️ **安全邊界**: Prism API / Go runtime has no built-in auth/token layer，沒有內建 API Token、Bearer Token 或使用者認證。Pi + Caddy 部署預設是 `localhost` / trusted LAN / VPN 用途；不要將 Caddy 或 Go 入口直接 port-forward 到 public internet。遠端存取請放在 VPN、SSH tunnel 或受認證保護的 reverse proxy 後面。
>
> **管理端點對 LAN 的實際範圍（PRISM-OPT-29）**：
> - Go 的 loopback 檢查只看 TCP 連線的 peer。Caddy 以 `reverse_proxy 127.0.0.1:5004` 轉進來的請求一律來自 loopback，所以能連到 `prism.local` 的 LAN 裝置也能使用以下功能：`/api/server/*`（備份下載、建立、還原、刪除，log，重新啟動，硬體與版本資訊）、`GET /api/export/full-snapshot`、`POST /api/system/inline-separated-notes`。
> - 筆記的讀寫、刪除、JSON 匯出與 DB 下載本來就沒有限制。
> - 2026-10-07 使用者決定不在程式內收緊。若 LAN 內有不信任的裝置（訪客 Wi-Fi、共用網路），請在 Caddy 加上 `basic_auth`；這樣筆記與管理功能會一起受到保護。

---

## 快速更新（日常使用）

日常 live 部署使用 Go primary ops script；它會建置 linux/arm64 artifact、上傳到 Pi、建立 pre-cutover backup/data snapshot、更新 `prism-go-primary.service`，並讓 Caddy 繼續指向 `127.0.0.1:5004`。部署 snapshot 位於 `/home/mask0709/prism/backups/go-primary-*/data-files.tar.gz`，預設只保留最新 5 份；舊 snapshot 會在 cutover smoke 通過後自動清理。

```powershell
# 在 Windows repo root 執行
powershell -ExecutionPolicy Bypass -File scripts/go_primary_pi_live_ops.ps1 -Mode Cutover
```

已確認 artifact 可重用時：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/go_primary_pi_live_ops.ps1 -Mode Cutover -SkipBuild
```

若需要調整 deploy snapshot 保留數，只允許 3-5 份：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/go_primary_pi_live_ops.ps1 -Mode Cutover -DeploySnapshotKeep 5
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

首次設定也以 Go primary 為唯一產品啟動路徑。建議優先從 Windows repo root 執行 Go cutover：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/go_primary_pi_live_ops.ps1 -Mode Cutover
```

如需在 Pi 上重新建立 mDNS / Caddy / systemd 範本，可在 artifact 已存在於 `/home/mask0709/prism/go-primary-live/bin/prism-go-runtime-linux-arm64` 後執行：

```bash
ssh PI5Mask24 "cd /home/mask0709/prism && bash deploy/raspberry_pi/setup.sh"
```

`deploy/raspberry_pi/setup.sh` 會：

- 安裝 / 設定 `avahi-daemon`
- 首次安裝時建立 Prism Caddy route；若已有共用 Caddyfile，只在既有 `prism.local → 127.0.0.1:5004` route 正確時保留不動，否則拒絕覆寫並要求人工合併
- 建立並啟用 `prism-go-primary.service`
- 停用 legacy `prism.service`；rollback 只回到上一版 Go artifact 與 pre-cutover snapshot

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

## Go primary live（Go-only cutover / rollback / soak）

`scripts/go_primary_pi_live_ops.ps1` 預設執行 `Cutover`。它先保留目前 Go binary、DB、uploads/attachments、Caddyfile 與 Go systemd unit，再安裝新 artifact。`Rollback` 只還原該 pre-cutover snapshot 與上一版 Go binary，不會啟動 Python。`Soak` 只檢查目前已在 live 的 Go primary，不再隱含執行第二次 cutover。

```powershell
# 日常部署（也是預設 mode）
powershell -ExecutionPolicy Bypass -File scripts/go_primary_pi_live_ops.ps1 -Mode Cutover -SkipBuild

# 回到最近一次 Cutover 保存的上一版 Go artifact + data snapshot
powershell -ExecutionPolicy Bypass -File scripts/go_primary_pi_live_ops.ps1 -Mode Rollback -SkipBuild

# 對目前 live Go primary 做 bounded soak
powershell -ExecutionPolicy Bypass -File scripts/go_primary_pi_live_ops.ps1 -Mode Soak -SkipBuild
```

目前 final live state：

- `prism-go-primary.service`: active/enabled，監聽 `127.0.0.1:5004`
- `prism.service`: inactive/disabled，不是 rollback target
- `prism-go-readonly.service`: inactive/disabled；Caddy 與備份皆不依賴它
- Caddy `https://prism.local`: proxy 到 Go primary，回應帶 `X-Prism-Go-Primary: hit`
- `PRISM_GO_ALLOW_PUBLIC_BIND` 未啟用；仍只適合 trusted LAN/VPN/proxy-auth 邊界
- Python packaged runtime、product startup path 與 backend source 已由 T045/T053 移除
- T051/T052 已同步 route/API/docs current truth 並清理 tracked stale packaging artifacts；Pi data paths 仍不被 package/deploy 覆蓋

證據會回收到本機：

- `build/go-primary-live/pi/evidence.json`
- `build/go-primary-live/pi/t042-full-workflow.json`
- `build/go-primary-live/pi/t043-rollback.json`
- `build/go-primary-live/pi/t044-soak.json`

`Rollback` 必須找到最近一次新制 `Cutover` evidence 中登記的 previous Go binary 與 snapshot；舊版只保存 Python rollback evidence 的 T042/T043 snapshot 不符合條件時會安全拒絕，不會猜測還原來源。

---

## 自動備份排程

每週日 03:00 透過 Go primary server backup API 下載 DB backup 並輪替。這是 SQLite 一致 DB snapshot，會包含 request 當下 active WAL 的最新 DB 交易；但它仍只是 `knowledge.db` 備份，與部署前的 `go-primary-*/data-files.tar.gz` snapshot 不同。DB backup 不包含 `static/uploads/` / `docs/attachments/`，不能還原已從檔案系統刪掉的圖片或附件檔。

```bash
ssh PI5Mask24 "sudo tee /home/mask0709/prism/scripts/auto-backup.sh > /dev/null <<'SCRIPT'
#!/bin/bash
set -e
BACKUP_DIR=/home/mask0709/prism/backups
TS=\$(date +%Y%m%d_%H%M%S)
curl -sk --http1.1 --fail -o \"\$BACKUP_DIR/prism_backup_\$TS.db\" https://prism.local/api/server/backup/download
curl -sk --http1.1 --fail -X POST -H 'Content-Type: application/json' -H 'Origin: https://prism.local' -d '{\"keep_count\":3}' https://prism.local/api/server/backup/rotate
SCRIPT
sudo chmod +x /home/mask0709/prism/scripts/auto-backup.sh
sudo chown mask0709:mask0709 /home/mask0709/prism/scripts/auto-backup.sh"

ssh PI5Mask24 "sudo tee /etc/systemd/system/prism-backup.service > /dev/null <<'EOF'
[Unit]
Description=Prism weekly auto-backup (download + rotate)
After=network.target prism-go-primary.service
Wants=prism-go-primary.service

[Service]
Type=oneshot
User=mask0709
WorkingDirectory=/home/mask0709/prism
ExecStart=/home/mask0709/prism/scripts/auto-backup.sh
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
ssh PI5Mask24 "cp /home/mask0709/prism/backups/prism_backup_YYYYMMDD_HHMMSS.db /home/mask0709/prism/knowledge.db && rm -f /home/mask0709/prism/knowledge.db-wal /home/mask0709/prism/knowledge.db-shm"
ssh PI5Mask24 "sudo systemctl start prism-go-primary.service"
```

---

## 從 Full snapshot 還原

手上有 `prism_full_data_snapshot_YYYYMMDD_HHMMSS.zip`（Settings 的「資料與復原」分頁 > 「完整資料快照」卡片）、要還原到 Pi 時使用。Prism 不會自動還原 snapshot，這是手動程序，且會**取代** Pi 上的資料庫、uploads、attachments、notes 與 config。與 `docs/desktop/README-PORTABLE.md` 的同名段落步驟相同，差別只在路徑、指令與服務管理。

Pi 上的 data-dir 與 DB 來自 `prism-go-primary.service` 的 `ExecStart`（`--db /home/mask0709/prism/knowledge.db --data-dir /home/mask0709/prism`），服務使用者是 `mask0709`，服務固定監聽 `127.0.0.1:5004`。以下假設 snapshot 已放在 Pi 的 `/home/mask0709/restore/prism_full_data_snapshot.zip`（例如 `scp prism_full_data_snapshot_*.zip PI5Mask24:/home/mask0709/restore/prism_full_data_snapshot.zip`）。以下指令都在 Pi 上、同一個 shell 內執行（`ssh PI5Mask24` 後），因為後面的步驟會沿用這些變數：

```bash
DATA=/home/mask0709/prism
ZIP=/home/mask0709/restore/prism_full_data_snapshot.zip
SNAP=/home/mask0709/restore/snap        # 解壓目錄，必須是還不存在的新目錄
```

### 1. 關閉程式

```bash
sudo systemctl stop prism-go-primary.service
systemctl is-active prism-go-primary.service     # 必須印出 inactive
```

### 2. 備份目前的 data-dir

把會被取代的內容整份複製到備份目錄（含 `-wal` / `-shm`，`-a` 保留權限與擁有者）。複製失敗就不要繼續。磁碟空間要夠放 uploads 的一份副本（`du -sh $DATA/static/uploads`）。

```bash
BACKUP=$DATA/backups/pre-restore-$(date +%Y%m%d_%H%M%S)
mkdir -p "$BACKUP/docs" "$BACKUP/static"
cp -a $DATA/knowledge.db* "$BACKUP/"
cp -a $DATA/static/uploads "$BACKUP/static/"
cp -a $DATA/docs/attachments $DATA/docs/notes "$BACKUP/docs/"
cp -a $DATA/config "$BACKUP/"
echo "Backup folder: $BACKUP"        # 把這個路徑記下來，下面的「回復」要用
```

### 3. 解壓 snapshot

```bash
python3 -m zipfile -e "$ZIP" "$SNAP"
ls "$SNAP"
```

首選 `python3 -m zipfile -e`。`unzip "$ZIP" -d "$SNAP"` 也可用，但若 CJK 檔名異常，步驟 5 會報 MISSING，請改用 python3。

應看到 `database/`、`static/`、`docs/`、`config/`（選配資料夾可為空或不存在）與 `snapshot-manifest.json`。snapshot 內的資料庫是 `database/knowledge.db`。

### 4. 依路徑對應放回檔案（DB 檔名）

| snapshot 內 | Pi 上 |
|---|---|
| `database/knowledge.db` | `/home/mask0709/prism/knowledge.db`（Pi 的 DB 檔名就是 `knowledge.db`，不需改名；桌面版才需改成 `prism_desktop_dev.db`） |
| `static/uploads/**` | `/home/mask0709/prism/static/uploads/` |
| `docs/attachments/**` | `/home/mask0709/prism/docs/attachments/` |
| `docs/notes/**` | `/home/mask0709/prism/docs/notes/` |
| `config/**` | `/home/mask0709/prism/config/` |

**執行下面的指令前，先跑步驟 5 的驗證（對解壓出來的資料夾，也就是 `test_manifest "$SNAP" database/knowledge.db` 那行）；必須看到 `problems: 0` 才能繼續。** 下面的指令會刪掉 data-dir 內舊檔，只有在步驟 2 已有完整備份、且 snapshot 已驗證完整時才安全。

舊的 `knowledge.db-wal` 與 `knowledge.db-shm` **必須移除**。演練證實：舊的 `-wal` 只要留著，服務啟動後就會讀到舊資料。snapshot 的 DB 是一個一致的單檔，沒有 `-wal` / `-shm`。

```bash
rm -f "${DATA:?}"/knowledge.db "${DATA:?}"/knowledge.db-wal "${DATA:?}"/knowledge.db-shm
# rm -f 不會回報失敗，所以明確檢查（出現 STOP 就先排除原因，不要繼續）：
[ -e "$DATA/knowledge.db-wal" ] && echo "STOP: stale wal"
[ -e "$DATA/knowledge.db-shm" ] && echo "STOP: stale shm"
cp "$SNAP/database/knowledge.db" $DATA/knowledge.db

# 取代四個檔案資料夾（snapshot 內沒有的資料夾會被略過）
for rel in static/uploads docs/attachments docs/notes config; do
  if [ -d "$SNAP/$rel" ]; then
    rm -rf "${DATA:?}/${rel:?}"
    mkdir -p "$(dirname "$DATA/$rel")"
    cp -r "$SNAP/$rel" "$DATA/$rel"
  fi
done

# 權限與擁有者：服務以 mask0709 執行；若你用 sudo 或其他帳號操作，這一步不可省
sudo chown -R mask0709:mask0709 $DATA/knowledge.db $DATA/static/uploads $DATA/docs/attachments $DATA/docs/notes $DATA/config
ls -l $DATA/knowledge.db*
```

`$DATA/backups/`（備份與還原點）與 `.csrf_disabled` 標記不在 snapshot 裡，還原後仍是 Pi 原本的。`backups/` 內的還原點是還原前的資料，不要在還原後再套用。

### 5. 驗證 manifest 的 SHA-256

`snapshot-manifest.json` 對每個 payload 檔列出 `path`（正斜線）、`size_bytes` 與 `sha256`（小寫十六進位）。下面的函式在指定根目錄下逐檔重算（Pi OS 內建 `python3`）。先定義一次，再跑兩次：步驟 4 的指令之前對**解壓目錄**跑，之後對 **data-dir** 跑。第二個參數是資料庫在該根目錄下的相對位置：解壓目錄是 `database/knowledge.db`，data-dir 是 `knowledge.db`。

```bash
test_manifest() {
python3 - "$SNAP" "$1" "$2" <<'PY'
import hashlib, json, os, sys
snap, root, db_rel = sys.argv[1:4]
m = json.load(open(os.path.join(snap, "snapshot-manifest.json"), encoding="utf-8"))
bad = 0
for f in m["files"]:
    rel = db_rel if f["path"] == "database/knowledge.db" else f["path"]
    p = os.path.join(root, rel)
    if not os.path.isfile(p):
        print("MISSING ", f["path"]); bad += 1; continue
    if os.path.getsize(p) != f["size_bytes"] or hashlib.sha256(open(p, "rb").read()).hexdigest() != f["sha256"]:
        print("MISMATCH", f["path"]); bad += 1
print("checked", len(m["files"]), "files, problems:", bad)
PY
}
test_manifest "$SNAP" database/knowledge.db     # 步驟 4 之前：解壓目錄
# ... 執行步驟 4 的指令 ...
test_manifest "$DATA" knowledge.db              # 步驟 4 之後：還原後的 data-dir
```

兩次都是 `problems: 0` 代表 snapshot 完整、檔案也放回正確。有 `MISSING` 或 `MISMATCH` 就是 zip 損毀或解壓錯誤：停止；若已執行步驟 4，先照下面「回復」處理，再重新解壓。單檔手動比對可用 `sha256sum "$SNAP/database/knowledge.db"` 對照 manifest 內 `database/knowledge.db` 那筆。

### 6. 啟動並檢查 `migration-status`

```bash
sudo systemctl start prism-go-primary.service
sleep 3
systemctl is-active prism-go-primary.service
curl -s http://127.0.0.1:5004/api/system/migration-status
sudo journalctl -u prism-go-primary.service -n 40 --no-pager
```

預期：服務 `active`，回應 `status` 為 `success`、`data.current_version` 等於 `data.latest_version`、`data.pending` 為空陣列。若 snapshot 來自較舊版本，啟動時 runtime 可能已套用 migration，只要最後 `pending` 為空即可。從瀏覽器（`https://prism.local`）抽查：筆記數量、一篇長文、一個附件下載、筆記內的圖片。

### 回復（還原失敗時）

`$BACKUP` 就是步驟 2 印出的路徑。此備份放在 `$DATA/backups/` 內，只含被取代的那幾項，所以不能整個資料夾對調，要把內容 cp 回去（若是新的 shell，先重新設定 `DATA` 與 `BACKUP`）：

```bash
sudo systemctl stop prism-go-primary.service
rm -f "${DATA:?}"/knowledge.db "${DATA:?}"/knowledge.db-wal "${DATA:?}"/knowledge.db-shm
cp -a $BACKUP/knowledge.db* $DATA/
for rel in static/uploads docs/attachments docs/notes config; do
  rm -rf "${DATA:?}/${rel:?}"
  cp -a "$BACKUP/$rel" "$DATA/$rel"
done
sudo chown -R mask0709:mask0709 $DATA/knowledge.db* $DATA/static/uploads $DATA/docs/attachments $DATA/docs/notes $DATA/config
sudo systemctl start prism-go-primary.service
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

# 正式 runtime owner 應只有 5004；5000/5002 不應監聽
ssh PI5Mask24 "systemctl is-active prism-go-primary.service; systemctl is-active prism.service prism-go-readonly.service || true"
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
ssh PI5Mask24 "ls -l /home/mask0709/prism/go-primary-live/bin/prism-go-runtime-linux-arm64 /home/mask0709/prism/knowledge.db"
```

---

**文件版本**：PI-PATH-MIGRATION-01 / 2026-08-17
