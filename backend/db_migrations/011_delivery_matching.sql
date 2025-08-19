-- Migration 011: Delivery Matching System
-- Creates tables for invoice-delivery note matching with confidence scoring

-- Table to store invoice-delivery note pairs
CREATE TABLE IF NOT EXISTS invoice_delivery_pairs (
    id TEXT PRIMARY KEY,
    invoice_id TEXT NOT NULL,
    delivery_note_id TEXT NOT NULL,
    confidence_score REAL NOT NULL,
    breakdown_supplier REAL NOT NULL,
    breakdown_date REAL NOT NULL,
    breakdown_line_items REAL NOT NULL,
    breakdown_value REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'confirmed', 'rejected'
    confirmed_by TEXT,
    confirmed_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(invoice_id, delivery_note_id)
);

-- Table to store unmatched delivery notes for late matching
CREATE TABLE IF NOT EXISTS unmatched_delivery_notes (
    id TEXT PRIMARY KEY,
    delivery_note_id TEXT NOT NULL,
    supplier_name TEXT,
    delivery_date TEXT,
    total_amount REAL,
    line_items_count INTEGER,
    created_at TEXT NOT NULL,
    matched_at TEXT,
    UNIQUE(delivery_note_id)
);

-- Table to store matching history for rejections
CREATE TABLE IF NOT EXISTS matching_history (
    id TEXT PRIMARY KEY,
    invoice_id TEXT NOT NULL,
    delivery_note_id TEXT NOT NULL,
    action TEXT NOT NULL, -- 'rejected', 'confirmed'
    confidence_score REAL NOT NULL,
    breakdown_supplier REAL NOT NULL,
    breakdown_date REAL NOT NULL,
    breakdown_line_items REAL NOT NULL,
    breakdown_value REAL NOT NULL,
    actor_role TEXT,
    notes TEXT,
    created_at TEXT NOT NULL
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_invoice_delivery_pairs_invoice ON invoice_delivery_pairs(invoice_id);
CREATE INDEX IF NOT EXISTS idx_invoice_delivery_pairs_delivery ON invoice_delivery_pairs(delivery_note_id);
CREATE INDEX IF NOT EXISTS idx_invoice_delivery_pairs_status ON invoice_delivery_pairs(status);
CREATE INDEX IF NOT EXISTS idx_unmatched_delivery_notes_supplier ON unmatched_delivery_notes(supplier_name);
CREATE INDEX IF NOT EXISTS idx_unmatched_delivery_notes_date ON unmatched_delivery_notes(delivery_date);
CREATE INDEX IF NOT EXISTS idx_matching_history_invoice ON matching_history(invoice_id);
CREATE INDEX IF NOT EXISTS idx_matching_history_delivery ON matching_history(delivery_note_id); 