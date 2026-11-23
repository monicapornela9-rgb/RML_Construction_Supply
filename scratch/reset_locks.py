import sys
import os

sys.path.insert(0, os.path.abspath('RML'))
from db import get_db

conn = get_db()
conn.execute("UPDATE users SET failed_login_attempts = 0, locked_until = NULL")
conn.commit()
conn.close()
print("All account locks reset successfully.")
