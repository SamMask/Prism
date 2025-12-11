# MVP Audit Report: Local Insight (2025-12-06)

## 1. 🚦 [紅燈] 阻斷性問題 (Critical Blocking Issues)

_此類問題嚴重影響系統可維護性或存在執行路徑上的重大矛盾，建議立即修正。_

### 🔴 S-01: 幽靈架構 (Ghost Architecture) - 代碼與文檔不符

- **現狀**: `TODO.md` (Line 796) 宣告已完成「**A-06** 拆分 `app.py` (Blueprint)」。然而，實際檢查 `app.py` (Line 313-2022) 發現它仍然是一個包含所有路由邏輯的巨大單體 (Monolith) 檔案。
- **證據**:
  - `routes/notes.py` 等檔案存在且包含完整的邏輯實現。
  - `app.py` **完全沒有匯入** `routes` 套件 (經 `grep` 搜索確認無 `register_blueprint` 或 `from routes` 語句)。
- **風險**:
  - **維護災難**: 開發者可能會以為邏輯在 `routes/xx.py` 中而進行修改，但實際運行的卻是 `app.py` 中的舊代碼，導致修改無效。
  - **代碼腐爛**: `routes/` 目錄下的代碼目前屬於 Dead Code，隨時間推移可能與主程式脫節。
- **修復建議**:
  - **方案 A (推薦)**: 大刀闊斧完成重構。備份並清空 `app.py` 中的路由邏輯，改為引用 `routes` 中的 Blueprint。
  - **方案 B (權宜)**: 如果 MVP 階段不敢動大架構，請更新 `TODO.md` 將 A-06 標記為「未完成」或「已回滾」，並刪除 `routes/` 目錄以免混淆。

### 🔴 L-01: 雙重資料源風險 (Duplication Logic)

- **現狀**: 由於 S-01，專案中存在兩套完全相同的邏輯 (例如 `duplicate_note` 在 `app.py` Line 938 和 `routes/notes.py` Line 517 都有定義)。
- **風險**: 若未修復 S-01，任何對業務邏輯的修正 (如 Schema 變更) 都必須同步修改兩處，極易遺漏導致 Bug。

---

## 2. 🟡 [黃燈] 風險與技術債 (Risks & Technical Debt)

_MVP 階段可暫時接受，但需列入 Backlog 的項目。_

### 🟡 SEC-01: 缺乏 CSRF 防護 (Missing CSRF Protection)

- **分析**: `app.py` 未實作 CSRF Token 機制。雖然這是本機端應用 (Localhost)，但若使用者在瀏覽器開啟惡意網站，該網站可透過 JS 對 `localhost:5000/api/notes/delete` 發送 POST/DELETE 請求進行攻擊 (Drive-by Attack)。
- **建議**: 引入 `Flask-WTF` 的 CSRFProtect，或在 API 請求中強制檢查 `Origin` / `Referer` Header 必須為 `localhost`。

### 🟡 PERF-01: 同步寫入的 FTS5 觸發器

- **分析**: `init_db` (Line 167-182) 設定了 SQLite Trigger，在 `Notes` 變更時同步寫入 `Notes_FTS`。
- **風險**: 對於大量匯入或批量修改操作，這會增加 Write Overhead。雖然 MVP 資料量小無感，但若未來有大量匯入需求，建議改為應用層異步更新或定時 Rebuild。

### 🟡 UX-01: 錯誤處理隱蔽性

- **分析**: 前端 `index.html` 的 `fetch` 錯誤處理多為 `alert("無法連線...")`。
- **建議**: 應引入全域的 Toast Notification (如 `vue-toastification` 或自製元件)，提升錯誤提示的友善度。

---

## 3. 📝 [建議] 架構修正方案 (Architectural Recommendations)

針對 **[紅燈] S-01** 問題，建議將 `app.py` 瘦身為單純的 Application Factory：

**修正後的 `app.py` 偽代碼 (Target Architecture):**

```python
import os
from flask import Flask, jsonify
from config import config

# 1. Import Blueprints
from routes import register_blueprints

def create_app(env_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[env_name])

    # Init DB logic (maintain here or move to extensions.py)
    with app.app_context():
        from database import init_db
        init_db()

    # 2. Register Blueprints
    register_blueprints(app)

    # Global Error Handlers
    @app.errorhandler(Exception)
    def handle_exception(e):
        return jsonify({'status': 'error', 'message': str(e)}), 500

    return app

if __name__ == '__main__':
    env = os.getenv('FLASK_ENV', 'default')
    app = create_app(env)
    debug = os.getenv('FLASK_DEBUG', 'False') == 'True'
    app.run(debug=debug)
```

## 4. 🔍 專案狀態總結

- **核心功能**: ✅ 完整 (CRUD, Tags, FTS Search, Image Upload, Markdown)
- **安全性**: ✅ 及格 (SQL Injection 防護, XSS Cleaning)
- **架構一致性**: ❌ **失敗** (嚴重的 Monolith vs Blueprint 分裂)
- **資料庫設計**: ✅ 優秀 (正規化合理, 包含 History 與 FTS)

**最終結論**: 系統功能面已達 MVP 標準，但**代碼組織結構存在致命矛盾**。在發布 v1.6 正式版前，必須解決 `app.py` 與 `routes/` 的整合問題，否則後續維護將寸步難行。
