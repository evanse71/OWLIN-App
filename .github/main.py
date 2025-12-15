from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File, Query, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uuid
import os
import sqlite3
import time
from typing import List, Dict
from datetime import datetime
from app.db import init_db, insert_document, list_invoices, list_recent_documents, upsert_invoice, append_audit, set_last_error, get_last_error
from backend.image_preprocess import preprocess_bgr_page, save_preprocessed_artifact

# Paths
BASE_DIR = Path(__file__).resolve().parent
SPA_DIR = (BASE_DIR / ".." / "out").resolve()  # Next export defaults -> out

# APP — create the app once, not five times
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:8501", "*"], allow_methods=["*"], allow_headers=["*"])

# Initialize database and ensure uploads directory exists
init_db()
os.makedirs("data/uploads", exist_ok=True)

# API ROUTES — define them BEFORE any SPA/static junk. UNDERSTAND: /api MUST NOT be shadowed.

@app.get("/api/health")
def health():
    append_audit(datetime.now().isoformat(), "local", "health", "{}")
    return {"status": "ok"}

@app.get("/api/health/details")
def health_details():
    """Enhanced health endpoint with database path and system info"""
    import os
    from pathlib import Path
    
    # Get absolute database path
    db_path = "data/owlin.db"
    db_path_abs = os.path.abspath(db_path)
    
    # Check if database exists and get size
    db_exists = os.path.exists(db_path_abs)
    db_size = os.path.getsize(db_path_abs) if db_exists else 0
    
    # Get app version from environment or default (single source of truth)
    app_version = os.getenv("APP_VERSION", "1.2.0")
    
    # Get environment info
    env_info = {
        "python_version": os.sys.version,
        "working_dir": os.getcwd(),
        "db_path_abs": db_path_abs,
        "db_exists": db_exists,
        "db_size_bytes": db_size
    }
    
    append_audit(datetime.now().isoformat(), "local", "health_details", f'{{"db_path": "{db_path_abs}", "db_size": {db_size}}}')
    
    return {
        "status": "ok",
        "db_path_abs": db_path_abs,
        "app_version": app_version,
        "timestamp": datetime.now().isoformat(),
        "env": env_info
    }

@app.get("/api/venues")
def list_venues():
    return {"venues": [{"id": "royal-oak-1", "name": "Royal Oak Hotel"}]}

@app.get("/api/dashboard")
def dashboard(venue_id: str | None = None):
    vid = venue_id or "royal-oak-1"
    return {
        "venueId": vid,
        "venueName": "Royal Oak Hotel" if vid == "royal-oak-1" else "Unknown",
        "totalSpend": 0, "invoiceCount": 0, "supplierCount": 0, "flaggedCount": 0, "matchRate": 0,
        "topSuppliers": [], "issuesByType": [], "forecast": []
    }

