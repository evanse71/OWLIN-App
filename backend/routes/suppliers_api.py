# backend/routes/suppliers_api.py
from fastapi import APIRouter
import sqlite3

router = APIRouter()

def _db():
    con = sqlite3.connect("data/owlin.db"); con.row_factory = sqlite3.Row
    return con

@router.get("/suppliers/scorecards")
def suppliers_scorecards():
    con = _db()
    rows = con.execute("""
        SELECT supplier,
               COUNT(*) AS invoices,
               COALESCE(SUM(total_value),0) AS spend,
               AVG((SELECT ocr_confidence FROM documents d WHERE d.id=i.document_id)) AS avg_ocr
        FROM invoices i
        GROUP BY supplier
        ORDER BY spend DESC
        LIMIT 100
    """).fetchall()
    return {"items":[{"supplier": r["supplier"], "invoices": r["invoices"], "spend": round(r["spend"] or 0,2), "avg_ocr": round(r["avg_ocr"] or 0,1), "mismatch_rate": 0.0, "volatility": 0.0} for r in rows]}