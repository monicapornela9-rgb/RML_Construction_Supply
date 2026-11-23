import sys
import os

sys.path.insert(0, os.path.abspath('RML'))
from db import get_db

conn = get_db()
u = conn.execute("SELECT id, name, email, password_hash FROM users WHERE id IN (7, 10)").fetchall()
for r in u:
    print(dict(r))
conn.close()
