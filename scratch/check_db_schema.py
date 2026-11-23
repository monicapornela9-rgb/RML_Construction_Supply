import sqlite3

conn = sqlite3.connect('RML/rml_database.db')
conn.row_factory = sqlite3.Row

tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print("Tables in DB:", tables)

for t in tables:
    cols = [c[1] for c in conn.execute(f"PRAGMA table_info({t})").fetchall()]
    count = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    print(f"\nTable: {t} (Count: {count})")
    print("  Columns:", cols)

print("\n--- Users Data Summary ---")
users = conn.execute("SELECT id, staff_id, name, email, phone, role, is_active, created_at FROM users").fetchall()
for u in users:
    print(dict(u))

conn.close()
