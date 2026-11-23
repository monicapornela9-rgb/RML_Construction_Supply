import sqlite3

conn = sqlite3.connect('RML/rml_database.db')
conn.row_factory = sqlite3.Row

custs = conn.execute("SELECT id, name, email FROM users WHERE role = 'customer'").fetchall()
for c in custs:
    o_count = conn.execute("SELECT COUNT(id) FROM orders WHERE customer_id = ?", (c["id"],)).fetchone()[0]
    n_count = conn.execute("SELECT COUNT(id) FROM notifications WHERE user_id = ?", (c["id"],)).fetchone()[0]
    print(f"Customer ID {c['id']}: {c['name']} | Orders: {o_count} | Notifications: {n_count}")

conn.close()
