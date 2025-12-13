-- Migration 002: Pairing Suggestions Table
-- This migration creates the pairing_suggestions table for document pairing

-- PAIRING_SUGGESTIONS TABLE - Document pairing suggestions
CREATE TABLE IF NOT EXISTS pairing_suggestions (
    id TEXT PRIMARY KEY,
    delivery_note_id TEXT NOT NULL,
    invoice_id TEXT NOT NULL,
    score INTEGER NOT NULL CHECK(score BETWEEN 0 AND 100),
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','confirmed','rejected')),
    reasons TEXT NOT NULL, -- JSON array
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY(delivery_note_id) REFERENCES delivery_notes(id) ON DELETE CASCADE,
    FOREIGN KEY(invoice_id) REFERENCES invoices(id) ON DELETE CASCADE,
    UNIQUE(delivery_note_id, invoice_id)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_pairing_suggestions_dn ON pairing_suggestions(delivery_note_id);
CREATE INDEX IF NOT EXISTS idx_pairing_suggestions_invoice ON pairing_suggestions(invoice_id);
CREATE INDEX IF NOT EXISTS idx_pairing_suggestions_score ON pairing_suggestions(score);
CREATE INDEX IF NOT EXISTS idx_pairing_suggestions_status ON pairing_suggestions(status); 