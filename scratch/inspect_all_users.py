import sys
import os

sys.path.insert(0, os.path.abspath('RML'))
from db import get_db

conn = get_db()
users = conn.execute("SELECT id, staff_id, name, email, phone, role, created_at FROM users ORDER BY id").fetchall()
print(f"Total Users: {len(users)}")
for u in users:
    order_count = conn.execute("SELECT COUNT(*) FROM orders WHERE customer_id = ?", (u["id"],)).fetchone()[0]
    print(f"User {u['id']}: {u['name']} ({u['email']}) | Role: {u['role']} | Orders: {order_count} | Created: {u['created_at']}")
conn.close()
