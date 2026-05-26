import sqlite3
import os

db_path = 'knowledge.db'

if not os.path.exists(db_path):
    print("knowledge.db not found!")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

def get_table_info(table_name):
    cursor.execute(f"PRAGMA table_info({table_name})")
    return cursor.fetchall()


with open('db_schema.txt', 'w', encoding='utf-8') as f:
    f.write(f"--- Table: Notes ---\n")
    columns = get_table_info('Notes')
    for col in columns:
        f.write(str(col) + "\n")

    f.write(f"\n--- Table: Embeddings ---\n")
    columns = get_table_info('Embeddings')
    if not columns:
        f.write("Table Embeddings does not exist.\n")
    else:
        for col in columns:
            f.write(str(col) + "\n")

conn.close()
