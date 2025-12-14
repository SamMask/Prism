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

---

## 系統需求

- Python 3.8+
- SQLite 3.x
- 依賴套件請參考 `requirements.txt`

## 安裝步驟

1. 安裝依賴套件:

```bash
pip install -r requirements.txt
```

2. 設定環境變數 (參考上方說明)

3. 執行應用程式:

```bash
python app.py
```

4. 開啟瀏覽器訪問:

```
http://localhost:5000
```

---

**版本**: v1.4.1
**更新日期**: 2025-12-15
**安全性增強**: 環境變數控制 Debug 模式
