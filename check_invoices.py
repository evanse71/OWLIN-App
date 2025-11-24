import sqlite3

# Connect to the backup database
conn = sqlite3.connect('data/owlin.db')
cursor = conn.cursor()

# Check invoices table
cursor.execute('SELECT COUNT(*) FROM invoices')
invoice_count = cursor.fetchone()[0]
print(f'Invoices table count: {invoice_count}')

if invoice_count > 0:
    cursor.execute('SELECT * FROM invoices LIMIT 5')
    rows = cursor.fetchall()
    print('\nSample invoices:')
    for row in rows:
        print(f'  {row}')

# Check delivery_notes table
cursor.execute('SELECT COUNT(*) FROM delivery_notes')
dn_count = cursor.fetchone()[0]
print(f'\nDelivery notes table count: {dn_count}')

if dn_count > 0:
    cursor.execute('SELECT * FROM delivery_notes LIMIT 5')
    rows = cursor.fetchall()
    print('\nSample delivery notes:')
    for row in rows:
        print(f'  {row}')

# Check table schemas
print('\nInvoices table schema:')
cursor.execute("PRAGMA table_info(invoices)")
for col in cursor.fetchall():
    print(f'  {col[1]} ({col[2]})')

print('\nDelivery notes table schema:')
cursor.execute("PRAGMA table_info(delivery_notes)")
for col in cursor.fetchall():
    print(f'  {col[1]} ({col[2]})')

conn.close()
