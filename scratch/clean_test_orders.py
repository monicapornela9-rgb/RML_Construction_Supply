import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "RML"))
from db import get_db

conn = get_db()
conn.execute("DELETE FROM order_items WHERE order_id IN (SELECT id FROM orders WHERE order_code LIKE '#TEST%')")
conn.execute("DELETE FROM deliveries WHERE order_id IN (SELECT id FROM orders WHERE order_code LIKE '#TEST%')")
conn.execute("DELETE FROM orders WHERE order_code LIKE '#TEST%'")
conn.commit()
conn.close()
print("Cleaned test orders successfully.")
