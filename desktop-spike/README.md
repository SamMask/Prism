# Prism Desktop Shell Phase 0

This is an isolated Windows message-loop spike.

Scope:

- Empty Win32 window.
- Tray icon with `Show` and `Quit`.
- One message loop for both window messages and tray callbacks.
- Console build remains intentional for debugging.

Out of scope:

- WebView2.
- Prism Go server startup.
- Backend, API, schema, migration, deploy, production data, installer, updater.

Manual run:

```powershell
cd desktop-spike
go run .
```

Automated smoke:

```powershell
cd desktop-spike
go run . --self-test
```
