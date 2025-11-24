-- Migration 003: Add line items table and document status tracking
-- Apply with: sqlite3 data/owlin.db < migrations/003_add_line_items_and_status.sql

-- Add status and confidence columns to documents table
ALTER TABLE documents ADD COLUMN status TEXT DEFAULT 'pending';
ALTER TABLE documents ADD COLUMN ocr_confidence REAL DEFAULT 0.0;
ALTER TABLE documents ADD COLUMN ocr_stage TEXT DEFAULT 'upload';
ALTER TABLE documents ADD COLUMN ocr_error TEXT DEFAULT NULL;

-- Create invoice_line_items table
CREATE TABLE IF NOT EXISTS invoice_line_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id TEXT NOT NULL,
    invoice_id TEXT,
    line_number INTEGER NOT NULL,
    description TEXT,
    qty REAL,
    unit_price REAL,
    total REAL,
    uom TEXT,
    confidence REAL DEFAULT 0.9,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(doc_id) REFERENCES documents(id),
    FOREIGN KEY(invoice_id) REFERENCES invoices(id)
);

CREATE INDEX IF NOT EXISTS idx_line_items_doc_id ON invoice_line_items(doc_id);
CREATE INDEX IF NOT EXISTS idx_line_items_invoice_id ON invoice_line_items(invoice_id);

-- Add confidence column to invoices table if not exists
ALTER TABLE invoices ADD COLUMN confidence REAL DEFAULT 0.9;
ALTER TABLE invoices ADD COLUMN status TEXT DEFAULT 'scanned';
ALTER TABLE invoices ADD COLUMN venue TEXT DEFAULT 'Main Restaurant';
ALTER TABLE invoices ADD COLUMN issues_count INTEGER DEFAULT 0;
ALTER TABLE invoices ADD COLUMN paired INTEGER DEFAULT 0;
ALTER TABLE invoices ADD COLUMN created_at TEXT DEFAULT CURRENT_TIMESTAMP;

