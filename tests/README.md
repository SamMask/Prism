# 測試腳本 (Test Suite)

本目錄包含專案的自動化測試腳本，已全面現代化為 **Pytest** 架構。

## Setup (設定)

- **框架**: `pytest`
- **設定檔**: `pytest.ini` (位於專案根目錄)
- **共用 Fixtures**: `conftest.py` (包含 `app`, `client`, 在記憶體中的測試資料庫設定)

## 測試檔案列表

| 檔案名稱                    | 說明               | 測試重點                                                    |
| :-------------------------- | :----------------- | :---------------------------------------------------------- |
| `test_upload_security.py`   | 檔案上傳安全性測試 | 驗證 Magic Number 檢查，防止偽裝的 EXE/HTML/Script 檔案上傳 |
| `test_pagination.py`        | 分頁邏輯測試       | 驗證 API 分頁參數 (`page`, `per_page`) 及邊界條件           |
| `test_tags_filter.py`       | 標籤過濾測試       | 驗證標籤清單 API 與前端整合格式                             |
| `test_sql.py`               | 資料庫邏輯測試     | 使用獨立環境驗證複雜 SQL 操作 (如筆記拖曳排序)              |
| `test_comma_tags.py`        | 特殊字元標籤測試   | 驗證含逗號的標籤 (如 "AI, ML") 能被正確儲存與讀取           |
| `test_batch_type_sync.py`   | 批量類型同步       | **BUG-001**: 批量修改類型同步 `category_id`                 |
| `test_batch_delete_images.py` | 批量刪除圖片     | 驗證批量刪除時關聯圖片清理                                  |
| `test_tags_merge.py`        | 標籤合併測試       | **BUG-002**: 標籤合併交易完整性                             |
| `test_categories.py`        | 分類 CRUD 測試     | 分類建立、重命名、刪除遷移                                  |
| `test_cleanup.py`           | 清理工具測試       | 孤兒圖片檢測、未使用縮圖                                    |
| `test_system.py`            | 系統維護測試       | VACUUM、一致性檢查、清空歷史                                |

## 如何執行測試 (Running Tests)

由於專案使用內嵌式 (Embedded) Python 環境，建議直接使用下列終端機指令執行：

```powershell
.\python\python.exe -m pytest
```

執行後應看到類似以下的輸出 (全綠燈 PASSED)：

```text
tests/test_comma_tags.py::test_comma_in_tags PASSED
tests/test_pagination.py::test_default_pagination PASSED
...
====================== 15 passed in 3.16s ======================
```
