import sys
import os
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException
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
    raw = fetch_invoice(invoice_id)
    if not raw:
        raise HTTPException(status_code=404, detail="invoice not found")
    # presentation conversion
    raw["meta"]["total_inc"] = _pounds(raw["meta"].pop("total_amount_pennies", None))
    for ln in raw["lines"]:
        if "unit_price_pennies" in ln:
            ln["unit_price"] = _pounds(ln.pop("unit_price_pennies"))
        if "line_total_pennies" in ln:
            ln["line_total"] = _pounds(ln.pop("line_total_pennies"))
    return raw

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
def manual_pairing(invoice_id: str, request: Dict[str, Any]):
    """Manual pairing of invoice with delivery note"""
    try:
        dn_id = request.get('dn_id')
        
        if not dn_id:
            raise HTTPException(status_code=400, detail="dn_id required")
        
        conn = get_db_manager().get_conn()
        cursor = conn.cursor()
        
        # Create manual match link
        link_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO match_links (id, invoice_id, delivery_note_id, confidence, status, reasons_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
        """, (link_id, invoice_id, dn_id, 1.0, 'matched', '[]'))
        
        # Create match link items for all lines
        cursor.execute("""
            INSERT INTO match_link_items (link_id, invoice_item_id, dn_item_id, reason, qty_match_pct)
            SELECT ?, id, NULL, 'MANUAL_OVERRIDE', 100.0
            FROM invoice_line_items WHERE invoice_id = ?
        """, (link_id, invoice_id))
        
        conn.commit()
        conn.close()
        
        return {"ok": True}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Owlin Test Server...")
    print("📍 Server will be available at: http://localhost:8000")
    print("✅ Health check: http://localhost:8000/health")
    uvicorn.run(app, host="0.0.0.0", port=8000) 