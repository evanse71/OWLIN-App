-- Vertical Cards Migration - Add fields for editable tables, verification flags, addresses, and signatures
-- Migration 008: Vertical Cards Enhancement

-- Add new columns to invoices table
ALTER TABLE invoices ADD COLUMN addresses TEXT; -- JSON: { supplier_address, delivery_address }
ALTER TABLE invoices ADD COLUMN signature_regions TEXT; -- JSON: [{ page, bbox, image_b64 }]
ALTER TABLE invoices ADD COLUMN verification_status TEXT DEFAULT 'unreviewed'; -- 'unreviewed' | 'needs_review' | 'reviewed'

-- Create invoice_line_items table if it doesn't exist
CREATE TABLE IF NOT EXISTS invoice_line_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id TEXT NOT NULL,
    row_idx INTEGER,
    page INTEGER,
    description TEXT,
    quantity REAL,
    unit TEXT,
    unit_price REAL,
    vat_rate REAL DEFAULT 0.0,
    line_total REAL,
    confidence REAL DEFAULT 1.0,
    flags TEXT, -- JSON: ["needs_check", "unit?", "qty_suspicious", "vat_missing", "sum_mismatch"]
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_invoice_line_items_invoice_id ON invoice_line_items(invoice_id);
CREATE INDEX IF NOT EXISTS idx_invoice_line_items_page ON invoice_line_items(page);
CREATE INDEX IF NOT EXISTS idx_invoice_line_items_row_idx ON invoice_line_items(row_idx);

-- Add indexes for new invoice columns
CREATE INDEX IF NOT EXISTS idx_invoices_verification_status ON invoices(verification_status);
CREATE INDEX IF NOT EXISTS idx_invoices_addresses ON invoices(addresses);

-- Update existing invoices to have default verification_status
UPDATE invoices SET verification_status = 'unreviewed' WHERE verification_status IS NULL; 