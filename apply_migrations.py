import sqlite3
import os
from migrations import run_migrations

DB_PATH = 'knowledge.db'

if not os.path.exists(DB_PATH):
    print("knowledge.db not found. Initializing empty DB...")
    # Minimal init needed for run_migrations to work?
    # db.py usually handles connection.
    # We can just connect, sqlite creates file.
    pass

conn = sqlite3.connect(DB_PATH)

try:
    print("Running migrations...")
    version = run_migrations(conn)
    print(f"Migration finished. Current Version: {version}")
except Exception as e:
    print(f"Migration failed: {e}")
finally:
    conn.close()
