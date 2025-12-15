from __future__ import annotations
import sqlite3
from typing import Dict, Any, List
from backend.services.db_exec import query_all

TOL_PCT = 0.05
TOL_PENNY = 1

def _pct_drift(a: int, b: int) -> float:
    if b == 0: return 1.0
    hi, lo = (a,b) if a >= b else (b,a)
    return (hi - lo) / max(1, b)

def evaluate_mismatches(conn: sqlite3.Connection, invoice_id: str, dn_id: str) -> Dict[str, Any]:
    # join suggestions to bring both sides
    rows = query_all(conn, """
      SELECT ml.invoice_line_idx AS i_idx, ml.dn_line_idx AS d_idx,
             ili.description AS inv_desc, dli.description AS dn_desc,
             COALESCE(ili.quantity_each, ili.quantity, 0.0) AS inv_qty,
             COALESCE(dli.quantity_each, dli.quantity, 0.0) AS dn_qty,
             COALESCE(ili.unit_price_pennies,0) AS inv_price_p,
             COALESCE(dli.unit_price_pennies,0) AS dn_price_p,
             COALESCE(ili.line_total_pennies,0) AS inv_total_p
      FROM match_line_links ml
      JOIN invoice_line_items   ili ON ili.invoice_id = ? AND ili.row_idx = ml.invoice_line_idx
      JOIN delivery_line_items  dli ON dli.delivery_note_id = ? AND dli.row_idx = ml.dn_line_idx
      WHERE ml.invoice_id = ? AND ml.delivery_note_id = ?
      ORDER BY ml.invoice_line_idx
    """, (invoice_id, dn_id, invoice_id, dn_id))

    line_flags: List[Dict[str, Any]] = []
    for r in rows:
        if abs((r["inv_qty"] or 0.0) - (r["dn_qty"] or 0.0)) > 1e-6:
            line_flags.append({"idx": int(r["i_idx"]), "flag": "QTY_DRIFT"})
        if _pct_drift(int(r["inv_price_p"]), int(r["dn_price_p"])) > TOL_PCT:
            line_flags.append({"idx": int(r["i_idx"]), "flag": "PRICE_DRIFT"})

    totals = query_all(conn, "SELECT COALESCE(SUM(line_total_pennies),0) AS s FROM invoice_line_items WHERE invoice_id=?", (invoice_id,))
    inv_total = int(totals[0]["s"]) if totals else 0
    iview  = query_all(conn, "SELECT COALESCE(total_amount_pennies,0) AS t FROM invoices WHERE id=?", (invoice_id,))
    header = int(iview[0]["t"]) if iview else 0
    doc_flags: List[str] = []
    if abs(inv_total - header) > TOL_PENNY:
        doc_flags.append("TOTAL_MISMATCH")

    return {"line_flags": line_flags, "doc_flags": doc_flags, "summary": {"calc_pennies": inv_total, "header_pennies": header}} 