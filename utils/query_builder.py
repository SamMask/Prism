# -*- coding: utf-8 -*-
"""
Note Query Builder - SQL 查詢建構器

Phase 0 Step 3: 重構查詢邏輯
取代 get_notes() 中的意大利麵條 SQL 組裝邏輯。

設計原則:
- Fluent API 設計
- 每個方法 < 20 行
- 職責分離: 一個方法只做一件事
"""

from typing import List, Tuple, Any, Optional


def sanitize_fts_query(keyword: str) -> str:
    """
    清洗 FTS5 查詢字串，防止注入

    Args:
        keyword: 原始搜尋關鍵字

    Returns:
        清洗後的 FTS5 查詢字串 (e.g., '"hello"* "world"*')
    """
    if not keyword:
        return ""

    # 只保留字母數字和空格
    safe_keyword = "".join([c for c in keyword if c.isalnum() or c.isspace()])
    tokens = safe_keyword.split()

    if not tokens:
        return ""

    # 每個 token 加上前綴匹配 (*)
    return " ".join([f'"{token}"*' for token in tokens])


class NoteQueryBuilder:
    """
    筆記查詢建構器

    使用 Fluent API 建構 SQL WHERE 子句和參數。

    Example:
        builder = NoteQueryBuilder()
        builder.filter_category(1).filter_tags([2, 3], mode='AND').search_fts('hello')
        where_sql, params = builder.build()
    """

    def __init__(self):
        self._where_clauses: List[str] = []
        self._params: List[Any] = []

    def filter_category(self, category_id: int) -> 'NoteQueryBuilder':
        """
        過濾分類

        Args:
            category_id: 分類 ID

        Returns:
            self (Fluent API)
        """
        if category_id:
            self._where_clauses.append("n.category_id = ?")
            self._params.append(category_id)
        return self

    def filter_tags(self, tag_ids: List[int], mode: str = 'AND') -> 'NoteQueryBuilder':
        """
        過濾標籤

        Args:
            tag_ids: 標籤 ID 列表
            mode: 'AND' (必須包含所有標籤) 或 'OR' (包含任一標籤)

        Returns:
            self (Fluent API)
        """
        if not tag_ids:
            return self

        if mode == 'OR':
            # OR 模式: 筆記只需包含任一選中標籤
            placeholders = ','.join(['?' for _ in tag_ids])
            self._where_clauses.append(f"""
                EXISTS (SELECT 1 FROM Note_Tags nt
                        WHERE nt.note_id = n.id AND nt.tag_id IN ({placeholders}))
            """)
            self._params.extend(tag_ids)
        else:
            # AND 模式 (預設): 筆記必須包含所有選中標籤
            for tag_id in tag_ids:
                self._where_clauses.append("""
                    EXISTS (SELECT 1 FROM Note_Tags nt
                            WHERE nt.note_id = n.id AND nt.tag_id = ?)
                """)
                self._params.append(tag_id)

        return self

    def filter_archived(self, include_archived: bool = False) -> 'NoteQueryBuilder':
        """
        過濾封存狀態

        Args:
            include_archived: True = 包含封存筆記, False = 只顯示未封存

        Returns:
            self (Fluent API)
        """
        if not include_archived:
            # Phase 0: is_archived 欄位尚未在 Migration 中實作
            # 目前先檢查欄位是否存在
            self._where_clauses.append("(n.is_archived IS NULL OR n.is_archived = 0)")

        return self

    def search_fts(self, keyword: str) -> 'NoteQueryBuilder':
        """
        全文檢索 (FTS5)

        Args:
            keyword: 搜尋關鍵字

        Returns:
            self (Fluent API)
        """
        if not keyword:
            return self

        fts_query = sanitize_fts_query(keyword)
        if fts_query:
            self._where_clauses.append(
                "n.id IN (SELECT rowid FROM Notes_FTS WHERE Notes_FTS MATCH ?)"
            )
            self._params.append(fts_query)

        return self

    def filter_pinned(self, pinned_only: bool = False) -> 'NoteQueryBuilder':
        """
        過濾置頂狀態

        Args:
            pinned_only: True = 只顯示置頂筆記

        Returns:
            self (Fluent API)
        """
        if pinned_only:
            self._where_clauses.append("n.is_pinned = 1")

        return self

    def build(self) -> Tuple[str, List[Any]]:
        """
        建構 WHERE 子句和參數

        Returns:
            (where_sql, params) tuple
            where_sql: "WHERE ..." or "" (如果沒有條件)
            params: 參數列表
        """
        if not self._where_clauses:
            return ("", [])

        where_sql = "WHERE " + " AND ".join(self._where_clauses)
        return (where_sql, self._params)

    def reset(self) -> 'NoteQueryBuilder':
        """重置建構器 (清空所有條件)"""
        self._where_clauses.clear()
        self._params.clear()
        return self
