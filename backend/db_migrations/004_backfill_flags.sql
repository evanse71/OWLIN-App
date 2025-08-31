-- Migration 004: Backfill Flags
-- Initialize JSON/text flag columns to '[]' where NULL

-- Backfill validation_flags in invoices
UPDATE invoices SET validation_flags = '[]' WHERE validation_flags IS NULL;

-- Backfill canonical_quantities in invoices  
UPDATE invoices SET canonical_quantities = '[]' WHERE canonical_quantities IS NULL;

-- Backfill parsed_metadata in invoices
UPDATE invoices SET parsed_metadata = '{}' WHERE parsed_metadata IS NULL;

-- Backfill validation_flags in delivery_notes
UPDATE delivery_notes SET validation_flags = '[]' WHERE validation_flags IS NULL;

-- Backfill canonical_quantities in delivery_notes
UPDATE delivery_notes SET canonical_quantities = '[]' WHERE canonical_quantities IS NULL;

-- Backfill parsed_metadata in delivery_notes
UPDATE delivery_notes SET parsed_metadata = '{}' WHERE parsed_metadata IS NULL;

-- Backfill line_flags in invoice_items
UPDATE invoice_items SET line_flags = '[]' WHERE line_flags IS NULL; 