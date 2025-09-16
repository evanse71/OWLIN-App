-- Documents table (file storage)
CREATE TABLE IF NOT EXISTS documents (
  id TEXT PRIMARY KEY,
  path TEXT NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Invoices
CREATE TABLE IF NOT EXISTS invoices (
  id TEXT PRIMARY KEY,
  supplier TEXT,
  invoice_date TEXT,
  status TEXT DEFAULT 'scanned',
  currency TEXT DEFAULT 'GBP',
  document_id TEXT,
  page_no INTEGER DEFAULT 0,
  total_value REAL,
  FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_invoices_document ON invoices(document_id);

-- Invoice line items
CREATE TABLE IF NOT EXISTS invoice_line_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  invoice_id TEXT NOT NULL,
  description TEXT,
  quantity REAL DEFAULT 0,
  unit_price REAL DEFAULT 0,
  total REAL DEFAULT 0,
  uom TEXT,
  vat_rate REAL DEFAULT 0,
  source TEXT DEFAULT 'ocr',
  FOREIGN KEY(invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_items_invoice_id ON invoice_line_items(invoice_id);

-- Delivery notes (basic)
CREATE TABLE IF NOT EXISTS delivery_notes (
  id TEXT PRIMARY KEY,
  supplier TEXT,
  note_date TEXT,
  status TEXT DEFAULT 'scanned',
  document_id TEXT,
  page_no INTEGER DEFAULT 0,
  total_amount REAL,
  FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE SET NULL
);

-- Processing jobs for UI progress (simple polling)
CREATE TABLE IF NOT EXISTS processing_jobs (
  id TEXT PRIMARY KEY,
  kind TEXT, -- 'invoice' | 'delivery_note' | 'unknown'
  status TEXT, -- queued|processing|parsed|persisted|done|error
  current_page INTEGER DEFAULT 0,
  total_pages INTEGER DEFAULT 0,
  message TEXT,
  created_ids TEXT, -- JSON array of created entity ids
  document_id TEXT,
  FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE SET NULL
);
