-- Migration 001: Clean Start - Unified Schema
-- This migration creates the complete unified schema from scratch

-- 1. UPLOADED_FILES TABLE - Canonical file storage
CREATE TABLE uploaded_files (
    id TEXT PRIMARY KEY,
    original_filename TEXT NOT NULL,
    canonical_path TEXT NOT NULL UNIQUE,
    file_size INTEGER NOT NULL,
    file_hash TEXT NOT NULL UNIQUE,
    mime_type TEXT NOT NULL,
    doc_type TEXT NOT NULL CHECK (doc_type IN ('invoice', 'delivery_note', 'receipt', 'utility', 'unknown')),
    doc_type_confidence REAL DEFAULT 0.0,
    upload_timestamp TEXT NOT NULL,
    processing_status TEXT NOT NULL DEFAULT 'pending' CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed', 'timeout', 'reviewed')),
    processing_progress INTEGER DEFAULT 0 CHECK (processing_progress >= 0 AND processing_progress <= 100),
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    last_retry_timestamp TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- 2. INVOICES TABLE - Complete invoice data
CREATE TABLE invoices (
    id TEXT PRIMARY KEY,
    file_id TEXT NOT NULL,
    invoice_number TEXT,
    invoice_date TEXT,
    supplier_name TEXT,
    venue TEXT,
    total_amount_pennies INTEGER NOT NULL DEFAULT 0,
    subtotal_pennies INTEGER,
    vat_total_pennies INTEGER,
    vat_rate REAL DEFAULT 20.0,
    currency TEXT DEFAULT 'GBP',
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'scanned', 'parsed', 'matched', 'failed', 'timeout', 'reviewed')),
    confidence REAL NOT NULL DEFAULT 0.0 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    paired BOOLEAN DEFAULT FALSE,
    issues_count INTEGER DEFAULT 0,
    processing_progress INTEGER DEFAULT 0 CHECK (processing_progress >= 0 AND processing_progress <= 100),
    error_message TEXT,
    page_range TEXT,
    validation_flags TEXT, -- JSON array of validation flags
    field_confidence TEXT, -- JSON object of field-specific confidence
    raw_extraction TEXT, -- JSON of raw OCR extraction
    warnings TEXT, -- JSON array of warnings
    addresses TEXT, -- JSON object with supplier_address, delivery_address
    signature_regions TEXT, -- JSON array of signature regions
    verification_status TEXT DEFAULT 'unreviewed' CHECK (verification_status IN ('unreviewed', 'needs_review', 'reviewed')),
    doc_type TEXT DEFAULT 'invoice',
    doc_type_score REAL DEFAULT 1.0,
    policy_action TEXT,
    reasons_json TEXT, -- JSON array of policy reasons
    validation_json TEXT, -- JSON object of validation results
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (file_id) REFERENCES uploaded_files(id) ON DELETE CASCADE
);

-- 3. DELIVERY_NOTES TABLE - Complete delivery note data
CREATE TABLE delivery_notes (
    id TEXT PRIMARY KEY,
    file_id TEXT NOT NULL,
    delivery_note_number TEXT,
    delivery_date TEXT,
    supplier_name TEXT,
    total_items INTEGER DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'scanned', 'parsed', 'matched', 'unmatched', 'failed', 'timeout')),
    confidence REAL NOT NULL DEFAULT 0.0 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    matched_invoice_id TEXT,
    processing_progress INTEGER DEFAULT 0 CHECK (processing_progress >= 0 AND processing_progress <= 100),
    error_message TEXT,
    page_range TEXT,
    validation_flags TEXT, -- JSON array of validation flags
    field_confidence TEXT, -- JSON object of field-specific confidence
    raw_extraction TEXT, -- JSON of raw OCR extraction
    warnings TEXT, -- JSON array of warnings
    doc_type TEXT DEFAULT 'delivery_note',
    doc_type_score REAL DEFAULT 1.0,
    policy_action TEXT,
    reasons_json TEXT, -- JSON array of policy reasons
    validation_json TEXT, -- JSON object of validation results
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (file_id) REFERENCES uploaded_files(id) ON DELETE CASCADE,
    FOREIGN KEY (matched_invoice_id) REFERENCES invoices(id) ON DELETE SET NULL
);

-- 4. INVOICE_LINE_ITEMS TABLE - Unified line items for invoices
CREATE TABLE invoice_line_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id TEXT NOT NULL,
    row_idx INTEGER,
    page INTEGER,
    description TEXT NOT NULL,
    quantity REAL NOT NULL DEFAULT 0,
    unit TEXT,
    unit_price_pennies INTEGER NOT NULL DEFAULT 0,
    vat_rate REAL DEFAULT 20.0,
    line_total_pennies INTEGER NOT NULL DEFAULT 0,
    confidence REAL DEFAULT 1.0 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    flags TEXT, -- JSON array of flags like ["needs_check", "unit?", "qty_suspicious", "vat_missing", "sum_mismatch"]
    line_confidence REAL DEFAULT 1.0,
    row_reasons_json TEXT, -- JSON array of row-specific reasons
    computed_total BOOLEAN DEFAULT FALSE,
    unit_original TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
);

