import sqlite3
import os

DB_PATH = 'knowledge.db'

def deep_clean():
    if not os.path.exists(DB_PATH):
        print(f"❌ Database {DB_PATH} not found.")
        return

    print("🧹 Starting Deep Clean (Extreme Edition)...")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 1. Clean Orphan History & Links (Basic)
        print("   - Cleaning orphans...")
        cursor.execute("DELETE FROM Note_History WHERE note_id NOT IN (SELECT id FROM Notes)")
        cursor.execute("DELETE FROM Note_Tags WHERE note_id NOT IN (SELECT id FROM Notes)")
        cursor.execute("DELETE FROM Source_Urls WHERE note_id NOT IN (SELECT id FROM Notes)")
        
        # 2. Clean Unused Tags
        print("   - Cleaning unused tags...")
        cursor.execute("DELETE FROM Tags WHERE id NOT IN (SELECT tag_id FROM Note_Tags)")
        
        # 3. Clean FTS (Full Text Search)
        print("   - Cleaning Search Index (FTS)...")
        # 標準 FTS 清除與重建方式
        try:
            cursor.execute("DELETE FROM Notes_FTS")
            cursor.execute("INSERT INTO Notes_FTS(Notes_FTS) VALUES('rebuild')")
        except sqlite3.OperationalError:
            # Table might not exist or named differently
            print("     (FTS table not found or error, skipping)")

        # 4. Reset Auto Increment Counters
        print("   - Resetting ID counters...")
        cursor.execute("SELECT COUNT(*) FROM Notes")
        count = cursor.fetchone()[0]
        if count == 0:
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='Notes'")
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='Note_History'")
            print("     (Counters reset to 1)")
        
        conn.commit()
        
        # 5. VACUUM
        print("🗜️  Vacuuming database...")
        conn.execute("VACUUM")
        
        conn.close()
        print("✅ Deep Clean completed.")
        
    except Exception as e:
        print(f"❌ Error during deep clean: {e}")

if __name__ == "__main__":
    deep_clean()
