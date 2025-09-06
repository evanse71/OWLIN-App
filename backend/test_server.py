import sys
import os
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import uuid
from typing import Dict, Any
from services.invoice_query import fetch_invoice
from db_manager_unified import get_db_manager
from pydantic import BaseModel
from typing import List, Dict, Any, Optional, Union

# Response models - document the API contract
class InvoiceLine(BaseModel):
    id: str
    desc: Union[str, None] = None
    unit_price: Union[float, None] = None   # pounds
    line_total: Union[float, None] = None   # pounds
    quantity_each: Union[float, None] = None
    packs: Union[float, None] = None
    units_per_pack: Union[float, None] = None
    quantity_ml: Union[float, None] = None
    quantity_l: Union[float, None] = None
    quantity_g: Union[float, None] = None
    vat_rate: Union[float, None] = None
    verdict: Union[str, None] = None
    flags: list = []
    discount: Union[dict, None] = None

class InvoiceMeta(BaseModel):
    total_inc: Union[float, None] = None    # pounds
    created_at: Union[str, None] = None
    ocr_avg_conf: Union[float, None] = None
    ocr_min_conf: Union[float, None] = None
    pages: list = []

class ManualPairRequest(BaseModel):
    dn_id: str

class InvoicePayload(BaseModel):
    id: str
    meta: InvoiceMeta
    lines: List[InvoiceLine]

app = FastAPI()

# Configure CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def _startup():
    from db_manager_unified import _DB_PATH
    print(f"[BOOT] DB path = {_DB_PATH}")
    print(f"[BOOT] DB exists = {_DB_PATH.exists()}")
    print(f"[BOOT] DB size = {_DB_PATH.stat().st_size if _DB_PATH.exists() else 'N/A'} bytes")

def _pounds(p): 
    return None if p is None else round(p/100.0, 2)

@app.get("/health")
def health(): 
    return {"status":"ok","bulletproof_ingestion":True}

@app.get("/api/debug/db-path")
def debug_db_path():
    """Debug endpoint to show resolved database path"""
    from db_manager_unified import _DB_PATH
    return {
        "db_path": str(_DB_PATH),
        "exists": _DB_PATH.exists(),
        "size_bytes": _DB_PATH.stat().st_size if _DB_PATH.exists() else None,
        "resolved": str(_DB_PATH.resolve())
    }

@app.get("/health/deep")
def health_deep():
    """Deep health check for CI/ops"""
    try:
        # Check DB connectivity
        conn = get_db_manager().get_conn()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        db_ok = cur.fetchone()[0] == 1
        
        # Check latest migration
        cur.execute("SELECT MAX(version) FROM migrations")
        latest_migration = cur.fetchone()[0]
        
        # Check foreign keys are ON
        cur.execute("PRAGMA foreign_keys")
        fk_ok = cur.fetchone()[0] == 1
        
        return {
            "db_ok": db_ok,
            "migrations_ok": latest_migration is not None,
            "foreign_keys_ok": fk_ok,
            "latest_migration": latest_migration
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@app.get("/api/invoices/{invoice_id}", response_model=InvoicePayload)
def get_invoice(invoice_id: str):
    # Minimal, schema-compliant payload from our seeded tables.
    from db_manager_unified import get_db_manager
    import sqlite3
    m = get_db_manager()
    conn = sqlite3.connect(m.db_path)
    conn.row_factory = sqlite3.Row
    try:
        inv = conn.execute(
            "SELECT id, currency, total_amount_pennies, ocr_avg_conf, ocr_min_conf "
            "FROM invoices WHERE id=?",
            (invoice_id,)
        ).fetchone()
        if not inv:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="invoice not found")

        rows = conn.execute(
            "SELECT id, row_idx, description, quantity, unit_price_pennies, line_total_pennies "
            "FROM invoice_line_items WHERE invoice_id=? ORDER BY row_idx",
            (invoice_id,)
        ).fetchall()

        meta = {
            "supplier": None,
            "invoice_no": None,
            "date_iso": None,
            "currency": inv["currency"] if "currency" in inv.keys() else "GBP",
            "ocr_avg_conf": inv["ocr_avg_conf"],
            "ocr_min_conf": inv["ocr_min_conf"],
            "total_inc": (inv["total_amount_pennies"] or 0) / 100.0,
        }

        lines = []
        for r in rows:
            line_id = r["id"] if "id" in r.keys() and r["id"] is not None else r["row_idx"]
            lines.append({
                "id": str(line_id if line_id is not None else 0),  # <-- must be string
                "desc": r["description"],
                "qty": float(r["quantity"] or 0),                   # <-- always float
                "unit_price": (r["unit_price_pennies"] or 0) / 100.0,
                "line_total": (r["line_total_pennies"] or 0) / 100.0,
                "flags": [],
            })

        return {"id": inv["id"], "meta": meta, "lines": lines}
    finally:
        conn.close()

