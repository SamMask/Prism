# 🐧 Linus Torvalds 批判式風格程式碼審查

**日期**: 2025-12-17  
**分析者**: Linus Torvalds (風格模擬)  
**專案**: Prism V2 - Headless Architecture + Local AI

---

## 📝 需求理解確認

> 審查 Prism V2 專案的技術文件 (`SCHEMA-V2.md`, `ARCHITECTURE-V2.md`, `TODO-V2.md`, `SEQUENCE-UPLOAD.md`, `ER-DIAGRAM.md`) 與核心程式碼，從資料結構、特殊情況處理、並發安全、向後相容性、務實程度五個層面進行批判式分析。

**專案定位**: 個人知識庫應用，從簡易 Flask 應用轉型為 Headless 架構 (React + Flask API)，支援本地 AI 功能 (Ollama, SQLite 向量搜尋)。

---

## 🔍 Linus 式問題分解 (5-Layer Framework)

### 第一層：資料結構分析 (Data Structures)

#### ⚠️ 問題 1: `Embeddings` 表的過度工程

**位置**: `SCHEMA-V2.md` Section 1.1

```sql
CREATE TABLE Embeddings (
    id INTEGER PK,
    resource_type TEXT,      -- 'note', 'image', 'attachment'
    resource_id INTEGER,
    chunk_index INTEGER,     -- 🤔 RAG 長文切塊預留
    model_name TEXT,
    vector BLOB,
    content_hash TEXT,
    dimensions INTEGER,      -- 🤔 永遠是 384
    created_at DATETIME
);
```

