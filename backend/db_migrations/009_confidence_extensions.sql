-- Migration 009: Extend invoice_line_items with per-field confidence columns
ALTER TABLE invoice_line_items ADD COLUMN IF NOT EXISTS description_confidence REAL;
ALTER TABLE invoice_line_items ADD COLUMN IF NOT EXISTS quantity_confidence REAL;
ALTER TABLE invoice_line_items ADD COLUMN IF NOT EXISTS unit_price_confidence REAL;
ALTER TABLE invoice_line_items ADD COLUMN IF NOT EXISTS vat_confidence REAL;
ALTER TABLE invoice_line_items ADD COLUMN IF NOT EXISTS line_total_confidence REAL; 