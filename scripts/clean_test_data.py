import sqlite3
import os
import shutil
from datetime import datetime

DB_PATH = 'knowledge.db'
BACKUP_DIR = 'backups'

def clean_db():
    if not os.path.exists(DB_PATH):
        print(f"❌ Database {DB_PATH} not found.")
        return

    # 1. Backup
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = os.path.join(BACKUP_DIR, f'knowledge_backup_{timestamp}.db')
    try:
        shutil.copy2(DB_PATH, backup_path)
        print(f"✅ Database backed up to {backup_path}")
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        return

    # 2. Clean
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Count before delete
        cursor.execute("SELECT COUNT(*) FROM Notes")
        notes_count = cursor.fetchone()[0]
        
        print(f"Found {notes_count} notes. Cleaning...")
        
        # Delete data (Keep Schema and static tables like Tags/Categories if mostly static? No, usually Tags from notes are trash too)
        # However, requirements usually imply keeping Categories structure but removing user data.
        # User said "Test Garbage", likely test notes.
        
        # Delete Notes and related
        cursor.execute("DELETE FROM Note_Tags")
        cursor.execute("DELETE FROM Source_Urls")
        cursor.execute("DELETE FROM Note_History")
        cursor.execute("DELETE FROM Notes")
        
        # Reset Sequences
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='Notes'")
        
        # Optional: Clean Tags that have no notes?
        # cursor.execute("DELETE FROM Tags WHERE id NOT IN (SELECT tag_id FROM Note_Tags)")
        
        conn.commit()
        conn.close()
        print(f"✅ Database cleaned. Removed {notes_count} notes.")
        
    except Exception as e:
        print(f"❌ Error cleaning database: {e}")

if __name__ == "__main__":
    clean_db()
