# Prism - 部署指南

## 環境變數設定

### FLASK_DEBUG (必要設定)

控制 Flask 應用程式的 Debug 模式，影響系統安全性。

**預設值**: `False` (安全)

**開發環境設定** (啟用 Debug 模式):

Windows (CMD):

```cmd
set FLASK_DEBUG=True
python app.py
```

Windows (PowerShell):

```powershell
$env:FLASK_DEBUG = "True"
python app.py
```

Linux / macOS:

```bash
export FLASK_DEBUG=True
python app.py
```

**生產環境設定** (關閉 Debug 模式):

Windows (CMD):

```cmd
set FLASK_DEBUG=False
python app.py
```

Windows (PowerShell):

```powershell
$env:FLASK_DEBUG = "False"
python app.py
```

Linux / macOS:

```bash
export FLASK_DEBUG=False
python app.py
```

或直接執行（預設為 False）:

```bash
python app.py
```

---

## 安全性提醒

⚠️ **重要**: 生產環境必須關閉 Debug 模式

Debug 模式啟用時會產生以下風險:

- 暴露敏感的系統資訊和堆疊追蹤
- 允許執行任意程式碼 (RCE 風險)
- 自動重載功能會消耗額外資源
- 錯誤頁面可能洩露應用程式內部結構

**建議做法**:

1. 生產環境永遠設定 `FLASK_DEBUG=False` 或不設定環境變數
2. 開發環境才設定 `FLASK_DEBUG=True`
3. 使用 WSGI 伺服器 (如 Gunicorn, uWSGI) 部署生產環境，而非 `app.run()`

### API 暴露邊界

Prism API 目前沒有內建 API Token / Bearer Token / 使用者認證機制，預設適合 `localhost`、trusted LAN、VPN，或 SSH tunnel / 受認證保護的 reverse proxy 使用。不要把 Flask 服務或 Caddy 入口直接暴露到 public internet / 公網。

若需要遠端存取，請先在外層加入 VPN、SSH tunnel、reverse proxy auth（例如 Caddy auth）或等效保護；Prism 內部尚未實作 OAuth、JWT、API key、RBAC 或使用者系統。

---

## 系統需求

- Python 3.10+
- Node.js 18+（僅開發 / 重新建置前端時需要）
- SQLite 3.x（內建）
- 依賴套件請參考 `requirements.txt`

> **目前穩定主線**: v2.4.9 推薦使用 Source / Dev mode，或依本文件與 `DEPLOY-PI.md` 走本機 / Raspberry Pi 部署。Portable / PyInstaller / 一鍵啟動仍屬後續發佈目標或內部打包流程；除非 repo / GitHub Releases 已提供正式 artifacts，請不要把它當作目前推薦安裝方式。

## 安裝步驟

### 本機整合模式（使用預建置前端）

1. 建置前端:

```bash
cd frontend
npm install
npm run build
cd ..
```

2. 安裝 Python 依賴:

```bash
pip install -r requirements.txt
```

3. 設定環境變數（參考上方說明）

```bash
set PRISM_V2=true      # Windows
export PRISM_V2=true   # Linux / macOS
```

4. 執行應用程式:

```bash
python app.py
```

5. 開啟瀏覽器訪問:

```
http://localhost:5000
```

### 開發環境（前後端分離）

```bash
# 終端機 1：後端
python app.py

# 終端機 2：前端 (Vite HMR)
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

### 重新建置前端

```bash
cd frontend
npm run build
# 建置產出至 frontend/dist/，由 Flask 靜態服務
```

---

## 🍓 樹莓派 / 無頭伺服器部署 (Phase 8.1)

> **目標**: 在區域網路內以 `https://prism.local` 存取 Prism，無需記 IP 或 Port。
> **前提**: Raspberry Pi OS (Debian-based) 或任何支援 systemd 的 Linux。
> **安全邊界**: `prism.local` / Caddy 部署預設是 trusted LAN 用途；不要將 443 / 5000 直接 port-forward 到公網，除非外層已有 VPN、SSH tunnel 或受認證保護的 reverse proxy。
>
> **詳細操作步驟（含日常更新）請見根目錄 [`DEPLOY-PI.md`](../DEPLOY-PI.md)**。

### Pi 一鍵安裝（首次）

```bash
cd /path/to/prism
bash deploy/raspberry_pi/setup.sh
```

腳本自動完成以下步驟（冪等，可重複執行）：

| 步驟 | 工具 | 效果 |
|------|------|------|
| 1 | `avahi-daemon` | 讓區網裝置可 ping `prism.local` |
| 2 | `Caddy` | 443 (HTTPS/TLS internal) → localhost:5000 反向代理 |
| 3 | `systemd` | 開機自動啟動 Prism |

設定完成後，區網內任何裝置皆可直接開啟：

```
https://prism.local
```

### Linux venv（必要，v2.4.2+）

> `requirements.txt` 包含 Windows 專用套件 `python-magic-bin`，**不可在 Pi 上使用**。
> Pi 必須使用 `requirements-pi.txt` + `linux-venv/`。

```bash
# 在 Pi 上執行（首次）
sudo apt-get install -y libmagic1 python3-venv
python3 -m venv linux-venv
linux-venv/bin/pip install -r requirements-pi.txt
```

systemd service 的 `ExecStart` 必須指向：
```
ExecStart=/home/<user>/prism/linux-venv/bin/python app.py
```

### Port 設定（`.port_config`）

`.port_config` 必須為 **JSON 格式**：

```json
{"preferred_port": 5000, "fallback_enabled": true, "fallback_range": 20}
```

> ⚠️ 不可寫成純數字（`5000`）——解析失敗會靜默回退，可能佔用錯誤 port 導致 Caddy 無法代理。

### 常用維運指令

```bash
sudo systemctl status prism          # 查看 Prism 狀態
sudo journalctl -u prism -f          # 即時查看 Prism 日誌
sudo systemctl restart prism         # 重啟 Prism
sudo systemctl status caddy          # 查看 Caddy 代理狀態
sudo ss -tlnp | grep -E '5000|5001'  # 確認 port 占用狀況
```

---

**版本**: v2.4.2
**更新日期**: 2026-04-12
**更新內容**: Linux venv 說明、`.port_config` JSON 格式要求、DEPLOY-PI.md 參照
