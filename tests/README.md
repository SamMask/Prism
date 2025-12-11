# 測試腳本

此目錄包含專案開發過程中的功能驗證與安全性測試腳本。

## 重要的測試腳本

- **test_upload_security.py**: 安全性測試。驗證系統是否能正確阻擋偽裝成圖片的惡意檔案（Magic Number 檢查）。
- **test_pagination.py**: 壓力測試。建立大量筆記來測試分頁效能與邏輯。

## 其他腳本

- **test_reorder.py**: 驗證拖放排序 API。
- **test_offline_mode.py**: 驗證靜態資源是否本地化（注意：需更新路徑以適應新的 template 架構，目前針對 v1.8.8 以前版本）。
- 測試 Jinja2 分隔符相關腳本 (`test_separator*.py`): 用於開發初期解決 Vue 與 Jinja2 語法衝突問題。
- **test_sql.py**, **test_tags_filter.py**: 簡單的資料庫與過濾邏輯驗證。

**使用說明**:
由於移入此目錄，執行腳本時可能需要將根目錄加入 `PYTHONPATH`，或將腳本移回根目錄執行。
例如：

```bash
set PYTHONPATH=..
python test_upload_security.py
```
