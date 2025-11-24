-- Create supplier aliases table for improved matching
CREATE TABLE IF NOT EXISTS supplier_aliases(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical TEXT NOT NULL,
    alias TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Create index for fast lookups
CREATE INDEX IF NOT EXISTS idx_supplier_aliases_alias ON supplier_aliases(alias);
CREATE INDEX IF NOT EXISTS idx_supplier_aliases_canonical ON supplier_aliases(canonical);

-- Insert common supplier aliases
INSERT OR IGNORE INTO supplier_aliases(canonical, alias) VALUES
('Acme', 'Acme Ltd'),
('Acme', 'ACME PLC'),
('Acme', 'Acme Supplies'),
('Acme', 'Acme Corporation'),
('Fresh Foods', 'Fresh Foods Ltd'),
('Fresh Foods', 'Fresh Foods Inc'),
('Fresh Foods', 'Fresh Foods Co'),
('Quality Meats', 'Quality Meats Co'),
('Quality Meats', 'Quality Meats Ltd'),
('Quality Meats', 'Quality Meats Inc');

-- Create view for normalized supplier matching
CREATE VIEW IF NOT EXISTS supplier_normalized AS
SELECT 
    d.*,
    COALESCE(sa.canonical, d.supplier) AS supplier_normalized
FROM documents d
LEFT JOIN supplier_aliases sa ON LOWER(d.supplier) = LOWER(sa.alias);
