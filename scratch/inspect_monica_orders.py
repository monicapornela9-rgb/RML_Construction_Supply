import sys
import os

sys.path.insert(0, os.path.abspath('RML'))
from db import get_db

conn = get_db()
monica_orders = conn.execute("""
    SELECT o.id, o.order_code, o.customer_id, u.name as user_name, u.email as user_email,
           o.recipient_name, o.phone, o.delivery_address, o.total_amount,
           o.order_status, o.created_at,
           (SELECT COUNT(*) FROM order_items oi WHERE oi.order_id = o.id) as item_count,
           (SELECT p.payment_status FROM payments p WHERE p.order_id = o.id) as payment_status,
           (SELECT d.delivery_code FROM deliveries d WHERE d.order_id = o.id) as delivery_code,
           (SELECT d.delivery_status FROM deliveries d WHERE d.order_id = o.id) as delivery_status
    FROM orders o
    LEFT JOIN users u ON o.customer_id = u.id
    WHERE o.customer_id IN (7, 10)
    ORDER BY o.id ASC
""").fetchall()

print(f"Total Monica Orders: {len(monica_orders)}")
for o in monica_orders:
    print(f"ID: {o['id']} | Code: {o['order_code']} | Cust: {o['user_name']} ({o['user_email']}) | Recipient: {o['recipient_name']} | Address: {o['delivery_address']} | Total: {o['total_amount']} | Status: {o['order_status']} | Items: {o['item_count']} | Pay: {o['payment_status']} | Dlv: {o['delivery_code']} ({o['delivery_status']}) | Created: {o['created_at']}")
conn.close()
