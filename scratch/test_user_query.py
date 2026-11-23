import sqlite3

conn = sqlite3.connect('RML/rml_database.db')
conn.row_factory = sqlite3.Row
query = """
    SELECT u.*,
           (SELECT COUNT(*) FROM orders WHERE customer_id = u.id) AS order_count,
           (SELECT COALESCE(SUM(total_amount), 0) FROM orders WHERE customer_id = u.id AND order_status != 'rejected') AS total_spent,
           (SELECT COUNT(*) FROM deliveries WHERE driver_id = u.id) AS delivery_count,
           (SELECT COUNT(*) FROM deliveries WHERE driver_id = u.id AND delivery_status = 'delivered') AS completed_deliveries
    FROM users u
    ORDER BY 
        CASE WHEN u.role = 'admin' THEN 1 WHEN u.role = 'driver' THEN 2 ELSE 3 END,
        u.id ASC
"""
rows = conn.execute(query).fetchall()
print(f"Fetched {len(rows)} user accounts:")
for r in rows:
    print(f"ID: {r['id']} | Staff: {r['staff_id']} | Name: {r['name']} | Role: {r['role']} | Active: {r['is_active']} | Orders: {r['order_count']} | Deliveries: {r['delivery_count']}")
conn.close()
