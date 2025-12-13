CREATE TABLE IF NOT EXISTS invoices (
  id TEXT PRIMARY KEY,
  supplier_id TEXT NOT NULL,
  supplier_name TEXT NOT NULL,
  invoice_date TEXT NOT NULL,
  invoice_ref TEXT NOT NULL,
  status TEXT,
  entry_mode TEXT,
  currency TEXT,
  total_net TEXT,
  total_vat TEXT,
  total_gross TEXT,
  notes TEXT,
  meta_json TEXT
);
CREATE TABLE IF NOT EXISTS delivery_notes (
  id TEXT PRIMARY KEY,
  supplier_id TEXT NOT NULL,
  supplier_name TEXT NOT NULL,
  delivery_date TEXT NOT NULL,
  delivery_ref TEXT NOT NULL,
  status TEXT,
  entry_mode TEXT,
  currency TEXT,
  notes TEXT,
  meta_json TEXT
);
