# -*- coding: utf-8 -*-
"""
Database Utilities
Local Insight v1.8.9

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
    """
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys = ON')
        g.db.execute('PRAGMA journal_mode = WAL')  # v1.8.9
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