-- 5. DELIVERY_LINE_ITEMS TABLE - Unified line items for delivery notes
CREATE TABLE delivery_line_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    delivery_note_id TEXT NOT NULL,
    row_idx INTEGER,
    page INTEGER,
    description TEXT NOT NULL,
    quantity REAL NOT NULL DEFAULT 0,
    unit TEXT,
    unit_price_pennies INTEGER NOT NULL DEFAULT 0,
    vat_rate REAL DEFAULT 20.0,
    line_total_pennies INTEGER NOT NULL DEFAULT 0,
    confidence REAL DEFAULT 1.0 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    flags TEXT, -- JSON array of flags
    line_confidence REAL DEFAULT 1.0,
    row_reasons_json TEXT, -- JSON array of row-specific reasons
    computed_total BOOLEAN DEFAULT FALSE,
    unit_original TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (delivery_note_id) REFERENCES delivery_notes(id) ON DELETE CASCADE
);

-- 6. JOBS TABLE - Complete job lifecycle management
CREATE TABLE jobs (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL CHECK (kind IN ('upload', 'ocr', 'parse', 'match', 'reprocess')),
    status TEXT NOT NULL DEFAULT 'queued' CHECK (status IN ('queued', 'processing', 'completed', 'failed', 'timeout', 'cancelled')),
    progress INTEGER DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
    meta_json TEXT, -- JSON object with job metadata
    result_json TEXT, -- JSON object with job results
    error TEXT,
    duration_ms INTEGER,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    timeout_seconds INTEGER DEFAULT 300,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- 7. AUDIT_LOG TABLE - Comprehensive audit trail
CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT DEFAULT (datetime('now')),
    user_id TEXT,
    session_id TEXT,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    document_id TEXT,
    policy_action TEXT,
    reasons_json TEXT, -- JSON array of reasons
    confidence REAL,
    processing_time_ms INTEGER,
    metadata_json TEXT, -- JSON object with additional metadata
    created_at TEXT DEFAULT (datetime('now'))
);

-- 8. MATCH_LINKS TABLE - Invoice-Delivery Note matching
CREATE TABLE match_links (
    id TEXT PRIMARY KEY,
    invoice_id TEXT NOT NULL,
    delivery_note_id TEXT NOT NULL,
    confidence REAL NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
    status TEXT NOT NULL CHECK (status IN ('matched', 'partial', 'unmatched', 'conflict')),
    reasons_json TEXT NOT NULL, -- JSON array of matching reasons
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE,
    FOREIGN KEY (delivery_note_id) REFERENCES delivery_notes(id) ON DELETE CASCADE,
    UNIQUE(invoice_id, delivery_note_id)
);

-- 9. MATCH_LINE_LINKS TABLE - Line-level matching details
CREATE TABLE match_line_links (
    id TEXT PRIMARY KEY,
    match_link_id TEXT NOT NULL,
    invoice_line_id INTEGER,
    delivery_line_id INTEGER,
    qty_delta REAL,
    price_delta_pennies INTEGER,
    confidence REAL NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
    status TEXT NOT NULL CHECK (status IN ('ok', 'qty_mismatch', 'price_mismatch', 'missing_on_dn', 'missing_on_inv')),
    reasons_json TEXT NOT NULL, -- JSON array of line-level reasons
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (match_link_id) REFERENCES match_links(id) ON DELETE CASCADE
);

-- 10. PROCESSING_LOGS TABLE - Detailed processing logs
CREATE TABLE processing_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id TEXT NOT NULL,
    stage TEXT NOT NULL CHECK (stage IN ('enqueue', 'dedup_check', 'rasterize', 'ocr', 'parse', 'persist', 'pairing', 'finalize')),
    status TEXT NOT NULL CHECK (status IN ('started', 'completed', 'failed', 'timeout')),
    confidence REAL,
    processing_time_ms INTEGER,
    error_message TEXT,
    metadata_json TEXT, -- JSON object with stage-specific metadata
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (file_id) REFERENCES uploaded_files(id) ON DELETE CASCADE
);

-- Create comprehensive indexes for performance
CREATE INDEX IF NOT EXISTS idx_uploaded_files_hash ON uploaded_files(file_hash);
CREATE INDEX IF NOT EXISTS idx_uploaded_files_status ON uploaded_files(processing_status);
CREATE INDEX IF NOT EXISTS idx_uploaded_files_doc_type ON uploaded_files(doc_type);
CREATE INDEX IF NOT EXISTS idx_uploaded_files_timestamp ON uploaded_files(upload_timestamp);

