-- Migration 010: Invoice ↔ Delivery Note Pairing Schema

-- Note: Column additions are handled in backend/app/db.py to keep this script
-- idempotent across existing installations. This migration focuses on tables
-- and indexes that can be created with IF NOT EXISTS guards.

BEGIN;

CREATE TABLE IF NOT EXISTS pairing_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL DEFAULT (datetime('now')),
    invoice_id TEXT NOT NULL,
    delivery_note_id TEXT,
    action TEXT NOT NULL,
    actor_type TEXT NOT NULL,
    user_id TEXT,
    previous_delivery_note_id TEXT,
    feature_vector_json TEXT,
    model_version TEXT,
    FOREIGN KEY(invoice_id) REFERENCES invoices(id),
    FOREIGN KEY(delivery_note_id) REFERENCES documents(id),
    FOREIGN KEY(previous_delivery_note_id) REFERENCES documents(id)
);

CREATE INDEX IF NOT EXISTS idx_pairing_events_invoice_id
    ON pairing_events(invoice_id);

CREATE INDEX IF NOT EXISTS idx_pairing_events_delivery_note_id
    ON pairing_events(delivery_note_id);

CREATE TABLE IF NOT EXISTS supplier_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id TEXT NOT NULL,
    venue_id TEXT NOT NULL DEFAULT '__default__',
    typical_delivery_weekdays TEXT,
    avg_days_between_deliveries REAL,
    std_days_between_deliveries REAL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(supplier_id, venue_id)
);

CREATE INDEX IF NOT EXISTS idx_supplier_stats_supplier
    ON supplier_stats(supplier_id);

-- Note: Index creation for columns is handled in backend/app/db.py
-- after columns are verified to exist. These are kept here for reference
-- but will be created conditionally in Python code.

COMMIT;

