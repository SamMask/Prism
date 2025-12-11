import sqlite3
import sys

def list_notes():
    try:
        conn = sqlite3.connect('knowledge.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, type, content FROM Notes")
        rows = cursor.fetchall()
        if not rows:
            print("No notes found in database.")
        for row in rows:
            print(f"ID: {row[0]}, Title: {row[1]}, Type: {row[2]}, Content Sample: {row[3][:50]}...")
        conn.close()
    except Exception as e:
        print(f"Error: {e}")
    sys.stdout.flush()

if __name__ == "__main__":
    list_notes()
