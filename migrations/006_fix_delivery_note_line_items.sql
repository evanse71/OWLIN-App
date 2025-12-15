-- Migration 006: Fix existing delivery note line items
-- Apply with: sqlite3 data/owlin.db < migrations/006_fix_delivery_note_line_items.sql
--
-- This migration fixes delivery note line items that were stored before the fix
-- was implemented. It updates invoice_id from doc_id to NULL for delivery notes.

-- First, check if doc_type column exists
-- If it doesn't exist, this migration won't do anything (no delivery notes to fix)

-- Update line items for delivery notes
-- Find all documents with doc_type = 'delivery_note' and update their line items
-- to set invoice_id = NULL where invoice_id = doc_id
UPDATE invoice_line_items
SET invoice_id = NULL
WHERE doc_id IN (
    SELECT id FROM documents WHERE doc_type = 'delivery_note'
)
AND invoice_id = doc_id;

-- Verify the migration
-- Count how many delivery note line items were updated
SELECT 
    COUNT(*) as updated_count,
    'Delivery note line items updated' as message
FROM invoice_line_items
WHERE doc_id IN (
    SELECT id FROM documents WHERE doc_type = 'delivery_note'
)
AND invoice_id IS NULL;

