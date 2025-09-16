import sqlite3, pathlib
DB = pathlib.Path("data/owlin.db")
DB.parent.mkdir(parents=True, exist_ok=True)
con = sqlite3.connect(str(DB)); cur = con.cursor()

cur.execute("""CREATE TABLE IF NOT EXISTS documents(
  id TEXT PRIMARY KEY, sha256 TEXT UNIQUE, type TEXT, path TEXT,
  ocr_confidence REAL, created_at TEXT DEFAULT CURRENT_TIMESTAMP
);""")

cur.execute("""CREATE TABLE IF NOT EXISTS invoices(
  id TEXT PRIMARY KEY, document_id TEXT, supplier TEXT,
  invoice_date TEXT, total_value REAL, matched_delivery_note_id TEXT,
  FOREIGN KEY(document_id) REFERENCES documents(id)
);""")

cur.execute("""CREATE TABLE IF NOT EXISTS delivery_notes(
  id TEXT PRIMARY KEY, document_id TEXT, supplier TEXT, delivery_date TEXT,
  FOREIGN KEY(document_id) REFERENCES documents(id)
);""")

cur.execute("""CREATE TABLE IF NOT EXISTS invoice_line_items(
  id TEXT PRIMARY KEY, invoice_id TEXT, description TEXT, qty REAL,
  unit_price REAL, total REAL, FOREIGN KEY(invoice_id) REFERENCES invoices(id)
);""")

cur.execute("""CREATE TABLE IF NOT EXISTS delivery_note_line_items(
  id TEXT PRIMARY KEY, delivery_note_id TEXT, description TEXT, qty REAL,
  FOREIGN KEY(delivery_note_id) REFERENCES delivery_notes(id)
);""")

cur.execute("CREATE INDEX IF NOT EXISTS idx_documents_sha ON documents(sha256)")
cur.execute("CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(type)")
cur.execute("CREATE INDEX IF NOT EXISTS idx_invoices_doc ON invoices(document_id)")
cur.execute("CREATE INDEX IF NOT EXISTS idx_dn_doc ON delivery_notes(document_id)")
cur.execute("CREATE INDEX IF NOT EXISTS idx_invoices_supplier_date ON invoices(supplier, invoice_date)")
cur.execute("CREATE INDEX IF NOT EXISTS idx_dn_supplier_date ON delivery_notes(supplier, delivery_date)")
con.commit()
print("Migration + indices complete.")
