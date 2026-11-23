import sqlite3
from werkzeug.security import check_password_hash

conn = sqlite3.connect(r'c:\xampp\htdocs\RML_Construction_Supply\RML\rml_database.db')
conn.row_factory = sqlite3.Row
user = conn.execute("SELECT * FROM users WHERE email = 'kirvee518@gmail.com'").fetchone()

candidates = [
    'Strong@Password2026', 'Customer123!', 'customer123', 'admin123', 'Admin123!',
    'Valid@Password123', 'Monica123!', 'monica123', 'Monica123', 'password123',
    'kirvee123', 'Kirvee123!', 'Kirvee518!', 'kirvee518', 'P@ssword123',
    '12345678', 'password', 'Rml12345!', 'RML12345!'
]
for p in candidates:
    if check_password_hash(user['password_hash'], p):
        print(f"MATCH FOUND: '{p}'")
        break
else:
    print("No match found among candidate passwords.")
conn.close()
