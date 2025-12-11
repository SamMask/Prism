# Backend Performance & Architecture Audit

> Date: 2025-12-09
> Reviewer: Backend Performance Engineer (Python/SQLite)
> Scope: SQL Query Logic, Search Performance, Frontend Rendering

## 1. N+1 Query Analysis (Backend)

**Status: ✅ Passed (Optimized)**

I have scrutinized `routes/notes/crud.py`, specifically the `get_notes` function.

- **Observation:** You are **not** using a naive ORM approach (fetching notes first, then iterating relationships).
- **Implementation:** You are using raw SQL with sophisticated subqueries to aggregate related data (Tags and URLs) into JSON arrays directly within the main query:
  ```sql
  -- Abstracted from your code
  SELECT ...,
      (SELECT json_group_array(...) FROM Note_Tags ...) as tags_json,
      (SELECT json_group_array(...) FROM Source_Urls ...) as urls_json
  FROM Notes n
  ...
  ```
- **Verdict:** This is the **correct pattern** for SQLite. It fetches all required data for a page (e.g., 20 items) in exactly **one DB round-trip**. There is **no N+1 query issue** here.

## 2. Search Performance (10k+ Records)

**Status: ✅ Passed (FTS5 Enabled)**

You asked if `LIKE` syntax would cause lag. Good news: **You are not using `LIKE` for keyword search.**

- **Implementation:** Your code in `routes/notes/crud.py` (lines 62-76) explicitly targets the `Notes_FTS` virtual table:
  ```python
  where_clauses.append("n.id IN (SELECT rowid FROM Notes_FTS WHERE Notes_FTS MATCH ?)")
  ```
- **Performance:** SQLite FTS5 is incredibly fast. Searching 10,000 or even 100,000 records will be sub-millisecond to single-digit milliseconds.
- **Note:** Your logic uses prefix matching (`"token"*`), which is efficient.
- **Correction:** You do **not** need to "force" FTS5; it is already the default path for keyword queries in your codebase.

## 3. Frontend Rendering (Vue `v-for`)

**Status: ⚠️ Warning (Infinite Scroll Risk)**

I examined `templates/components/_note-grid.html`.

- **Current State:** You are using standard `v-for` loop on `filteredNotes`.
  ```html
  <div v-for="(note, index) in filteredNotes" ...></div>
  ```
- **Pagination:** Your backend correctly uses `LIMIT/OFFSET`.
- **The Bottleneck:** However, your frontend implements "Infinite Scroll" (appending data to the list).
  - **Scenario:** If a user scrolls through 50 pages (1000 items), there will be **1000 complex Card Components** in the DOM.
  - **Impact:** Vue's reactivity system and the browser's layout engine (Reflow/Repaint) will start to choke. Memory usage will spike.
- **Recommendation:**
  - **Immediate:** Ensure `per_page` stays reasonable (e.g., 20-50).
  - **Pro (Virtualization):** For a "Local-First" tool where users might scroll through thousands of notes, you should implement **DOM Virtualization** (Virtual Scroller).
  - **Suggestion:** Since you are using Vue 3 without a build step (importing from CDN/static), putting in a full virtual-scroller library might be tricky.
  - **Alternative:** Implement a **"paged"** view instead of infinite scroll, OR use a lightweight virtualization technique (recycle DOM nodes by padding top/bottom).

## Summary

| Area              | Status           | Notes                                                                    |
| :---------------- | :--------------- | :----------------------------------------------------------------------- |
| **N+1 Logic**     | ✅ **Excellent** | Using `json_group_array` subqueries.                                     |
| **Search Speed**  | ✅ **Excellent** | FTS5 is fully implemented and active.                                    |
| **DOM Rendering** | ⚠️ **Caution**   | Infinite scroll will lag after ~500+ items. Consider **Virtualization**. |
