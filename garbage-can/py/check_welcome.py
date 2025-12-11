import sqlite3

def check_notes():
    try:
        conn = sqlite3.connect('knowledge.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        print("Searching for notes with '歡迎' or 'Welcome' in title...")
        cursor.execute("SELECT id, title, content FROM Notes WHERE title LIKE '%歡迎%' OR title LIKE '%Welcome%'")
        rows = cursor.fetchall()
        
        if not rows:
            print("No notes found.")
        else:
            for row in rows:
                print(f"--- Note ID: {row['id']} ---")
                print(f"Title: {row['title']}")
                print(f"Content Preview: {row['content'][:100]}")
                print("-------------------------")
        
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_notes()
