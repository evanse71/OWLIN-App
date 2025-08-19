-- Migration: Invoice Delivery Note Matching Links
-- Date: 2025-08-18
-- Purpose: Create tables for deterministic matching engine with confidence scoring

-- Document-level matching pairs
CREATE TABLE IF NOT EXISTS match_links (
    id TEXT PRIMARY KEY,
    invoice_id TEXT NOT NULL,
    delivery_note_id TEXT NOT NULL,
    confidence REAL NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('matched', 'partial', 'unmatched', 'conflict')),
    reasons_json TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (invoice_id) REFERENCES invoices(id),
    FOREIGN KEY (delivery_note_id) REFERENCES delivery_notes(id)
);

-- Line-level matching details
CREATE TABLE IF NOT EXISTS match_line_links (
    id TEXT PRIMARY KEY,
    match_link_id TEXT NOT NULL,
    invoice_line_id INTEGER,
    delivery_line_id INTEGER,
    qty_delta REAL,
    price_delta REAL,
    confidence REAL NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('ok', 'qty_mismatch', 'price_mismatch', 'missing_on_dn', 'missing_on_inv')),
    reasons_json TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (match_link_id) REFERENCES match_links(id)
);

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_match_links_invoice ON match_links(invoice_id);
CREATE INDEX IF NOT EXISTS idx_match_links_dn ON match_links(delivery_note_id);
CREATE INDEX IF NOT EXISTS idx_match_links_status ON match_links(status);
CREATE INDEX IF NOT EXISTS idx_match_links_confidence ON match_links(confidence);
CREATE INDEX IF NOT EXISTS idx_match_line_links_match ON match_line_links(match_link_id);
CREATE INDEX IF NOT EXISTS idx_match_line_links_status ON match_line_links(status);

-- Audit table for matching actions
CREATE TABLE IF NOT EXISTS matching_audit (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    role TEXT,
    venue_id TEXT,
    pair_id TEXT,
    line_id TEXT,
    action TEXT NOT NULL,
    reason TEXT,
    before_json TEXT,
    after_json TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (pair_id) REFERENCES match_links(id)
);

CREATE INDEX IF NOT EXISTS idx_matching_audit_pair ON matching_audit(pair_id);
CREATE INDEX IF NOT EXISTS idx_matching_audit_user ON matching_audit(user_id);
CREATE INDEX IF NOT EXISTS idx_matching_audit_action ON matching_audit(action); 