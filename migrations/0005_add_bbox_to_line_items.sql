-- Migration: Add bbox column to invoice_line_items table
-- Date: 2025-12-03
-- Purpose: Store bounding box coordinates [x, y, w, h] for visual verification

-- Add bbox column (TEXT to store JSON array "[x,y,w,h]")
ALTER TABLE invoice_line_items ADD COLUMN bbox TEXT;

-- Create index for queries that filter by bbox presence
CREATE INDEX IF NOT EXISTS idx_line_items_bbox ON invoice_line_items(bbox) WHERE bbox IS NOT NULL;

-- Log migration
INSERT INTO schema_version (version, description, applied_at)
VALUES (5, 'Add bbox column to invoice_line_items table', datetime('now'));

