# Prism

[English](README.md) | [繁體中文](README.zh-TW.md)

> Local-first, offline-capable personal knowledge management and prompt tooling.
> Current release path: Go primary runtime, Raspberry Pi service deployment, and Windows desktop portable zip.

![Version](https://img.shields.io/badge/version-2.4.9-blue)
![Runtime](https://img.shields.io/badge/runtime-Go%20primary-green)
![Frontend](https://img.shields.io/badge/react-18-61dafb)
![License](https://img.shields.io/badge/license-MIT-yellow)

Prism stores your notes, prompts, attachments, tags, and history in a local SQLite database. It deliberately avoids built-in AI, cloud sync, telemetry, and public-internet assumptions. External agents can talk to Prism through a clean REST API; Prism focuses on durable storage, fast keyword search, and predictable local operations.

## Current Status

- **Runtime**: Go primary is the only product runtime. The Python Flask backend source was removed in T053.
- **Windows desktop**: `Prism.exe` is the primary Windows portable entry. It starts the Go runtime in the same process and opens the UI in WebView2.
- **Portable data**: the Windows portable package stores user data next to the executable in `PrismData\` by default.
- **Raspberry Pi**: Pi deployment remains a separate headless Go artifact path using `prism-go-primary.service`, Caddy, and `DEPLOY-PI.md`.
- **Language**: a fresh browser follows the OS/browser language for Traditional/Simplified Chinese, English, Japanese, and Korean; both Simplified and Traditional Chinese resolve to Traditional Chinese (`zh-TW`). Other languages default to English. Manual changes in Settings > Appearance are persisted in `localStorage`.

## Download

Use the latest GitHub Release asset:

- `PrismDesktopPortable-v2.4.9.zip` - Windows desktop portable package

The portable package includes:

- `Prism.exe` - GUI desktop app
- `PrismDesktop-debug.exe` - console build for diagnostics
- `Prism.ico`
- `README-PORTABLE.md`
- seed config under `static/config/`

Microsoft Edge WebView2 Runtime must already be installed. If the machine does not have it, install it from Microsoft's official [Download Microsoft Edge WebView2](https://developer.microsoft.com/microsoft-edge/webview2/consumer/) page. The portable package does not install WebView2 and is not an MSI/NSIS/WiX installer.

## Quick Start

### Windows Portable

1. Download `PrismDesktopPortable-v2.4.9.zip` from Releases.
2. Extract it anywhere.
3. Double-click `Prism.exe`.

Data is created in:

```text
<Prism.exe folder>\PrismData
```

For diagnostics:

```powershell
.\PrismDesktop-debug.exe --data-dir "D:\PrismData" --addr 127.0.0.1:5015
```

### Go Primary Local Runtime

```powershell
cd D:/AI/Prism
.\scripts\build_go_runtime.ps1
.\scripts\start_go_primary.ps1
```

Local service:

```text
http://127.0.0.1:5004
```

### Frontend Development

```bash
cd frontend
npm install
npm run dev
```

## Core Features

- **Headless KMS REST API** - notes, tags, categories, attachments, import/export, maintenance, and server/system surfaces are Go-owned.
- **Fast keyword search** - SQLite FTS5 plus remarks, tags, attachment metadata, and bounded text attachment body search.
- **React SPA** - React 18, TypeScript, Vite, Zustand, Tailwind CSS, local assets only.
- **Prompt Builder** - structured prompt options and wizard config seeded into a fresh data directory.
- **Attachments** - Markdown/text attachments and local upload handling.
- **Lineage and history** - note variants, parent relationships, and note history restore.
- **Maintenance tools** - manual FTS integrity check/rebuild, WAL checkpoint, backup operations, and server dashboard.
- **Local privacy** - no cloud service, telemetry, embedding pipeline, or bundled AI dependency.

## Architecture

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

Go primary embeds and serves the built SPA. Windows desktop mode wraps the same local web UI in WebView2 and starts the Go server in the same process. Pi deployment stays headless and uses Caddy as the local reverse proxy.

## Safety Boundary

Prism currently has no built-in user login, bearer token, or public API authentication layer. Run it on localhost, trusted LAN, VPN, SSH tunnel, or behind an authenticated reverse proxy. Do not expose the raw Go runtime or Caddy entrypoint directly to the public internet.

## Documentation

| Need | Document |
|---|---|
| Documentation hub | [`docs/README.md`](docs/README.md) |
| Current roadmap and next entry | [`docs/TODO.md`](docs/TODO.md) |
| Architecture | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) |
| API reference | [`docs/API_REFERENCE.md`](docs/API_REFERENCE.md) |
| Database schema | [`docs/SCHEMA.md`](docs/SCHEMA.md) |
| Raspberry Pi deployment | [`DEPLOY-PI.md`](DEPLOY-PI.md) |
| Windows portable notes | [`docs/desktop/README-PORTABLE.md`](docs/desktop/README-PORTABLE.md) |
| Development handoff | [`HANDOFF.md`](HANDOFF.md) |

## Development and Verification

Prism's product runtime is Go. Python is used only for repository test
orchestration through `pytest`; it is not a backend runtime or Windows portable
runtime dependency.

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

Build the Windows portable package:

```powershell
.\scripts\build_desktop_portable.ps1 -OutputDir build/release -PackageName PrismDesktopPortable-v2.4.9
```

## License

MIT License. See [`LICENSE`](LICENSE).
