-- Migration 007: Add SKU column to invoice_line_items table
-- Apply with: sqlite3 data/owlin.db < migrations/007_add_sku_to_line_items.sql

-- Add SKU column to invoice_line_items table
ALTER TABLE invoice_line_items ADD COLUMN sku TEXT DEFAULT NULL;

-- Create index on SKU for performance (partial index for non-null values)
CREATE INDEX IF NOT EXISTS idx_line_items_sku ON invoice_line_items(sku) WHERE sku IS NOT NULL;

