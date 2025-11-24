from pathlib import Path
import sys
import os

# Add project root to Python path so imports work regardless of working directory
_BACKEND_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _BACKEND_DIR.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from fastapi import FastAPI, HTTPException, UploadFile, File, Query, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse, RedirectResponse
from starlette.responses import RedirectResponse as StarletteRedirectResponse
from fastapi.exceptions import RequestValidationError
import uuid
import io
import sqlite3
import time
import asyncio
import subprocess
import logging
import hashlib
from logging.handlers import RotatingFileHandler
from typing import List, Dict
from datetime import datetime
from backend.app.db import init_db, insert_document, find_document_by_hash, list_invoices, list_recent_documents, upsert_invoice, append_audit, set_last_error, get_last_error, clear_last_error, get_line_items_for_invoice, get_line_items_for_doc, update_document_status, get_db_wal_mode
from backend.image_preprocess import preprocess_bgr_page, save_preprocessed_artifact
from backend.config import FEATURE_OCR_PIPELINE_V2, env_int

# ============================================================================
# LOGGING CONFIGURATION WITH ROTATION
# ============================================================================

# Configure root logger with rotating file handler + console
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Remove any existing handlers to avoid duplicates
for handler in logger.handlers[:]:
    logger.removeHandler(handler)

# Rotating file handler (5MB per file, 3 backups)
file_handler = RotatingFileHandler(
    "backend_stdout.log",
    maxBytes=5_000_000,  # 5MB
    backupCount=3,
    encoding="utf-8"
)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

logger.addHandler(file_handler)
logger.addHandler(console_handler)

logger.info("[STARTUP] Logging configured with rotation (5MB, 3 backups)")

# Paths
BASE_DIR = Path(__file__).resolve().parent
SPA_DIR = (BASE_DIR / ".." / "out").resolve()  # Next export defaults -> out

# APP â€” create the app once, not five times
app = FastAPI(title="Owlin Local API")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:8501", "http://localhost:5176", "http://127.0.0.1:5176", "*"], allow_methods=["*"], allow_headers=["*"])

# Initialize database and ensure uploads directory exists
init_db()
os.makedirs("data/uploads", exist_ok=True)

# ============================================================================
# CONCURRENCY CONTROLS & METRICS
# ============================================================================

# Semaphore to limit concurrent OCR tasks (configurable via env)
OCR_MAX_CONCURRENCY = env_int("OCR_MAX_CONCURRENCY", 4)
_ocr_semaphore = asyncio.Semaphore(OCR_MAX_CONCURRENCY)

# Metrics tracking
_ocr_metrics = {
    "ocr_inflight": 0,
    "ocr_queue": 0,
    "last_doc_id": None,
    "total_processed": 0,
    "total_errors": 0
}

def _update_metrics(key: str, value):
    """Thread-safe metrics update"""
    _ocr_metrics[key] = value

def _get_metrics() -> dict:
    """Get current metrics snapshot"""
    return dict(_ocr_metrics)

# Include OCR router
from backend.api.ocr_router import router as ocr_router
app.include_router(ocr_router)

# Include LLM router
from backend.api.llm_router import router as llm_router
app.include_router(llm_router)

# Include Performance router
from backend.api.performance_router import router as performance_router
app.include_router(performance_router)

# Include Invoices Submit router
from backend.routes.invoices_submit import router as invoices_submit_router
app.include_router(invoices_submit_router)

# Include Documents router
from backend.routes.documents import router as documents_router
app.include_router(documents_router)

# Include Metrics router
from backend.routes.metrics import router as metrics_router
app.include_router(metrics_router)

# Include Forecast router
from backend.routes.forecast import router as forecast_router
app.include_router(forecast_router)

# Include Suppliers router
from backend.routes.suppliers import router as suppliers_router
app.include_router(suppliers_router)

# Include System Health router (for watchdog)
from backend.routes.system_health import router as system_health_router
app.include_router(system_health_router)

# Include Debug Lifecycle router
from backend.routes.debug_lifecycle import router as debug_lifecycle_router
app.include_router(debug_lifecycle_router)

# Include Audit Export router
from backend.routes.audit_export import router as audit_export_router
app.include_router(audit_export_router)

# Include Dev Tools router
from backend.routes.dev_tools import router as dev_tools_router
app.include_router(dev_tools_router)

# Include Chat router
logger.info("[ROUTER] Attempting to import chat router...")
_chat_router_loaded = False
_chat_endpoint = None
_chat_request_model = None
_chat_response_model = None
_chat_router = None