CREATE INDEX IF NOT EXISTS idx_invoices_file_id ON invoices(file_id);
CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(status);
CREATE INDEX IF NOT EXISTS idx_invoices_supplier ON invoices(supplier_name);
CREATE INDEX IF NOT EXISTS idx_invoices_date ON invoices(invoice_date);
CREATE INDEX IF NOT EXISTS idx_invoices_paired ON invoices(paired);
CREATE INDEX IF NOT EXISTS idx_invoices_confidence ON invoices(confidence);
CREATE INDEX IF NOT EXISTS idx_invoices_verification ON invoices(verification_status);

CREATE INDEX IF NOT EXISTS idx_delivery_notes_file_id ON delivery_notes(file_id);
CREATE INDEX IF NOT EXISTS idx_delivery_notes_status ON delivery_notes(status);
CREATE INDEX IF NOT EXISTS idx_delivery_notes_supplier ON delivery_notes(supplier_name);
CREATE INDEX IF NOT EXISTS idx_delivery_notes_matched ON delivery_notes(matched_invoice_id);

CREATE INDEX IF NOT EXISTS idx_invoice_line_items_invoice ON invoice_line_items(invoice_id);
CREATE INDEX IF NOT EXISTS idx_invoice_line_items_page ON invoice_line_items(page);
CREATE INDEX IF NOT EXISTS idx_invoice_line_items_confidence ON invoice_line_items(confidence);

CREATE INDEX IF NOT EXISTS idx_delivery_line_items_dn ON delivery_line_items(delivery_note_id);
CREATE INDEX IF NOT EXISTS idx_delivery_line_items_page ON delivery_line_items(page);
CREATE INDEX IF NOT EXISTS idx_delivery_line_items_confidence ON delivery_line_items(confidence);

CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_kind ON jobs(kind);
CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at);

CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_log_action ON audit_log(action);
CREATE INDEX IF NOT EXISTS idx_audit_log_entity ON audit_log(entity_type, entity_id);

CREATE INDEX IF NOT EXISTS idx_match_links_invoice ON match_links(invoice_id);
CREATE INDEX IF NOT EXISTS idx_match_links_dn ON match_links(delivery_note_id);
CREATE INDEX IF NOT EXISTS idx_match_links_status ON match_links(status);
CREATE INDEX IF NOT EXISTS idx_match_links_confidence ON match_links(confidence);

CREATE INDEX IF NOT EXISTS idx_match_line_links_match ON match_line_links(match_link_id);
CREATE INDEX IF NOT EXISTS idx_match_line_links_status ON match_line_links(status);

CREATE INDEX IF NOT EXISTS idx_processing_logs_file ON processing_logs(file_id);
CREATE INDEX IF NOT EXISTS idx_processing_logs_stage ON processing_logs(stage);
CREATE INDEX IF NOT EXISTS idx_processing_logs_status ON processing_logs(status);
CREATE INDEX IF NOT EXISTS idx_processing_logs_timestamp ON processing_logs(created_at);

-- Create triggers for updated_at timestamps
CREATE TRIGGER IF NOT EXISTS update_invoices_updated_at 
    AFTER UPDATE ON invoices 
    BEGIN 
        UPDATE invoices SET updated_at = datetime('now') WHERE id = NEW.id; 
    END;

CREATE TRIGGER IF NOT EXISTS update_delivery_notes_updated_at 
    AFTER UPDATE ON delivery_notes 
    BEGIN 
        UPDATE delivery_notes SET updated_at = datetime('now') WHERE id = NEW.id; 
    END;

CREATE TRIGGER IF NOT EXISTS update_uploaded_files_updated_at 
    AFTER UPDATE ON uploaded_files 
    BEGIN 
        UPDATE uploaded_files SET updated_at = datetime('now') WHERE id = NEW.id; 
    END;

CREATE TRIGGER IF NOT EXISTS update_jobs_updated_at 
    AFTER UPDATE ON jobs 
    BEGIN 
        UPDATE jobs SET updated_at = datetime('now') WHERE id = NEW.id; 
    END;

CREATE TRIGGER IF NOT EXISTS update_match_links_updated_at 
    AFTER UPDATE ON match_links 
    BEGIN 
        UPDATE match_links SET updated_at = datetime('now') WHERE id = NEW.id; 
    END;

CREATE TRIGGER IF NOT EXISTS update_match_line_links_updated_at 
    AFTER UPDATE ON match_line_links 
    BEGIN 
        UPDATE match_line_links SET updated_at = datetime('now') WHERE id = NEW.id; 
    END; 