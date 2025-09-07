-- 016_complete_ingest_schema.sql
-- Complete the ingest schema by adding missing columns

-- Add missing columns to ingest_batches table
ALTER TABLE ingest_batches ADD COLUMN status TEXT DEFAULT 'processing';
ALTER TABLE ingest_batches ADD COLUMN total_assets INTEGER DEFAULT 0;
ALTER TABLE ingest_batches ADD COLUMN processed_assets INTEGER DEFAULT 0;

-- Add missing columns to ingest_assets table if not already present
ALTER TABLE ingest_assets ADD COLUMN phash TEXT;
ALTER TABLE ingest_assets ADD COLUMN header_text TEXT;
ALTER TABLE ingest_assets ADD COLUMN file_size INTEGER;
ALTER TABLE ingest_assets ADD COLUMN created_at TEXT DEFAULT (datetime('now'));
ALTER TABLE ingest_assets ADD COLUMN mime_type TEXT;

-- Update mime_type from existing mime column
UPDATE ingest_assets SET mime_type = mime WHERE mime_type IS NULL;

-- Add missing columns to documents table if not already present
ALTER TABLE documents ADD COLUMN supplier_id TEXT;
ALTER TABLE documents ADD COLUMN fingerprint_hash TEXT;
ALTER TABLE documents ADD COLUMN created_at TEXT DEFAULT (datetime('now'));
ALTER TABLE documents ADD COLUMN assembled_at TEXT;
ALTER TABLE documents ADD COLUMN doc_kind_new TEXT CHECK (doc_kind_new IN ('invoice', 'dn', 'receipt', 'utility'));

-- Update doc_kind_new from existing kind column
UPDATE documents SET doc_kind_new = CASE 
    WHEN kind = 'invoice' THEN 'invoice'
    WHEN kind = 'delivery_note' THEN 'dn'
    ELSE 'receipt'
END WHERE doc_kind_new IS NULL;

-- Add missing columns to document_pages table if not already present
ALTER TABLE document_pages ADD COLUMN ocr_json TEXT;
ALTER TABLE document_pages ADD COLUMN ocr_avg_conf REAL DEFAULT 0.0;
ALTER TABLE document_pages ADD COLUMN ocr_min_conf REAL DEFAULT 0.0;
ALTER TABLE document_pages ADD COLUMN preproc_metrics TEXT;
ALTER TABLE document_pages ADD COLUMN created_at TEXT DEFAULT (datetime('now'));
ALTER TABLE document_pages ADD COLUMN page_no INTEGER;

-- Update page_no from existing page_order column
UPDATE document_pages SET page_no = page_order WHERE page_no IS NULL;

-- Create missing indexes
CREATE INDEX IF NOT EXISTS idx_assets_phash ON ingest_assets(phash);
CREATE INDEX IF NOT EXISTS idx_assets_batch ON ingest_assets(batch_id);
CREATE INDEX IF NOT EXISTS idx_pages_document_id ON document_pages(document_id);
CREATE INDEX IF NOT EXISTS idx_docs_batch_kind ON documents(batch_id, doc_kind_new);
CREATE INDEX IF NOT EXISTS idx_docs_fingerprint ON documents(fingerprint_hash);
CREATE INDEX IF NOT EXISTS idx_docs_supplier ON documents(supplier_id); 