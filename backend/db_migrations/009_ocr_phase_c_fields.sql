-- Migration: Add Phase-C OCR fields
-- Adds doc_type, doc_type_score, policy_action, reasons_json, validation_json, and row-level fields

-- Add new columns to invoices table
ALTER TABLE invoices ADD COLUMN doc_type TEXT;
ALTER TABLE invoices ADD COLUMN doc_type_score REAL DEFAULT 0.0;
ALTER TABLE invoices ADD COLUMN policy_action TEXT;
ALTER TABLE invoices ADD COLUMN reasons_json TEXT;
ALTER TABLE invoices ADD COLUMN validation_json TEXT;

-- Add row-level fields to line_items table
ALTER TABLE line_items ADD COLUMN line_confidence REAL DEFAULT 0.0;
ALTER TABLE line_items ADD COLUMN row_reasons_json TEXT;
ALTER TABLE line_items ADD COLUMN computed_total BOOLEAN DEFAULT FALSE;
ALTER TABLE line_items ADD COLUMN unit_original TEXT;

-- Create index for policy actions
CREATE INDEX IF NOT EXISTS idx_invoices_policy_action ON invoices(policy_action);
CREATE INDEX IF NOT EXISTS idx_invoices_doc_type ON invoices(doc_type);

-- Create audit_log table for policy decisions
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    user_id TEXT,
    session_id TEXT,
    action TEXT NOT NULL,
    document_id INTEGER,
    policy_action TEXT,
    reasons_json TEXT,
    confidence REAL,
    processing_time_ms INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_log_action ON audit_log(action);
CREATE INDEX IF NOT EXISTS idx_audit_log_policy_action ON audit_log(policy_action); 