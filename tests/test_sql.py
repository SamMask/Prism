import sqlite3
import os
os.chdir(r'c:\AI\Local Insight')

# Test the exact same logic as in notes.py
note_ids = [1, 2, 3]

db = sqlite3.connect('knowledge.db')
db.row_factory = sqlite3.Row
db.execute('PRAGMA foreign_keys = ON')

try:
    # 更新每個筆記的 sort_order
    for index, note_id in enumerate(note_ids):
        db.execute(
            'UPDATE Notes SET sort_order = ? WHERE id = ?',
            (index, note_id)
        )
    
    db.commit()
    print(f"Success! Reordered {len(note_ids)} notes")
    
except sqlite3.Error as e:
    db.rollback()
    print(f"SQLite Error: {e}")
except Exception as e:
    print(f"General Error: {e}")
finally:
    db.close()
