import sqlite3

def list_notes():
    with open('notes_dump.txt', 'w', encoding='utf-8') as f:
        try:
            conn = sqlite3.connect('knowledge.db')
            cursor = conn.cursor()
            cursor.execute("SELECT id, title, type, content FROM Notes")
            rows = cursor.fetchall()
            if not rows:
                f.write("No notes found in database.")
            for row in rows:
                f.write(f"ID: {row[0]}, Title: {row[1]}, Type: {row[2]}\nContent Start: {row[3][:50]}\n---\n")
            conn.close()
        except Exception as e:
            f.write(f"Error: {e}")

if __name__ == "__main__":
    list_notes()
