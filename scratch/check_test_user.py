import sqlite3
from werkzeug.security import check_password_hash

conn = sqlite3.connect(r'c:\xampp\htdocs\RML_Construction_Supply\RML\rml_database.db')
conn.row_factory = sqlite3.Row
user = conn.execute("SELECT * FROM users WHERE email = 'new_customer_test@example.com'").fetchone()
if user:
    print('Password matches Strong@Password2026?', check_password_hash(user['password_hash'], 'Strong@Password2026'))
conn.close()
