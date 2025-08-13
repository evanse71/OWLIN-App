-- Bulletproof Ingestion v3 Database Migration
-- Creates new tables for the comprehensive ingestion system

-- Documents table - every segmented piece, typed
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    source_file_id TEXT NOT NULL,
    doc_type TEXT NOT NULL, -- invoice, delivery, receipt, utility, other
    supplier_guess TEXT,
    page_range TEXT, -- JSON array of page numbers
    fingerprint_hashes TEXT, -- JSON with phash, header_simhash, footer_simhash, text_hash
    stitch_group_id TEXT,
    confidence REAL DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Pages table - one row per rendered page
CREATE TABLE IF NOT EXISTS pages (
    id TEXT PRIMARY KEY,
    source_file_id TEXT NOT NULL,
    page_index INTEGER NOT NULL,
    phash TEXT, -- perceptual hash
    header_simhash TEXT, -- header simhash
    footer_simhash TEXT, -- footer simhash
    text_hash TEXT, -- text content hash
    classified_type TEXT, -- invoice, delivery, receipt, utility, other
    features TEXT, -- JSON features for classification
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Canonical invoices table - final "truth" entity
CREATE TABLE IF NOT EXISTS canonical_invoices (
    id TEXT PRIMARY KEY,
    supplier_name TEXT,
    invoice_number TEXT,
    invoice_date TEXT, -- ISO "YYYY-MM-DD" if known
    currency TEXT,
    subtotal REAL,
    tax REAL,
    total_amount REAL,
    field_confidence TEXT, -- JSON
    warnings TEXT, -- JSON array
    raw_extraction TEXT, -- JSON
    source_segments TEXT, -- JSON array
    source_pages TEXT, -- JSON array
    confidence REAL DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Canonical documents table - non-invoice documents
CREATE TABLE IF NOT EXISTS canonical_documents (
    id TEXT PRIMARY KEY,
    doc_type TEXT NOT NULL, -- delivery, receipt, utility, other
    supplier_name TEXT,
    document_number TEXT,
    document_date TEXT,
    content TEXT, -- JSON
    confidence REAL DEFAULT 1.0,
    source_segments TEXT, -- JSON array
    source_pages TEXT, -- JSON array
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Canonical links table - mapping many documents/pages → one canonical entity
CREATE TABLE IF NOT EXISTS canonical_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_id TEXT NOT NULL,
    canonical_type TEXT NOT NULL, -- 'invoice' or 'document'
    document_id TEXT,
    page_id TEXT,
    link_type TEXT NOT NULL, -- 'primary', 'duplicate', 'related'
    confidence REAL DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(canonical_id) REFERENCES canonical_invoices(id) ON DELETE CASCADE,
    FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE,
    FOREIGN KEY(page_id) REFERENCES pages(id) ON DELETE CASCADE
);

-- Stitch groups table - groups of segments that were stitched together
CREATE TABLE IF NOT EXISTS stitch_groups (
    id TEXT PRIMARY KEY,
    group_type TEXT NOT NULL, -- 'invoice', 'delivery', 'receipt', 'utility', 'other'
    confidence REAL DEFAULT 1.0,
    supplier_guess TEXT,
    invoice_numbers TEXT, -- JSON array
    dates TEXT, -- JSON array
    reasons TEXT, -- JSON array
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Stitch group members table - segments that belong to a stitch group
CREATE TABLE IF NOT EXISTS stitch_group_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stitch_group_id TEXT NOT NULL,
    document_id TEXT NOT NULL,
    member_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(stitch_group_id) REFERENCES stitch_groups(id) ON DELETE CASCADE,
    FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE
);

-- Duplicate groups table - groups of duplicate pages/files
CREATE TABLE IF NOT EXISTS duplicate_groups (
    id TEXT PRIMARY KEY,
    duplicate_type TEXT NOT NULL, -- 'page' or 'file'
    primary_id TEXT NOT NULL,
    confidence REAL DEFAULT 1.0,
    reasons TEXT, -- JSON array
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Duplicate group members table - items that belong to a duplicate group
CREATE TABLE IF NOT EXISTS duplicate_group_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    duplicate_group_id TEXT NOT NULL,
    item_id TEXT NOT NULL,
    item_type TEXT NOT NULL, -- 'page' or 'file'
    is_primary BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(duplicate_group_id) REFERENCES duplicate_groups(id) ON DELETE CASCADE
);

-- Processing sessions table - track processing sessions
CREATE TABLE IF NOT EXISTS processing_sessions (
    id TEXT PRIMARY KEY,
    session_type TEXT NOT NULL, -- 'bulletproof_ingestion'
    files_processed INTEGER DEFAULT 0,
    pages_processed INTEGER DEFAULT 0,
    canonical_invoices_created INTEGER DEFAULT 0,
    canonical_documents_created INTEGER DEFAULT 0,
    duplicates_found INTEGER DEFAULT 0,
    stitch_groups_created INTEGER DEFAULT 0,
    processing_time REAL, -- seconds
    status TEXT DEFAULT 'completed', -- pending, running, completed, failed
    warnings TEXT, -- JSON array
    errors TEXT, -- JSON array
    metadata TEXT, -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_documents_source_file_id ON documents(source_file_id);
CREATE INDEX IF NOT EXISTS idx_documents_stitch_group_id ON documents(stitch_group_id);
CREATE INDEX IF NOT EXISTS idx_documents_doc_type ON documents(doc_type);
CREATE INDEX IF NOT EXISTS idx_pages_source_file_id ON pages(source_file_id);
CREATE INDEX IF NOT EXISTS idx_pages_classified_type ON pages(classified_type);
CREATE INDEX IF NOT EXISTS idx_canonical_invoices_supplier_name ON canonical_invoices(supplier_name);
CREATE INDEX IF NOT EXISTS idx_canonical_invoices_invoice_number ON canonical_invoices(invoice_number);
CREATE INDEX IF NOT EXISTS idx_canonical_invoices_invoice_date ON canonical_invoices(invoice_date);
CREATE INDEX IF NOT EXISTS idx_canonical_documents_doc_type ON canonical_documents(doc_type);
CREATE INDEX IF NOT EXISTS idx_canonical_links_canonical_id ON canonical_links(canonical_id);
CREATE INDEX IF NOT EXISTS idx_canonical_links_document_id ON canonical_links(document_id);
CREATE INDEX IF NOT EXISTS idx_canonical_links_page_id ON canonical_links(page_id);
CREATE INDEX IF NOT EXISTS idx_stitch_groups_group_type ON stitch_groups(group_type);
CREATE INDEX IF NOT EXISTS idx_stitch_group_members_stitch_group_id ON stitch_group_members(stitch_group_id);
CREATE INDEX IF NOT EXISTS idx_duplicate_groups_duplicate_type ON duplicate_groups(duplicate_type);
CREATE INDEX IF NOT EXISTS idx_duplicate_group_members_duplicate_group_id ON duplicate_group_members(duplicate_group_id);
CREATE INDEX IF NOT EXISTS idx_processing_sessions_status ON processing_sessions(status);
CREATE INDEX IF NOT EXISTS idx_processing_sessions_created_at ON processing_sessions(created_at); 