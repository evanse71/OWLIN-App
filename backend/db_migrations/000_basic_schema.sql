-- Basic schema setup
CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_name TEXT,
    invoice_number TEXT,
    invoice_date TEXT,
    total_amount REAL,
    status TEXT DEFAULT 'parsed',
    confidence REAL DEFAULT 0.0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS line_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER,
    description TEXT,
    quantity REAL,
    unit TEXT,
    unit_price REAL,
    line_total REAL,
    FOREIGN KEY (invoice_id) REFERENCES invoices(id)
); 