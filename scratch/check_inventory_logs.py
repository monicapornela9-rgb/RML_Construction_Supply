import sys
import os

sys.path.insert(0, os.path.abspath('RML'))
from db import get_db

conn = get_db()
logs = conn.execute("SELECT * FROM inventory_logs").fetchall()
print(f"Total inventory logs: {len(logs)}")
for l in logs:
    print(dict(l))
conn.close()
