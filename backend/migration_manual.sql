-- Manual migration script for Owlin OCR
-- Run this if you want to manually update the database schema

-- idempotent schema normalization
CREATE TABLE IF NOT EXISTS uploaded_files (
  file_hash    TEXT PRIMARY KEY,
  absolute_path TEXT NOT NULL,
  size_bytes    INTEGER,
  created_at    TEXT DEFAULT CURRENT_TIMESTAMP
);

-- add columns only if missing
PRAGMA foreign_keys=off;
BEGIN TRANSACTION;

-- invoices.line_items
SELECT CASE 
  WHEN COUNT(*) = 0 THEN 
    (SELECT 'ALTER TABLE invoices ADD COLUMN line_items TEXT DEFAULT "[]"' FROM pragma_table_info('invoices') WHERE name='line_items' LIMIT 1)
  ELSE 'SELECT "line_items column already exists"'
END FROM pragma_table_info('invoices') WHERE name='line_items';

-- invoices.error_message
SELECT CASE 
  WHEN COUNT(*) = 0 THEN 
    (SELECT 'ALTER TABLE invoices ADD COLUMN error_message TEXT' FROM pragma_table_info('invoices') WHERE name='error_message' LIMIT 1)
  ELSE 'SELECT "error_message column already exists"'
END FROM pragma_table_info('invoices') WHERE name='error_message';

-- invoices.page_range
SELECT CASE 
  WHEN COUNT(*) = 0 THEN 
    (SELECT 'ALTER TABLE invoices ADD COLUMN page_range TEXT' FROM pragma_table_info('invoices') WHERE name='page_range' LIMIT 1)
  ELSE 'SELECT "page_range column already exists"'
END FROM pragma_table_info('invoices') WHERE name='page_range';

COMMIT;
PRAGMA foreign_keys=on;

-- Verify schema
SELECT "Schema verification:" as info;
SELECT name, type FROM pragma_table_info('uploaded_files');
SELECT name, type FROM pragma_table_info('invoices') WHERE name IN ('line_items', 'error_message', 'page_range'); 