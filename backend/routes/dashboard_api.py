from fastapi import APIRouter
import sqlite3

dashboard = APIRouter()

def _db():
    con = sqlite3.connect("data/owlin.db")
    con.row_factory = sqlite3.Row
    return con

@dashboard.get("/dashboard/metrics")
def metrics():
    con = _db()
    total_spend = con.execute("SELECT COALESCE(SUM(total_value),0) AS s FROM invoices").fetchone()["s"]
    total_invoices = con.execute("SELECT COUNT(*) c FROM invoices").fetchone()["c"]
    matched = con.execute("SELECT COUNT(*) c FROM invoices WHERE matched_delivery_note_id IS NOT NULL").fetchone()["c"]
    match_rate = (matched / total_invoices) * 100 if total_invoices else 0
    avg_ocr = con.execute("SELECT COALESCE(AVG(ocr_confidence),0) a FROM documents WHERE type='invoice'").fetchone()["a"]
    issues = con.execute("SELECT COUNT(*) c FROM invoice_line_items WHERE /* your rule for issue */ 1=0").fetchone()["c"]
    con.close()
    return {
        "total_spend": round(total_spend,2),
        "match_rate": round(match_rate,1),
        "issues": issues,
        "avg_ocr": round(avg_ocr,1),
    }

@dashboard.get("/dashboard/spend_timeseries")
def spend_timeseries():
    con = _db()
    rows = con.execute("""
        SELECT date(invoice_date) d, COALESCE(SUM(total_value),0) s
        FROM invoices
        WHERE invoice_date IS NOT NULL
        GROUP BY date(invoice_date)
        ORDER BY d
    """).fetchall()
    con.close()
    return {"series":[{"date": r["d"], "spend": r["s"]} for r in rows]}
