-- Migration 003: Normalisation Fields
-- Add optional analysis columns for canonical units, flags, parsed notes, SKU/UOM fields

-- Add normalization fields to invoices table
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS validation_flags TEXT DEFAULT '[]';
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS canonical_quantities TEXT DEFAULT '[]';
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS parsed_metadata TEXT DEFAULT '{}';

-- Add normalization fields to delivery_notes table  
ALTER TABLE delivery_notes ADD COLUMN IF NOT EXISTS validation_flags TEXT DEFAULT '[]';
ALTER TABLE delivery_notes ADD COLUMN IF NOT EXISTS canonical_quantities TEXT DEFAULT '[]';
ALTER TABLE delivery_notes ADD COLUMN IF NOT EXISTS parsed_metadata TEXT DEFAULT '{}';

-- Add normalization fields to invoice_items table
ALTER TABLE invoice_items ADD COLUMN IF NOT EXISTS uom_key TEXT;
ALTER TABLE invoice_items ADD COLUMN IF NOT EXISTS packs REAL;
ALTER TABLE invoice_items ADD COLUMN IF NOT EXISTS units_per_pack REAL;
ALTER TABLE invoice_items ADD COLUMN IF NOT EXISTS quantity_each REAL;
ALTER TABLE invoice_items ADD COLUMN IF NOT EXISTS unit_size_ml REAL;
ALTER TABLE invoice_items ADD COLUMN IF NOT EXISTS unit_size_g REAL;
ALTER TABLE invoice_items ADD COLUMN IF NOT EXISTS unit_size_l REAL;
ALTER TABLE invoice_items ADD COLUMN IF NOT EXISTS quantity_ml REAL;
ALTER TABLE invoice_items ADD COLUMN IF NOT EXISTS quantity_g REAL;
ALTER TABLE invoice_items ADD COLUMN IF NOT EXISTS quantity_l REAL;
ALTER TABLE invoice_items ADD COLUMN IF NOT EXISTS line_flags TEXT DEFAULT '[]';
ALTER TABLE invoice_items ADD COLUMN IF NOT EXISTS sku TEXT;
ALTER TABLE invoice_items ADD COLUMN IF NOT EXISTS brand TEXT;
ALTER TABLE invoice_items ADD COLUMN IF NOT EXISTS category TEXT;

-- Create price sources snapshot table
CREATE TABLE IF NOT EXISTS price_sources_snapshot (
    id TEXT PRIMARY KEY,
    invoice_id TEXT NOT NULL,
    line_id TEXT NOT NULL,
    source TEXT NOT NULL,
    value REAL NOT NULL,
    uom_key TEXT NOT NULL,
    captured_at TEXT DEFAULT (datetime('now')),
    source_hash TEXT NOT NULL,
    FOREIGN KEY(invoice_id) REFERENCES invoices(id) ON DELETE CASCADE,
    FOREIGN KEY(line_id) REFERENCES invoice_items(id) ON DELETE CASCADE
);

-- Create line verdicts table
CREATE TABLE IF NOT EXISTS line_verdicts (
    id TEXT PRIMARY KEY,
    invoice_id TEXT NOT NULL,
    line_id TEXT NOT NULL,
    verdict TEXT NOT NULL,
    hypothesis TEXT,
    implied_value REAL,
    expected_value REAL,
    residual REAL,
    ruleset_id TEXT NOT NULL,
    engine_version TEXT NOT NULL,
    lf TEXT NOT NULL, -- line fingerprint
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY(invoice_id) REFERENCES invoices(id) ON DELETE CASCADE,
    FOREIGN KEY(line_id) REFERENCES invoice_items(id) ON DELETE CASCADE
);

-- Create supplier discounts table
CREATE TABLE IF NOT EXISTS supplier_discounts (
    id TEXT PRIMARY KEY,
    supplier_id TEXT NOT NULL,
    scope TEXT NOT NULL CHECK(scope IN ('supplier', 'category', 'product')),
    rule_type TEXT NOT NULL CHECK(rule_type IN ('percent', 'fixed_per_case', 'fixed_per_litre')),
    value REAL NOT NULL,
    valid_from TEXT NOT NULL,
    valid_to TEXT,
    evidence_ref TEXT,
    ruleset_id TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY(supplier_id) REFERENCES suppliers(id) ON DELETE CASCADE
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_processing_logs_kind ON processing_logs(kind);
CREATE INDEX IF NOT EXISTS idx_price_sources_invoice ON price_sources_snapshot(invoice_id);
CREATE INDEX IF NOT EXISTS idx_price_sources_line ON price_sources_snapshot(line_id);
CREATE INDEX IF NOT EXISTS idx_line_verdicts_invoice ON line_verdicts(invoice_id);
CREATE INDEX IF NOT EXISTS idx_line_verdicts_line ON line_verdicts(line_id);
CREATE INDEX IF NOT EXISTS idx_line_verdicts_verdict ON line_verdicts(verdict);
CREATE INDEX IF NOT EXISTS idx_supplier_discounts_supplier ON supplier_discounts(supplier_id);
CREATE INDEX IF NOT EXISTS idx_supplier_discounts_scope ON supplier_discounts(scope);
CREATE INDEX IF NOT EXISTS idx_supplier_discounts_validity ON supplier_discounts(valid_from, valid_to); 