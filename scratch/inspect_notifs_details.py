import sqlite3

conn = sqlite3.connect('RML/rml_database.db')
conn.row_factory = sqlite3.Row

for uid in [38, 7]:
    print(f"=== Notifications for User {uid} ===")
    notifs = conn.execute("SELECT n.*, o.order_code FROM notifications n LEFT JOIN orders o ON o.id = n.order_id WHERE n.user_id = ? ORDER BY n.created_at DESC", (uid,)).fetchall()
    for n in notifs:
        print(f"[{n['created_at']}] [{n['notification_type']}] {n['title']} (Order {n['order_code']} / ID {n['order_id']}): {n['message']} (Read: {n['is_read']})")

conn.close()
