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


def tokenize_search_terms(keyword: str, max_tokens: int = 20) -> List[str]:
    """
    將使用者輸入拆成安全搜尋 token。

    與 FTS 查詢共用清洗規則，讓備註 / 標籤 / 附件搜尋和 title/content
    的 token 行為一致。
    """
    if not keyword:
        return []

    safe_keyword = "".join([
        c.lower() if c.isalnum() else " " for c in keyword
    ])
    tokens = safe_keyword.split()

    if len(tokens) > max_tokens:
        return tokens[:max_tokens]

    return tokens


def sanitize_fts_query(keyword: str, max_tokens: int = 20) -> str:
    """
    清洗 FTS5 查詢字串，防止注入

    Args:
        keyword: 原始搜尋關鍵字
        max_tokens: 最大允許的關鍵字數量 (預設 20)，防止 DoS

    Returns:
        清洗後的 FTS5 查詢字串 (e.g., '"hello"* "world"*')
    """
    if not keyword:
        return ""

    tokens = tokenize_search_terms(keyword, max_tokens=max_tokens)

    if not tokens:
        return ""

    # 限制 token 數量防止 DoS
    if len(tokens) > max_tokens:
        tokens = tokens[:max_tokens]

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

    def filter_archived_only(self) -> 'NoteQueryBuilder':
        """只顯示封存筆記。"""
        self._where_clauses.append("n.is_archived = 1")
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

    def search_card_fields(
        self,
        keyword: str,
        attachment_content_note_ids: Optional[List[int]] = None
    ) -> 'NoteQueryBuilder':
        """
        搜尋使用者在卡片上會期待可查到的文字欄位。

        覆蓋:
        - Notes_FTS(title, content)
        - Notes.remarks
        - Tags.name
        - Note_Attachments.title / file_path
        - attachment_content_note_ids: 由檔案內容掃描器提供
        """
        if not keyword:
            return self

        tokens = tokenize_search_terms(keyword)
        fts_query = sanitize_fts_query(keyword)
        clauses: List[str] = []
        params: List[Any] = []

        if fts_query:
            clauses.append(
                "n.id IN (SELECT rowid FROM Notes_FTS WHERE Notes_FTS MATCH ?)"
            )
            params.append(fts_query)

        if tokens:
            clauses.append(self._build_remarks_clause(tokens, params))
            clauses.append(self._build_tags_clause(tokens, params))
            clauses.append(self._build_attachment_metadata_clause(tokens, params))

        if attachment_content_note_ids:
            unique_ids = sorted(set(attachment_content_note_ids))
            placeholders = ','.join(['?' for _ in unique_ids])
            clauses.append(f"n.id IN ({placeholders})")
            params.extend(unique_ids)

        if clauses:
            self._where_clauses.append("(" + " OR ".join(clauses) + ")")
            self._params.extend(params)

        return self

    def _build_remarks_clause(self, tokens: List[str], params: List[Any]) -> str:
        token_clauses = []
        for token in tokens:
            token_clauses.append("LOWER(COALESCE(n.remarks, '')) LIKE ?")
            params.append(f"%{token}%")
        return "(" + " AND ".join(token_clauses) + ")"

    def _build_tags_clause(self, tokens: List[str], params: List[Any]) -> str:
        token_clauses = []
        for token in tokens:
            token_clauses.append("""
                EXISTS (
                    SELECT 1 FROM Note_Tags nt
                    JOIN Tags t ON nt.tag_id = t.id
                    WHERE nt.note_id = n.id
                    AND LOWER(t.name) LIKE ?
                )
            """)
            params.append(f"%{token}%")
        return "(" + " AND ".join(token_clauses) + ")"

    def _build_attachment_metadata_clause(
        self,
        tokens: List[str],
        params: List[Any]
    ) -> str:
        token_clauses = []
        for token in tokens:
            token_clauses.append("""
                EXISTS (
                    SELECT 1 FROM Note_Attachments a
                    WHERE a.note_id = n.id
                    AND (
                        LOWER(COALESCE(a.title, '')) LIKE ?
                        OR LOWER(COALESCE(a.file_path, '')) LIKE ?
                    )
                )
            """)
            like_token = f"%{token}%"
            params.extend([like_token, like_token])
        return "(" + " AND ".join(token_clauses) + ")"

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
