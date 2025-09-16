CREATE TABLE IF NOT EXISTS invoice_line_items (
  id TEXT PRIMARY KEY,
  invoice_id TEXT NOT NULL,
  description TEXT,
  quantity REAL DEFAULT 0,
  unit_price REAL DEFAULT 0,
  total REAL DEFAULT 0,
  uom TEXT,
  vat_rate REAL DEFAULT 0,
  FOREIGN KEY(invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_invoice_line_items_invoice_id ON invoice_line_items(invoice_id);
