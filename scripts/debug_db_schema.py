import os
import sqlite3
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

try:
    from backend.app.db import DB_PATH
except Exception as exc:
    print("Failed to import DB_PATH:", exc)
    DB_PATH = os.path.join(BASE_DIR, "data", "owlin.db")

print("Using DB_PATH:", DB_PATH)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("PRAGMA table_info(invoices)")
print("INVOICES =", [row[1] for row in cursor.fetchall()])

cursor.execute("PRAGMA table_info(documents)")
print("DOCUMENTS =", [row[1] for row in cursor.fetchall()])

conn.close()

