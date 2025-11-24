import sqlite3
import os

# Connect to the backup database
db_path = r'data\owlin.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check documents count
cursor.execute('SELECT COUNT(*) FROM documents')
count = cursor.fetchone()[0]
print(f'Documents count: {count}')

# Check sample documents
cursor.execute('SELECT id, supplier, invoice_no, doc_date, total, doc_type FROM documents LIMIT 10')
rows = cursor.fetchall()
print('\nSample documents:')
for row in rows:
    print(f'  ID: {row[0]}, Supplier: {row[1]}, Invoice: {row[2]}, Date: {row[3]}, Total: {row[4]}, Type: {row[5]}')

# Check if there are any invoices specifically
cursor.execute("SELECT COUNT(*) FROM documents WHERE doc_type = 'invoice' OR invoice_no IS NOT NULL")
invoice_count = cursor.fetchone()[0]
print(f'\nInvoice documents count: {invoice_count}')

# Check all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print(f'\nAvailable tables: {[table[0] for table in tables]}')

conn.close()
