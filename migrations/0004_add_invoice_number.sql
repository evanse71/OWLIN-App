-- Migration: Add invoice_number column to invoices table
-- Date: 2025-12-03
-- Purpose: Store extracted invoice numbers from OCR (e.g., INV-12345)

-- Add invoice_number column (nullable to support existing records)
ALTER TABLE invoices ADD COLUMN invoice_number TEXT;

-- Create index for faster lookups by invoice number
CREATE INDEX IF NOT EXISTS idx_invoices_invoice_number ON invoices(invoice_number);

-- Log migration
INSERT INTO schema_version (version, description, applied_at)
VALUES (4, 'Add invoice_number column to invoices table', datetime('now'));

