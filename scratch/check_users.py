import sqlite3
conn = sqlite3.connect(r"RML\rml_database.db")
conn.row_factory = sqlite3.Row
users = conn.execute("SELECT id, name, email, role, password_hash FROM users").fetchall()
for u in users:
    print(u["id"], u["email"], u["role"], u["password_hash"][:15])
