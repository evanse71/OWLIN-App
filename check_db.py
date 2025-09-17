import sqlite3

conn = sqlite3.connect('data/owlin.db')
cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cursor.fetchall()]
print('Tables:', tables)

if 'invoice_pages' in tables:
    cursor = conn.execute("PRAGMA table_info(invoice_pages)")
    columns = [row[1] for row in cursor.fetchall()]
    print('invoice_pages columns:', columns)
else:
    print('invoice_pages table not found')

conn.close()