@app.get("/api/invoices")
def invoices(
    status: str = Query(None, description="Filter by status"),
    limit: int = Query(50, description="Number of invoices to return"),
    offset: int = Query(0, description="Number of invoices to skip"),
    sort: str = Query("date", description="Sort field (id, date, supplier, value)"),
    q: str = Query(None, description="Search query for supplier or filename"),
    date_from: str = Query(None, description="Filter from date (YYYY-MM-DD)"),
    date_to: str = Query(None, description="Filter to date (YYYY-MM-DD)")
):
    """Get invoices with pagination and filtering"""
    try:
        con = sqlite3.connect("data/owlin.db", check_same_thread=False)
        cur = con.cursor()
        
        # Build query with filters
        where_clause = ""
        params = []
        
        if status:
            where_clause += " AND i.status = ?"
            params.append(status)
            
        if q:
            where_clause += " AND (i.supplier LIKE ? OR d.filename LIKE ?)"
            search_term = f"%{q}%"
            params.extend([search_term, search_term])
            
        if date_from:
            where_clause += " AND i.date >= ?"
            params.append(date_from)
            
        if date_to:
            where_clause += " AND i.date <= ?"
            params.append(date_to)
        
        # Sort mapping with stable sorting (date desc, then id)
        sort_map = {
            "id": "i.id DESC, i.id",
            "date": "i.date DESC, i.id DESC", 
            "supplier": "i.supplier ASC, i.date DESC, i.id DESC",
            "value": "i.value DESC, i.date DESC, i.id DESC"
        }
        sort_field = sort_map.get(sort, "i.date DESC, i.id DESC")
        
        query = f"""
            SELECT i.id, i.doc_id, i.supplier, i.date, i.value, d.filename,
                   COALESCE(i.status, 'scanned') as status,
                   COALESCE(i.confidence, 0.9) as confidence,
                   COALESCE(i.venue, 'Main Restaurant') as venue,
                   COALESCE(i.issues_count, 0) as issues_count,
                   COALESCE(i.paired, 0) as paired,
                   d.filename as source_filename
            FROM invoices i
            LEFT JOIN documents d ON i.doc_id = d.id
            WHERE 1=1 {where_clause}
            ORDER BY {sort_field} DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        
        cur.execute(query, params)
        rows = cur.fetchall()
        
        # Get total count for pagination
        count_query = f"""
            SELECT COUNT(*) FROM invoices i WHERE 1=1 {where_clause}
        """
        cur.execute(count_query, params[:-2])  # Remove limit/offset
        total_count = cur.fetchone()[0]
        
        con.close()
        
        # Transform to normalized format
        invoices = []
        for row in rows:
            invoices.append({
                "id": row[0],
                "doc_id": row[1],
                "filename": row[5] or f"INV-{row[0]}",
                "supplier": row[2] or "Unknown Supplier",
                "date": row[3] or "",
                "total_value": float(row[4]) if row[4] else 0.0,
                "status": row[6],
                "confidence": float(row[7]),
                "venue": row[8],
                "issues_count": int(row[9]),
                "paired": bool(row[10]),
                "source_filename": row[11] or "",
                "delivery_note_ids": []  # TODO: implement delivery note relationships
            })
        
        append_audit(datetime.now().isoformat(), "local", "invoices", f'{{"count": {len(invoices)}, "total": {total_count}}}')
        
        return {
            "items": invoices,
            "total": total_count,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        error_msg = str(e)
        set_last_error(datetime.now().isoformat(), "invoices", error_msg, "{}")
        append_audit(datetime.now().isoformat(), "local", "invoices_error", f'{{"error": "{error_msg}"}}')
        raise HTTPException(status_code=500, detail=error_msg)

@app.get("/api/invoices/{invoice_id}")
def get_invoice(invoice_id: str):
    """Get a specific invoice by ID with line items"""
    try:
        con = sqlite3.connect("data/owlin.db", check_same_thread=False)
        cur = con.cursor()
        
        # Get invoice details
        cur.execute("""
            SELECT i.id, i.doc_id, i.supplier, i.date, i.value, d.filename,
                   COALESCE(i.status, 'scanned') as status,
                   COALESCE(i.confidence, 0.9) as confidence,
                   COALESCE(i.venue, 'Main Restaurant') as venue,
                   COALESCE(i.issues_count, 0) as issues_count,
                   COALESCE(i.paired, 0) as paired
            FROM invoices i
            LEFT JOIN documents d ON i.doc_id = d.id
            WHERE i.id = ?
        """, (invoice_id,))
        
        row = cur.fetchone()
        if not row:
            con.close()
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        # Get line items (mock for now - TODO: implement line_items table)
        cur.execute("""
            SELECT 'Organic Tomatoes' as sku, 'Fresh organic tomatoes' as desc, 
                   50 as qty, 2.50 as unit_price, 125.00 as total, 'kg' as uom
            UNION ALL
            SELECT 'Free Range Eggs', 'Farm fresh eggs', 100, 0.75, 75.00, 'dozen'
            UNION ALL  
            SELECT 'Artisan Bread', 'Handmade sourdough', 25, 3.20, 80.00, 'loaf'
        """)
        line_items = []
        for item_row in cur.fetchall():
            line_items.append({
                "sku": item_row[0],
                "desc": item_row[1], 
                "qty": item_row[2],
                "unit_price": item_row[3],
                "total": item_row[4],
                "uom": item_row[5]
            })
        
        # Get delivery notes (mock for now - TODO: implement delivery_notes table)
        cur.execute("SELECT 'dn-001' as id, 'DN-2024-001' as note_number, '2024-01-15' as date")
        delivery_notes = []
        for dn_row in cur.fetchall():
            delivery_notes.append({
                "id": dn_row[0],
                "note_number": dn_row[1],
                "date": dn_row[2]
            })
        
        con.close()
        
        # Return normalized invoice with line items
        invoice = {
            "id": row[0],
            "filename": row[5] or f"INV-{row[0]}",
            "supplier": row[2] or "Unknown Supplier", 
            "date": row[3] or "",
            "total_value": float(row[4]) if row[4] else 0.0,
            "status": row[6],
            "confidence": float(row[7]),
            "venue": row[8],
            "issues_count": int(row[9]),
            "paired": bool(row[10]),
            "line_items": line_items,
            "delivery_notes": delivery_notes
        }
        
        append_audit(datetime.now().isoformat(), "local", "get_invoice", f'{{"invoice_id": "{invoice_id}", "line_items": {len(line_items)}}}')
        return invoice
    
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        set_last_error(datetime.now().isoformat(), "get_invoice", error_msg, "{}")
        append_audit(datetime.now().isoformat(), "local", "get_invoice_error", f'{{"error": "{error_msg}"}}')
        raise HTTPException(status_code=500, detail=error_msg)

@app.get("/api/notes/unmatched")
def unmatched_notes():
    """Get unmatched delivery notes - placeholder for now"""
    append_audit(datetime.now().isoformat(), "local", "unmatched_notes", "{}")
    # For now, return empty array since we don't have delivery notes table yet
    return []

@app.get("/api/invoices/{invoice_id}/suggestions")
def get_invoice_suggestions(invoice_id: str):
    """Get pairing suggestions for a specific invoice"""
    try:
        from db.pairs import db_list_pairs
        
        # Get suggestions for this invoice (mock for now)
        # TODO: Implement real suggestion logic based on supplier, date, amount similarity
        suggestions = [
            {
                "id": 1,
                "delivery_note_id": "dn-001",
                "delivery_note_number": "DN-2024-001",
                "delivery_date": "2024-01-15",
                "supplier": "Fresh Foods Ltd",
                "total_amount": 125050,
                "similarity": 0.85,
                "confidence": 0.78,
                "value_delta": 0,
                "date_delta_days": 0,
                "reason": "Exact supplier match, same date, amount within 5%"
            },
            {
                "id": 2,
                "delivery_note_id": "dn-002", 
                "delivery_note_number": "DN-2024-002",
                "delivery_date": "2024-01-14",
                "supplier": "Fresh Foods Ltd",
                "total_amount": 118000,
                "similarity": 0.72,
                "confidence": 0.65,
                "value_delta": -7050,
                "date_delta_days": -1,
                "reason": "Same supplier, 1 day difference, amount within 10%"
            }
        ]
        
        append_audit(datetime.now().isoformat(), "local", "invoice_suggestions", f'{{"invoice_id": "{invoice_id}", "count": {len(suggestions)}}}')
        return {"suggestions": suggestions}
        
    except Exception as e:
        error_msg = str(e)
        set_last_error(datetime.now().isoformat(), "invoice_suggestions", error_msg, "{}")
        append_audit(datetime.now().isoformat(), "local", "invoice_suggestions_error", f'{{"error": "{error_msg}"}}')
        raise HTTPException(status_code=500, detail=error_msg)

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        # Generate unique doc_id
        doc_id = str(uuid.uuid4())
        
        # Create safe filename
        safe_name = "".join(c for c in file.filename if c.isalnum() or c in "._-")
        stored_path = f"data/uploads/{doc_id}__{safe_name}"
        
        # Save file
        with open(stored_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Insert into database
        insert_document(doc_id, file.filename, stored_path, len(content))
        
        # Audit log
        append_audit(datetime.now().isoformat(), "local", "upload", f'{{"filename": "{file.filename}", "size": {len(content)}}}')
        
        return {"doc_id": doc_id}
    
    except Exception as e:
        error_msg = str(e)
        set_last_error(datetime.now().isoformat(), "upload", error_msg, "{}")
        append_audit(datetime.now().isoformat(), "local", "upload_error", f'{{"error": "{error_msg}"}}')
        raise HTTPException(status_code=500, detail=error_msg)

@app.post("/api/ocr/run")
def ocr_run(doc: dict):
    try:
        doc_id = doc.get("doc_id", "1")
        
        # Get the uploaded file path from the document
        con = sqlite3.connect("data/owlin.db", check_same_thread=False)
        cur = con.cursor()
        cur.execute("SELECT file_path FROM documents WHERE id = ?", (doc_id,))
        row = cur.fetchone()
        con.close()
        
        preprocess_meta = {}
        if row and row[0]:
            file_path = row[0]
            # Load image for preprocessing
            import cv2
            img_bgr = cv2.imread(file_path)
            if img_bgr is not None:
                # Preprocess the image
                processed_img, preprocess_meta = preprocess_bgr_page(img_bgr)
                
                # Save preprocessed artifact
                doc_stem = os.path.splitext(os.path.basename(file_path))[0]
                artifact_dir = f"data/uploads/{doc_stem}/pages"
                artifact_path = save_preprocessed_artifact(processed_img, artifact_dir, "page_001")
                preprocess_meta["artifact_path"] = artifact_path
        
        # For now, return a stub invoice (existing OCR logic would go here)
        result = {
            "invoice": {
                "supplier": "TestCo",
                "date": "2025-10-12",
                "value": 123.45
            },
            "confidence": 0.9,
            "preprocess": preprocess_meta
        }
        
        # Upsert into invoices table
        upsert_invoice(doc_id, "TestCo", "2025-10-12", 123.45)
        
        # Audit log
        append_audit(datetime.now().isoformat(), "local", "ocr_run", f'{{"doc_id": "{doc_id}", "preprocessed": {bool(preprocess_meta)}}}')
        
        return result
    
    except Exception as e:
        error_msg = str(e)
        set_last_error(datetime.now().isoformat(), "ocr_run", error_msg, "{}")
        append_audit(datetime.now().isoformat(), "local", "ocr_error", f'{{"error": "{error_msg}"}}')
        raise HTTPException(status_code=500, detail=error_msg)

@app.get("/api/documents/recent")
def recent_documents():
    append_audit(datetime.now().isoformat(), "local", "recent_documents", "{}")
    return {"documents": list_recent_documents()}

@app.get("/api/debug/last_error")
def last_error():
    append_audit(datetime.now().isoformat(), "local", "last_error", "{}")
    return get_last_error()

@app.get("/api/analytics/price_history")
def price_history(supplier: str = Query(..., min_length=1)):
    """Return price history for a supplier"""
    try:
        con = sqlite3.connect("data/owlin.db", check_same_thread=False)
        cur = con.cursor()
        cur.execute("""
            SELECT invoice_date, AVG(total_value) as avg_value
            FROM invoices
            WHERE supplier = ?
            GROUP BY invoice_date
            ORDER BY invoice_date ASC
        """, (supplier,))
        rows = cur.fetchall()
        con.close()
        
        series = [{"date": r[0], "value": float(r[1])} for r in rows]
        
        append_audit(datetime.now().isoformat(), "local", "price_history", f'{{"supplier": "{supplier}", "points": {len(series)}}}')
        
        return {"supplier": supplier, "series": series}
    
    except Exception as e:
        error_msg = str(e)
        set_last_error(datetime.now().isoformat(), "price_history", error_msg, "{}")
        append_audit(datetime.now().isoformat(), "local", "price_history_error", f'{{"error": "{error_msg}"}}')
        raise HTTPException(status_code=500, detail=error_msg)

@app.get("/api/analytics/suppliers")
def suppliers():
    """Get list of all suppliers"""
    try:
        con = sqlite3.connect("data/owlin.db", check_same_thread=False)
        cur = con.cursor()
        cur.execute("SELECT DISTINCT supplier FROM invoices WHERE supplier IS NOT NULL AND supplier <> '' ORDER BY supplier")
        out = [r[0] for r in cur.fetchall()]
        con.close()
        
        append_audit(datetime.now().isoformat(), "local", "suppliers", f'{{"count": {len(out)}}}')
        
        return {"suppliers": out}
    
    except Exception as e:
        error_msg = str(e)
        set_last_error(datetime.now().isoformat(), "suppliers", error_msg, "{}")
        append_audit(datetime.now().isoformat(), "local", "suppliers_error", f'{{"error": "{error_msg}"}}')
        raise HTTPException(status_code=500, detail=error_msg)

@app.get("/api/issues/summary")
def issues_summary():
    """Get summary of flagged issues by type"""
    try:
        con = sqlite3.connect("data/owlin.db", check_same_thread=False)
        cur = con.cursor()
        
        # Get total counts by issue type (mock data for now)
        # TODO: Implement real issue tracking
        summary = {
            "total_issues": 8,
            "by_type": [
                {"type": "price_mismatch", "count": 3, "severity": "high"},
                {"type": "quantity_discrepancy", "count": 2, "severity": "medium"}, 
                {"type": "date_mismatch", "count": 2, "severity": "low"},
                {"type": "supplier_mismatch", "count": 1, "severity": "high"}
            ],
            "recent_issues": [
                {
                    "id": "issue-001",
                    "type": "price_mismatch",
                    "severity": "high",
                    "supplier": "Metro Supplies",
                    "invoice_id": "inv-001",
                    "value_delta": -150.00,
                    "created_at": "2024-01-15T10:30:00Z",
                    "description": "Invoice total differs from delivery note by £150"
                },
                {
                    "id": "issue-002", 
                    "type": "quantity_discrepancy",
                    "severity": "medium",
                    "supplier": "Fresh Foods Ltd",
                    "invoice_id": "inv-002",
                    "value_delta": -25.00,
                    "created_at": "2024-01-15T09:15:00Z",
                    "description": "Quantity mismatch: Invoice shows 50kg, delivery note shows 48kg"
                },
                {
                    "id": "issue-003",
                    "type": "date_mismatch", 
                    "severity": "low",
                    "supplier": "Quality Meats Co",
                    "invoice_id": "inv-003",
                    "value_delta": 0.00,
                    "created_at": "2024-01-14T16:45:00Z",
                    "description": "Invoice date 1 day after delivery date"
                }
            ]
        }
        
        con.close()
        
        append_audit(datetime.now().isoformat(), "local", "issues_summary", f'{{"total": {summary["total_issues"]}}}')
        
        return summary
        
    except Exception as e:
        error_msg = str(e)
        set_last_error(datetime.now().isoformat(), "issues_summary", error_msg, "{}")
        append_audit(datetime.now().isoformat(), "local", "issues_summary_error", f'{{"error": "{error_msg}"}}')
        raise HTTPException(status_code=500, detail=error_msg)

@app.get("/api/issues/export")
def export_issues():
    """Export flagged issues as CSV"""
    try:
        # TODO: Implement real CSV export
        # For now, return a mock CSV content
        csv_content = """issue_id,type,severity,supplier,invoice_id,value_delta,created_at,description
