import sqlite3

conn = sqlite3.connect('data/owlin.db')
cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%document%'")
tables = cursor.fetchall()
print('Document tables:', tables)

# Check if there are any documents with proper IDs
cursor = conn.execute("SELECT COUNT(*) FROM documents WHERE id IS NOT NULL")
count = cursor.fetchone()
print('Documents with IDs:', count[0])

# Check the actual data
cursor = conn.execute("SELECT * FROM documents LIMIT 3")
docs = cursor.fetchall()
print('Sample documents:')
for i, doc in enumerate(docs):
    print(f'  {i}: {doc}')

conn.close()