try:
    # Try importing step by step to identify which import fails
    try:
        from backend.routes import chat_router as chat_router_module
        logger.info("[ROUTER] chat_router module imported successfully")
    except Exception as e:
        logger.error(f"[ROUTER] Failed to import chat_router module: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise
    
    try:
        from backend.routes.chat_router import router as chat_router, chat as chat_endpoint, ChatRequest, ChatResponse
        logger.info("[ROUTER] Chat router imported successfully")
        _chat_router_loaded = True
        _chat_endpoint = chat_endpoint
        _chat_request_model = ChatRequest
        _chat_response_model = ChatResponse
        _chat_router = chat_router
    except Exception as e:
        logger.error(f"[ROUTER] Failed to import chat router components: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise
    
except ImportError as e:
    logger.error(f"[ROUTER] ImportError loading chat router: {e}")
    logger.error(f"[ROUTER] This will prevent /api/chat from working!")
    import traceback
    logger.error(traceback.format_exc())
    _chat_router_loaded = False
except SyntaxError as e:
    logger.error(f"[ROUTER] SyntaxError in chat router or dependencies: {e}")
    logger.error(f"[ROUTER] This will prevent /api/chat from working!")
    import traceback
    logger.error(traceback.format_exc())
    _chat_router_loaded = False
except Exception as e:
    logger.error(f"[ROUTER] Unexpected error loading chat router: {e}")
    logger.error(f"[ROUTER] This will prevent /api/chat from working!")
    import traceback
    logger.error(traceback.format_exc())
    _chat_router_loaded = False

# Register route OUTSIDE try/except to ensure it always happens if import succeeded
if _chat_router_loaded and _chat_endpoint and _chat_request_model and _chat_response_model:
    try:
        # Register explicit POST /api/chat route FIRST (before router inclusion to avoid conflicts)
        @app.post("/api/chat", response_model=_chat_response_model, name="chat_post")
        async def chat_route(request: _chat_request_model) -> _chat_response_model:
            return await _chat_endpoint(request)
        logger.info("[ROUTER] Explicit POST /api/chat route registered")
        
        # Include router for other routes (/stream, /history, /status, etc.)
        if _chat_router:
            app.include_router(_chat_router)
            logger.info("[ROUTER] Chat router included successfully")
    except Exception as e:
        logger.error(f"[ROUTER] Failed to register route: {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    # Enhanced route verification
    routes = [r for r in app.routes if hasattr(r, 'path') and r.path == '/api/chat']
    logger.info(f"[ROUTER] Verified: Found {len(routes)} route(s) for /api/chat")
    for route in routes:
        if hasattr(route, 'methods'):
            logger.info(f"[ROUTER]   - Methods: {route.methods}, Name: {getattr(route, 'name', 'N/A')}")
    
    # Check for duplicate routes (same path + method)
    route_signatures = {}
    for route in app.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            for method in route.methods:
                sig = (route.path, method)
                if sig in route_signatures:
                    logger.warning(f"[ROUTER] Duplicate route detected: {method} {route.path} (already registered at {route_signatures[sig]})")
                else:
                    route_signatures[sig] = route.path
    
    # Verify all expected chat routes exist
    expected_routes = [
        ("/api/chat", "POST"),
        ("/api/chat/stream", "POST"),
        ("/api/chat/status", "GET"),
        ("/api/chat/models", "GET"),
        ("/api/chat/diagnose", "GET"),
    ]
    missing_routes = []
    for path, method in expected_routes:
        if (path, method) not in route_signatures:
            missing_routes.append(f"{method} {path}")
    
    if missing_routes:
        logger.error(f"[ROUTER] MISSING ROUTES: {', '.join(missing_routes)}")
    else:
        logger.info("[ROUTER] All expected chat routes are registered")

# Final verification - check if route was actually registered
if _chat_router_loaded:
    final_check = [r for r in app.routes if hasattr(r, 'path') and r.path == '/api/chat' and hasattr(r, 'methods') and 'POST' in r.methods]
    if not final_check:
        logger.error("[ROUTER] CRITICAL: POST /api/chat route was NOT registered despite successful import!")
    else:
        logger.info(f"[ROUTER] Final verification: POST /api/chat route is registered (found {len(final_check)} route(s))")
else:
    logger.error("[ROUTER] CRITICAL: Chat router failed to load - POST /api/chat will not work!")

# Route status diagnostic endpoint
@app.get("/api/routes/status")
async def routes_status():
    """Diagnostic endpoint to check route registration status."""
    routes_info = []
    for route in app.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            routes_info.append({
                "path": route.path,
                "methods": list(route.methods),
                "name": getattr(route, 'name', 'N/A')
            })
    
    # Filter chat routes
    chat_routes = [r for r in routes_info if '/api/chat' in r['path']]
    
    # Check specifically for POST /api/chat
    post_chat_routes = [r for r in chat_routes if r['path'] == '/api/chat' and 'POST' in r['methods']]
    
    return {
        "total_routes": len(routes_info),
        "chat_routes": chat_routes,
        "post_chat_registered": len(post_chat_routes) > 0,
        "post_chat_routes": post_chat_routes,
        "chat_router_loaded": _chat_router_loaded,
        "chat_endpoint_available": _chat_endpoint is not None,
        "all_routes": routes_info
    }

# Simple test endpoint to verify POST routes work
@app.post("/api/test-post")
async def test_post():
    """Simple test endpoint to verify POST routes are working."""
    return {"status": "ok", "message": "POST routes are working"}

# API ROUTES â€" define them BEFORE any SPA/static junk. UNDERSTAND: /api MUST NOT be shadowed.

# NOTE: /invoices is a frontend route (React Router), not an API route
# The SPA fallback route (defined later) will serve index.html for /invoices
# so React Router can handle it. API calls should use /api/invoices

@app.get("/api/health")
def health(request: Request):
    """Health check endpoint with correlation ID support"""
    try:
        correlation_id = getattr(request.state, "correlation_id", None) or request.headers.get("X-Request-Id") or str(uuid.uuid4())
        # Try to log audit, but don't fail if it doesn't work
        try:
            append_audit(datetime.now().isoformat(), "local", "health", f'{{"request_id": "{correlation_id}"}}')
        except Exception as e:
            logger.warning(f"Failed to append audit log: {e}")
        
        return {
            "status": "ok", 
            "ocr_v2_enabled": FEATURE_OCR_PIPELINE_V2,
            "request_id": correlation_id
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Health check error: {str(e)}")

@app.get("/api/health/details")
def health_details():
    """Enhanced health endpoint with database path, metrics, and system info"""
    import os
    from pathlib import Path
    import subprocess
    
    # Get absolute database path
    db_path = "data/owlin.db"
    db_path_abs = os.path.abspath(db_path)
    
    # Check if database exists and get size
    db_exists = os.path.exists(db_path_abs)
    db_size = os.path.getsize(db_path_abs) if db_exists else 0
    
    # Check SQLite WAL mode
    db_wal = (get_db_wal_mode() == "WAL")
    
    # Get app version from environment or default
    app_version = os.getenv("APP_VERSION", "1.2.0")
    
    # Get build SHA (short git hash if available)
    build_sha = "unknown"
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            build_sha = result.stdout.strip()
    except Exception:
        pass
    
    # Get OCR metrics
    metrics = _get_metrics()
    
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
        "db_wal": db_wal,
        "ocr_v2_enabled": FEATURE_OCR_PIPELINE_V2,
        "ocr_inflight": metrics.get("ocr_inflight", 0),
        "ocr_queue": metrics.get("ocr_queue", 0),
        "ocr_max_concurrency": OCR_MAX_CONCURRENCY,
        "total_processed": metrics.get("total_processed", 0),
        "total_errors": metrics.get("total_errors", 0),
        "build_sha": build_sha,
        "last_doc_id": metrics.get("last_doc_id"),
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

# Update the global reference when invoices() is defined
@app.get("/api/invoices")
def invoices(
    status: str = Query(None, description="Filter by status"),
    limit: int = Query(50, description="Number of invoices to return"),
    offset: int = Query(0, description="Number of invoices to skip"),
    sort: str = Query("id", description="Sort field (id, date, supplier, value)")
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
        
        # Sort mapping
        sort_map = {
            "id": "i.id",
            "date": "i.date", 
            "supplier": "i.supplier",
            "value": "i.value"
        }
        sort_field = sort_map.get(sort, "i.id")
        
        query = f"""
            SELECT i.id, i.doc_id as document_id, i.supplier, i.date as invoice_date, i.value as total_value, d.filename,
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
            invoice_id = row[0]
            doc_id = row[1]
            
            # Get line items for this invoice
            line_items = get_line_items_for_invoice(invoice_id) if invoice_id else []
            
            # If no line items by invoice_id, try by doc_id
            if not line_items and doc_id:
                line_items = get_line_items_for_doc(doc_id)
            
            invoices.append({
                "id": invoice_id,
                "doc_id": doc_id,
                "filename": row[5] or f"INV-{invoice_id}",
                "supplier": row[2] or "Unknown Supplier",
                "date": row[3] or "",
                "total_value": float(row[4]) if row[4] else 0.0,
                "status": row[6],
                "confidence": float(row[7]),
                "ocr_confidence": float(row[7]),  # Alias for frontend compatibility
                "venue": row[8],
                "issues_count": int(row[9]),
                "paired": bool(row[10]),
                "source_filename": row[11] or "",
                "delivery_note_ids": [],  # TODO: implement delivery note relationships
                "line_items": line_items
            })
        
        append_audit(datetime.now().isoformat(), "local", "invoices", f'{{"count": {len(invoices)}, "total": {total_count}}}')
        
        return {
            "invoices": invoices,
            "count": len(invoices),
            "total": total_count,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        error_msg = str(e)
        set_last_error(datetime.now().isoformat(), "invoices", error_msg, "{}")
        append_audit(datetime.now().isoformat(), "local", "invoices_error", f'{{"error": "{error_msg}"}}')
        raise HTTPException(status_code=500, detail=error_msg)

# Update the global reference so the alias route can use it
_invoices_func = invoices

# NOTE: /invoices is a FRONTEND route (React Router), not a backend API route
# The frontend (Vite dev server on port 5176) handles /invoices
# Backend only serves /api/invoices for API calls
# Do NOT add a /invoices route here - it will shadow the frontend route!

@app.get("/api/invoices/{invoice_id}")
def get_invoice(invoice_id: str):
    """Get a specific invoice by ID with line items"""
    try:
        con = sqlite3.connect("data/owlin.db", check_same_thread=False)
        cur = con.cursor()
        
        # Get invoice details
        cur.execute("""
            SELECT i.id, i.doc_id as document_id, i.supplier, i.date as invoice_date, i.value as total_value, d.filename,
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
        
        invoice_id = row[0]
        doc_id = row[1]
        
        # Get real line items from database
        line_items = get_line_items_for_invoice(invoice_id)
        
        # If no line items by invoice_id, try by doc_id
        if not line_items and doc_id:
            line_items = get_line_items_for_doc(doc_id)
        
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
        
        # Convert invoice_id to int if possible, otherwise return empty
        try:
            invoice_id_int = int(invoice_id)
        except ValueError:
            return {"suggestions": []}
        
        # Get suggested pairs for this specific invoice
        pairs = db_list_pairs(status="suggested", limit=100, invoice_id=invoice_id_int)
        
        # Format response to match frontend expectations
        suggestions = []
        for pair in pairs:
            suggestion = {
                "id": pair["id"],
                "delivery_note_id": str(pair.get("delivery_id", "")),
                "delivery_note_number": pair.get("delivery_no", ""),
                "delivery_date": pair.get("delivery_date", ""),
                "supplier": pair.get("invoice_supplier", ""),
                "total_amount": float(pair.get("invoice_total", 0.0)) if pair.get("invoice_total") else 0.0,
                "similarity": float(pair.get("confidence", 0.0)),
                "confidence": float(pair.get("confidence", 0.0)),
                "value_delta": 0,  # Calculate if needed
                "date_delta_days": 0,  # Calculate if needed
                "reason": f"Confidence: {pair.get('confidence', 0.0):.0%}"
            }
            suggestions.append(suggestion)
        
        append_audit(datetime.now().isoformat(), "local", "invoice_suggestions", f'{{"invoice_id": "{invoice_id}", "count": {len(suggestions)}}}')
        return {"suggestions": suggestions}
        
    except Exception as e:
        error_msg = str(e)
        set_last_error(datetime.now().isoformat(), "invoice_suggestions", error_msg, "{}")
        append_audit(datetime.now().isoformat(), "local", "invoice_suggestions_error", f'{{"error": "{error_msg}"}}')
        raise HTTPException(status_code=500, detail=error_msg)

@app.get("/api/pairs/suggestions")
def get_pair_suggestions():
    """Get all pairing suggestions"""
    try:
        from db.pairs import db_list_pairs
        
        # Get all suggested pairs from database
        pairs = db_list_pairs(status="suggested", limit=50)
        
        # Format response to match PairSuggestion type
        suggestions = []
        for pair in pairs:
            suggestion = {
                "id": pair["id"],
                "confidence": float(pair.get("confidence", 0.0)),
                "status": pair.get("status", "suggested"),
                "created_at": pair.get("created_at", datetime.now().isoformat()),
                "invoice_filename": pair.get("invoice_filename", ""),
                "invoice_supplier": pair.get("invoice_supplier", ""),
                "invoice_no": pair.get("invoice_no", ""),
                "invoice_date": pair.get("invoice_date", ""),
                "invoice_total": float(pair.get("invoice_total", 0.0)) if pair.get("invoice_total") else 0.0,
                "delivery_filename": pair.get("delivery_filename", ""),
                "delivery_no": pair.get("delivery_no", ""),
                "delivery_date": pair.get("delivery_date", "")
            }
            suggestions.append(suggestion)
        
        append_audit(datetime.now().isoformat(), "local", "pair_suggestions", f'{{"count": {len(suggestions)}}}')
        return {"suggestions": suggestions}
        
    except Exception as e:
        error_msg = str(e)
        set_last_error(datetime.now().isoformat(), "pair_suggestions", error_msg, "{}")
        append_audit(datetime.now().isoformat(), "local", "pair_suggestions_error", f'{{"error": "{error_msg}"}}')
        raise HTTPException(status_code=500, detail=error_msg)

@app.post("/api/pairs/{pair_id}/accept")
def accept_pair(pair_id: int):
    """Accept a pairing suggestion"""
    try:
        from db.pairs import db_set_pair_status
        
        db_set_pair_status(pair_id, "accepted")
        
        append_audit(datetime.now().isoformat(), "local", "pair_accepted", f'{{"pair_id": {pair_id}}}')
        return {"status": "accepted", "pair_id": pair_id}
        
    except Exception as e:
        error_msg = str(e)
        set_last_error(datetime.now().isoformat(), "pair_accept", error_msg, "{}")
        append_audit(datetime.now().isoformat(), "local", "pair_accept_error", f'{{"error": "{error_msg}"}}')
        raise HTTPException(status_code=500, detail=error_msg)

@app.post("/api/pairs/{pair_id}/reject")
def reject_pair(pair_id: int):
    """Reject a pairing suggestion"""
    try:
        from db.pairs import db_set_pair_status
        
        db_set_pair_status(pair_id, "rejected")
        
        append_audit(datetime.now().isoformat(), "local", "pair_rejected", f'{{"pair_id": {pair_id}}}')
        return {"status": "rejected", "pair_id": pair_id}
        
    except Exception as e:
        error_msg = str(e)
        set_last_error(datetime.now().isoformat(), "pair_reject", error_msg, "{}")
        append_audit(datetime.now().isoformat(), "local", "pair_reject_error", f'{{"error": "{error_msg}"}}')
        raise HTTPException(status_code=500, detail=error_msg)

# MOCK REMOVED: returns only real OCR/DB data
@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        # File size limit: 25MB per spec (UPLOAD_MAX_MB=25)
        MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB in bytes
        
        # Validate file format
        filename_lower = file.filename.lower() if file.filename else ""
        allowed_extensions = {'.pdf', '.jpg', '.jpeg', '.png', '.heic', '.heif'}
        file_ext = None
        for ext in allowed_extensions:
            if filename_lower.endswith(ext):
                file_ext = ext
                break
        
        if not file_ext:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file format. Allowed: PDF, JPG, PNG, HEIC"
            )
        
        # Read file content and compute SHA-256 hash
        content = await file.read()
        file_size = len(content)
        
        # Validate file size
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File too large ({file_size / (1024*1024):.1f}MB). Maximum size: 25MB"
            )
        
        # Compute SHA-256 hash for duplicate detection
        file_hash = hashlib.sha256(content).hexdigest()
        
        # Check for duplicate
        existing_doc = find_document_by_hash(file_hash)
        if existing_doc:
            append_audit(datetime.now().isoformat(), "local", "upload_duplicate", 
                        f'{{"filename": "{file.filename}", "hash": "{file_hash[:8]}", "existing_doc_id": "{existing_doc["id"]}"}}')
            return {
                "doc_id": existing_doc["id"],
                "filename": existing_doc["filename"],
                "status": "duplicate",
                "message": "File already uploaded",
                "existing_doc_id": existing_doc["id"],
                "format": file_ext
            }
        
        # Generate unique doc_id
        doc_id = str(uuid.uuid4())
        
        # Create safe filename
        safe_name = "".join(c for c in file.filename if c.isalnum() or c in "._-")
        stored_path = f"data/uploads/{doc_id}__{safe_name}"
        
        # Convert HEIC to PNG if needed
        if file_ext in {'.heic', '.heif'}:
            try:
                from PIL import Image
                import pillow_heif
                pillow_heif.register_heif_opener()
                
                # Open HEIC image
                img = Image.open(io.BytesIO(content))
                # Convert to RGB if needed
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Save as PNG
                png_path = stored_path.rsplit('.', 1)[0] + '.png'
                img.save(png_path, 'PNG')
                stored_path = png_path
                
                # Update content size after conversion
                with open(png_path, 'rb') as f:
                    content = f.read()
                    file_size = len(content)
                    
            except ImportError:
                raise HTTPException(
                    status_code=500,
                    detail="HEIC support requires pillow-heif. Install with: pip install pillow-heif"
                )
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"HEIC conversion failed: {str(e)}"
                )
        else:
            # Save non-HEIC files directly
            with open(stored_path, "wb") as f:
                f.write(content)
        
        # Insert into database with pending status and SHA-256 hash
        insert_document(doc_id, file.filename, stored_path, file_size, sha256=file_hash)
        
        # Audit log
        append_audit(datetime.now().isoformat(), "local", "upload", 
                    f'{{"filename": "{file.filename}", "size": {file_size}, "doc_id": "{doc_id}", "format": "{file_ext}", "hash": "{file_hash[:8]}"}}')
        
        # Clear any previous errors since upload succeeded
        clear_last_error()
        
        # Trigger OCR processing asynchronously
        try:
            from backend.services.ocr_service import process_document_ocr
            import asyncio
            
            logger.info(f"[UPLOAD] Triggering OCR background task for doc_id={doc_id}, file={stored_path}")
            # Run OCR in background (fire and forget)
            asyncio.create_task(_run_ocr_background(doc_id, stored_path))
            logger.info(f"[UPLOAD] OCR background task created for doc_id={doc_id}")
            
        except Exception as ocr_error:
            # Log OCR trigger failure but don't fail the upload
            error_msg = str(ocr_error)
            logger.error(f"[UPLOAD] Failed to trigger OCR for doc_id={doc_id}: {error_msg}")
            append_audit(datetime.now().isoformat(), "local", "ocr_trigger_error", 
                        f'{{"doc_id": "{doc_id}", "error": "{error_msg}"}}')
        
        return {
            "doc_id": doc_id,
            "filename": file.filename,
            "status": "processing",
            "format": file_ext,
            "size_bytes": file_size,
            "hash": file_hash[:8]  # Return first 8 chars for reference
        }
    
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        set_last_error(datetime.now().isoformat(), "upload", error_msg, "{}")
        append_audit(datetime.now().isoformat(), "local", "upload_error", f'{{"error": "{error_msg}"}}')
        raise HTTPException(status_code=500, detail=error_msg)

# MOCK REMOVED: returns only real OCR/DB data
@app.get("/api/upload/status")
def upload_status(doc_id: str = Query(..., description="Document ID to check status")):
    """
    Return status + parsed summary + line items for a given doc_id.
    Useful for polling during OCR processing.
    MOCK REMOVED: Returns only real data from DB, no mock fallback.
    """
    try:
        con = sqlite3.connect("data/owlin.db", check_same_thread=False)
        cur = con.cursor()
        
        # Check if document exists (handle missing status column gracefully)
        doc_row = None
        doc_status = "processing"
        try:
            cur.execute("""
                SELECT id, filename, status
                FROM documents
                WHERE id = ?
            """, (doc_id,))
            doc_row = cur.fetchone()
            if doc_row and len(doc_row) > 2:
                doc_status = doc_row[2] if doc_row[2] else "processing"
        except sqlite3.OperationalError as e:
            if "no such column: status" in str(e):
                # Fallback: query without status column (for old databases)
                cur.execute("""
                    SELECT id, filename
                    FROM documents
                    WHERE id = ?
                """, (doc_id,))
                doc_row = cur.fetchone()
                doc_status = "processing"
            else:
                raise
        
        if not doc_row:
            con.close()
            return {
                "doc_id": doc_id,
                "status": "processing",
                "parsed": None,
                "items": []
            }
        
        # Get invoice data if available
        cur.execute("""
            SELECT i.id, i.supplier, i.date as invoice_date, i.value as value_pence,
                   COALESCE(i.status, 'scanned') as status,
                   COALESCE(i.confidence, 0.9) as confidence
            FROM invoices i
            WHERE i.doc_id = ?
            LIMIT 1
        """, (doc_id,))
        
        inv_row = cur.fetchone()
        
        # Get line items if invoice exists
        items = []
        if inv_row:
            invoice_id = inv_row[0]
            items = get_line_items_for_invoice(invoice_id)
            # If no items by invoice_id, try by doc_id
            if not items:
                items = get_line_items_for_doc(doc_id)
            
            # Shape response
            con.close()
            return {
                "doc_id": doc_id,
                "status": inv_row[4] if inv_row[4] else "scanned",
                "parsed": {
                    "supplier": inv_row[1],
                    "date": inv_row[2],
                    "value_pence": inv_row[3],
                    "confidence": float(inv_row[5]) if inv_row[5] else 0.9,
                    "id": inv_row[0],
                },
                "items": items,
                "invoice": {
                    "id": inv_row[0],
                    "supplier": inv_row[1],
                    "invoice_date": inv_row[2],
                    "value_pence": inv_row[3],
                    "status": inv_row[4],
                    "confidence": float(inv_row[5]) if inv_row[5] else 0.9,
                    "items": items
                }
            }
        
        # Document exists but invoice not processed yet
        con.close()
        
        return {
            "doc_id": doc_id,
            "status": doc_status,
            "parsed": None,
            "items": []
        }
    
    except Exception as e:
        error_msg = str(e)
        append_audit(datetime.now().isoformat(), "local", "upload_status_error", f'{{"doc_id": "{doc_id}", "error": "{error_msg}"}}')
        return {
            "doc_id": doc_id,
            "status": "error",
            "error": error_msg,
            "parsed": None,
            "items": []
        }

async def _run_ocr_background(doc_id: str, file_path: str):
    """Background task to run OCR processing with concurrency control"""
    # Update metrics: queue
    _update_metrics("ocr_queue", _ocr_metrics["ocr_queue"] + 1)
    _update_metrics("last_doc_id", doc_id)
    
    async with _ocr_semaphore:
        # Update metrics: inflight
        _update_metrics("ocr_queue", _ocr_metrics["ocr_queue"] - 1)
        _update_metrics("ocr_inflight", _ocr_metrics["ocr_inflight"] + 1)
        
        try:
            from backend.services.ocr_service import process_document_ocr
            logger.info(f"[OCR_BG] Starting OCR processing for doc_id={doc_id}, file={file_path}")
            result = process_document_ocr(doc_id, file_path)
            logger.info(f"[OCR_BG] OCR processing completed for doc_id={doc_id}, status={result.get('status')}, confidence={result.get('confidence', 0)}")
            _update_metrics("total_processed", _ocr_metrics["total_processed"] + 1)
        except Exception as e:
            _update_metrics("total_errors", _ocr_metrics["total_errors"] + 1)
            error_msg = str(e)
            logger.exception(f"[OCR_BG] OCR processing failed for doc_id={doc_id}: {error_msg}")
            append_audit(datetime.now().isoformat(), "local", "ocr_background_error", f'{{"doc_id": "{doc_id}", "error": "{error_msg}"}}')
            update_document_status(doc_id, "error", "ocr_error", error=error_msg)
        finally:
            _update_metrics("ocr_inflight", _ocr_metrics["ocr_inflight"] - 1)

@app.post("/api/ocr/retry/{doc_id}")
async def retry_ocr(doc_id: str):
    """Retry OCR processing for a failed or incomplete document"""
    try:
        # Get document from database
        con = sqlite3.connect("data/owlin.db", check_same_thread=False)
        cur = con.cursor()
        cur.execute("SELECT stored_path, filename FROM documents WHERE id = ?", (doc_id,))
        row = cur.fetchone()
        con.close()
        
        if not row:
            raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")
        
        file_path = row[0]
        filename = row[1]
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
        
        # Reset document status to pending
        update_document_status(doc_id, "pending", "retry")
        append_audit(datetime.now().isoformat(), "local", "ocr_retry", f'{{"doc_id": "{doc_id}", "filename": "{filename}"}}')
        
        # Trigger OCR processing again
        import asyncio
        asyncio.create_task(_run_ocr_background(doc_id, file_path))
        
        return {
            "status": "processing",
            "doc_id": doc_id,
            "message": "OCR retry initiated"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        set_last_error(datetime.now().isoformat(), "retry_ocr", error_msg, "{}")
        append_audit(datetime.now().isoformat(), "local", "retry_ocr_error", f'{{"doc_id": "{doc_id}", "error": "{error_msg}"}}')
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
                    "description": "Invoice total differs from delivery note by Â£150"
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
issue-001,price_mismatch,high,Metro Supplies,inv-001,-150.00,2024-01-15T10:30:00Z,Invoice total differs from delivery note by Â£150
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
    """Middleware to log API calls to audit trail with correlation IDs"""
    start_time = time.time()
    
    # Generate or extract correlation ID (X-Request-Id header)
    correlation_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
    request.state.correlation_id = correlation_id
    
    # Extract request info
    method = request.method
    url = str(request.url)
    path = request.url.path
    
    # Log the request with correlation ID
    logger.info(f"[AUDIT REQUEST] {method} {path} - {correlation_id} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        response = await call_next(request)
        duration = time.time() - start_time
        
        # Add correlation ID to response headers
        response.headers["X-Request-Id"] = correlation_id
        
        # Log successful response
        logger.info(f"[AUDIT RESPONSE] {method} {path} - {correlation_id} - {response.status_code} - {duration:.3f}s")
        
        # Log to audit trail with correlation ID
        append_audit(datetime.now().isoformat(), "local", f"{method.lower()}_{path.replace('/', '_').replace('-', '_')}", f'{{"status": {response.status_code}, "duration": {duration:.3f}, "request_id": "{correlation_id}"}}')
        
        return response
    except HTTPException as http_ex:
        # HTTPExceptions should be re-raised to preserve status codes
        duration = time.time() - start_time
        
        # Add correlation ID to the exception response if possible
        # Note: HTTPException responses are created by FastAPI, so we'll log the ID
        logger.error(f"[AUDIT ERROR] {method} {path} - {correlation_id} - HTTP {http_ex.status_code} - {duration:.3f}s - {http_ex.detail}")
        
        # Log to audit trail with correlation ID
        append_audit(datetime.now().isoformat(), "local", f"{method.lower()}_{path.replace('/', '_').replace('-', '_')}_error", f'{{"error": "{http_ex.detail}", "status": {http_ex.status_code}, "duration": {duration:.3f}, "request_id": "{correlation_id}"}}')
        
        raise http_ex
    except Exception as e:
        duration = time.time() - start_time
        
        # Log error response
        logger.error(f"[AUDIT ERROR] {method} {path} - {correlation_id} - ERROR - {duration:.3f}s - {str(e)}")
        
        # Log to audit trail with correlation ID
        append_audit(datetime.now().isoformat(), "local", f"{method.lower()}_{path.replace('/', '_').replace('-', '_')}_error", f'{{"error": "{str(e)}", "duration": {duration:.3f}, "request_id": "{correlation_id}"}}')
        
        raise e

# Exception handler to add correlation IDs to HTTPException responses
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Add correlation ID to HTTPException responses"""
    correlation_id = getattr(request.state, "correlation_id", None) or request.headers.get("X-Request-Id") or str(uuid.uuid4())
    
    response = JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "request_id": correlation_id},
        headers={"X-Request-Id": correlation_id}
    )
    return response

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Add correlation ID to validation error responses"""
    correlation_id = getattr(request.state, "correlation_id", None) or request.headers.get("X-Request-Id") or str(uuid.uuid4())
    
    response = JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": exc.body, "request_id": correlation_id},
        headers={"X-Request-Id": correlation_id}
    )
    return response

# Static file serving - Enable SPA mode
STATIC_DIR = BASE_DIR / "static"
SPA_INDEX = STATIC_DIR / "index.html"

# Force check with absolute paths
import os
STATIC_DIR_ABS = Path(os.path.abspath(str(STATIC_DIR)))
SPA_INDEX_ABS = Path(os.path.abspath(str(SPA_INDEX)))

# Always use absolute paths
STATIC_DIR = STATIC_DIR_ABS
SPA_INDEX = SPA_INDEX_ABS

logger.info(f"[STATIC] Static directory: {STATIC_DIR}, exists: {STATIC_DIR.exists()}")
logger.info(f"[STATIC] SPA index: {SPA_INDEX}, exists: {SPA_INDEX.exists()}")

# Mount assets directory if it exists
assets_dir = STATIC_DIR / "assets"
if assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(assets_dir), html=False), name="assets")
    logger.info(f"[STATIC] Assets mounted at /assets")

# Always register SPA routes - check file existence at request time
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def root():
    """Root endpoint - serve SPA if available"""
    # Use direct path resolution
    spa_file = BASE_DIR / "static" / "index.html"
    logger.info(f"[ROOT] Checking: {spa_file}, exists: {spa_file.exists()}")
    
    if spa_file.exists() and spa_file.is_file():
        logger.info(f"[ROOT] Serving SPA index.html from {spa_file}")
        return FileResponse(str(spa_file), headers={"Cache-Control": "no-cache"})
    
    logger.warning(f"[ROOT] SPA_INDEX not found at {spa_file}")
    return JSONResponse({
        "message": "Owlin API Server",
        "status": "running",
        "frontend_url": "http://localhost:5177/invoices?dev=1",
        "api_docs": "/docs",
        "health": "/api/health",
        "note": "Frontend not found in backend/static/"
    })

# SPA fallback route - MUST be last to catch all non-API routes
@app.get("/{full_path:path}", response_class=HTMLResponse, include_in_schema=False)
async def spa_fallback(request: Request, full_path: str):
    """SPA fallback - serve index.html for all non-API routes"""
    # Don't hijack API routes or assets
    if full_path.startswith("api/") or full_path.startswith("assets/"):
        raise HTTPException(status_code=404, detail="Not found")
    
    # Check if it's a static file that exists
    static_file = STATIC_DIR / full_path
    if static_file.exists() and static_file.is_file():
        return FileResponse(str(static_file))
    
    # Serve index.html for all SPA routes - use direct path resolution
    import os
    # Build path directly from BASE_DIR which is resolved at module load
    spa_file = BASE_DIR / "static" / "index.html"
    
    # Log for debugging
    logger.info(f"[SPA_FALLBACK] Path: /{full_path}, Checking: {spa_file}, exists: {spa_file.exists()}")
    
    if spa_file.exists() and spa_file.is_file():
        logger.info(f"[SPA_FALLBACK] Serving SPA for path: /{full_path} from {spa_file}")
        try:
            return FileResponse(
                str(spa_file),
                headers={
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0"
                }
            )
        except Exception as e:
            logger.error(f"[SPA_FALLBACK] Error serving file: {e}")
            raise HTTPException(status_code=500, detail=f"Error serving SPA: {e}")
    
    logger.warning(f"[SPA_FALLBACK] SPA_INDEX not found at {spa_file} for path /{full_path}")
    raise HTTPException(status_code=404, detail="Not found")

# Log that SPA routes are registered
logger.info("[STATIC] SPA fallback route registered at /{full_path:path}")





