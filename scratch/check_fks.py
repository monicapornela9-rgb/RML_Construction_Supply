import sys
import os

sys.path.insert(0, os.path.abspath('RML'))
from db import get_db

conn = get_db()
tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print("Tables in DB:", tables)

for t in tables:
    fks = conn.execute(f"PRAGMA foreign_key_list({t})").fetchall()
    for fk in fks:
        if fk[2] == 'orders':
            print(f"Table '{t}' references 'orders' on column '{fk[3]}'")

conn.close()
