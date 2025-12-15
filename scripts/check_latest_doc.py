import sqlite3

conn = sqlite3.connect('data/owlin.db')
cur = conn.cursor()
cur.execute('SELECT id, filename, status, ocr_stage, ocr_error FROM documents ORDER BY id DESC LIMIT 1')
row = cur.fetchone()
if row:
    print(f"Latest Doc: {row[0]}")
    print(f"Filename: {row[1]}")
    print(f"Status: {row[2]}")
    print(f"Stage: {row[3]}")
    print(f"Error: {row[4][:500] if row[4] else 'None'}")
    
    # Check invoice
    cur.execute('SELECT supplier, date, value, invoice_number FROM invoices WHERE doc_id = ?', (row[0],))
    inv = cur.fetchone()
    if inv:
        print(f"\nInvoice Data:")
        print(f"  Supplier: {inv[0]}")
        print(f"  Date: {inv[1]}")
        print(f"  Total: {inv[2]}")
        print(f"  Invoice Number: {inv[3]}")
else:
    print("No documents found")
conn.close()

