import sys
import os

sys.path.insert(0, os.path.abspath('RML'))
from db import get_db
from werkzeug.security import check_password_hash

conn = get_db()
users = conn.execute("SELECT id, email, password_hash FROM users WHERE role = 'customer'").fetchall()
test_passwords = ["customer123", "password123", "Password123!", "Strong@Password2026", "admin123", "driver123", "rml123", "monica123", "123456", "password"]

for u in users:
    matched = None
    for p in test_passwords:
        if check_password_hash(u["password_hash"], p):
            matched = p
            break
    print(f"User {u['id']} ({u['email']}) -> Password: {matched}")

conn.close()
