import sqlite3
conn = sqlite3.connect("bot_database.db")
c = conn.cursor()

c.execute("SELECT id, tg_id, username, full_name FROM users ORDER BY id")
for r in c.fetchall():
    print(f"  user_id={r[0]} tg_id={r[1]} username={r[2]} name={r[3]}")

conn.close()
