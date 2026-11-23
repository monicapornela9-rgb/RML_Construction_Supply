import sys
import os

sys.path.insert(0, os.path.abspath('RML'))
from db import get_db

conn = get_db()
orders = conn.execute("""
    SELECT o.id, o.order_code, o.customer_id, u.name as user_name, u.email as user_email,
           o.recipient_name, o.phone, o.delivery_address, o.total_amount,
           o.order_status, o.created_at, o.preferred_date, o.delivery_slot,
           (SELECT COUNT(*) FROM order_items oi WHERE oi.order_id = o.id) as item_count,
           (SELECT p.payment_status FROM payments p WHERE p.order_id = o.id) as payment_status,
           (SELECT p.method FROM payments p WHERE p.order_id = o.id) as payment_method,
           (SELECT p.reference_number FROM payments p WHERE p.order_id = o.id) as payment_ref,
           (SELECT d.id FROM deliveries d WHERE d.order_id = o.id) as delivery_id,
           (SELECT d.delivery_code FROM deliveries d WHERE d.order_id = o.id) as delivery_code,
           (SELECT d.delivery_status FROM deliveries d WHERE d.order_id = o.id) as delivery_status,
           (SELECT d.driver_id FROM deliveries d WHERE d.order_id = o.id) as driver_id
    FROM orders o
    LEFT JOIN users u ON o.customer_id = u.id
    ORDER BY o.id ASC
""").fetchall()

by_customer = {}
for o in orders:
    key = (o['customer_id'], o['user_name'], o['user_email'])
    by_customer.setdefault(key, []).append(o)

for (cid, uname, uemail), o_list in by_customer.items():
    print(f"\n=======================================================")
    print(f"Customer {cid}: {uname} ({uemail}) - {len(o_list)} orders")
    print(f"=======================================================")
    for o in o_list:
        print(f"  Order #{o['id']} [{o['order_code']}] | Status: {o['order_status']} | Recipient: {o['recipient_name']} | Addr: {o['delivery_address']} | Pay: {o['payment_status']} ({o['payment_method']}: {o['payment_ref']}) | Dlv: {o['delivery_code']} ({o['delivery_status']}, Driver {o['driver_id']}) | Created: {o['created_at']}")

conn.close()
