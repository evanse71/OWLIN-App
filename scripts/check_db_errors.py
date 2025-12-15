import sqlite3
import sys

conn = sqlite3.connect('data/owlin.db')
cur = conn.cursor()
cur.execute('SELECT id, filename, status, ocr_stage, ocr_error FROM documents WHERE status = ? ORDER BY id DESC LIMIT 5', ('error',))
rows = cur.fetchall()
for r in rows:
    print(f"Doc: {r[0]}")
    print(f"  Filename: {r[1]}")
    print(f"  Status: {r[2]}")
    print(f"  Stage: {r[3]}")
    print(f"  Error: {r[4][:500] if r[4] else 'None'}")
    print()
conn.close()

