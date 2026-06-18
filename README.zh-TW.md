# Prism

[English](README.md) | [繁體中文](README.zh-TW.md)

> 本地優先、離線可用的個人知識中樞與 Prompt 工具。
> 目前發行主路徑：Go primary runtime、Raspberry Pi service 部署、Windows desktop portable zip。

![Version](https://img.shields.io/badge/version-2.5-blue)
![Runtime](https://img.shields.io/badge/runtime-Go%20primary-green)
![Frontend](https://img.shields.io/badge/react-18-61dafb)
![License](https://img.shields.io/badge/license-MIT-yellow)

Prism 把筆記、Prompt、附件、標籤與歷史版本存在本機 SQLite。它刻意不內建 AI、雲端同步、遙測或 public internet 假設。外部 Agent 可以透過乾淨的 REST API 對接；Prism 專心做好穩定儲存、快速關鍵字搜尋與可預期的本機操作。

## 目前狀態

- **Runtime**：Go primary 是唯一產品 runtime；Python Flask backend source 已於 T053 移除。
- **Windows desktop**：`Prism.exe` 是目前 Windows portable 主入口；同一行程內啟動 Go runtime，並用 WebView2 開啟 UI。
- **Portable data**：Windows portable 預設把使用者資料放在 exe 同層 `PrismData\`。
- **Raspberry Pi**：Pi 部署仍是獨立 headless Go artifact 路線，使用 `prism-go-primary.service`、Caddy 與 `DEPLOY-PI.md`。
- **語系**：新使用者預設英文。到「設定 > 外觀」手動切換後會存在 `localStorage`；目前提供繁體中文、英文、日文、韓文。

## 下載

請使用最新 GitHub Release asset：

- `PrismDesktopPortable-v2.5.zip` - Windows desktop portable package

Portable package 內容：

- `Prism.exe` - GUI desktop app
- `PrismDesktop-debug.exe` - 診斷用 console build
- `Prism.ico`
- `README-PORTABLE.md`
- `static/config/` seed config

目標機器需要已安裝 Microsoft Edge WebView2 Runtime。如果電腦沒有 WebView2，請到 Microsoft 官方 [Download Microsoft Edge WebView2](https://developer.microsoft.com/microsoft-edge/webview2/consumer/) 頁面下載安裝。此 portable package 不會安裝 WebView2，也不是 MSI/NSIS/WiX 安裝包。

## 快速開始

### Windows Portable

1. 從 Releases 下載 `PrismDesktopPortable-v2.5.zip`。
2. 解壓到任意資料夾。
3. 雙擊 `Prism.exe`。

資料會建立在：

```text
<Prism.exe folder>\PrismData
```

診斷模式：

```powershell
.\PrismDesktop-debug.exe --data-dir "D:\PrismData" --addr 127.0.0.1:5015
```

### Go Primary 本機 Runtime

```powershell
cd D:/AI/Prism
.\scripts\build_go_runtime.ps1
.\scripts\start_go_primary.ps1
```

本機服務：

```text
http://127.0.0.1:5004
```

### 前端開發

```bash
cd frontend
npm install
npm run dev
```

## 核心特色

- **Headless KMS REST API**：notes、tags、categories、attachments、import/export、maintenance、server/system surface 皆由 Go 擁有。
- **快速關鍵字搜尋**：SQLite FTS5 + 備註、標籤、附件 metadata、bounded 文字附件內容搜尋。
- **React SPA**：React 18、TypeScript、Vite、Zustand、Tailwind CSS，前端資源本地化。
- **Prompt Builder**：結構化 prompt options 與 wizard config，fresh data-dir 可由 package seed。
- **附件系統**：Markdown/text 附件與本機 upload handling。
- **譜系與歷史**：note variant、parent relationship、history restore。
- **維護工具**：手動 FTS integrity check/rebuild、WAL checkpoint、backup operations、Server Dashboard。
- **本地隱私**：無雲端、無遙測、無 embedding pipeline、無 bundled AI dependency。

## 架構

```text
Browser / WebView2
        |
React SPA (Vite)
        |
Go Primary REST API
        |
SQLite (WAL) + external data directory
        |
uploads / attachments / logs / backups / config
```

Go primary 會嵌入並服務建置後的 SPA。Windows desktop 模式用 WebView2 包住同一套本機 Web UI，並在同一行程啟動 Go server。Pi 部署維持 headless，使用 Caddy 作本機 reverse proxy。

## 安全邊界

Prism 目前沒有內建使用者登入、Bearer Token 或 public API auth layer。請在 localhost、trusted LAN、VPN、SSH tunnel，或受認證保護的 reverse proxy 後使用。不要把 raw Go runtime 或 Caddy entrypoint 直接暴露到 public internet。

## 文件

| 想做的事 | 文件 |
|---|---|
| 文檔中心 | [`docs/README.md`](docs/README.md) |
| Current roadmap / next entry | [`docs/TODO.md`](docs/TODO.md) |
| 架構 | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) |
| API 參考 | [`docs/API_REFERENCE.md`](docs/API_REFERENCE.md) |
| DB schema | [`docs/SCHEMA.md`](docs/SCHEMA.md) |
| Raspberry Pi 部署 | [`DEPLOY-PI.md`](DEPLOY-PI.md) |
| Windows portable 說明 | [`docs/desktop/README-PORTABLE.md`](docs/desktop/README-PORTABLE.md) |
| 開發接手 | [`HANDOFF.md`](HANDOFF.md) |

## 開發與驗證

Prism 的產品 runtime 是 Go。Python 只用在 repo 開發測試流程，透過 `pytest`
執行回歸測試；它不是 backend runtime，也不是 Windows portable 的執行依賴。

```bash
# Go runtime tests
cd go-shadow
go test ./...
```

```bash
# Frontend type-check and build
cd frontend
npm run build
```

```bash
# Python dev/test-only regression suite
pytest tests/ -v
```

建置 Windows portable package：

```powershell
.\scripts\build_desktop_portable.ps1 -OutputDir build/release -PackageName PrismDesktopPortable-v2.5
```

## 授權

MIT License。見 [`LICENSE`](LICENSE)。
