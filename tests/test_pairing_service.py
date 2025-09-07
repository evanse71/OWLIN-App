import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import sqlite3
from db_manager_unified import get_db_manager
from services.pairing_service import suggest_pairs, persist_pairs

def seed(conn: sqlite3.Connection) -> None:
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO invoices(id, file_id, created_at, total_amount_pennies) VALUES ('invA','f','2025-01-01',0)")
    c.execute("INSERT OR IGNORE INTO delivery_notes(id, created_at, status) VALUES ('dnA','2025-01-01','unmatched')")
    # Minimal lines
    c.execute("INSERT OR REPLACE INTO invoice_line_items(invoice_id,row_idx,description,quantity_each,unit_price_pennies,line_total_pennies) VALUES('invA',0,'TIA MARIA 1L',6,1200,7200)")
    c.execute("INSERT OR REPLACE INTO delivery_line_items(delivery_note_id,row_idx,description,quantity_each,unit_price_pennies) VALUES('dnA',0,'TIA MARIA 1L',6,1200)")
    conn.commit()

def test_pairs_persist():
    db = get_db_manager()
    conn = db.get_conn()
    seed(conn)
    pairs = suggest_pairs(conn, "invA", "dnA")
    assert pairs and pairs[0][2].total >= 0.72
    persist_pairs(conn, "invA", "dnA", pairs)
    rows = conn.execute("SELECT COUNT(*) FROM match_line_links WHERE invoice_id='invA' AND delivery_note_id='dnA'").fetchone()[0]
    assert rows >= 1 