"""
invoice_query.py
===============

Advanced invoice query service with filtering, sorting, and role-aware defaults.
Supports SQLite-backed queries with performance optimizations.
"""

import sqlite3, json
import logging
from typing import Any, Dict, List, Optional
from db_manager_unified import get_db_manager

logger = logging.getLogger(__name__)

def _read_int(row, key: str) -> Optional[int]:
    return int(row[key]) if key in row.keys() and row[key] is not None else None

def _read_float(row, key: str) -> Optional[float]:
    return float(row[key]) if key in row.keys() and row[key] is not None else None

def _pounds(pennies: Optional[int]) -> Optional[float]:
    return None if pennies is None else round(pennies / 100.0, 2)

def fetch_invoice(invoice_id: str) -> Optional[Dict[str, Any]]:
    try:
        conn = get_db_manager().get_conn()
        cur = conn.cursor()

        inv = cur.execute("SELECT * FROM invoices WHERE id=?", (invoice_id,)).fetchone()
        if not inv:
            return None
    except Exception as e:
        logger.exception("invoice_query_failed", extra={"invoice_id": invoice_id})
        raise

    # pages optional
    pages: List[Dict[str, Any]] = []
    if cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='invoice_pages'").fetchone():
        for p in cur.execute("SELECT * FROM invoice_pages WHERE invoice_id=? ORDER BY page_no", (invoice_id,)):
            pages.append({
                "id": p["id"] if "id" in p.keys() else f"{invoice_id}:{p['page_no']}",
                "page_no": int(p["page_no"]),
                "ocr_avg_conf_page": _read_float(p, "ocr_avg_conf_page"),
                "ocr_min_conf_line": _read_float(p, "ocr_min_conf_line"),
            })

    lines: List[Dict[str, Any]] = []
    for r in cur.execute("SELECT * FROM invoice_line_items WHERE invoice_id=? ORDER BY rowid", (invoice_id,)):
        flags: List[Any] = []
        if "line_flags" in r.keys() and r["line_flags"]:
            try:
                flags = json.loads(r["line_flags"])
                if not isinstance(flags, list):  # loud if corrupted
                    flags = [{"_corrupt_flags_payload": r["line_flags"]}]
            except Exception:
                flags = [{"_invalid_json": r["line_flags"]}]
        
        # Add line-level corruption flag for insights
        if flags and any("_corrupt" in str(f) or "_invalid" in str(f) for f in flags):
            flags.append("LINE_FLAGS_CORRUPT")
        discount = None
        if "discount_kind" in r.keys() and r["discount_kind"] is not None:
            discount = {
                "kind": r["discount_kind"],
                "value": _read_float(r, "discount_value"),
                "residual_pennies": _read_int(r, "discount_residual_pennies"),
                "implied_pct": _read_float(r, "implied_discount_pct"),
            }
        lines.append({
            "id": str(r["id"]),
            "sku": r["sku"] if "sku" in r.keys() else None,
            "desc": r["description"] if "description" in r.keys() else r.get("desc"),
            "quantity_each": _read_float(r, "quantity_each"),
            "packs": _read_float(r, "packs"),
            "units_per_pack": _read_float(r, "units_per_pack"),
            "quantity_ml": _read_float(r, "quantity_ml"),
            "quantity_l": _read_float(r, "quantity_l"),
            "quantity_g": _read_float(r, "quantity_g"),
            # keep pennies internally
            "unit_price_pennies": _read_int(r, "unit_price_pennies"),
            "line_total_pennies": _read_int(r, "line_total_pennies"),
            "vat_rate": _read_float(r, "vat_rate"),
            "flags": flags,
            "verdict": r["line_verdict"] if "line_verdict" in r.keys() else None,
            "discount": discount
        })

    return {
        "id": inv["id"],
        "meta": {
            "created_at": inv["created_at"],
            "supplier_id": inv["supplier_id"] if "supplier_id" in inv.keys() else None,
            "ocr_avg_conf": _read_float(inv, "ocr_avg_conf"),
            "ocr_min_conf": _read_float(inv, "ocr_min_conf"),
            "total_amount_pennies": _read_int(inv, "total_amount_pennies"),
            "pages": pages
        },
        "lines": lines
    } 