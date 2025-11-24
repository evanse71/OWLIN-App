-- Create documents table
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sha256 TEXT UNIQUE NOT NULL,
    filename TEXT NOT NULL,
    bytes INTEGER NOT NULL,
    supplier TEXT,
    invoice_no TEXT,
    delivery_no TEXT,
    doc_date TEXT,
    total REAL,
    currency TEXT,
    doc_type TEXT DEFAULT 'unknown',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Create pairs table
CREATE TABLE IF NOT EXISTS pairs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER NOT NULL,
    delivery_id INTEGER NOT NULL,
    confidence REAL NOT NULL,
    status TEXT DEFAULT 'suggested',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    decided_at DATETIME,
    FOREIGN KEY (invoice_id) REFERENCES documents(id),
    FOREIGN KEY (delivery_id) REFERENCES documents(id),
    UNIQUE(invoice_id, delivery_id)
);

-- Create audit log table for tracking pairing decisions
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL DEFAULT (datetime('now')),
    actor TEXT NOT NULL DEFAULT 'system',
    action TEXT NOT NULL,
    object TEXT NOT NULL,
    meta TEXT,  -- JSON metadata
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_documents_sha256 ON documents(sha256);
CREATE INDEX IF NOT EXISTS idx_documents_doc_type ON documents(doc_type);
CREATE INDEX IF NOT EXISTS idx_documents_supplier ON documents(supplier);
CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at);
CREATE INDEX IF NOT EXISTS idx_pairs_status ON pairs(status);
CREATE INDEX IF NOT EXISTS idx_pairs_confidence ON pairs(confidence);
CREATE INDEX IF NOT EXISTS idx_audit_log_ts ON audit_log(ts);
CREATE INDEX IF NOT EXISTS idx_audit_log_action ON audit_log(action);

-- Create view to normalize old/new schemas for reporting
CREATE VIEW IF NOT EXISTS documents_v AS
SELECT id, sha256,
       COALESCE(filename, path) AS filename,
       bytes, supplier, invoice_no, delivery_no, doc_date, total, currency,
       COALESCE(doc_type, type, 'unknown') AS doc_type,
       created_at
FROM documents;