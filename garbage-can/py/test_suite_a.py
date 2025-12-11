import sqlite3
import json
import os

def test_backend_integrity():
    print("=== Suite A: Backend Test (Raw SQLite) ===", flush=True)
    
    db_path = 'knowledge.db'
    if not os.path.exists(db_path):
        print(f"❌ Database not found at {db_path}", flush=True)
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # A-1: Verify Schema Version
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Schema_Meta'")
            if not cursor.fetchone():
                print("❌ A-1: Table 'Schema_Meta' does not exist!", flush=True)
            else:
                cursor.execute("SELECT version FROM Schema_Meta ORDER BY version DESC LIMIT 1")
                version = cursor.fetchone()
                if version and version[0] >= 2:
                    print(f"✅ A-1: Schema Version is {version[0]} (>= 2)", flush=True)
                else:
                    print(f"❌ A-1: Schema Version mismatch. Found: {version}", flush=True)
        except Exception as e:
            print(f"❌ A-1: Failed to query Schema_Meta: {e}", flush=True)

        # A-2: Verify category_id column
        try:
            cursor.execute("PRAGMA table_info(Notes)")
            columns = [info[1] for info in cursor.fetchall()]
            if 'category_id' in columns:
                print("✅ A-2: 'category_id' column exists in Notes table.", flush=True)
            else:
                print("❌ A-2: 'category_id' column MISSING in Notes table.", flush=True)
        except Exception as e:
            print(f"❌ A-2: Failed to inspect Notes table: {e}", flush=True)

        # A-3: Test get_notes logic (json_group_array)
        print("Testing JSON aggregation query...", flush=True)
        try:
            query = """
            SELECT 
                n.id, n.title,
                json_group_array(DISTINCT json_object('id', t.id, 'name', t.name)) FILTER (WHERE t.id IS NOT NULL) as tags_json,
                json_group_array(DISTINCT u.url) FILTER (WHERE u.url IS NOT NULL) as urls_json
            FROM Notes n
            LEFT JOIN Note_Tags nt ON n.id = nt.note_id
            LEFT JOIN Tags t ON nt.tag_id = t.id
            LEFT JOIN Source_Urls u ON n.id = u.note_id
            GROUP BY n.id
            LIMIT 1
            """
            cursor.execute(query)
            row = cursor.fetchone()
            if row:
                try:
                    tags = json.loads(row[2])
                    urls = json.loads(row[3])
                    print("✅ A-3: JSON aggregation query returns parsable JSON.", flush=True)
                except json.JSONDecodeError as e:
                    print(f"❌ A-3: JSON parsing failed: {e}", flush=True)
            else:
                print("⚠️ A-3: No notes found in DB, but SQL syntax is valid.", flush=True)
        except Exception as e:
            print(f"❌ A-3: Query execution failed: {e}", flush=True)
            
        conn.close()
        
    except Exception as e:
        print(f"❌ Fatal error: {e}", flush=True)

if __name__ == "__main__":
    test_backend_integrity()
