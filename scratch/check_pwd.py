import sys
import os

sys.path.insert(0, os.path.abspath('RML'))
from db import get_db
from werkzeug.security import check_password_hash

conn = get_db()
u4 = conn.execute("SELECT email, password_hash FROM users WHERE id = 4").fetchone()
print("customer@rml.com:", check_password_hash(u4["password_hash"], "customer123"))

u10 = conn.execute("SELECT email, password_hash FROM users WHERE id = 10").fetchone()
for pwd in ["Password123!", "Strong@Password2026", "customer123", "password123", "monica123"]:
    if check_password_hash(u10["password_hash"], pwd):
        print(f"monicapornela9@gmail.com password is: {pwd}")
        break
else:
    print("monica password not found among common list")
conn.close()
