import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import sqlite3
from db_manager_unified import get_db_manager
from services.mismatch_service import evaluate_mismatches

def test_totals_flag_when_header_mismatch():
    db = get_db_manager()
    conn = db.get_conn()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO invoices(id,file_id,created_at,total_amount_pennies) VALUES('invM','f','2025-01-01',7100)")
    c.execute("INSERT OR IGNORE INTO delivery_notes(id,created_at,status) VALUES('dnM','2025-01-01','unmatched')")
    c.execute("INSERT OR REPLACE INTO invoice_line_items(invoice_id,row_idx,description,quantity_each,unit_price_pennies,line_total_pennies) VALUES('invM',0,'X',1,7000,7000)")
    c.execute("INSERT OR REPLACE INTO delivery_line_items(delivery_note_id,row_idx,description,quantity_each,unit_price_pennies) VALUES('dnM',0,'X',1,7000)")
    c.execute("INSERT OR REPLACE INTO match_line_links(invoice_id,delivery_note_id,invoice_line_idx,dn_line_idx,score_total,score_desc,score_qty,score_price,score_uom) VALUES('invM','dnM',0,0,0.9,1,1,1,1)")
    conn.commit()
    res = evaluate_mismatches(conn, "invM", "dnM")
    assert "TOTAL_MISMATCH" in res["doc_flags"] 