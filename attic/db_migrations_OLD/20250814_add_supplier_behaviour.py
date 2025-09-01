-- Migration: Add supplier behaviour tracking tables
-- Date: 2025-08-14
-- Description: Creates supplier_events and supplier_insights tables for behaviour tracking

-- Create supplier_events table
CREATE TABLE IF NOT EXISTS supplier_events (
    id TEXT PRIMARY KEY,
    supplier_id TEXT NOT NULL,
    event_type TEXT NOT NULL CHECK (event_type IN ('missed_delivery', 'invoice_mismatch', 'late_delivery', 'quality_issue', 'price_spike')),
    severity TEXT NOT NULL CHECK (severity IN ('low', 'medium', 'high')),
    description TEXT,
    source TEXT NOT NULL CHECK (source IN ('invoice_audit', 'manual', 'system')),
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL,
    is_acknowledged BOOLEAN DEFAULT FALSE
);

-- Create supplier_insights table
CREATE TABLE IF NOT EXISTS supplier_insights (
    id TEXT PRIMARY KEY,
    supplier_id TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value REAL NOT NULL,
    trend_direction TEXT NOT NULL CHECK (trend_direction IN ('up', 'down', 'flat')),
    trend_percentage REAL NOT NULL,
    period_days INTEGER NOT NULL,
    last_updated TEXT NOT NULL
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_supplier_events_sup_type ON supplier_events(supplier_id, event_type);
CREATE INDEX IF NOT EXISTS idx_supplier_events_created ON supplier_events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_supplier_insights_sup_updated ON supplier_insights(supplier_id, last_updated); 