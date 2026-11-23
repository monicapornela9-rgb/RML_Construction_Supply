import sys
import os

sys.path.insert(0, os.path.abspath('RML'))
from db import get_db

conn = get_db()
orders = conn.execute("""
    SELECT o.id, o.order_code, o.customer_id, u.name as user_name, u.email as user_email,
           o.recipient_name, o.phone, o.delivery_address, o.total_amount,
           o.order_status, o.created_at, o.special_instructions
    FROM orders o
    LEFT JOIN users u ON o.customer_id = u.id
    ORDER BY o.id ASC
""").fetchall()

for o in orders:
    print(f"[{o['id']}] Code: {o['order_code']} | Cust: {o['user_name']} ({o['customer_id']}) | Recipient: {o['recipient_name']} | Address: {o['delivery_address']} | Created: {o['created_at']}")
conn.close()
