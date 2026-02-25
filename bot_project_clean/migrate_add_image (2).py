import sqlite3

def migrate():
    print("Starting migration: Add image_url to computers table")
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    
    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(computers)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if 'image_url' not in columns:
            print("Adding 'image_url' column...")
            cursor.execute("ALTER TABLE computers ADD COLUMN image_url TEXT")
            conn.commit()
            print("Migration successful: Column added.")
        else:
            print("Migration skipped: Column 'image_url' already exists.")
            
    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
