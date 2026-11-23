import sys
import os

sys.path.insert(0, os.path.abspath('RML'))
from db import get_db

conn = get_db()
trucks = conn.execute("SELECT * FROM trucks").fetchall()
print("Trucks:")
for t in trucks:
    print(dict(t))
conn.close()
