# 測試套件 (Test Suite)

本目錄包含專案的自動化測試，框架為 **pytest**。

## 執行測試

```bash
# 標準執行方式（venv 已啟動）
pytest tests/ -v
```

實際通過數量以 `test_run.log`（專案根目錄）為準。

## 列出所有測試案例

```bash
pytest tests/ --collect-only
```

## 共用設定

- **設定檔**: `pytest.ini`（專案根目錄）
- **Fixtures**: `tests/conftest.py`（`app` / `client` / 記憶體測試資料庫）
