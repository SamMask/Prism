# -*- coding: utf-8 -*-
"""
Database Utilities
Prism v1.4.1

統一的資料庫連線層，避免各 routes 模組重複定義 get_db()
"""

import sqlite3
from contextlib import contextmanager
from flask import g, current_app


def get_db():
    """
    取得資料庫連線 (Flask Application Context 內共用)

    使用方式:
        from db import get_db
        db = get_db()
        db.execute('SELECT * FROM Notes')

    v1.2: 修正 Foreign Keys 啟用邏輯 (MVP Audit 2025-12-12)
    """
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES,
            isolation_level=None  # 使用 autocommit 模式，確保 PRAGMA 立即生效
        )
        g.db.row_factory = sqlite3.Row

        # 啟用 Foreign Keys 並驗證
        g.db.execute('PRAGMA foreign_keys = ON')
        fk_status = g.db.execute('PRAGMA foreign_keys').fetchone()[0]
        if fk_status != 1:
            raise RuntimeError(
                f'Failed to enable foreign keys (status: {fk_status}). '
                'Database integrity at risk!'
            )

        # 啟用 WAL 模式
        g.db.execute('PRAGMA journal_mode = WAL')

        # 恢復預設的交易隔離級別 (DEFERRED)
        g.db.isolation_level = 'DEFERRED'

    return g.db


@contextmanager
def transaction():
    """
    交易 Context Manager，確保原子性操作
    
    使用方式:
        from db import transaction
        
        with transaction() as db:
            db.execute('INSERT INTO Notes ...')
            db.execute('UPDATE Tags ...')
            # 自動 commit，若異常則 rollback
    """
    db = get_db()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise


def close_db(error=None):
    """
    關閉資料庫連線 (應在 app.teardown_appcontext 註冊)
    """
    db = g.pop('db', None)
    if db is not None:
        db.close()
