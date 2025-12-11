import sqlite3

# Check if sort_order column exists
db = sqlite3.connect('knowledge.db')
cursor = db.execute("PRAGMA table_info(Notes)")
columns = [col[1] for col in cursor.fetchall()]
print("Notes columns:", columns)
print("sort_order exists:", 'sort_order' in columns)

# Try to test the query
if 'sort_order' in columns:
    try:
        cursor = db.execute("UPDATE Notes SET sort_order = 0 WHERE id = 1")
        db.commit()
        print("Test UPDATE successful")
    except Exception as e:
        print(f"Test UPDATE failed: {e}")
else:
    print("Adding sort_order column...")
    db.execute('ALTER TABLE Notes ADD COLUMN sort_order INTEGER DEFAULT 0')
    db.execute('UPDATE Notes SET sort_order = id WHERE sort_order = 0')
    db.commit()
    print("Column added and initialized!")

db.close()
