# Prism Desktop Portable

This folder is the Windows desktop portable package.

## Run

Double-click `Prism.exe`.

`Prism.exe` is built as a Windows GUI executable and starts the Prism desktop shell directly: the Go runtime runs in the same process and the UI opens in WebView2 at a local `127.0.0.1` address.

For diagnostics, run `PrismDesktop-debug.exe` from PowerShell. It keeps a console window and accepts the same flags:

```powershell
.\PrismDesktop-debug.exe --data-dir "$env:LOCALAPPDATA\Prism\DesktopData" --addr 127.0.0.1:5015
```

## Data

User data is not stored in this package folder.

If no `--data-dir` is provided, Prism Desktop uses:

```text
%LOCALAPPDATA%\Prism\DesktopData
```

The data directory contains the desktop database (`prism_desktop_dev.db`), uploads, attachments, config, backups, and logs. Desktop shell logs are written to:

```text
<data-dir>\logs\desktop-shell.log
```

## Requirement

Microsoft Edge WebView2 Runtime must be installed on the machine. If WebView2 is missing, the desktop shell exits with a diagnostic error in the debug console or desktop log. This portable package does not install WebView2 Runtime and is not an MSI/NSIS/WiX installer.

## Boundaries

- No installer or auto updater is included.
- No local production database is bundled.
- Raspberry Pi deployment is separate and still uses the linux/arm64 Go primary artifact, systemd, Caddy, and `DEPLOY-PI.md`.
