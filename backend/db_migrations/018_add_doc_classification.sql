-- Migration 018: Add document classification columns
-- Adds doc_type_confidence and doc_type_reasons to documents table

-- Add doc_type_confidence column (0-100 scale)
ALTER TABLE documents ADD COLUMN doc_type_confidence REAL DEFAULT 0.0;

-- Add doc_type_reasons column (JSON array of strings)
ALTER TABLE documents ADD COLUMN doc_type_reasons TEXT;

-- Create index on doc_type_confidence for filtering/sorting
CREATE INDEX IF NOT EXISTS idx_documents_doc_type_confidence ON documents(doc_type_confidence);

