# backend/app.py
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uuid, pathlib, os

# Ensure DB ready first
from db import init as db_init, migrate as db_migrate, get_conn
from migrations import run_startup_migrations, get_db_path

# Run startup migrations
db_path = get_db_path()
run_startup_migrations(db_path)

# Initialize database
db_init()
db_migrate()

# Import services AFTER migrations
from services import handle_upload_and_queue, compare_dn_invoice, get_job_analytics, STORAGE

app = FastAPI(title="Owlin OCR API", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/health")
def health():
    try:
        with get_conn() as c:
            c.execute("SELECT 1;").fetchone()
        return {"status":"ok","database":"connected"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status":"error","detail":str(e)})

@app.get("/ready")
def ready():
    # extend if you add external deps later
    return {"ready": True}

@app.get("/invoices")
def list_invoices(limit: int = 50, cursor: str = None):
    """List invoices with pagination support"""
    with get_conn() as c:
        # Simple query to debug
        query = "SELECT id, status, confidence, supplier_name, filename FROM invoices ORDER BY id DESC LIMIT ?"
        params = [limit]
        
        rows = c.execute(query, params).fetchall()
        invoices = [dict(r) for r in rows]
        
        return {
            "invoices": invoices,
            "pagination": {
                "limit": limit,
                "has_more": False,
                "next_cursor": None
            }
        }

@app.get("/invoices/{inv_id}")
def get_invoice(inv_id: str):
    with get_conn() as c:
        # Use data database schema directly
        inv = c.execute("SELECT * FROM invoices WHERE id=?", (inv_id,)).fetchone()
        if not inv:
            raise HTTPException(status_code=404, detail="Not found")
        
        # Parse line_items from JSON
        import json
        line_items_json = inv.get('line_items', '[]')
        try:
            items_dict = json.loads(line_items_json) if line_items_json else []
        except:
            items_dict = []
        
        return {
            "invoice": dict(inv), 
            "items": items_dict,  # legacy field
            "line_items": items_dict  # new field for UI compatibility
        }

@app.post("/invoices/{invoice_id}/reprocess")
def reprocess_invoice(invoice_id: str):
    with get_conn() as c:
        row = c.execute("SELECT file_hash, filename FROM invoices WHERE id=?", (invoice_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    # Use robust path resolver
    from services import resolve_path_for_reprocess
    path = resolve_path_for_reprocess(row["file_hash"], row["filename"])
    if not path:
        # Return actionable guidance, don't 500
        raise HTTPException(
            status_code=409,
            detail="Original file not present in storage; re-upload required"
        )
    
    job_id = services.new_job_for_existing_file(path, row["file_hash"])
    return {"job_id": job_id}

@app.post("/upload")
def upload(file: UploadFile = File(...)):
    # Create temporary file first
    suffix = pathlib.Path(file.filename).suffix.lower() or ".bin"
    temp_dest = STORAGE / f"temp_{uuid.uuid4().hex}{suffix}"
    temp_dest.write_bytes(file.file.read())
    
    # Use canonical storage system
    from services import _store_upload, _sha256_bytes
    with open(temp_dest, "rb") as f:
        file_hash = _sha256_bytes(f.read())
    
    # Store with canonical naming
    canonical_path = _store_upload(str(temp_dest), file_hash, file.filename)
    
    result = handle_upload_and_queue(canonical_path, file.filename)
    if result.get("duplicate"):
        return JSONResponse(
            status_code=409,
            content={"error":"duplicate","invoice_id":result["invoice_id"],"job_id":result["job_id"]}
        )
    return {"job_id": result["job_id"]}

@app.get("/jobs/{job_id}")
def job_status(job_id: str):
    with get_conn() as c:
        r = c.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        if not r: raise HTTPException(status_code=404, detail="Not found")
        return dict(r)

@app.get("/analytics")
def analytics():
    return get_job_analytics()

@app.post("/support-pack")
def create_support_pack():
    """Create a support pack with database, audit log, and OCR traces"""
    try:
        from diagnostics import create_support_pack
        pack_path = create_support_pack(max_jobs=10, include_ocr_traces=True)
        return {
            "ok": True, 
            "path": pack_path,
            "message": "Support pack created successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create support pack: {str(e)}")

@app.get("/support-packs")
def list_support_packs():
    """List existing support packs"""
    try:
        from diagnostics import list_support_packs
        packs = list_support_packs()
        return {
            "packs": packs,
            "count": len(packs)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list support packs: {str(e)}")

@app.get("/delivery-notes/unmatched")
def get_unmatched_notes():
    """Get unmatched delivery notes"""
    with get_conn() as c:
        rows = c.execute("""
          SELECT id, note_number, supplier_name, date, venue, paired_invoice_id
          FROM delivery_notes 
          WHERE paired_invoice_id IS NULL
          ORDER BY rowid DESC
        """).fetchall()
        return [dict(r) for r in rows]

@app.get("/delivery-notes/{dn_id}")
def get_delivery_note(dn_id: str):
    """Get delivery note details with items"""
    with get_conn() as c:
        dn = c.execute("SELECT * FROM delivery_notes WHERE id=?", (dn_id,)).fetchone()
        if not dn:
            raise HTTPException(status_code=404, detail="Not found")
        items = c.execute("SELECT * FROM dn_items WHERE dn_id=?", (dn_id,)).fetchall()
        return {"delivery_note": dict(dn), "items": [dict(i) for i in items]}

@app.get("/unmatched-count")
def get_unmatched_count():
    """Get count of unmatched delivery notes"""
    with get_conn() as c:
        count = c.execute("SELECT COUNT(*) FROM delivery_notes WHERE paired_invoice_id IS NULL").fetchone()[0]
        return {"count": count}

@app.get("/issues-count")
def get_issues_count():
    """Get count of invoices with issues"""
    with get_conn() as c:
        count = c.execute("SELECT COUNT(*) FROM invoices WHERE issues_count > 0").fetchone()[0]
        return {"count": count}

@app.get("/invoices/{invoice_id}/pairing_suggestions")
def pairing_suggestions(invoice_id: str):
    """Get delivery note pairing suggestions for an invoice"""
    try:
        # Get invoice details
        with get_conn() as c:
            inv = c.execute("SELECT * FROM invoices WHERE id=?", (invoice_id,)).fetchone()
            if not inv:
                raise HTTPException(status_code=404, detail="Invoice not found")
            
            # Get unmatched delivery notes
            dns = c.execute("""
                SELECT id, supplier_name, date, total_amount 
                FROM delivery_notes 
                WHERE paired_invoice_id IS NULL
                ORDER BY rowid DESC
            """).fetchall()
        
        # Convert to dict format for pairing
        invoice_dict = {
            "supplier": inv["supplier_name"],
            "invoice_date": inv["invoice_date"],
            "totals": {"subtotal": inv["total_amount"]}
        }
        
        delivery_notes = []
        for dn in dns:
            delivery_notes.append({
                "id": dn["id"],
                "supplier": dn["supplier_name"],
                "date": dn["date"],
                "amount": dn["total_amount"]
            })
        
        # Get suggestions
        try:
            from pairing import suggest_dn_matches
            suggestions = suggest_dn_matches(invoice_dict, delivery_notes)
        except ImportError:
            # Fallback if pairing module not available
            suggestions = []
        
        return [
            {
                "score": round(score, 3),
                "delivery_note": dn,
            } for (score, dn) in suggestions
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get pairing suggestions: {str(e)}")

@app.post("/dev/reset")
def dev_reset():
    """Development endpoint: Reset entire database and clear uploaded files"""
    try:
        import shutil
        import os
        
        # Clear database
        with get_conn() as c:
            c.execute("DELETE FROM invoices")
            c.execute("DELETE FROM invoice_items") 
            c.execute("DELETE FROM jobs")
            c.execute("DELETE FROM delivery_notes")
            c.execute("DELETE FROM dn_items")
            c.execute("DELETE FROM audit_log")
            c.commit()
        
        # Clear uploaded files
        if STORAGE.exists():
            shutil.rmtree(STORAGE)
            STORAGE.mkdir(parents=True, exist_ok=True)
        
        # Clear support packs
        backup_dir = pathlib.Path("backups")
        if backup_dir.exists():
            for file in backup_dir.glob("support_pack_*.zip"):
                file.unlink()
        
        return {
            "ok": True,
            "message": "Development reset complete - database and files cleared",
            "timestamp": str(pathlib.Path().cwd())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reset failed: {str(e)}")

@app.post("/dev/sample-data")
def dev_sample_data():
    """Development endpoint: Create sample delivery notes for testing"""
    try:
        with get_conn() as c:
            # Create sample delivery notes
            sample_notes = [
                {
                    "id": "dn_sample_1",
                    "note_number": "DN-2024-001",
                    "supplier_name": "Fresh Foods Ltd",
                    "date": "2024-01-15",
                    "venue": "Main Kitchen",
                    "paired_invoice_id": None
                },
                {
                    "id": "dn_sample_2", 
                    "note_number": "DN-2024-002",
                    "supplier_name": "Beverage Supply Co",
                    "date": "2024-01-16",
                    "venue": "Bar Area",
                    "paired_invoice_id": None
                },
                {
                    "id": "dn_sample_3",
                    "note_number": "DN-2024-003", 
                    "supplier_name": "Cleaning Supplies Inc",
                    "date": "2024-01-17",
                    "venue": "Housekeeping",
                    "paired_invoice_id": None
                }
            ]
            
            for note in sample_notes:
                c.execute("""
                    INSERT OR REPLACE INTO delivery_notes 
                    (id, note_number, supplier_name, date, venue, paired_invoice_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    note["id"], note["note_number"], note["supplier_name"],
                    note["date"], note["venue"], note["paired_invoice_id"]
                ))
                
                # Add some sample items for each note
                sample_items = [
                    ("Fresh Tomatoes", 5.0, 120, 20),
                    ("Lettuce Heads", 3.0, 80, 20),
                    ("Cucumbers", 2.0, 60, 20)
                ]
                
                for desc, qty, unit_price, vat_rate in sample_items:
                    c.execute("""
                        INSERT INTO dn_items 
                        (dn_id, description, qty, unit_price, vat_rate)
                        VALUES (?, ?, ?, ?, ?)
                    """, (note["id"], desc, qty, unit_price, vat_rate))
            
            c.commit()
            
        return {
            "ok": True,
            "message": f"Created {len(sample_notes)} sample delivery notes",
            "notes": sample_notes
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sample data creation failed: {str(e)}") 

@app.get("/api/health/post_ocr")
def post_ocr_health():
    """Health probe for post-OCR pipeline performance"""
    try:
        with get_conn() as c:
            # Count total invoices
            try:
                total_invoices = c.execute("SELECT COUNT(*) FROM invoices").fetchone()[0]
            except Exception:
                total_invoices = 0
            
            # Count multi-invoice uploads (group by file_hash)
            try:
                multi_invoice_uploads = c.execute("""
                    SELECT COUNT(DISTINCT file_hash) 
                    FROM (
                        SELECT file_hash, COUNT(*) as cnt 
                        FROM invoices 
                        WHERE file_hash IS NOT NULL
                        GROUP BY file_hash 
                        HAVING cnt > 1
                    )
                """).fetchone()[0]
            except Exception:
                multi_invoice_uploads = 0
            
            # Count high confidence but zero line items (try both line_items column and invoice_items table)
            hi_conf_zero_lines = 0
            try:
                # Try line_items column first
                hi_conf_zero_lines = c.execute("""
                    SELECT COUNT(*) 
                    FROM invoices
                    WHERE confidence >= 80 
                    AND (line_items IS NULL OR line_items = '' OR line_items = '[]')
                """).fetchone()[0]
            except Exception:
                try:
                    # Fallback to invoice_items table
                    hi_conf_zero_lines = c.execute("""
                        SELECT COUNT(*) 
                        FROM invoices i
                        LEFT JOIN invoice_items ii ON ii.invoice_id = i.id
                        WHERE i.confidence >= 80 
                        AND (SELECT COUNT(*) FROM invoice_items WHERE invoice_id = i.id) = 0
                    """).fetchone()[0]
                except Exception:
                    hi_conf_zero_lines = 0
            
            # Count potential total mismatches
            total_mismatch = 0
            try:
                total_mismatch = c.execute("""
                    SELECT COUNT(*) 
                    FROM invoices i
                    WHERE (i.subtotal_p = 0 OR i.subtotal_p IS NULL)
                    AND (SELECT COUNT(*) FROM invoice_items WHERE invoice_id = i.id) > 0
                """).fetchone()[0]
            except Exception:
                total_mismatch = 0
            
            stats = {
                "invoices": total_invoices,
                "multi_invoice_uploads": multi_invoice_uploads,
                "hi_conf_zero_lines": hi_conf_zero_lines,
                "total_mismatch": total_mismatch,
                "status": "healthy" if hi_conf_zero_lines < 5 else "warning"
            }
            return stats
    except Exception as e:
        return {"status": "error", "detail": str(e)} 