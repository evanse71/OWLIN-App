-- Migration: Add supplier templates table
-- Stores template information for repeat vendors to improve accuracy and speed

CREATE TABLE IF NOT EXISTS supplier_templates (
    supplier_key TEXT PRIMARY KEY,
    header_zones_json TEXT NOT NULL,   -- {keyword: bbox, ...}
    currency_hint TEXT,
    vat_hint TEXT,
    samples_count INTEGER DEFAULT 0,
    updated_at TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Index for faster template lookups
CREATE INDEX IF NOT EXISTS idx_supplier_templates_updated_at ON supplier_templates(updated_at);
CREATE INDEX IF NOT EXISTS idx_supplier_templates_samples_count ON supplier_templates(samples_count);

-- Add template_hint_used to audit_log for tracking template usage
ALTER TABLE audit_log ADD COLUMN template_hint_used BOOLEAN DEFAULT FALSE; 