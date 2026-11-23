import sqlite3

conn = sqlite3.connect('RML/rml_database.db')
conn.row_factory = sqlite3.Row

orders = conn.execute("SELECT id, customer_id, order_code, order_status FROM orders").fetchall()
for o in orders:
    n_count = conn.execute("SELECT COUNT(*) FROM notifications WHERE order_id = ?", (o["id"],)).fetchone()[0]
    print(f"Order ID {o['id']} ({o['order_code']} / {o['order_status']}) Customer {o['customer_id']} -> {n_count} notifications")

conn.close()