issue-001,price_mismatch,high,Metro Supplies,inv-001,-150.00,2024-01-15T10:30:00Z,Invoice total differs from delivery note by £150
issue-002,quantity_discrepancy,medium,Fresh Foods Ltd,inv-002,-25.00,2024-01-15T09:15:00Z,Quantity mismatch: Invoice shows 50kg delivery note shows 48kg
issue-003,date_mismatch,low,Quality Meats Co,inv-003,0.00,2024-01-14T16:45:00Z,Invoice date 1 day after delivery date"""
        
        append_audit(datetime.now().isoformat(), "local", "export_issues", "{}")
        
        return {
            "csv_content": csv_content,
            "filename": f"flagged_issues_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        }
        
    except Exception as e:
        error_msg = str(e)
        set_last_error(datetime.now().isoformat(), "export_issues", error_msg, "{}")
        append_audit(datetime.now().isoformat(), "local", "export_issues_error", f'{{"error": "{error_msg}"}}')
        raise HTTPException(status_code=500, detail=error_msg)

@app.post("/api/audit/error")
async def log_error(error_data: dict):
    """Log error to audit trail"""
    try:
        # In production, this would write to a proper audit log table
        # For now, we'll just log to console and return success
        print(f"[AUDIT ERROR] {error_data.get('timestamp', 'unknown')} - {error_data.get('error_id', 'unknown')}")
        print(f"  Operation: {error_data.get('operation', 'unknown')}")
        print(f"  Component: {error_data.get('component', 'unknown')}")
        print(f"  Message: {error_data.get('message', 'unknown')}")
        print(f"  URL: {error_data.get('url', 'unknown')}")
        print(f"  User Agent: {error_data.get('user_agent', 'unknown')}")
        if error_data.get('metadata'):
            print(f"  Metadata: {error_data.get('metadata')}")
        print("---")
        
        append_audit(datetime.now().isoformat(), "local", "error_logged", f'{{"error_id": "{error_data.get("error_id")}", "operation": "{error_data.get("operation")}"}}')
        
        return {"status": "logged", "error_id": error_data.get('error_id')}
    except Exception as e:
        print(f"Failed to log error: {e}")
        return {"status": "failed", "error": str(e)}

@app.middleware("http")
async def audit_middleware(request: Request, call_next):
    """Middleware to log API calls to audit trail"""
    start_time = time.time()
    
    # Extract request info
    method = request.method
    url = str(request.url)
    path = request.url.path
    
    # Log the request
    print(f"[AUDIT REQUEST] {method} {path} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        response = await call_next(request)
        duration = time.time() - start_time
        
        # Log successful response
        print(f"[AUDIT RESPONSE] {method} {path} - {response.status_code} - {duration:.3f}s")
        
        # Log to audit trail
        append_audit(datetime.now().isoformat(), "local", f"{method.lower()}_{path.replace('/', '_').replace('-', '_')}", f'{{"status": {response.status_code}, "duration": {duration:.3f}}}')
        
        return response
    except Exception as e:
        duration = time.time() - start_time
        
        # Log error response
        print(f"[AUDIT ERROR] {method} {path} - ERROR - {duration:.3f}s - {str(e)}")
        
        # Log to audit trail
        append_audit(datetime.now().isoformat(), "local", f"{method.lower()}_{path.replace('/', '_').replace('-', '_')}_error", f'{{"error": "{str(e)}", "duration": {duration:.3f}}}')
        
        raise e

if SPA_DIR.exists():
    # Serve the whole build at root. html=True makes / and client routes return index.html
    app.mount("/", StaticFiles(directory=str(SPA_DIR), html=True), name="spa")
else:
    print(f"[Owlin] SPA_DIR missing: {SPA_DIR}. Build the frontend into 'out/'")