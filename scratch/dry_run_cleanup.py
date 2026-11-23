import sys
import os

sys.path.insert(0, os.path.abspath('RML'))
from db import get_db

conn = get_db()

# Target dummy order IDs
dummy_order_ids = [r[0] for r in conn.execute("""
    SELECT id FROM orders 
    WHERE customer_id IN (4, 5, 6, 8)
""").fetchall()]

legit_order_ids = [r[0] for r in conn.execute("""
    SELECT id FROM orders 
    WHERE customer_id IN (7, 10)
""").fetchall()]

print(f"Dummy orders count: {len(dummy_order_ids)}")
print(f"Dummy order IDs: {dummy_order_ids}")
print(f"Legitimate orders count: {len(legit_order_ids)}")
print(f"Legitimate order IDs: {legit_order_ids}")

# Check related records to be deleted
dummy_items = conn.execute("SELECT COUNT(*) FROM order_items WHERE order_id IN ({})".format(','.join(map(str, dummy_order_ids)))).fetchone()[0]
dummy_payments = conn.execute("SELECT COUNT(*) FROM payments WHERE order_id IN ({})".format(','.join(map(str, dummy_order_ids)))).fetchone()[0]
dummy_deliveries = conn.execute("SELECT COUNT(*) FROM deliveries WHERE order_id IN ({})".format(','.join(map(str, dummy_order_ids)))).fetchone()[0]

# Check related records to be preserved
legit_items = conn.execute("SELECT COUNT(*) FROM order_items WHERE order_id IN ({})".format(','.join(map(str, legit_order_ids)))).fetchone()[0]
legit_payments = conn.execute("SELECT COUNT(*) FROM payments WHERE order_id IN ({})".format(','.join(map(str, legit_order_ids)))).fetchone()[0]
legit_deliveries = conn.execute("SELECT COUNT(*) FROM deliveries WHERE order_id IN ({})".format(','.join(map(str, legit_order_ids)))).fetchone()[0]

print(f"\n--- Records proposed for deletion ---")
print(f"Orders: {len(dummy_order_ids)}")
print(f"Order Items: {dummy_items}")
print(f"Payments: {dummy_payments}")
print(f"Deliveries: {dummy_deliveries}")

print(f"\n--- Legitimate records strictly preserved ---")
print(f"Orders: {len(legit_order_ids)}")
print(f"Order Items: {legit_items}")
print(f"Payments: {legit_payments}")
print(f"Deliveries: {legit_deliveries}")

conn.close()