**批評**:
- `dimensions` 欄位是冗餘。你們用的是 `all-MiniLM-L6-v2`，維度永遠是 384。如果換模型，整個表都要重建，存這個欄位幹嘛？
- `chunk_index` 是「為未來預留」的典型症狀。**YAGNI (You Ain't Gonna Need It)**。
- `resource_type` + `resource_id` 這種多態關聯 (Polymorphic Association) 是資料庫設計的反模式 — 無法建立 Foreign Key 約束。

**【品味評分】**: 🟡 湊合（能用，但過度設計）

**Linus 式方案**:
```sql
-- 簡化版，適用於「現在」的需求
CREATE TABLE Note_Embeddings (
    note_id INTEGER PRIMARY KEY REFERENCES Notes(id),
    vector BLOB NOT NULL,
    content_hash TEXT,
    updated_at DATETIME
);
-- 單表單用途。等你真的需要 Image Embedding 時再說。
```

---

#### ✅ 好的設計: `content_hash` 增量更新

`SCHEMA-V2.md` 中的 `content_hash` 設計是正確的：

> `content_hash`: 避免每次重建索引都重新計算，節省 90% 運算

這是**有品味**的設計 — 用資料結構解決問題，而不是用程式碼。

---

#### ⚠️ 問題 2: `Notes.type` vs `Notes.category_id` 雙重事實

**位置**: `ER-DIAGRAM.md`, `SCHEMA-V2.md`

根據 ER 圖，`Notes` 表同時有：
- `category_id FK` → 指向 `Categories` 表
- 另有 `type` 欄位（字串）

這違反了**單一事實來源 (Single Source of Truth)** 原則。

從 `TODO-V2.md` Line 256 可見這已被識別：
> | P2 | #5 `type/category_id` 冗餘 | 已記錄於 SCHEMA.md，屬向後相容設計 | ⏳ 長期計劃 |

**Linus 式評論**:
> 「向後相容」不是讓垃圾永遠留在程式碼裡的藉口。設一個 deprecation 日期，然後刪掉它。

---

### 第二層：特殊情況分析 (Special Cases)

#### ⚠️ 問題 3: 自動分離的魔法數字

**位置**: `SCHEMA-V2.md` Section 1.7

```
觸發條件: 筆記內容超過 5000 字元
preview_length: 預設 500 字元
```

**批評**:  
- 5000 字元是怎麼來的？是拍腦袋決定的還是有效能測試依據？
- 這個閾值應該是可配置的，不是硬編碼

**【品味評分】**: 🟡 湊合

**正確做法**:
```python
# config.py
CONTENT_SEPARATION_THRESHOLD = int(os.getenv('PRISM_SEPARATION_THRESHOLD', 5000))
```

---

#### ✅ 好的設計: 分離流程的優雅處理

`SCHEMA-V2.md` Section 1.7 的分離流程 (v2 精緻化) 設計得不錯：

> - 若已存在 `is_auto_extracted=1` 附件 → **更新**檔案內容
> - 若不存在 → 建立新附件

這避免了「重複分離」的邊緣情況，是前瞻性設計。

---

### 第三層：複雜度與並行安全 (Complexity & Concurrency)

#### ✅ 已修復: Embedding 線程控制

根據 `TODO-V2.md` Line 253:
> | P0 | #3 Embedding 線程無限產生 | 使用 `ThreadPoolExecutor(max_workers=2)` | ✅ 已修復 |

很好，你們處理了無限線程產生的問題。

---

#### ✅ 已修復: `_batch_tasks` 記憶體洩漏

根據 `TODO-V2.md` Line 254:
> | P0 | #4 `_batch_tasks` 記憶體洩漏 | 加入 TTL(1hr) + Max(100) 限制 | ✅ 已修復 |

很好。

---

#### ⚠️ 問題 4: `VectorStore` 單例模式的潛在問題

**位置**: `embedding_service.py` 中的 `_model` 全域變數

```python
_model = None  # 全域單例

def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(_model_name)
    return _model
```

**批評**:
- 這是模組級全域狀態，在多線程環境下是**競態條件**的溫床
- 第一次呼叫會阻塞主線程（模型載入約 2-3 秒）

**【品味評分】**: 🟡 湊合

**Linus 式方案**:
```python
import threading
_model_lock = threading.Lock()
_model = None

def get_model():
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:  # Double-check locking
                _model = SentenceTransformer(_model_name)
    return _model
```

---

### 第四層：向後相容性 (Breaking Userspace)

#### ✅ 良好: 遷移系統設計

根據 `SCHEMA-V2.md` Section 4:
> Prism V2 首次啟動時，檢查 Schema 版本。執行 `ALTER TABLE` 語句。

這表示有版本化遷移系統。不會破壞現有使用者資料。

---

#### ⚠️ 問題 5: `Note_Edges` 和 `AI_Tasks` 表尚未實作

**位置**: `SCHEMA-V2.md` Section 1.2, 1.3

這兩個表在 Schema 文件中定義，但在 `TODO-V2.md` 中標記為 🧊 Icebox:
> **3.3 知識畫布 (Canvas / Graph View) 🧊 已凍結**

**風險**: 如果使用者期望這些功能，會失望。文件應該明確標註「規劃中，尚未實作」。

**【品味評分】**: 🟢 OK（延後實作是正確的優先級判斷）

---

### 第五層：務實程度 (Pragmatism)

#### ✅ **非常務實**: SQLite BLOB 向量儲存

**位置**: `SCHEMA-V2.md` Section 備註

> 對於 "Vector DB"，建議初期先使用 SQLite BLOB 儲存 + 暴力計算 (Cosine Similarity via Python/NumPy)，因為個人知識庫數據量 (通常 < 10萬) 完全撐得住，無需引入複雜的 Vector Index 引擎，保持 "Portable" 特性。

**Linus 式讚美**:
> 這是**有品味**的決定。Chrome 就是用 SQLite，不是 PostgreSQL。能用簡單的方案就不要搞複雜。

**【品味評分】**: 🟢 有品味

---

#### ✅ **務實**: Hybrid Search (RRF)

**位置**: `TODO-V2.md` Line 105-109

```
3.2.5 Hybrid Search (FTS + Vector) ✅ 完成
演算法: RRF (Reciprocal Rank Fusion), k=60
```

這是正確的方法 — FTS 處理精確匹配，Vector 處理語意，RRF 融合結果。不需要引入 Elasticsearch。

---

#### ✅ **務實**: 測試策略

**位置**: `TODO-V2.md` Line 312-318

| 測試類型 | 適用場景 | 執行者 |
|----------|----------|--------|
| 自動化 API | 所有 API 端點 | pytest |
| 自動化 E2E | 核心路徑 | Playwright |
| 手動測試 | 體驗與美感 | Human |
| 探索性測試 | 亂按破壞 | Human |

**Linus 式讚美**:
> 「不要為了 100% 覆蓋率而測試 CSS 顏色」— 你們懂這個道理。

---

#### ⚠️ 問題 6: 過度規劃 (Over-Planning)

**位置**: `TODO-V2.md` Phase 4, 5

Phase 4 (影片智慧分析) 和 Phase 5 (Plugin Ecosystem) 的規劃過於詳細，但明顯不會短期內實作。

> 4.1 影片智慧分析 //影片不做 太麻煩了 檔案也太大
> 4.2 生成式編輯 //也不作 好象沒啥用

**Linus 式評論**:
> 如果你已經決定不做，就刪掉這些條目。保留「不做的東西」在 TODO 裡只會產生認知負擔。

---

## 🎯 核心判斷 (The Verdict)

### ✅ 值得做 (Worth Doing)

Prism V2 是一個**有潛力**的專案，架構決策大多數是務實的。

### 🔑 關鍵洞察 (Key Insight)

> **最大的贏點**: 堅持 SQLite + BLOB Vector 的輕量化策略，拒絕過早引入複雜的向量資料庫。這體現了「做對的事比做複雜的事更難」的工程智慧。

> **最大的隱患**: `Embeddings` 表的多態關聯設計 (`resource_type` + `resource_id`) 會在未來造成 JOIN 地獄。

---

## 📊 程式碼審查總結 (Code Review Summary)

### 品味評分 (Taste Score): 🟢 有品味

整體架構決策正確，務實程度高。有一些過度設計的跡象，但不致命。

### 致命問題 (Fatal Issues): 無

P0 問題已在之前修復：
- ✅ Embedding 線程控制 → 已用 `ThreadPoolExecutor` 修復
- ✅ `_batch_tasks` 記憶體洩漏 → 已加入 TTL + Max 限制
- ✅ 重複的 `get_db()` → 已刪除 `app.py` 版本

### 中等問題 (Medium Issues)

| # | 問題 | 嚴重度 | 建議 |
|---|------|--------|------|
| 1 | `Embeddings` 表多態關聯 | 🟡 Med | 短期可接受，長期考慮拆分為專用表 |
| 2 | `Notes.type` 冗餘欄位 | 🟡 Med | 設 deprecation date，逐步移除 |
| 3 | 分離閾值硬編碼 | 🟢 Low | 移至配置檔 |
| 4 | `_model` 全域變數無鎖 | 🟡 Med | 加入 Double-Check Locking |
| 5 | TODO 中保留「不做」的項目 | 🟢 Low | 清理或移至別處 |

### Linus 式修復建議 (The "Linus Fix")

1. **短期** (本週):
   - 在 `embedding_service.py` 中加入 Lock 保護 `_model` 初始化
   - 將 `CONTENT_SEPARATION_THRESHOLD` 移至環境變數

2. **中期** (下個版本):
   - 標記 `Notes.type` 欄位為 deprecated
   - 清理 TODO.md 中標記為「不做」的項目

3. **長期** (半年內):
   - 考慮將 `Embeddings` 表拆分為 `Note_Embeddings`, `Image_Embeddings` 專用表
   - 刪除 `Notes.type` 欄位

---

## 📐 架構圖分析 (Architecture Review)

### `ARCHITECTURE-V2.md` C4 Container Diagram

```
Frontend SPA → API Server → SQLite (WAL Mode)
                    ↓
            AI Service Layer → Ollama / HuggingFace
```

**評價**: 🟢 簡潔明瞭

- 沒有過度的中間層
- AI Service 是可選的（Graceful Degradation）
- 檔案系統和資料庫分離（圖片 vs 元資料）

---

### `SEQUENCE-UPLOAD.md` 上傳流程

1. Upload → Generate WebP Thumbnail → Calculate pHash
2. Check Duplicates (pHash) → Reject or Proceed
3. Extract PNG Info → INSERT Note
4. **Async**: Enqueue Tagging + Embedding

**評價**: 🟢 有品味

- 同步處理快速操作（縮圖、去重）
- 非同步處理慢速操作（AI 分析）
- Optimistic UI (前端先顯示卡片，背景處理)

---

## 🏁 結語

> "Talk is cheap. Show me the code."

你們的程式碼**不是垃圾**。P0 問題已修復，架構決策大多正確。

但記住：
1. **刪掉不用的東西** — 連文件裡的都要刪
2. **不要為未來預留欄位** — 等你真的需要時再加
3. **多態關聯是魔鬼** — 用專用表取代 `resource_type + resource_id`

繼續保持務實，不要被「最佳實踐」洗腦。

---

*報告完畢。去寫程式碼。*

🐧 Linus (模擬)
