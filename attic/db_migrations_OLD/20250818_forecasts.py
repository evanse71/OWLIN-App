-- Migration: Item-Level Price Forecasts
-- Date: 2025-08-18
-- Purpose: Create tables for deterministic forecasting pipeline with confidence intervals and quality metrics

-- Forecasts table (predictions)
CREATE TABLE IF NOT EXISTS forecasts (
    id TEXT PRIMARY KEY,
    item_id INTEGER NOT NULL,
    supplier_id INTEGER,
    venue_id INTEGER,
    model TEXT NOT NULL,
    horizon_months INTEGER NOT NULL,
    granularity TEXT NOT NULL DEFAULT 'month',
    version INTEGER NOT NULL DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now')),
    series_json TEXT NOT NULL,
    explain_json TEXT NOT NULL,
    FOREIGN KEY (item_id) REFERENCES items(id),
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id),
    FOREIGN KEY (venue_id) REFERENCES venues(id)
);

-- Forecast metrics table (quality from backtests)
CREATE TABLE IF NOT EXISTS forecast_metrics (
    id TEXT PRIMARY KEY,
    item_id INTEGER NOT NULL,
    model TEXT NOT NULL,
    window_days INTEGER NOT NULL,
    smape REAL NOT NULL,
    mape REAL NOT NULL,
    wape REAL NOT NULL,
    bias_pct REAL NOT NULL,
    last_updated TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (item_id) REFERENCES items(id)
);

-- Item price history table (if not exists)
CREATE TABLE IF NOT EXISTS item_price_history (
    id TEXT PRIMARY KEY,
    item_id INTEGER NOT NULL,
    supplier_id INTEGER,
    venue_id INTEGER,
    date TEXT NOT NULL,
    unit_price REAL NOT NULL,
    quantity REAL,
    total_amount REAL,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (item_id) REFERENCES items(id),
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id),
    FOREIGN KEY (venue_id) REFERENCES venues(id)
);

-- Job queue for long-running forecast tasks
CREATE TABLE IF NOT EXISTS forecast_jobs (
    id TEXT PRIMARY KEY,
    job_type TEXT NOT NULL,
    payload TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    progress INTEGER DEFAULT 0,
    result TEXT,
    error TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    started_at TEXT,
    completed_at TEXT
);

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_forecasts_item_horizon ON forecasts(item_id, horizon_months);
CREATE INDEX IF NOT EXISTS idx_forecasts_supplier ON forecasts(supplier_id);
CREATE INDEX IF NOT EXISTS idx_forecasts_venue ON forecasts(venue_id);
CREATE INDEX IF NOT EXISTS idx_forecasts_model ON forecasts(model);
CREATE INDEX IF NOT EXISTS idx_forecast_metrics_item ON forecast_metrics(item_id);
CREATE INDEX IF NOT EXISTS idx_forecast_metrics_model ON forecast_metrics(model);
CREATE INDEX IF NOT EXISTS idx_item_price_history_item ON item_price_history(item_id);
CREATE INDEX IF NOT EXISTS idx_item_price_history_date ON item_price_history(date);
CREATE INDEX IF NOT EXISTS idx_item_price_history_supplier ON item_price_history(supplier_id);
CREATE INDEX IF NOT EXISTS idx_forecast_jobs_status ON forecast_jobs(status);
CREATE INDEX IF NOT EXISTS idx_forecast_jobs_created ON forecast_jobs(created_at);

-- Audit table for forecast actions
CREATE TABLE IF NOT EXISTS forecast_audit (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    role TEXT,
    action TEXT NOT NULL,
    item_id INTEGER,
    model TEXT,
    horizon_months INTEGER,
    scenario_json TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (item_id) REFERENCES items(id)
);

CREATE INDEX IF NOT EXISTS idx_forecast_audit_user ON forecast_audit(user_id);
CREATE INDEX IF NOT EXISTS idx_forecast_audit_action ON forecast_audit(action);
CREATE INDEX IF NOT EXISTS idx_forecast_audit_item ON forecast_audit(item_id); 