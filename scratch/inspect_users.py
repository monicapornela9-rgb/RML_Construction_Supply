import sqlite3
from werkzeug.security import check_password_hash

conn = sqlite3.connect(r'c:\xampp\htdocs\RML_Construction_Supply\RML\rml_database.db')
conn.row_factory = sqlite3.Row
users = conn.execute("SELECT id, name, email, password_hash, role FROM users WHERE role = 'customer'").fetchall()
for u in users:
    for test_pwd in ['customer123', 'Customer123!', 'Admin123!', 'admin123', 'password']:
        if check_password_hash(u['password_hash'], test_pwd):
            print(f"{u['id']}: {u['name']} ({u['email']}) -> password is '{test_pwd}'")
            break
    else:
        print(f"{u['id']}: {u['name']} ({u['email']}) -> unknown password hash: {u['password_hash'][:25]}...")
conn.close()
