from __future__ import annotations
import sqlite3
from typing import List, Tuple
from services.db_exec import query_all, exec_one
from schemas.pairing import CandidateLine, LineScore
from services.pairing_math import score_line

PAIR_THRESHOLD = 0.72

def _fetch_invoice_lines(conn: sqlite3.Connection, invoice_id: str) -> List[CandidateLine]:
    rows = query_all(conn, """
        SELECT description,
               COALESCE(quantity_each, quantity, 0.0) AS qty,
               COALESCE(unit_price_pennies, 0)        AS unit_price_pennies,
               COALESCE(quantity_l, 0.0)              AS quantity_l,
               COALESCE(sku, NULL)                    AS sku
        FROM invoice_line_items
        WHERE invoice_id = ?
        ORDER BY row_idx
    """, (invoice_id,))
    return [
        CandidateLine(
            sku=r["sku"],
            description=r["description"] or "",
            quantity_each=float(r["qty"] or 0),
            unit_price_pennies=int(r["unit_price_pennies"] or 0),
            quantity_l=float(r["quantity_l"] or 0.0)
        ) for r in rows
    ]

def _fetch_dn_lines(conn: sqlite3.Connection, dn_id: str) -> List[CandidateLine]:
    rows = query_all(conn, """
        SELECT description,
               COALESCE(quantity_each, quantity, 0.0) AS qty,
               COALESCE(unit_price_pennies, 0)        AS unit_price_pennies,
               COALESCE(quantity_l, 0.0)              AS quantity_l,
               COALESCE(sku, NULL)                    AS sku
        FROM delivery_line_items
        WHERE delivery_note_id = ?
        ORDER BY row_idx
    """, (dn_id,))
    return [
        CandidateLine(
            sku=r["sku"],
            description=r["description"] or "",
            quantity_each=float(r["qty"] or 0),
            unit_price_pennies=int(r["unit_price_pennies"] or 0),
            quantity_l=float(r["quantity_l"] or 0.0)
        ) for r in rows
    ]

def suggest_pairs(conn: sqlite3.Connection, invoice_id: str, dn_id: str) -> List[Tuple[int,int,LineScore]]:
    inv = _fetch_invoice_lines(conn, invoice_id)
    dn  = _fetch_dn_lines(conn, dn_id)
    pairs: List[Tuple[int,int,LineScore]] = []
    for i, li in enumerate(inv):
        best_j, best = -1, None
        for j, lj in enumerate(dn):
            s = score_line(li, lj)
            if best is None or s.total > best.total:
                best, best_j = s, j
        if best and best.total >= PAIR_THRESHOLD:
            pairs.append((i, best_j, best))
    return pairs

def persist_pairs(conn: sqlite3.Connection, invoice_id: str, dn_id: str, pairs: List[Tuple[int,int,LineScore]]) -> None:
    cur = conn.cursor()
    cur.execute("BEGIN")
    try:
        exec_one(conn,
            "INSERT OR IGNORE INTO match_links(invoice_id, delivery_note_id, status) VALUES (?,?,?)",
            (invoice_id, dn_id, "suggested"))
        for i_idx, j_idx, s in pairs:
            exec_one(conn, """
                INSERT OR REPLACE INTO match_line_links
                  (invoice_id, delivery_note_id, invoice_line_idx, dn_line_idx,
                   score_total, score_desc, score_qty, score_price, score_uom)
                VALUES (?,?,?,?,?,?,?,?,?)
            """, (invoice_id, dn_id, i_idx, j_idx, s.total, s.desc_score, s.qty_score, s.price_score, s.uom_score))
        cur.execute("COMMIT")
    except Exception:
        cur.execute("ROLLBACK")
        raise 