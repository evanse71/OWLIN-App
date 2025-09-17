# Adds invoice_pages table and useful indexes. Idempotent.
import sqlite3, os
from pathlib import Path

DB_PATH = os.environ.get("OWLIN_DB_PATH") or str(Path("data") / "owlin.db")

DDL = """
CREATE TABLE IF NOT EXISTS invoice_pages (
  id TEXT PRIMARY KEY,
  invoice_id TEXT NOT NULL,
  page_no INTEGER,
  ocr_json TEXT,
  FOREIGN KEY(invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_invoice_pages_invoice ON invoice_pages(invoice_id);
CREATE INDEX IF NOT EXISTS idx_invoice_pages_page_no ON invoice_pages(page_no);
"""

def main():
  os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
  con = sqlite3.connect(DB_PATH)
  try:
    con.executescript(DDL)
    con.commit()
    print("invoice_pages ensured")
  finally:
    con.close()

if __name__ == "__main__":
  main()
