-- 015_ingest_assembly.sql
-- Ingest and assembly system for multi-format document processing

-- Add missing columns to ingest_batches table
ALTER TABLE ingest_batches ADD COLUMN status TEXT DEFAULT 'processing';
ALTER TABLE ingest_batches ADD COLUMN total_assets INTEGER DEFAULT 0;
ALTER TABLE ingest_batches ADD COLUMN processed_assets INTEGER DEFAULT 0;

-- Modify existing ingest_assets table to add fingerprinting columns
ALTER TABLE ingest_assets ADD COLUMN phash TEXT;
ALTER TABLE ingest_assets ADD COLUMN header_text TEXT;
ALTER TABLE ingest_assets ADD COLUMN file_size INTEGER;
ALTER TABLE ingest_assets ADD COLUMN created_at TEXT DEFAULT (datetime('now'));

-- Rename mime column to mime_type for consistency
ALTER TABLE ingest_assets ADD COLUMN mime_type TEXT;
UPDATE ingest_assets SET mime_type = mime;

-- Modify existing documents table to add assembly columns
ALTER TABLE documents ADD COLUMN supplier_id TEXT;
ALTER TABLE documents ADD COLUMN fingerprint_hash TEXT;
ALTER TABLE documents ADD COLUMN created_at TEXT DEFAULT (datetime('now'));
ALTER TABLE documents ADD COLUMN assembled_at TEXT;

-- Update doc_kind constraint if needed
ALTER TABLE documents ADD COLUMN doc_kind_new TEXT CHECK (doc_kind_new IN ('invoice', 'dn', 'receipt', 'utility'));
UPDATE documents SET doc_kind_new = CASE 
    WHEN kind = 'invoice' THEN 'invoice'
    WHEN kind = 'delivery_note' THEN 'dn'
    ELSE 'receipt'
END;

-- Modify existing document_pages table to add OCR and preprocessing columns
ALTER TABLE document_pages ADD COLUMN ocr_json TEXT;
ALTER TABLE document_pages ADD COLUMN ocr_avg_conf REAL DEFAULT 0.0;
ALTER TABLE document_pages ADD COLUMN ocr_min_conf REAL DEFAULT 0.0;
ALTER TABLE document_pages ADD COLUMN preproc_metrics TEXT; -- JSON of deskew, threshold, denoise, contrast
ALTER TABLE document_pages ADD COLUMN created_at TEXT DEFAULT (datetime('now'));

-- Add page_no column for consistency (existing table uses page_order)
ALTER TABLE document_pages ADD COLUMN page_no INTEGER;
UPDATE document_pages SET page_no = page_order WHERE page_no IS NULL;

-- Critical indexes for performance
CREATE INDEX IF NOT EXISTS idx_assets_phash ON ingest_assets(phash);
CREATE INDEX IF NOT EXISTS idx_assets_batch ON ingest_assets(batch_id);
CREATE INDEX IF NOT EXISTS idx_pages_document_id ON document_pages(document_id);
CREATE INDEX IF NOT EXISTS idx_docs_batch_kind ON documents(batch_id, doc_kind_new);
CREATE INDEX IF NOT EXISTS idx_docs_fingerprint ON documents(fingerprint_hash);
CREATE INDEX IF NOT EXISTS idx_docs_supplier ON documents(supplier_id);

-- Add missing columns to existing tables if they don't exist
-- OCR confidence columns for invoices (if not already present)
-- Note: SQLite doesn't support IF NOT EXISTS for ADD COLUMN, so we'll handle errors gracefully
-- in the migration runner
ALTER TABLE invoices ADD COLUMN ocr_avg_conf REAL DEFAULT 0.0;

ALTER TABLE invoices ADD COLUMN ocr_min_conf REAL DEFAULT 0.0;

-- Line confidence column for invoice line items
ALTER TABLE invoice_line_items ADD COLUMN line_confidence REAL DEFAULT 0.0; 