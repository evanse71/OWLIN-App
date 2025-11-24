-- Migration 0004: Complete System Bible Implementation
-- Creates all missing tables as specified in the System Bible

-- Issues table for tracking mismatches and problems
CREATE TABLE IF NOT EXISTS issues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id TEXT NOT NULL,
    delivery_id TEXT,
    type TEXT NOT NULL,
    severity TEXT NOT NULL,
    status TEXT DEFAULT 'open',
    value_delta REAL,
    description TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    resolved_at TEXT,
    FOREIGN KEY(invoice_id) REFERENCES invoices(id)
);

CREATE INDEX IF NOT EXISTS idx_issues_invoice_id ON issues(invoice_id);
CREATE INDEX IF NOT EXISTS idx_issues_status ON issues(status);
CREATE INDEX IF NOT EXISTS idx_issues_type ON issues(type);

-- Supplier price history for forecasting
CREATE TABLE IF NOT EXISTS supplier_price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id TEXT NOT NULL,
    price_ex_vat REAL NOT NULL,
    observed_at TEXT NOT NULL,
    invoice_id TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(invoice_id) REFERENCES invoices(id)
);

CREATE INDEX IF NOT EXISTS idx_price_history_item_id ON supplier_price_history(item_id);
CREATE INDEX IF NOT EXISTS idx_price_history_observed_at ON supplier_price_history(observed_at);

-- Forecast points table
CREATE TABLE IF NOT EXISTS forecast_points (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id TEXT NOT NULL,
    forecast_date TEXT NOT NULL,
    predicted_price REAL NOT NULL,
    lower_bound REAL NOT NULL,
    upper_bound REAL NOT NULL,
    confidence REAL DEFAULT 0.95,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(item_id, forecast_date)
);

CREATE INDEX IF NOT EXISTS idx_forecast_points_item_id ON forecast_points(item_id);
CREATE INDEX IF NOT EXISTS idx_forecast_points_date ON forecast_points(forecast_date);

-- OCR retry queue for low-confidence pages
CREATE TABLE IF NOT EXISTS ocr_retry_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    page_id TEXT NOT NULL,
    doc_id TEXT NOT NULL,
    original_confidence REAL NOT NULL,
    original_engine TEXT NOT NULL,
    retry_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending',
    alternate_engines TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    processed_at TEXT,
    final_confidence REAL,
    final_engine TEXT,
    FOREIGN KEY(doc_id) REFERENCES documents(id)
);

CREATE INDEX IF NOT EXISTS idx_retry_queue_status ON ocr_retry_queue(status);
CREATE INDEX IF NOT EXISTS idx_retry_queue_page_id ON ocr_retry_queue(page_id);

-- Normalization log for supplier/item matching
CREATE TABLE IF NOT EXISTS normalization_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_name TEXT NOT NULL,
    matched_id TEXT,
    confidence REAL,
    action TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_normalization_supplier_name ON normalization_log(supplier_name);
CREATE INDEX IF NOT EXISTS idx_normalization_matched_id ON normalization_log(matched_id);

-- Supplier alias review for managing alias drift
CREATE TABLE IF NOT EXISTS supplier_alias_review (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    original_name TEXT NOT NULL,
    suggested_match TEXT,
    confidence REAL,
    status TEXT DEFAULT 'pending',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TEXT,
    reviewed_by TEXT
);

CREATE INDEX IF NOT EXISTS idx_alias_review_status ON supplier_alias_review(status);
CREATE INDEX IF NOT EXISTS idx_alias_review_original_name ON supplier_alias_review(original_name);

-- Metrics daily for pre-aggregated KPIs
CREATE TABLE IF NOT EXISTS metrics_daily (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    venue_id TEXT NOT NULL,
    date TEXT NOT NULL,
    kpi TEXT NOT NULL,
    value REAL NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(venue_id, date, kpi)
);

CREATE INDEX IF NOT EXISTS idx_metrics_daily_venue_date ON metrics_daily(venue_id, date);
CREATE INDEX IF NOT EXISTS idx_metrics_daily_kpi ON metrics_daily(kpi);

-- Add doc_type column to documents if it doesn't exist
-- (Some databases may already have this from migration 0003)
-- SQLite doesn't support IF NOT EXISTS for ALTER TABLE, so we'll handle this in Python

-- Add status column to invoices if it doesn't exist
-- (May already exist from initial schema)

-- Add confidence column to ocr_pages if ocr_pages table exists
-- (This table may be created elsewhere)

