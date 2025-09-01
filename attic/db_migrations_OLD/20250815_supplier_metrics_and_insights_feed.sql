-- Migration: Supplier metrics and insights feed
-- Date: 2025-08-18

CREATE TABLE IF NOT EXISTS supplier_metrics (
    id INTEGER PRIMARY KEY,
    supplier_id TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value REAL NOT NULL,
    metric_period TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_supplier_metrics_supplier ON supplier_metrics(supplier_id);
CREATE INDEX IF NOT EXISTS idx_supplier_metrics_name_period ON supplier_metrics(metric_name, metric_period);

-- Narrative insights feed (separate from prior supplier_insights metrics table)
CREATE TABLE IF NOT EXISTS supplier_insights_feed (
    id TEXT PRIMARY KEY,
    supplier_id TEXT NOT NULL,
    severity TEXT NOT NULL,
    message TEXT NOT NULL,
    timestamp TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_supplier_insights_feed_supplier ON supplier_insights_feed(supplier_id); 