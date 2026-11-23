import sqlite3

conn = sqlite3.connect(r'c:\xampp\htdocs\RML_Construction_Supply\RML\rml_database.db')
cur = conn.cursor()
tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print('Existing tables in DB:', tables)
for t in tables:
    cols = [r[1] for r in cur.execute(f"PRAGMA table_info({t})").fetchall()]
    print(f'  {t}: {cols}')
conn.close()
