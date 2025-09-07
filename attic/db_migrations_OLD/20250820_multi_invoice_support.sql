-- Multi-Invoice PDF Support Migration
-- Adds fields for invoice boundary detection and manual review

-- Add new columns to invoices table for multi-invoice support
ALTER TABLE invoices ADD COLUMN requires_manual_review BOOLEAN DEFAULT FALSE;
ALTER TABLE invoices ADD COLUMN page_range TEXT; -- e.g., "1-3", "4-6"
ALTER TABLE invoices ADD COLUMN parent_pdf_filename TEXT; -- Original PDF filename
ALTER TABLE invoices ADD COLUMN invoice_block_id TEXT; -- For grouping related invoices
ALTER TABLE invoices ADD COLUMN boundary_confidence REAL DEFAULT 1.0; -- Confidence of boundary detection

-- Add indexes for better performance
CREATE INDEX IF NOT EXISTS idx_invoices_parent_pdf ON invoices(parent_pdf_filename);
CREATE INDEX IF NOT EXISTS idx_invoices_manual_review ON invoices(requires_manual_review);
CREATE INDEX IF NOT EXISTS idx_invoices_block_id ON invoices(invoice_block_id);

-- Update existing invoices to have default values
UPDATE invoices SET requires_manual_review = FALSE WHERE requires_manual_review IS NULL;
UPDATE invoices SET boundary_confidence = 1.0 WHERE boundary_confidence IS NULL;

-- Create table for OCR retry tracking
CREATE TABLE IF NOT EXISTS ocr_retry_log (
    id TEXT PRIMARY KEY,
    invoice_id TEXT NOT NULL,
    retry_count INTEGER DEFAULT 0,
    last_retry_timestamp TEXT,
    retry_reason TEXT,
    success BOOLEAN DEFAULT FALSE,
    confidence_improvement REAL DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
);

-- Create index for retry log
CREATE INDEX IF NOT EXISTS idx_ocr_retry_invoice_id ON ocr_retry_log(invoice_id);
CREATE INDEX IF NOT EXISTS idx_ocr_retry_timestamp ON ocr_retry_log(last_retry_timestamp); 