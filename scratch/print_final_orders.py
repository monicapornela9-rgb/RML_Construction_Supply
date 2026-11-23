import sys
import os

sys.path.insert(0, os.path.abspath('RML'))
from db import get_db

conn = get_db()
orders = conn.execute("""
    SELECT o.id, o.order_code, o.customer_id, u.name as customer_name, u.email,
           o.recipient_name, o.delivery_address, o.total_amount, o.order_status,
           (SELECT p.payment_status FROM payments p WHERE p.order_id = o.id) as payment_status,
           (SELECT p.method FROM payments p WHERE p.order_id = o.id) as payment_method,
           (SELECT d.delivery_code FROM deliveries d WHERE d.order_id = o.id) as delivery_code,
           (SELECT d.delivery_status FROM deliveries d WHERE d.order_id = o.id) as delivery_status,
           o.created_at
    FROM orders o
    JOIN users u ON o.customer_id = u.id
    ORDER BY o.id DESC
""").fetchall()

print(f"=== CURRENT ACTIVE LEGITIMATE ORDERS IN DATABASE ({len(orders)}) ===")
for o in orders:
    print(f"Order #{o['id']} [{o['order_code']}] | Customer: {o['customer_name']} ({o['email']}) | Recipient: {o['recipient_name']} | Total: PHP {o['total_amount']:,.2f} | Status: {o['order_status']} | Pay: {o['payment_status']} ({o['payment_method']}) | Dlv: {o['delivery_code']} ({o['delivery_status']}) | Date: {o['created_at']}")
conn.close()
