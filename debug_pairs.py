import sqlite3

conn = sqlite3.connect('data/owlin.db')
cursor = conn.execute('SELECT id, supplier, invoice_no, delivery_no FROM documents WHERE id IN (1, 2)')
docs = cursor.fetchall()
print('Documents 1,2:', docs)

cursor = conn.execute("""
SELECT
  p.id, p.confidence, p.status,
  di.id AS inv_id, di.supplier AS inv_supplier, di.invoice_no AS inv_no,
  di.doc_date AS inv_date, di.total AS inv_total,
  dd.id AS dn_id, dd.supplier AS dn_supplier, dd.delivery_no AS dn_no,
  dd.doc_date AS dn_date, dd.total AS dn_total
FROM pairs p
JOIN documents di ON di.id = p.invoice_id
JOIN documents dd ON dd.id = p.delivery_id
WHERE p.status = 'suggested'
""")
pairs = cursor.fetchall()
print('JOIN result:', pairs)

# Check if documents exist
cursor = conn.execute('SELECT COUNT(*) FROM documents WHERE id = 1')
count1 = cursor.fetchone()
print('Document 1 exists:', count1[0])

cursor = conn.execute('SELECT COUNT(*) FROM documents WHERE id = 2')
count2 = cursor.fetchone()
print('Document 2 exists:', count2[0])

conn.close()
