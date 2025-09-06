CREATE INDEX IF NOT EXISTS idx_delivery_line_items_dn
  ON delivery_line_items(delivery_note_id);

CREATE INDEX IF NOT EXISTS idx_invoice_line_items_invoice
  ON invoice_line_items(invoice_id);

CREATE TABLE IF NOT EXISTS match_links(
  invoice_id TEXT NOT NULL,
  delivery_note_id TEXT NOT NULL,
  status TEXT DEFAULT 'suggested',
  PRIMARY KEY (invoice_id, delivery_note_id)
);

CREATE TABLE IF NOT EXISTS match_line_links(
  invoice_id TEXT NOT NULL,
  delivery_note_id TEXT NOT NULL,
  invoice_line_idx INTEGER NOT NULL,
  dn_line_idx INTEGER NOT NULL,
  score_total REAL NOT NULL,
  score_desc REAL NOT NULL,
  score_qty REAL NOT NULL,
  score_price REAL NOT NULL,
  score_uom REAL NOT NULL,
  PRIMARY KEY (invoice_id, delivery_note_id, invoice_line_idx),
  FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
); 