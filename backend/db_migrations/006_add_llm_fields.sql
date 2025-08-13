-- backend/db_migrations/006_add_llm_fields.sql
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS field_confidence TEXT;   -- JSON
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS raw_extraction TEXT;     -- JSON
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS warnings TEXT;           -- JSON

CREATE TABLE IF NOT EXISTS invoice_line_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  invoice_id TEXT NOT NULL,
  row_idx INTEGER,
  page INTEGER,
  description TEXT,
  quantity REAL,
  unit TEXT,
  unit_price REAL,
  line_total REAL,
  confidence REAL,
  FOREIGN KEY(invoice_id) REFERENCES invoices(id)
); 