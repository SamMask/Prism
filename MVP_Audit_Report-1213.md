# MVP 技術審查報告

**日期**: 2025-12-13
**版本**: 1.0 (審查 Local Insight v1.8.9/v1.0 代碼庫)
**審查員**: Antigravity (Google Deepmind)

本報告概述了 MVP 級別技術審查的發現。重點關注「致命邏輯」(Blockers)、「架構完整性」、「高風險漏洞」和「資料結構」。

---

## 🛑 [紅燈] 阻斷性問題 (必須修復) //已處理

這些問題代表安全或核心功能的重大風險，**必須在任何公開使用或發布前解決**。

### 1. 未經身份驗證的遠端存取風險 (嚴重安全問題)

- **嚴重性**: **嚴重 (Critical)**
- **位置**: `app.py` 第 442 行 (`app.run(host='0.0.0.0', ...)`)
- **問題**: 應用程式預設綁定到 `0.0.0.0`。這將網頁介面和 API 暴露給整個區域網路 (LAN)。
- **風險**: 由於應用程式**沒有身份驗證機制** (無登入、無密碼)，**任何**在同一 Wi-Fi 連線上的人 (例如咖啡廳、辦公室) 都可以：
  - 讀取所有個人筆記。
  - 透過 API 刪除所有資料。
  - 上傳惡意檔案 (儘管執行受到緩解，但儲存沒有)。
- **修復**: 將預設 host 更改為 `127.0.0.1` 以限制僅本機存取。如果需要 LAN 存取，則必須實作身份驗證。

### 2. 缺少 CSRF 防護

- **嚴重性**: **高 (High)**
- **位置**: 全域 (API 路由)
- **問題**: 沒有 CSRF (跨站請求偽造) 防護 (例如：無 CSRF token、嚴格的 `SameSite` cookie 策略或 Origin 檢查)。
- **風險**: 如果使用者在執行 `Local Insight` 時訪問了惡意網站，惡意網站可以在使用者不知情的情況下發送背景請求至 `http://localhost:5000/api/notes/delete/...` 來刪除資料。
- **修復**: 實作 `Flask-WTF` CSRF 保護，或在全球 `before_request` hook 中進行簡單的 `Origin/Referer` 標頭驗證。

---

## ⚠️ [黃燈] 風險與技術債 //以後再說

這些問題不會阻止應用程式運行，但會造成維護困難、資料一致性風險或邏輯脆弱。

### 1. 資料架構「雙重事實」 (資料完整性)

- **位置**: 資料庫架構 (`Notes` 表)
- **問題**: `Notes` 表同時儲存 `category_id` (外鍵) 和 `type` (文字)。應用程式邏輯 (`crud.py`, `app.py`) 在這兩個事實來源之間搖擺不定。
  - `get_notes` 優先使用 `Categories.name` 但回退到 `Notes.type`。
  - `create_note` 同時寫入兩者。
  - `auto_fix_consistency` 試圖在啟動時同步它們。
- **風險**: 如果「自動修復」失敗或發生手動 DB 編輯，`type` 和 `category_id` 可能會脫鉤，導致微妙的 Bug。
- **建議**: 計劃在 v1.1 中棄用 `type` 文字欄位，並完全依賴 `category_id`。

### 2. 重複的資料庫邏輯 (可維護性)//不動

- **位置**: `app.py` vs `db.py`
- **問題**: `get_db()` 在**兩個**檔案中都有定義。
  - `app.py` (第 97-112 行): 用於初始化。
  - `db.py` (第 14-49 行): 用於路由。
- **風險**: `db.py` 擁有更好的邏輯 (顯式管理隔離級別和 FK 檢查)。`app.py` 的版本略有不同。可能導致潛在的 DB 行為不一致。
- **建議**: 重構 `app.py` 以從 `db.py` 匯入 `get_db`。

### 3. 冗餘的手動串聯刪除 (代碼膨脹)

- **位置**: `notes/crud.py` 屬性 `delete_note`
- **問題**: 代碼在刪除 Note 之前手動刪除 `Note_History`, `Note_Tags` 等。然而，資料庫架構 (`app.py`, `db.py`) 已顯式定義 `ON DELETE CASCADE`。
- **風險**: 冗餘代碼增加了維護面。
- **建議**: 驗證 FK 支援是否可靠 (這是 `db.py` 會檢查的)，並移除手動子項目刪除以簡化邏輯。

---

## 💡 [建議] 架構修正

### 簡化邏輯圖 (針對紅燈修復 #1)

與其硬編碼 `0.0.0.0`，不如將其設為可配置但預設安全。

```python
# app.py 建議

if __name__ == '__main__':
    # ... logic ...

    # 為了安全，預設使用 localhost
    host = os.environ.get('HOST', '127.0.0.1')

    # 只有在顯式啟用時才允許 0.0.0.0 (最好警告使用者)
    if host == '0.0.0.0':
         print("[WARNING] Binding to all interfaces. Ensure you trust this network!")

    app.run(host=host, port=port, ...)
```

### CSRF 緩解 (極簡方法)

對於沒有重型框架的 MVP，簡單的 Origin 檢查中介軟體對大多數 CSRF 攻擊都有效。

```python
# app.py middleware

@app.before_request
def csrf_protect():
    if request.method != "GET":
        # 僅允許來自同源的請求
        origin = request.headers.get('Origin')
        referer = request.headers.get('Referer')
        # 驗證 origin 是否匹配 request.host_url 的邏輯
```

## 總結

專案功能大部分運作正常，且結構良好，採用現代模組化設計 (Blueprints, Vue Composables)。**DOMPurify** 和 **SQL 參數化** 的實作非常優秀。然而，**0.0.0.0 綁定** 對於個人、無身份驗證的工具來說是一個致命的安全缺陷，必須立即修復。
