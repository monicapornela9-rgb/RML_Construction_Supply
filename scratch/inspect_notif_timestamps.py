import sqlite3
from datetime import datetime, date, timedelta

conn = sqlite3.connect('RML/rml_database.db')
conn.row_factory = sqlite3.Row
notifs = conn.execute("SELECT id, user_id, title, created_at FROM notifications ORDER BY created_at DESC LIMIT 10").fetchall()
now = datetime.now()
print(f"Current python now: {now}")
for n in notifs:
    ts_str = n["created_at"]
    print(f"ID {n['id']} | user: {n['user_id']} | created_at: {ts_str} | title: {n['title']}")
conn.close()
