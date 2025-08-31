# backend/app.py
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uuid, pathlib, os

# Use unified database manager
from db_manager_unified import get_db_manager

# Initialize unified database manager and run migrations
db_manager = get_db_manager()
db_manager.run_migrations()

# Import STORAGE from services.py for backward compatibility
import importlib.util
import os
spec = importlib.util.spec_from_file_location("services_module", os.path.join(os.path.dirname(__file__), "services.py"))
services_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(services_module)
STORAGE = services_module.STORAGE

app = FastAPI(title="Owlin OCR API", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/health")
def health():
    try:
        # Use unified database manager for health check
        stats = db_manager.get_system_stats()
        return {"status":"ok","database":"connected","stats":stats}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status":"error","detail":str(e)})

@app.get("/ready")
def ready():
    # extend if you add external deps later
    return {"ready": True}

@app.get("/invoices")
def list_invoices(limit: int = 50, cursor: str = None):
    """List invoices with pagination support"""
    with db_manager.get_connection() as c:
        # Use correct column names from unified schema - exact fields as required
        query = """
            SELECT i.id, i.status, i.confidence, i.validation_flags, i.page_range, 
                   i.doc_type, i.paired, i.created_at, uf.canonical_path as absolute_path, 
                   uf.file_hash
            FROM invoices i
            LEFT JOIN uploaded_files uf ON i.file_id = uf.id
            ORDER BY i.created_at DESC LIMIT ?
        """
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
    with db_manager.get_connection() as c:
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
    with db_manager.get_connection() as c:
        # Use correct column names and join with uploaded_files
        row = c.execute("""
            SELECT uf.file_hash, uf.original_filename, uf.canonical_path
            FROM invoices i
            JOIN uploaded_files uf ON i.file_id = uf.id
            WHERE i.id = ?
        """, (invoice_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    # Check if file exists at canonical path
    import os
    if not os.path.exists(row["canonical_path"]):
        # Return 409 with proper error code and remediation
        return JSONResponse(
            status_code=409,
            content={
                "error": "missing_source_file",
                "code": "missing_source_file", 
                "detail": "Original file not present in storage; re-upload required",
                "file_hash": row["file_hash"],
                "original_filename": row["original_filename"],
                "expected_path": row["canonical_path"],
                "remediation": "Please re-upload the original file to reprocess this invoice"
            }
        )
    
    # Create a new job for reprocessing
    job_id = f"job_{uuid.uuid4().hex[:8]}"
    db_manager.create_job(
        job_id=job_id,
        kind="reprocess",
        status="queued"
    )
    
    return {"job_id": job_id}

@app.post("/upload")
def upload(file: UploadFile = File(...)):
    """Upload file using bulletproof pipeline"""
    try:
        # Use the bulletproof upload pipeline
        from upload_pipeline_bulletproof import get_upload_pipeline
        pipeline = get_upload_pipeline()
        
        # Save uploaded file to temporary location
        import tempfile
        from pathlib import Path
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp:
            content = file.file.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        # Process the uploaded file
        import asyncio
        result = asyncio.run(pipeline.process_upload(tmp_path, file.filename))
        
        # Clean up temp file
        os.unlink(tmp_path)
        
        if not result.success:
            raise HTTPException(status_code=400, detail=result.error_message or "Upload failed")
        
        # Return job ID (we'll need to create a job for this)
        job_id = f"job_{uuid.uuid4().hex[:8]}"
        
        # Create job record
        db_manager.create_job(
            job_id=job_id,
            kind="upload",
            status="completed" if result.success else "failed"
        )
        
        return {"job_id": job_id}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.get("/jobs/{job_id}")
def job_status(job_id: str):
    with db_manager.get_connection() as c:
        r = c.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        if not r: raise HTTPException(status_code=404, detail="Not found")
        return dict(r)

@app.get("/analytics")
def analytics():
    """Get job analytics using unified database manager"""
    try:
        with db_manager.get_connection() as c:
            # Get job statistics
            stats = {}
            
            # Total jobs by status
            cursor = c.execute("""
                SELECT status, COUNT(*) as count 
                FROM jobs 
                GROUP BY status
            """)
            stats['jobs_by_status'] = {row['status']: row['count'] for row in cursor.fetchall()}
            
            # Recent job activity
            cursor = c.execute("""
                SELECT status, created_at 
                FROM jobs 
                ORDER BY created_at DESC 
                LIMIT 10
            """)
            stats['recent_jobs'] = [dict(row) for row in cursor.fetchall()]
            
            # Upload statistics
            cursor = c.execute("""
                SELECT processing_status, COUNT(*) as count 
                FROM uploaded_files 
                GROUP BY processing_status
            """)
            stats['uploads_by_status'] = {row['processing_status']: row['count'] for row in cursor.fetchall()}
            
            return {
                "analytics": stats,
                "timestamp": "2024-01-01T00:00:00Z"  # Placeholder timestamp
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analytics error: {str(e)}")

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
    with db_manager.get_connection() as c:
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
    with db_manager.get_connection() as c:
        dn = c.execute("SELECT * FROM delivery_notes WHERE id=?", (dn_id,)).fetchone()
        if not dn:
            raise HTTPException(status_code=404, detail="Not found")
        items = c.execute("SELECT * FROM dn_items WHERE dn_id=?", (dn_id,)).fetchall()
        return {"delivery_note": dict(dn), "items": [dict(i) for i in items]}

@app.get("/unmatched-count")
def get_unmatched_count():
    """Get count of unmatched delivery notes"""
    with db_manager.get_connection() as c:
        count = c.execute("SELECT COUNT(*) FROM delivery_notes WHERE paired_invoice_id IS NULL").fetchone()[0]
        return {"count": count}

@app.get("/issues-count")
def get_issues_count():
    """Get count of invoices with issues"""
    with db_manager.get_connection() as c:
        count = c.execute("SELECT COUNT(*) FROM invoices WHERE issues_count > 0").fetchone()[0]
        return {"count": count}

@app.get("/invoices/{invoice_id}/pairing_suggestions")
def pairing_suggestions(invoice_id: str):
    """Get delivery note pairing suggestions for an invoice"""
    try:
        # Get invoice details
        with db_manager.get_connection() as c:
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

@app.post("/pairing/suggestions")
def get_pairing_suggestions_endpoint(invoice_id: str):
    """Get pairing suggestions for an invoice"""
    try:
        from pairing import get_pairing_suggestions, auto_pair_if_threshold_met
        
        # Check for auto-pairing first
        auto_paired_dn = auto_pair_if_threshold_met(invoice_id)
        if auto_paired_dn:
            return {
                "auto_paired": True,
                "delivery_note_id": auto_paired_dn,
                "suggestions": []
            }
        
        # Get manual suggestions
        suggestions = get_pairing_suggestions(invoice_id, top_k=3)
        
        return {
            "auto_paired": False,
            "delivery_note_id": None,
            "suggestions": suggestions
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get pairing suggestions: {str(e)}")

@app.post("/pairing/confirm")
def confirm_pairing_endpoint(request: dict):
    """Confirm pairing between invoice and delivery note"""
    try:
        invoice_id = request.get("invoice_id")
        delivery_note_id = request.get("delivery_note_id")
        
        if not invoice_id or not delivery_note_id:
            raise HTTPException(status_code=400, detail="Missing invoice_id or delivery_note_id")
        
        from pairing import confirm_pairing
        
        success = confirm_pairing(invoice_id, delivery_note_id)
        
        if success:
            return {
                "success": True,
                "message": "Pairing confirmed successfully",
                "invoice_id": invoice_id,
                "delivery_note_id": delivery_note_id
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to confirm pairing")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to confirm pairing: {str(e)}")

@app.post("/dev/reset")
def dev_reset():
    """Development endpoint: Reset entire database and clear uploaded files"""
    try:
        import shutil
        import os
        
        # Clear database
        with db_manager.get_connection() as c:
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
        with db_manager.get_connection() as c:
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
def get_post_ocr_health():
    """Enhanced health endpoint with specific OCR metrics"""
    try:
        from datetime import datetime, timedelta
        
        # Calculate 24 hours ago
        twenty_four_hours_ago = datetime.now() - timedelta(hours=24)
        twenty_four_hours_str = twenty_four_hours_ago.strftime('%Y-%m-%d %H:%M:%S')
        
        with db_manager.get_connection() as conn:
            # Timeouts in last 24h
            timeouts_24h = conn.execute("""
                SELECT COUNT(*) as count FROM jobs 
                WHERE status = 'timeout' AND created_at >= ?
            """, (twenty_four_hours_str,)).fetchone()['count']
            
            # Failed jobs in last 24h
            failed_24h = conn.execute("""
                SELECT COUNT(*) as count FROM jobs 
                WHERE status = 'failed' AND created_at >= ?
            """, (twenty_four_hours_str,)).fetchone()['count']
            
            # Average duration for completed jobs in last 24h
            avg_duration = conn.execute("""
                SELECT AVG(duration_ms) as avg_duration FROM jobs 
                WHERE status = 'completed' AND created_at >= ? AND duration_ms IS NOT NULL
            """, (twenty_four_hours_str,)).fetchone()['avg_duration']
            avg_duration_ms_24h = int(avg_duration) if avg_duration else 0
            
            # High confidence invoices with zero line items in last 24h
            hi_conf_zero_lines_24h = conn.execute("""
                SELECT COUNT(*) as count FROM invoices i
                LEFT JOIN invoice_line_items ili ON i.id = ili.invoice_id
                WHERE i.confidence > 0.8 AND i.created_at >= ?
                GROUP BY i.id
                HAVING COUNT(ili.id) = 0
            """, (twenty_four_hours_str,)).fetchall()
            hi_conf_zero_lines_24h = len(hi_conf_zero_lines_24h)
            
            # Multiple invoice uploads (same file hash) in last 24h
            multi_invoice_uploads_24h = conn.execute("""
                SELECT COUNT(*) as count FROM (
                    SELECT uf.file_hash, COUNT(*) as upload_count
                    FROM uploaded_files uf
                    JOIN invoices i ON uf.id = i.file_id
                    WHERE uf.upload_timestamp >= ?
                    GROUP BY uf.file_hash
                    HAVING upload_count > 1
                )
            """, (twenty_four_hours_str,)).fetchone()['count']
            
            # Evaluate health status based on metrics
            violations = []
            status = "healthy"
            
            # Check for critical violations
            if timeouts_24h > 0:
                violations.append(f"OCR timeouts detected: {timeouts_24h} in last 24h")
                status = "critical"
            elif failed_24h > 0:
                violations.append(f"Failed jobs detected: {failed_24h} in last 24h")
                status = "critical"
            
            # Check for degraded conditions
            if avg_duration_ms_24h > 10000:
                violations.append(f"Slow processing: avg {avg_duration_ms_24h}ms in last 24h")
                if status != "critical":
                    status = "degraded"
            
            if hi_conf_zero_lines_24h > 0:
                violations.append(f"High confidence invoices with no line items: {hi_conf_zero_lines_24h}")
                if status != "critical":
                    status = "degraded"
            
            return {
                "status": status,
                "timestamp": datetime.now().isoformat(),
                "metrics": {
                    "timeouts_24h": timeouts_24h,
                    "failed_24h": failed_24h,
                    "avg_duration_ms_24h": avg_duration_ms_24h,
                    "hi_conf_zero_lines_24h": hi_conf_zero_lines_24h,
                    "multi_invoice_uploads_24h": multi_invoice_uploads_24h
                },
                "violations": violations
            }
            
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        ) 

# Add pairing endpoints
@app.get("/api/pairing/suggestions")
def get_pairing_suggestions(limit: int = 10):
    """Get delivery note pairing suggestions"""
    try:
        from services.pairing_service import PairingService
        suggestions = PairingService.get_pairing_suggestions(limit)
        
        return {
            "suggestions": suggestions,
            "count": len(suggestions)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting pairing suggestions: {str(e)}")

@app.post("/api/pairing/confirm")
def confirm_pairing(delivery_note_id: str, invoice_id: str):
    """Confirm pairing between delivery note and invoice"""
    try:
        from services.pairing_service import PairingService
        result = PairingService.confirm_pairing(delivery_note_id, invoice_id)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return {
            "delivery_note_id": delivery_note_id,
            "invoice_id": invoice_id,
            "score": result["score"],
            "matched": True
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error confirming pairing: {str(e)}")

@app.post("/api/pairing/reject")
def reject_pairing(suggestion_id: str):
    """Reject pairing suggestion"""
    try:
        from services.pairing_service import PairingService
        result = PairingService.reject_pairing(suggestion_id)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return {
            "suggestion_id": suggestion_id,
            "rejected": True
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error rejecting pairing: {str(e)}") 