@app.post("/api/invoices/{invoice_id}/pairing/auto")
def auto_pairing(invoice_id: str):
    """Auto-pair invoice with delivery notes"""
    try:
        conn = get_db_manager().get_conn()
        cursor = conn.cursor()
        
        # Find best matching delivery note
        cursor.execute("""
            SELECT dn.id as dn_id, 
                   COUNT(*) as matching_lines,
                   AVG(ABS(ili.quantity_each - dli.quantity_each)) as avg_qty_diff
            FROM delivery_notes dn
            JOIN delivery_line_items dli ON dn.id = dli.delivery_note_id
            JOIN invoice_line_items ili ON ili.invoice_id = ?
            WHERE dn.supplier_name = (SELECT supplier_name FROM invoices WHERE id = ?)
            GROUP BY dn.id
            ORDER BY matching_lines DESC, avg_qty_diff ASC
            LIMIT 1
        """, (invoice_id, invoice_id))
        
        match = cursor.fetchone()
        if match:
            # Create match link
            link_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO match_links (id, invoice_id, delivery_note_id, confidence, status, reasons_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            """, (link_id, invoice_id, match['dn_id'], 0.8, 'matched', '[]'))
            
            # Create match link items
            cursor.execute("""
                INSERT INTO match_link_items (link_id, invoice_item_id, dn_item_id, reason, qty_match_pct)
                SELECT ?, ili.id, dli.id, 'AUTO_MATCH', 95.0
                FROM invoice_line_items ili
                JOIN delivery_line_items dli ON dli.delivery_note_id = ?
                WHERE ili.invoice_id = ?
            """, (link_id, match['dn_id'], invoice_id))
            
            conn.commit()
            conn.close()
            
            return {
                "dn_id": match['dn_id'],
                "score": 0.8,
                "qty_match_pct": 95.0
            }
        else:
            conn.close()
            raise HTTPException(status_code=404, detail="No matching delivery notes found")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/invoices/{invoice_id}/pairing/manual")
async def manual_pairing(invoice_id: str, body: ManualPairRequest):
    """Manual pairing: 422 (validation via model), 404 (DN missing),
    200 (create), 200 (idempotent duplicate), 409 (other constraint)."""
    dn_id = body.dn_id

    # Per-request connection avoids "closed database" and locking weirdness
    db_path = (Path(__file__).resolve().parent.parent / "data" / "owlin.db")
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    cur = conn.cursor()
    try:
        # 404 if delivery note does not exist
        cur.execute("SELECT 1 FROM delivery_notes WHERE id = ?", (dn_id,))
        r = cur.fetchone()
        if r is None:
            raise HTTPException(status_code=404, detail="delivery_note not found")

        # Idempotent: if link already exists, return it
        cur.execute(
            "SELECT id FROM match_links WHERE invoice_id = ? AND delivery_note_id = ?",
            (invoice_id, dn_id),
        )
        r = cur.fetchone()
        if r:
            link_id = r[0] if not hasattr(r, "keys") else r["id"]
            return {"ok": True, "link_id": link_id, "idempotent": True}

        import uuid
        link_id = str(uuid.uuid4())
        cur.execute(
            """
            INSERT INTO match_links
                (id, invoice_id, delivery_note_id, confidence, status, reasons_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            """,
            (link_id, invoice_id, dn_id, 1.0, "matched", "[]"),
        )

        cur.execute(
            """
            INSERT INTO match_link_items (link_id, invoice_item_id, dn_item_id, reason, qty_match_pct)
            SELECT ?, id, NULL, 'MANUAL_OVERRIDE', 100.0
            FROM invoice_line_items
            WHERE invoice_id = ?
            """,
            (link_id, invoice_id),
        )

        conn.commit()
        return {"ok": True, "link_id": link_id}
    except HTTPException:
        raise
    except sqlite3.IntegrityError as e:
        msg = str(e)
        # Treat duplicate race as idempotent 200
        if "UNIQUE constraint failed: match_links.invoice_id, match_links.delivery_note_id" in msg:
            cur.execute(
                "SELECT id FROM match_links WHERE invoice_id = ? AND delivery_note_id = ?",
                (invoice_id, dn_id),
            )
            r2 = cur.fetchone()
            if r2:
                link_id = r2[0] if not hasattr(r2, "keys") else r2["id"]
                return {"ok": True, "link_id": link_id, "idempotent": True}
        if "FOREIGN KEY constraint failed" in msg:
            # Shouldn't happen due to precheck; map to 404 if it does
            raise HTTPException(status_code=404, detail="delivery_note not found")
        raise HTTPException(status_code=409, detail=f"constraint error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            conn.close()
        except Exception:
            pass

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Owlin Test Server...")
    print("📍 Server will be available at: http://localhost:8000")
    print("✅ Health check: http://localhost:8000/health")
    uvicorn.run(app, host="0.0.0.0", port=8000)
