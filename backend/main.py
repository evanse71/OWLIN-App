from pathlib import Path
import sys
import os

# CRITICAL: Set protobuf environment variable BEFORE any imports that might use PaddleOCR
# This fixes "Descriptors cannot be created directly" error
os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")

# Add project root to Python path so imports work regardless of working directory
_BACKEND_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _BACKEND_DIR.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from fastapi import FastAPI, HTTPException, UploadFile, File, Query, Request, Body, BackgroundTasks
from pydantic import BaseModel
from typing import List
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
import json
from logging.handlers import RotatingFileHandler
from typing import List, Dict, Optional, Any
from datetime import datetime
# Import from app/db.py - handle the app.py vs app/ directory conflict by using importlib
import sys
from pathlib import Path
import importlib.util
_backend_dir = Path(__file__).resolve().parent
_app_db_path = _backend_dir / "app" / "db.py"
_spec = importlib.util.spec_from_file_location("app_db", _app_db_path)
_app_db = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_app_db)
init_db = _app_db.init_db
insert_document = _app_db.insert_document
find_document_by_hash = _app_db.find_document_by_hash
list_invoices = _app_db.list_invoices
list_recent_documents = _app_db.list_recent_documents
upsert_invoice = _app_db.upsert_invoice
append_audit = _app_db.append_audit
set_last_error = _app_db.set_last_error
get_last_error = _app_db.get_last_error
clear_last_error = _app_db.clear_last_error
get_line_items_for_invoice = _app_db.get_line_items_for_invoice
get_line_items_for_doc = _app_db.get_line_items_for_doc
update_document_status = _app_db.update_document_status
get_db_wal_mode = _app_db.get_db_wal_mode
DB_PATH = _app_db.DB_PATH
check_invoice_exists = _app_db.check_invoice_exists
from backend.image_preprocess import preprocess_bgr_page, save_preprocessed_artifact
from backend.config import FEATURE_OCR_PIPELINE_V2, FEATURE_OCR_V2_PREPROC, FEATURE_OCR_V2_LAYOUT, FEATURE_OCR_V3_TABLES, env_int

# ============================================================================
# LOGGING CONFIGURATION WITH ROTATION
# ============================================================================

# Configure root logger with rotating file handler + console
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Remove any existing handlers to avoid duplicates
for handler in logger.handlers[:]:
    logger.removeHandler(handler)

# NOTE: RotatingFileHandler temporarily disabled because the uvicorn
# reloader spawns multiple processes and they fight over backend_stdout.log
# on Windows (WinError 32). For now we rely on console logging only.

# Rotating file handler (5MB per file, 3 backups) - DISABLED
# file_handler = RotatingFileHandler(
#     "backend_stdout.log",
#     maxBytes=5_000_000,  # 5MB
#     backupCount=3,
#     encoding="utf-8"
# )
# file_handler.setLevel(logging.INFO)
# file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

# logger.addHandler(file_handler)  # DISABLED
logger.addHandler(console_handler)

logger.info("[STARTUP] Logging configured with rotation (5MB, 3 backups)")

# Paths
BASE_DIR = Path(__file__).resolve().parent
SPA_DIR = (BASE_DIR / ".." / "out").resolve()  # Next export defaults -> out

# Version tracking - module load timestamp
_MAIN_LOAD_TIMESTAMP = time.time()
_MAIN_LOAD_ISO = datetime.fromtimestamp(_MAIN_LOAD_TIMESTAMP).isoformat()

# APP â€” create the app once, not five times
app = FastAPI(title="Owlin Local API")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:8501", "http://localhost:5176", "http://127.0.0.1:5176", "*"], allow_methods=["*"], allow_headers=["*"])

# Log build timestamp immediately after app creation
logger.info(f"[BUILD] backend.main loaded at {_MAIN_LOAD_ISO}")

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
from backend.routes.invoices_submit import router as invoices_submit_router, delete_invoices, DeleteInvoicesRequest
# Register batch/delete route explicitly BEFORE parameterized routes to ensure it matches first
@app.post("/api/invoices/batch/delete")
async def delete_invoices_route(request: DeleteInvoicesRequest):
    return await delete_invoices(request)
app.include_router(invoices_submit_router)  # Route /api/invoices/batch/delete is defined in this router

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

# Include Manual Entry router
from backend.routes.manual_entry import router as manual_entry_router
app.include_router(manual_entry_router)

# Include Pairing router
from backend.routes.pairing_router import router as pairing_router
app.include_router(pairing_router)

# Include Dashboard router
from backend.routes.dashboard import router as dashboard_router
app.include_router(dashboard_router)

# Include Review router
from backend.routes.review_router import router as review_router
app.include_router(review_router)

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
        # Register explicit POST /api/chat route FIRST
        # This ensures it takes precedence over any router routes
        @app.post("/api/chat", response_model=_chat_response_model, name="chat_post")
        async def chat_route(request: _chat_request_model) -> _chat_response_model:
            return await _chat_endpoint(request)
        logger.info("[ROUTER] Explicit POST /api/chat route registered")
        
        # Include router for sub-routes (/stream, /history, /status, etc.)
        # Router has prefix /api/chat, so routes become /api/chat/status, etc.
        if _chat_router:
            app.include_router(_chat_router)
            logger.info("[ROUTER] Chat router included successfully")
    except Exception as e:
        logger.error(f"[ROUTER] Failed to register route: {e}")
        import traceback
        logger.error(traceback.format_exc())
else:
    # Try to include router even if endpoint/models failed, as long as router exists
    if _chat_router:
        try:
            app.include_router(_chat_router)
            logger.info("[ROUTER] Chat router included (endpoint/models may be unavailable)")
        except Exception as e:
            logger.error(f"[ROUTER] Failed to include chat router: {e}")
    
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
    """Health check endpoint with correlation ID support - optimized for speed"""
    try:
        correlation_id = getattr(request.state, "correlation_id", None) or request.headers.get("X-Request-Id") or str(uuid.uuid4())
        
        # Get feature flag status
        from backend.config import (
            FEATURE_OCR_PIPELINE_V2, FEATURE_OCR_V2_LAYOUT, FEATURE_OCR_V2_PREPROC,
            FEATURE_OCR_V3_TABLES, FEATURE_LLM_EXTRACTION, validate_feature_flags
        )
        feature_flags = {
            "FEATURE_OCR_PIPELINE_V2": FEATURE_OCR_PIPELINE_V2,
            "FEATURE_OCR_V2_LAYOUT": FEATURE_OCR_V2_LAYOUT,
            "FEATURE_OCR_V2_PREPROC": FEATURE_OCR_V2_PREPROC,
            "FEATURE_OCR_V3_TABLES": FEATURE_OCR_V3_TABLES,
            "FEATURE_LLM_EXTRACTION": FEATURE_LLM_EXTRACTION
        }
        flag_warnings = validate_feature_flags()
        
        # Return immediately - audit logging is non-critical and can be async
        response = {
            "status": "ok", 
            "ocr_v2_enabled": FEATURE_OCR_PIPELINE_V2,
            "feature_flags": feature_flags,
            "feature_flag_warnings": flag_warnings,
            "request_id": correlation_id
        }
        
        # Log audit asynchronously (fire and forget) to avoid blocking
        try:
            # Use a thread or async task if available, but don't wait for it
            import threading
            def log_audit_async():
                try:
                    append_audit(datetime.now().isoformat(), "local", "health", f'{{"request_id": "{correlation_id}"}}')
                except Exception:
                    pass  # Silently fail - audit logging is not critical for health checks
            threading.Thread(target=log_audit_async, daemon=True).start()
        except Exception:
            pass  # If threading fails, just skip audit logging
        
        return response
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
    db_path_abs = DB_PATH
    
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

@app.get("/api/health/ocr")
def health_ocr():
    """OCR readiness check endpoint - returns dependency status and blocks if prerequisites missing"""
    from backend.services.ocr_readiness import get_readiness_summary
    from fastapi import status
    
    summary = get_readiness_summary()
    
    # Return 503 Service Unavailable if not ready, 200 if ready
    status_code = status.HTTP_200_OK if summary["ready"] else status.HTTP_503_SERVICE_UNAVAILABLE
    
    return JSONResponse(
        content=summary,
        status_code=status_code
    )

@app.post("/api/watchdog/fix-stuck")
def watchdog_fix_stuck(max_minutes: int = Query(10, description="Maximum minutes before considering a document stuck")):
    """Watchdog endpoint to detect and fix documents stuck in processing status"""
    from backend.services.ocr_service import fix_stuck_documents
    
    try:
        fixed_count = fix_stuck_documents(max_processing_minutes=max_minutes)
        return {
            "status": "ok",
            "fixed_count": fixed_count,
            "message": f"Fixed {fixed_count} stuck document(s)"
        }
    except Exception as e:
        logger.exception(f"[WATCHDOG] Error fixing stuck documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/watchdog/status")
def watchdog_status():
    """Get status of stuck documents without fixing them"""
    from backend.services.ocr_service import detect_stuck_documents
    
    try:
        stuck_docs = detect_stuck_documents(max_processing_minutes=10)
        return {
            "status": "ok",
            "stuck_count": len(stuck_docs),
            "stuck_documents": stuck_docs
        }
    except Exception as e:
        logger.exception(f"[WATCHDOG] Error detecting stuck documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
        con = sqlite3.connect(DB_PATH, check_same_thread=False)
        cur = con.cursor()
        
        # #region agent log - Check database schema
        column_names = []  # Initialize to empty list to prevent NameError
        try:
            cur.execute("PRAGMA table_info(invoices)")
            schema_info = cur.fetchall()
            column_names = [col[1] for col in schema_info]
            with open(r'c:\Users\tedev\FixPack_2025-11-02_133105\.cursor\debug.log', 'a', encoding='utf-8') as f:
                f.write('{"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"main.py:491","message":"Database schema check","data":{"columns":' + repr(column_names) + '},"timestamp":' + str(int(time.time() * 1000)) + '}\n')
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            with open(r'c:\Users\tedev\FixPack_2025-11-02_133105\.cursor\debug.log', 'a', encoding='utf-8') as f:
                f.write('{"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"main.py:498","message":"Schema check failed","data":{"error":' + repr(str(e)) + ',"traceback":' + repr(error_trace[:1000]) + '},"timestamp":' + str(int(time.time() * 1000)) + '}\n')
            # If schema check fails, try to get column names from a sample query
            try:
                cur.execute("SELECT * FROM invoices LIMIT 1")
                column_names = [description[0] for description in cur.description] if cur.description else []
            except:
                column_names = []  # Fallback to empty list
        # #endregion
        
        # Build query with filters
        where_clause = ""
        params = []
        
        if status:
            where_clause += " AND i.status = ?"
            params.append(status)
        
        # Detect which columns exist for sorting and query building
        has_supplier_name = 'supplier_name' in column_names
        has_supplier = 'supplier' in column_names
        has_invoice_date = 'invoice_date' in column_names
        has_date = 'date' in column_names
        has_total_p = 'total_p' in column_names
        has_total_amount_pennies = 'total_amount_pennies' in column_names
        has_value = 'value' in column_names
        
        # Sort mapping - use correct column names based on schema
        supplier_sort = 'i.supplier_name' if has_supplier_name else ('i.supplier' if has_supplier else 'i.id')
        date_sort = 'i.invoice_date' if has_invoice_date else ('i.date' if has_date else 'i.id')
        value_sort = 'COALESCE(i.total_p, i.total_amount_pennies)' if (has_total_p or has_total_amount_pennies) else ('i.value' if has_value else 'i.id')
        
        sort_map = {
            "id": "i.id",
            "date": date_sort, 
            "supplier": supplier_sort,
            "value": value_sort
        }
        sort_field = sort_map.get(sort, "i.id")
        
        # Build query with correct column names based on what exists (using column_names from earlier check)
        supplier_col = 'i.supplier_name' if has_supplier_name else ('i.supplier' if has_supplier else 'NULL')
        date_col = 'i.invoice_date' if has_invoice_date else ('i.date' if has_date else 'NULL')
        total_col = 'COALESCE(i.total_p, i.total_amount_pennies, 0)' if (has_total_p or has_total_amount_pennies) else ('i.value' if has_value else '0')
        
        # Check if subtotal_p, vat_total_p, total_p, confidence_breakdown columns exist
        has_subtotal_p = 'subtotal_p' in column_names
        has_vat_total_p = 'vat_total_p' in column_names
        has_confidence_breakdown = 'confidence_breakdown' in column_names
        
        # Build optional column selections
        optional_cols = []
        if has_subtotal_p:
            optional_cols.append("i.subtotal_p")
        if has_vat_total_p:
            optional_cols.append("i.vat_total_p")
        if has_total_p:
            optional_cols.append("i.total_p")
        if has_confidence_breakdown:
            optional_cols.append("i.confidence_breakdown")
        optional_cols_str = ", " + ", ".join(optional_cols) if optional_cols else ""
        
        query = f"""
            SELECT i.id, i.doc_id as document_id, {supplier_col} as supplier, {date_col} as invoice_date, {total_col} as total_value, d.filename,
                   COALESCE(i.status, 'scanned') as status,
                   COALESCE(i.confidence, 0.9) as confidence,
                   COALESCE(i.venue, 'Main Restaurant') as venue,
                   COALESCE(i.issues_count, 0) as issues_count,
                   COALESCE(i.paired, 0) as paired,
                   d.filename as source_filename,
                   i.invoice_number{optional_cols_str}
            FROM invoices i
            LEFT JOIN documents d ON i.doc_id = d.id
            WHERE 1=1 {where_clause}
            ORDER BY {sort_field} DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        
        # #region agent log
        with open(r'c:\Users\tedev\FixPack_2025-11-02_133105\.cursor\debug.log', 'a', encoding='utf-8') as f:
            f.write('{"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"main.py:501","message":"Executing invoice query","data":{"query":' + repr(query) + ',"params":' + repr(params) + '},"timestamp":' + str(int(time.time() * 1000)) + '}\n')
        # #endregion
        
        cur.execute(query, params)
        rows = cur.fetchall()
        
        # #region agent log
        with open(r'c:\Users\tedev\FixPack_2025-11-02_133105\.cursor\debug.log', 'a', encoding='utf-8') as f:
            f.write('{"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"main.py:503","message":"Query results","data":{"row_count":' + str(len(rows)) + ',"first_row_sample":' + (repr(list(rows[0]) if rows else [])[:500]) + '},"timestamp":' + str(int(time.time() * 1000)) + '}\n')
        # #endregion
        
        # Get total count for pagination
        count_query = f"""
            SELECT COUNT(*) FROM invoices i WHERE 1=1 {where_clause}
        """
        cur.execute(count_query, params[:-2])  # Remove limit/offset
        total_count = cur.fetchone()[0]
        
        con.close()
        
        # Transform to normalized format
        invoices = []
        # Base columns: id(0), doc_id(1), supplier(2), date(3), total_value(4), filename(5), status(6), confidence(7), venue(8), issues_count(9), paired(10), source_filename(11), invoice_number(12)
        base_col_count = 13
        # Calculate offset for optional columns
        col_idx = base_col_count
        
        for row in rows:
            invoice_id = row[0]
            doc_id = row[1]
            
            # Get line items for this invoice
            line_items = get_line_items_for_invoice(invoice_id) if invoice_id else []
            
            # If no line items by invoice_id, try by doc_id with invoice_id
            if not line_items and doc_id and invoice_id:
                line_items = get_line_items_for_doc(doc_id, invoice_id=invoice_id)
            
            # Extract data from row - handle both old and new schemas
            supplier_val = row[2] or "Unknown Supplier"
            invoice_date_val = row[3] or ""
            total_value_raw = row[4]
            # Convert total_value - if it's in pennies (integer), convert to pounds; if already float, use as-is
            if isinstance(total_value_raw, (int, float)) and total_value_raw:
                # If value is > 1000, assume it's in pennies, convert to pounds
                total_value = float(total_value_raw) / 100.0 if total_value_raw > 1000 else float(total_value_raw)
            else:
                total_value = 0.0
            
            # Extract additional fields if available (new schema) - only if columns were selected
            subtotal_p = None
            vat_total_p = None
            total_p = None
            confidence_breakdown = None
            current_idx = base_col_count
            if has_subtotal_p and len(row) > current_idx:
                subtotal_p = row[current_idx]
                current_idx += 1
            if has_vat_total_p and len(row) > current_idx:
                vat_total_p = row[current_idx]
                current_idx += 1
            if has_total_p and len(row) > current_idx:
                total_p = row[current_idx]
                current_idx += 1
            if has_confidence_breakdown and len(row) > current_idx:
                confidence_breakdown_raw = row[current_idx]
                # Parse JSON if it's a string
                if confidence_breakdown_raw:
                    try:
                        if isinstance(confidence_breakdown_raw, str):
                            confidence_breakdown = json.loads(confidence_breakdown_raw)
                        else:
                            confidence_breakdown = confidence_breakdown_raw
                    except (json.JSONDecodeError, TypeError):
                        confidence_breakdown = None
                current_idx += 1
            
            # Convert pennies to pounds for display if needed
            if total_p and total_p > 0:
                total_value = float(total_p) / 100.0
            elif total_value_raw and isinstance(total_value_raw, int) and total_value_raw > 100:
                total_value = float(total_value_raw) / 100.0
            
            invoice_data = {
                "id": invoice_id,
                "doc_id": doc_id,
                "supplier": supplier_val,
                "supplier_name": supplier_val,  # Add supplier_name for frontend compatibility
                "invoice_date": invoice_date_val,
                "total_value": total_value,
                "total_amount": total_value * 100 if total_value else 0,  # In pennies for frontend
                "total_p": total_p if total_p is not None else (int(total_value * 100) if total_value else 0),
                "subtotal_p": subtotal_p,
                "vat_total_p": vat_total_p,
                "currency": "GBP",  # Default currency
                "confidence": float(row[7]) if row[7] is not None else 0.0,
                "confidence_breakdown": confidence_breakdown,  # Include confidence breakdown if available
                "status": row[6] or "scanned",
                "venue": row[8] or "Main Restaurant",
                "issues_count": int(row[9]) if row[9] is not None else 0,
                "paired": bool(row[10]) if row[10] is not None else False,
                "invoice_number": row[12] if len(row) > 12 and row[12] else None,
                "pairing_status": None,  # TODO: populate from invoices table if column exists
                "delivery_note_id": None,  # TODO: populate from invoices table if column exists
                "line_items": line_items
            }
            
            # #region agent log
            with open(r'c:\Users\tedev\FixPack_2025-11-02_133105\.cursor\debug.log', 'a', encoding='utf-8') as f:
                f.write('{"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"main.py:600","message":"Transformed invoice data","data":{"invoice_id":"' + str(invoice_id) + '","supplier":"' + str(supplier_val) + '","supplier_name":"' + str(invoice_data.get("supplier_name") if invoice_data else None) + '","total_value":' + str(total_value) + ',"total_p":' + str(invoice_data.get("total_p") if invoice_data else None) + ',"subtotal_p":' + str(subtotal_p) + ',"vat_total_p":' + str(vat_total_p) + ',"row_data":' + repr(list(row)[:8]) + '},"timestamp":' + str(int(time.time() * 1000)) + '}\n')
            # #endregion
            
            # Compare DB values to API response for debugging
            db_supplier = row[2] if len(row) > 2 else None
            api_supplier = invoice_data.get("supplier")
            db_total = row[4] if len(row) > 4 else None
            api_total = invoice_data.get("total_value")
            db_status = row[6] if len(row) > 6 else None
            api_status = invoice_data.get("status")
            
            discrepancies = []
            if db_supplier != api_supplier:
                discrepancies.append(f"supplier: DB='{db_supplier}' vs API='{api_supplier}'")
            if abs((db_total or 0) - (api_total or 0)) > 0.01:  # Allow small floating point differences
                discrepancies.append(f"total: DB={db_total} vs API={api_total}")
            if db_status != api_status:
                discrepancies.append(f"status: DB='{db_status}' vs API='{api_status}'")
            
            if discrepancies:
                logger.warning(f"[API_DISCREPANCY] doc_id={doc_id} invoice_id={invoice_id}: {', '.join(discrepancies)}")
            
            invoices.append(invoice_data)
        
        append_audit(datetime.now().isoformat(), "local", "invoices", f'{{"count": {len(invoices)}, "total": {total_count}}}')
        
        return {
            "invoices": invoices,
            "count": len(invoices),
            "total": total_count,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        import traceback
        error_msg = str(e)
        error_trace = traceback.format_exc()
        # #region agent log
        with open(r'c:\Users\tedev\FixPack_2025-11-02_133105\.cursor\debug.log', 'a', encoding='utf-8') as f:
            f.write('{"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"main.py:655","message":"Invoices endpoint exception","data":{"error":' + repr(error_msg) + ',"traceback":' + repr(error_trace[:2000]) + '},"timestamp":' + str(int(time.time() * 1000)) + '}\n')
        # #endregion
        set_last_error(datetime.now().isoformat(), "invoices", error_msg, "{}")
        append_audit(datetime.now().isoformat(), "local", "invoices_error", f'{{"error": "{error_msg}"}}')
        logger.exception(f"Invoices endpoint error: {error_msg}")
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
        con = sqlite3.connect(DB_PATH, check_same_thread=False)
        cur = con.cursor()
        
        # Detect which columns exist
        cur.execute("PRAGMA table_info(invoices)")
        schema_info = cur.fetchall()
        column_names = [col[1] for col in schema_info]
        
        has_supplier_name = 'supplier_name' in column_names
        has_supplier = 'supplier' in column_names
        has_invoice_date = 'invoice_date' in column_names
        has_date = 'date' in column_names
        has_total_p = 'total_p' in column_names
        has_total_amount_pennies = 'total_amount_pennies' in column_names
        has_value = 'value' in column_names
        
        supplier_col = 'i.supplier_name' if has_supplier_name else ('i.supplier' if has_supplier else 'NULL')
        date_col = 'i.invoice_date' if has_invoice_date else ('i.date' if has_date else 'NULL')
        total_col = 'COALESCE(i.total_p, i.total_amount_pennies, 0)' if (has_total_p or has_total_amount_pennies) else ('i.value' if has_value else '0')
        
        # Get invoice details including ocr_stage to determine if manual
        query = f"""
            SELECT i.id, i.doc_id as document_id, {supplier_col} as supplier, {date_col} as invoice_date, {total_col} as total_value, d.filename,
                   COALESCE(i.status, 'scanned') as status,
                   COALESCE(i.confidence, 0.9) as confidence,
                   COALESCE(i.venue, 'Main Restaurant') as venue,
                   COALESCE(i.issues_count, 0) as issues_count,
                   COALESCE(i.paired, 0) as paired,
                   COALESCE(d.ocr_stage, 'upload') as ocr_stage
            FROM invoices i
            LEFT JOIN documents d ON i.doc_id = d.id
            WHERE i.id = ?
        """
        cur.execute(query, (invoice_id,))
        
        row = cur.fetchone()
        if not row:
            con.close()
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        # #region agent log
        import json
        from pathlib import Path as _Path
        try:
            log_path = _Path(__file__).parent.parent / ".cursor" / "debug.log"
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "G", "location": "main.py:862", "message": "get_invoice row fetched", "data": {"invoice_id": invoice_id, "row_length": len(row) if row else 0, "row_7": row[7] if row and len(row) > 7 else None, "row_7_type": type(row[7]).__name__ if row and len(row) > 7 else "N/A"}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
        except: pass
        # #endregion
        
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
        
        # Return normalized invoice with line items (canonical field names)
        ocr_stage = row[11] if len(row) > 11 else None
        # #region agent log
        try:
            confidence_val = row[7] if len(row) > 7 else None
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "G", "location": "main.py:890", "message": "before creating invoice dict", "data": {"confidence_val": confidence_val, "confidence_val_type": type(confidence_val).__name__ if confidence_val is not None else "None", "row_7_is_none": row[7] is None if len(row) > 7 else True}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
        except: pass
        # #endregion
        invoice = {
            "id": row[0],
            "doc_id": doc_id,
            "supplier": row[2] or "Unknown Supplier", 
            "invoice_date": row[3] or "",
            "total_value": float(row[4]) if row[4] else 0.0,
            "currency": "GBP",  # Default currency
            "confidence": float(row[7]) if row[7] is not None else 0.0,
            "status": row[6],
            "venue": row[8],
            "issues_count": int(row[9]) if row[9] is not None else 0,
            "paired": bool(row[10]) if row[10] is not None else False,
            "pairing_status": None,  # TODO: populate from invoices table if column exists
            "delivery_note_id": None,  # TODO: populate from invoices table if column exists
            "ocr_stage": ocr_stage,
            "ocrStage": ocr_stage,
            "source": "manual" if ocr_stage == "manual" else "scanned",
            "line_items": line_items
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

@app.get("/api/delivery-notes")
def list_delivery_notes(
    limit: int = Query(50, description="Number of delivery notes to return"),
    offset: int = Query(0, description="Number of delivery notes to skip")
):
    """Get all delivery notes (both manual and OCR'd)"""
    try:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        cursor = conn.cursor()
        
        # Check which columns exist
        cursor.execute("PRAGMA table_info(documents)")
        columns = [row[1] for row in cursor.fetchall()]
        has_doc_type = 'doc_type' in columns
        has_supplier = 'supplier' in columns
        has_doc_date = 'doc_date' in columns
        has_total = 'total' in columns
        has_delivery_no = 'delivery_no' in columns
        has_venue = 'venue' in columns
        
        # Build WHERE clause
        if has_doc_type:
            where_clause = "doc_type = 'delivery_note'"
        else:
            # Fallback: try to identify delivery notes by filename or other means
            where_clause = "1=1"  # Return all documents if we can't filter by type
        
        # Build SELECT fields
        select_fields = ["id", "filename"]
        field_index = 2  # Track index for row access
        if has_supplier:
            select_fields.append("supplier")
            supplier_idx = field_index
            field_index += 1
        else:
            select_fields.append("NULL as supplier")
            supplier_idx = field_index
            field_index += 1
        if has_doc_date:
            select_fields.append("doc_date")
            date_idx = field_index
            field_index += 1
        else:
            select_fields.append("NULL as doc_date")
            date_idx = field_index
            field_index += 1
        if has_total:
            select_fields.append("total")
            total_idx = field_index
            field_index += 1
        else:
            select_fields.append("NULL as total")
            total_idx = field_index
            field_index += 1
        if has_delivery_no:
            select_fields.append("delivery_no")
            delivery_no_idx = field_index
            field_index += 1
        else:
            select_fields.append("NULL as delivery_no")
            delivery_no_idx = field_index
            field_index += 1
        if has_venue:
            select_fields.append("venue")
            venue_idx = field_index
            field_index += 1
        else:
            select_fields.append("NULL as venue")
            venue_idx = field_index
            field_index += 1
        
        # Query delivery notes
        # Build ORDER BY clause - use doc_date if available, otherwise use id
        if has_doc_date:
            order_by = "doc_date DESC, id DESC"
        else:
            order_by = "id DESC"
        
        query = f"""
            SELECT {', '.join(select_fields)}
            FROM documents
            WHERE {where_clause}
            ORDER BY {order_by}
            LIMIT ? OFFSET ?
        """
        cursor.execute(query, (limit, offset))
        rows = cursor.fetchall()
        
        # Get total count
        count_query = f"SELECT COUNT(*) FROM documents WHERE {where_clause}"
        cursor.execute(count_query)
        total = cursor.fetchone()[0]
        
        # Transform results
        delivery_notes = []
        for row in rows:
            supplier_val = row[supplier_idx] if has_supplier and row[supplier_idx] else None
            date_val = row[date_idx] if has_doc_date and row[date_idx] else None
            total_val = float(row[total_idx]) if has_total and row[total_idx] is not None else 0.0
            delivery_no_val = row[delivery_no_idx] if has_delivery_no and row[delivery_no_idx] else None
            venue_val = row[venue_idx] if has_venue and row[venue_idx] else None
            
            # Debug logging
            logger.info(f"[list_delivery_notes] Processing DN id={row[0]}, supplier={supplier_val}, date={date_val}, delivery_no={delivery_no_val}, venue={venue_val}")
            
            # Only use "Unknown Supplier" if supplier is truly None or empty string
            final_supplier = supplier_val if supplier_val and supplier_val.strip() else "Unknown Supplier"
            
            delivery_notes.append({
                "id": row[0],
                "filename": row[1] or f"Delivery Note {row[0]}",
                "supplier": final_supplier,
                "date": date_val if date_val else "",
                "doc_date": date_val if date_val else "",  # Also include as doc_date for frontend compatibility
                "total": total_val,
                "delivery_note_number": delivery_no_val if delivery_no_val else "",
                "noteNumber": delivery_no_val if delivery_no_val else "",
                "delivery_no": delivery_no_val if delivery_no_val else "",  # Also include as delivery_no
                "venue": venue_val if venue_val else None,
            })
        
        conn.close()
        
        append_audit(datetime.now().isoformat(), "local", "list_delivery_notes", f'{{"count": {len(delivery_notes)}, "total": {total}}}')
        return delivery_notes
        
    except Exception as e:
        error_msg = str(e)
        set_last_error(datetime.now().isoformat(), "list_delivery_notes", error_msg, "{}")
        append_audit(datetime.now().isoformat(), "local", "list_delivery_notes_error", f'{{"error": "{error_msg}"}}')
        logger.error(f"Error listing delivery notes: {error_msg}", exc_info=True)
        # Return empty array instead of raising error
        return []

@app.get("/api/delivery-notes/unpaired")
def get_unpaired_delivery_notes(
    venue: Optional[str] = Query(None, description="Filter by venue"),
    supplier: Optional[str] = Query(None, description="Filter by supplier"),
    from_date: Optional[str] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(None, description="Filter to date (YYYY-MM-DD)"),
    limit: int = Query(50, description="Number of delivery notes to return"),
    offset: int = Query(0, description="Number of delivery notes to skip")
):
    """
    Get delivery notes that are not currently paired (no accepted/confirmed pair).
    
    Excludes DNs that have a pair with status in ('accepted', 'confirmed').
    """
    try:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        cursor = conn.cursor()
        
        # Check which columns exist
        cursor.execute("PRAGMA table_info(documents)")
        columns = [row[1] for row in cursor.fetchall()]
        has_doc_type = 'doc_type' in columns
        has_supplier = 'supplier' in columns
        has_doc_date = 'doc_date' in columns
        has_total = 'total' in columns
        has_delivery_no = 'delivery_no' in columns
        has_venue = 'venue' in columns
        
        # Check if pairs table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pairs'")
        pairs_table_exists = cursor.fetchone() is not None
        
        # Build WHERE clause
        where_parts = []
        if has_doc_type:
            where_parts.append("d.doc_type = 'delivery_note'")
        
        params = []
        
        # Add optional filters
        if venue and has_venue:
            where_parts.append("d.venue = ?")
            params.append(venue)
        
        if supplier and has_supplier:
            where_parts.append("d.supplier = ?")
            params.append(supplier)
        
        if from_date and has_doc_date:
            where_parts.append("d.doc_date >= ?")
            params.append(from_date)
        
        if to_date and has_doc_date:
            where_parts.append("d.doc_date <= ?")
            params.append(to_date)
        
        where_clause = " AND ".join(where_parts) if where_parts else "1=1"
        
        # Build SELECT fields
        select_fields = ["d.id", "d.filename"]
        if has_supplier:
            select_fields.append("d.supplier")
        else:
            select_fields.append("NULL as supplier")
        if has_doc_date:
            select_fields.append("d.doc_date")
        else:
            select_fields.append("NULL as doc_date")
        if has_total:
            select_fields.append("d.total")
        else:
            select_fields.append("NULL as total")
        if has_delivery_no:
            select_fields.append("d.delivery_no")
        else:
            select_fields.append("NULL as delivery_no")
        if has_venue:
            select_fields.append("d.venue")
        else:
            select_fields.append("NULL as venue")
        
        # Query delivery notes that are NOT paired (no accepted/confirmed pair)
        if pairs_table_exists:
            query = f"""
                SELECT {', '.join(select_fields)}
                FROM documents d
                LEFT JOIN pairs p ON p.delivery_id = d.id 
                    AND p.status IN ('accepted', 'confirmed')
                WHERE {where_clause}
                    AND p.id IS NULL
                ORDER BY d.doc_date DESC, d.id DESC
                LIMIT ? OFFSET ?
            """
        else:
            # If pairs table doesn't exist, return all delivery notes
            query = f"""
                SELECT {', '.join(select_fields)}
                FROM documents d
                WHERE {where_clause}
                ORDER BY d.doc_date DESC, d.id DESC
                LIMIT ? OFFSET ?
            """
        
        params.extend([limit, offset])
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # Get total count
        if pairs_table_exists:
            count_query = f"""
                SELECT COUNT(*)
                FROM documents d
                LEFT JOIN pairs p ON p.delivery_id = d.id 
                    AND p.status IN ('accepted', 'confirmed')
                WHERE {where_clause}
                    AND p.id IS NULL
            """
        else:
            count_query = f"SELECT COUNT(*) FROM documents d WHERE {where_clause}"
        
        cursor.execute(count_query, params[:-2])
        total = cursor.fetchone()[0]
        
        # Transform results
        delivery_notes = []
        for row in rows:
            col_idx = 0
            dn_id = row[col_idx]
            col_idx += 1
            filename = row[col_idx] if col_idx < len(row) else None
            col_idx += 1
            supplier_val = row[col_idx] if col_idx < len(row) and has_supplier and row[col_idx] else "Unknown Supplier"
            col_idx += 1
            date_val = row[col_idx] if col_idx < len(row) and has_doc_date and row[col_idx] else ""
            col_idx += 1
            total_val = float(row[col_idx]) if col_idx < len(row) and has_total and row[col_idx] is not None else 0.0
            col_idx += 1
            delivery_no_val = row[col_idx] if col_idx < len(row) and has_delivery_no and row[col_idx] else ""
            col_idx += 1
            venue_val = row[col_idx] if col_idx < len(row) and has_venue and row[col_idx] else None
            
            delivery_notes.append({
                "id": dn_id,
                "filename": filename or f"Delivery Note {dn_id}",
                "supplier": supplier_val,
                "date": date_val,
                "doc_date": date_val,
                "total": total_val,
                "delivery_note_number": delivery_no_val,
                "noteNumber": delivery_no_val,
                "deliveryNo": delivery_no_val,
                "venue": venue_val,
                "venueId": venue_val,
            })
        
        conn.close()
        
        append_audit(datetime.now().isoformat(), "local", "list_unpaired_delivery_notes", f'{{"count": {len(delivery_notes)}, "total": {total}}}')
        return delivery_notes
        
    except Exception as e:
        error_msg = str(e)
        set_last_error(datetime.now().isoformat(), "list_unpaired_delivery_notes", error_msg, "{}")
        append_audit(datetime.now().isoformat(), "local", "list_unpaired_delivery_notes_error", f'{{"error": "{error_msg}"}}')
        logger.error(f"Error listing unpaired delivery notes: {error_msg}", exc_info=True)
        # Return empty array instead of raising error
        return []

@app.get("/api/delivery-notes/{delivery_note_id}")
def get_delivery_note(delivery_note_id: str):
    """Get a specific delivery note by ID with line items"""
    try:
        con = sqlite3.connect(DB_PATH, check_same_thread=False)
        cur = con.cursor()
        
        # Check which columns exist in documents table
        cur.execute("PRAGMA table_info(documents)")
        columns = [row[1] for row in cur.fetchall()]
        has_doc_type = 'doc_type' in columns
        has_supplier = 'supplier' in columns
        has_doc_date = 'doc_date' in columns
        has_total = 'total' in columns
        has_delivery_no = 'delivery_no' in columns
        
        # Build SELECT query based on available columns
        select_fields = ["id", "filename"]
        if has_supplier:
            select_fields.append("supplier")
        else:
            select_fields.append("NULL as supplier")
        if has_doc_date:
            select_fields.append("doc_date")
        else:
            select_fields.append("NULL as doc_date")
        if has_total:
            select_fields.append("total")
        else:
            select_fields.append("NULL as total")
        if has_delivery_no:
            select_fields.append("delivery_no")
        else:
            select_fields.append("NULL as delivery_no")
        if has_doc_type:
            select_fields.append("doc_type")
        else:
            select_fields.append("NULL as doc_type")
        
        # Build WHERE clause
        where_clause = "id = ?"
        if has_doc_type:
            where_clause += " AND doc_type = 'delivery_note'"
        
        query = f"SELECT {', '.join(select_fields)} FROM documents WHERE {where_clause}"
        cur.execute(query, (delivery_note_id,))
        
        row = cur.fetchone()
        if not row:
            con.close()
            raise HTTPException(status_code=404, detail="Delivery note not found")
        
        doc_id = row[0]
        filename = row[1] or f"Delivery Note {delivery_note_id}"
        supplier = row[2] if has_supplier and row[2] else "Unknown Supplier"
        doc_date = row[3] if has_doc_date and row[3] else ""
        total = float(row[4]) if has_total and row[4] is not None else 0.0
        delivery_no = row[5] if has_delivery_no and row[5] else ""
        
        # Get line items for this delivery note (invoice_id=None for delivery notes)
        line_items = get_line_items_for_doc(doc_id, invoice_id=None)
        
        # Transform line items to match frontend format
        transformed_line_items = []
        for item in line_items:
            transformed_line_items.append({
                "description": (item.get("desc") if item else None) or (item.get("description") if item else None) or "",
                "qty": (item.get("qty") if item else None) or (item.get("quantity") if item else None) or 0,
                "quantity": (item.get("qty") if item else None) or (item.get("quantity") if item else None) or 0,
                "unit": (item.get("uom") if item else None) or (item.get("unit") if item else None) or "",
                "uom": (item.get("uom") if item else None) or (item.get("unit") if item else None) or "",
                "unit_price": (item.get("unit_price") if item else None) or (item.get("price") if item else None) or 0,
                "price": (item.get("unit_price") if item else None) or (item.get("price") if item else None) or 0,
                "total": (item.get("total") if item else None) or (item.get("line_total") if item else None) or 0,
                "line_total": (item.get("total") if item else None) or (item.get("line_total") if item else None) or 0,
                "line_number": item.get("line_number") if item else None,
            })
        
        con.close()
        
        # Extract delivery note number from delivery_no or filename
        note_number = delivery_no
        if not note_number and filename.startswith("Manual Delivery Note "):
            note_number = filename.replace("Manual Delivery Note ", "")
        if not note_number:
            note_number = f"DN-{doc_id[:8]}"
        
        # Return delivery note with line items in format expected by frontend
        delivery_note = {
            "id": doc_id,
            "noteNumber": note_number,
            "note_number": note_number,
            "delivery_no": delivery_no,
            "date": doc_date,
            "doc_date": doc_date,
            "supplier": supplier,
            "total": float(total),
            "total_value": float(total),
            "value": float(total),
            "filename": filename,
            "lineItems": transformed_line_items,
            "line_items": transformed_line_items,  # Both formats for compatibility
        }
        
        append_audit(datetime.now().isoformat(), "local", "get_delivery_note", f'{{"delivery_note_id": "{delivery_note_id}", "line_items": {len(transformed_line_items)}}}')
        return delivery_note
    
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        set_last_error(datetime.now().isoformat(), "get_delivery_note", error_msg, "{}")
        append_audit(datetime.now().isoformat(), "local", "get_delivery_note_error", f'{{"error": "{error_msg}"}}')
        raise HTTPException(status_code=500, detail=error_msg)

@app.get("/api/delivery-notes/{delivery_note_id}/suggestions")
def get_delivery_note_suggestions(delivery_note_id: str):
    """Get invoice pairing suggestions for a specific delivery note"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if delivery note exists in documents table (handles both manual and regular IDs)
        cursor.execute("PRAGMA table_info(documents)")
        columns = [row[1] for row in cursor.fetchall()]
        has_doc_type = 'doc_type' in columns
        
        # Query for delivery note
        if has_doc_type:
            cursor.execute("""
                SELECT id, supplier, doc_date, total, delivery_no
                FROM documents
                WHERE id = ? AND doc_type = 'delivery_note'
            """, (delivery_note_id,))
        else:
            cursor.execute("""
                SELECT id, supplier, doc_date, total, delivery_no
                FROM documents
                WHERE id = ?
            """, (delivery_note_id,))
        
        dn_row = cursor.fetchone()
        if not dn_row:
            conn.close()
            return {"suggestions": []}
        
        dn_doc_id = dn_row[0]
        dn_supplier = dn_row[1] if dn_row[1] else ""
        dn_date_str = dn_row[2] if dn_row[2] else ""
        dn_total = float(dn_row[3]) if dn_row[3] else 0.0
        
        # Parse delivery note date for matching
        dn_date = None
        if dn_date_str:
            try:
                # Try parsing ISO format
                if 'T' in dn_date_str:
                    dn_date = datetime.fromisoformat(dn_date_str.replace('Z', '+00:00'))
                else:
                    # Try YYYY-MM-DD format
                    dn_date = datetime.strptime(dn_date_str, '%Y-%m-%d')
            except:
                pass
        
        # Track invoice IDs we've already added (from pairs table)
        seen_invoice_ids = set()
        suggestions = []
        
        # First, get existing pair suggestions
        cursor.execute("""
            SELECT 
                p.id, p.invoice_id, p.delivery_id, p.confidence, p.status, p.created_at,
                i.filename as invoice_filename, i.supplier as invoice_supplier,
                i.invoice_no, i.doc_date as invoice_date, i.total as invoice_total,
                d.filename as delivery_filename, d.delivery_no, d.doc_date as delivery_date
            FROM pairs p
            JOIN documents i ON p.invoice_id = i.id
            JOIN documents d ON p.delivery_id = d.id
            WHERE p.status = 'suggested' AND p.delivery_id = ?
            ORDER BY p.confidence DESC, p.created_at DESC
            LIMIT 100
        """, (dn_doc_id,))
        
        rows = cursor.fetchall()
        pairs = []
        if cursor.description:
            column_names = [desc[0] for desc in cursor.description]
            for row in rows:
                pair_dict = {}
                for idx, col_name in enumerate(column_names):
                    pair_dict[col_name] = row[idx]
                pairs.append(pair_dict)
        
        # Process existing pair suggestions
        for pair in pairs:
            invoice_doc_id = str(pair.get("invoice_id", ""))
            
            # Try to get invoice_id from invoices table
            cursor.execute("SELECT id FROM invoices WHERE doc_id = ?", (invoice_doc_id,))
            invoice_row = cursor.fetchone()
            
            invoice_id = invoice_row[0] if invoice_row else None
            if invoice_id:
                seen_invoice_ids.add(str(invoice_id))
            
            # Calculate quantity match if invoice_id is available
            quantity_match_score = 1.0
            quantity_differences = []
            has_quantity_mismatch = False
            quantity_warnings = []
            
            if invoice_id:
                try:
                    from backend.services.quantity_validator import validate_quantity_match
                    validation_result = validate_quantity_match(invoice_id, delivery_note_id)
                    quantity_match_score = validation_result.get("match_score", 1.0)
                    discrepancies = validation_result.get("discrepancies", [])
                    quantity_warnings = validation_result.get("warnings", [])[:3]
                    
                    for disc in discrepancies:
                        quantity_differences.append({
                            "description": disc.get("description", ""),
                            "invoiceQty": disc.get("invoice_qty", 0),
                            "dnQty": disc.get("delivery_qty", 0),
                            "difference": disc.get("difference", 0)
                        })
                    
                    has_quantity_mismatch = len(discrepancies) > 0 or quantity_match_score < 0.95
                except Exception as e:
                    logger.warning(f"Failed to validate quantities for DN suggestion (invoice={invoice_id}, delivery={delivery_note_id}): {e}")
            
            # Calculate date delta
            date_delta_days = 0
            try:
                if pair.get("invoice_date") and pair.get("delivery_date"):
                    inv_date = datetime.fromisoformat(pair["invoice_date"].replace('Z', '+00:00'))
                    dn_date_pair = datetime.fromisoformat(pair["delivery_date"].replace('Z', '+00:00'))
                    date_delta_days = abs((inv_date - dn_date_pair).days)
            except:
                pass
            
            # Calculate value delta
            value_delta = 0.0
            try:
                invoice_total = float(pair.get("invoice_total", 0.0)) if pair.get("invoice_total") else 0.0
                value_delta = abs(invoice_total - dn_total)
            except:
                pass
            
            suggestion = {
                "id": str(pair["id"]),
                "invoiceId": invoice_id if invoice_id else invoice_doc_id,
                "invoice_id": invoice_id if invoice_id else invoice_doc_id,
                "invoiceNumber": pair.get("invoice_no", ""),
                "invoice_number": pair.get("invoice_no", ""),
                "invoiceDate": pair.get("invoice_date", ""),
                "invoice_date": pair.get("invoice_date", ""),
                "supplier": pair.get("invoice_supplier", ""),
                "totalAmount": float(pair.get("invoice_total", 0.0)) if pair.get("invoice_total") else 0.0,
                "total_amount": float(pair.get("invoice_total", 0.0)) if pair.get("invoice_total") else 0.0,
                "similarity": float(pair.get("confidence", 0.0)),
                "confidence": float(pair.get("confidence", 0.0)),
                "quantityDifferences": quantity_differences,
                "quantity_differences": quantity_differences,
                "hasQuantityMismatch": has_quantity_mismatch,
                "has_quantity_mismatch": has_quantity_mismatch,
                "quantityMatchScore": quantity_match_score,
                "quantity_match_score": quantity_match_score,
                "quantityWarnings": quantity_warnings,
                "quantity_warnings": quantity_warnings,
                "valueDelta": value_delta,
                "value_delta": value_delta,
                "dateDeltaDays": date_delta_days,
                "date_delta_days": date_delta_days,
                "reason": f"Confidence: {pair.get('confidence', 0.0):.0%}",
            }
            suggestions.append(suggestion)
        
        # Now find additional matching invoices that aren't in pairs table yet
        if dn_supplier and dn_date:
            # Detect which columns exist
            cursor.execute("PRAGMA table_info(invoices)")
            schema_info = cursor.fetchall()
            column_names = [col[1] for col in schema_info]
            
            has_supplier_name = 'supplier_name' in column_names
            has_supplier = 'supplier' in column_names
            has_invoice_date = 'invoice_date' in column_names
            has_date = 'date' in column_names
            has_total_p = 'total_p' in column_names
            has_total_amount_pennies = 'total_amount_pennies' in column_names
            has_value = 'value' in column_names
            
            supplier_col = 'i.supplier_name' if has_supplier_name else ('i.supplier' if has_supplier else 'NULL')
            date_col = 'i.invoice_date' if has_invoice_date else ('i.date' if has_date else 'NULL')
            total_col = 'COALESCE(i.total_p, i.total_amount_pennies, 0)' if (has_total_p or has_total_amount_pennies) else ('i.value' if has_value else '0')
            
            # Query invoices table for matching invoices
            # Match by supplier (case-insensitive) and date within ±3 days
            # Exclude invoices that are already in pairs table with this delivery note
            # Note: pairs.invoice_id refers to doc_id, not invoices.id
            query = f"""
                SELECT i.id, i.doc_id, {supplier_col} as supplier, {date_col} as date, {total_col} as value, i.venue,
                       d.filename, d.invoice_no
                FROM invoices i
                LEFT JOIN documents d ON i.doc_id = d.id
                WHERE LOWER({supplier_col}) = LOWER(?)
                AND {date_col} IS NOT NULL
                AND {date_col} != ''
                AND i.doc_id NOT IN (
                    SELECT invoice_id FROM pairs 
                    WHERE delivery_id = ? AND status IN ('suggested', 'accepted', 'confirmed')
                )
                ORDER BY {date_col} DESC
                LIMIT 50
            """
            cursor.execute(query, (dn_supplier, dn_doc_id))
            
            invoice_rows = cursor.fetchall()
            
            for inv_row in invoice_rows:
                invoice_id = str(inv_row[0])
                invoice_doc_id = str(inv_row[1]) if inv_row[1] else ""
                invoice_supplier = inv_row[2] if inv_row[2] else ""
                invoice_date_str = inv_row[3] if inv_row[3] else ""
                invoice_total = float(inv_row[4]) if inv_row[4] else 0.0
                invoice_venue = inv_row[5] if inv_row[5] else ""
                invoice_filename = inv_row[6] if inv_row[6] else ""
                invoice_no = inv_row[7] if inv_row[7] else ""
                
                # Skip if we already have this invoice in suggestions
                if invoice_id in seen_invoice_ids:
                    continue
                
                # Parse invoice date
                invoice_date = None
                if invoice_date_str:
                    try:
                        # Try ISO format first
                        if 'T' in invoice_date_str:
                            invoice_date = datetime.fromisoformat(invoice_date_str.replace('Z', '+00:00'))
                        else:
                            # Try YYYY-MM-DD format
                            invoice_date = datetime.strptime(invoice_date_str.split(' ')[0], '%Y-%m-%d')
                    except (ValueError, AttributeError) as e:
                        logger.warning(f"Failed to parse invoice date '{invoice_date_str}': {e}")
                        pass
                
                # Calculate confidence score
                confidence = 0.0
                date_delta_days = 0
                
                # Base score for supplier match
                if invoice_supplier.lower() == dn_supplier.lower():
                    confidence = 0.5
                
                # Add score for date proximity
                if invoice_date and dn_date:
                    date_delta_days = abs((invoice_date - dn_date).days)
                    if date_delta_days <= 3:
                        # Same day: +0.3, decreasing by 0.1 per day
                        date_score = max(0.0, 0.3 - (date_delta_days * 0.1))
                        confidence += date_score
                
                # Add score for amount similarity (within 5%)
                if invoice_total > 0 and dn_total > 0:
                    amount_diff = abs(invoice_total - dn_total)
                    max_amount = max(invoice_total, dn_total)
                    if amount_diff <= 0.05 * max_amount:
                        confidence += 0.2
                
                # Only include if confidence >= 0.5 (supplier match required)
                if confidence >= 0.5:
                    # Calculate quantity match
                    quantity_match_score = 1.0
                    quantity_differences = []
                    has_quantity_mismatch = False
                    quantity_warnings = []
                    
                    try:
                        from backend.services.quantity_validator import validate_quantity_match
                        validation_result = validate_quantity_match(invoice_id, delivery_note_id)
                        quantity_match_score = validation_result.get("match_score", 1.0)
                        discrepancies = validation_result.get("discrepancies", [])
                        quantity_warnings = validation_result.get("warnings", [])[:3]
                        
                        for disc in discrepancies:
                            quantity_differences.append({
                                "description": disc.get("description", ""),
                                "invoiceQty": disc.get("invoice_qty", 0),
                                "dnQty": disc.get("delivery_qty", 0),
                                "difference": disc.get("difference", 0)
                            })
                        
                        has_quantity_mismatch = len(discrepancies) > 0 or quantity_match_score < 0.95
                        
                        # Adjust confidence based on quantity match
                        if quantity_match_score >= 0.95:
                            confidence += 0.05
                        elif quantity_match_score < 0.85:
                            confidence -= 0.10
                    except Exception as e:
                        logger.warning(f"Failed to validate quantities for invoice match (invoice={invoice_id}, delivery={delivery_note_id}): {e}")
                    
                    # Cap confidence at 0.99
                    confidence = min(0.99, confidence)
                    
                    # Calculate value delta
                    value_delta = abs(invoice_total - dn_total)
                    
                    # Build reason string
                    reason_parts = []
                    if invoice_supplier.lower() == dn_supplier.lower():
                        reason_parts.append("Same supplier")
                    if date_delta_days == 0:
                        reason_parts.append("Same date")
                    elif date_delta_days <= 3:
                        reason_parts.append(f"{date_delta_days} day{'s' if date_delta_days > 1 else ''} difference")
                    if quantity_match_score >= 0.95:
                        reason_parts.append("Quantity match")
                    reason = ", ".join(reason_parts) if reason_parts else "Potential match"
                    
                    suggestion = {
                        "id": f"match-{invoice_id}",
                        "invoiceId": invoice_id,
                        "invoice_id": invoice_id,
                        "invoiceNumber": invoice_no or invoice_filename or f"INV-{invoice_id[:8]}",
                        "invoice_number": invoice_no or invoice_filename or f"INV-{invoice_id[:8]}",
                        "invoiceDate": invoice_date_str,
                        "invoice_date": invoice_date_str,
                        "supplier": invoice_supplier,
                        "totalAmount": invoice_total,
                        "total_amount": invoice_total,
                        "similarity": confidence,
                        "confidence": confidence,
                        "quantityDifferences": quantity_differences,
                        "quantity_differences": quantity_differences,
                        "hasQuantityMismatch": has_quantity_mismatch,
                        "has_quantity_mismatch": has_quantity_mismatch,
                        "quantityMatchScore": quantity_match_score,
                        "quantity_match_score": quantity_match_score,
                        "quantityWarnings": quantity_warnings,
                        "quantity_warnings": quantity_warnings,
                        "valueDelta": value_delta,
                        "value_delta": value_delta,
                        "dateDeltaDays": date_delta_days,
                        "date_delta_days": date_delta_days,
                        "reason": reason,
                    }
                    suggestions.append(suggestion)
                    seen_invoice_ids.add(invoice_id)
        
        # Sort all suggestions by confidence (highest first)
        suggestions.sort(key=lambda x: x.get("confidence", 0.0), reverse=True)
        
        conn.close()
        
        append_audit(datetime.now().isoformat(), "local", "delivery_note_suggestions", f'{{"delivery_note_id": "{delivery_note_id}", "count": {len(suggestions)}}}')
        return {"suggestions": suggestions}
        
    except Exception as e:
        error_msg = str(e)
        set_last_error(datetime.now().isoformat(), "delivery_note_suggestions", error_msg, "{}")
        append_audit(datetime.now().isoformat(), "local", "delivery_note_suggestions_error", f'{{"error": "{error_msg}"}}')
        logger.error(f"Error getting delivery note suggestions: {error_msg}", exc_info=True)
        # Return empty suggestions instead of raising error to avoid breaking frontend
        return {"suggestions": []}

@app.get("/api/items/suggestions")
def get_item_suggestions(
    q: str = Query("", description="Search query for item descriptions"),
    limit: int = Query(20, description="Maximum number of suggestions to return")
):
    """
    Get item description suggestions from existing line items in the database.
    Returns distinct descriptions that match the query, sorted by frequency.
    """
    try:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        cursor = conn.cursor()
        
        # Query for distinct descriptions matching the query
        # Sort by frequency (how many times it appears) and then alphabetically
        query = """
            SELECT DISTINCT description, COUNT(*) as frequency
            FROM invoice_line_items
            WHERE description IS NOT NULL 
              AND description != ''
              AND LOWER(description) LIKE LOWER(? || '%')
            GROUP BY description
            ORDER BY frequency DESC, description ASC
            LIMIT ?
        """
        
        search_pattern = q.strip() if q else ""
        cursor.execute(query, (search_pattern, limit))
        rows = cursor.fetchall()
        conn.close()
        
        # Extract just the descriptions
        suggestions = [row[0] for row in rows if row[0]]
        
        return {
            "suggestions": suggestions,
            "count": len(suggestions)
        }
    except Exception as e:
        logger.exception("Failed to get item suggestions")
        raise HTTPException(status_code=500, detail=f"Failed to get item suggestions: {str(e)}")

@app.get("/api/delivery-notes/{delivery_note_id}/paired-invoices")
def get_paired_invoices_for_delivery_note(delivery_note_id: str):
    """Get invoices that are paired (accepted/confirmed) with a specific delivery note"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if delivery note exists in documents table
        cursor.execute("PRAGMA table_info(documents)")
        columns = [row[1] for row in cursor.fetchall()]
        has_doc_type = 'doc_type' in columns
        
        # Query for delivery note
        if has_doc_type:
            cursor.execute("""
                SELECT id, supplier, doc_date, total, delivery_no
                FROM documents
                WHERE id = ? AND doc_type = 'delivery_note'
            """, (delivery_note_id,))
        else:
            cursor.execute("""
                SELECT id, supplier, doc_date, total, delivery_no
                FROM documents
                WHERE id = ?
            """, (delivery_note_id,))
        
        dn_row = cursor.fetchone()
        if not dn_row:
            conn.close()
            return {"invoices": []}
        
        dn_doc_id = dn_row[0]
        
        # Check if pairs table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pairs'")
        if not cursor.fetchone():
            conn.close()
            return {"invoices": []}
        
        # Query pairs table for accepted/confirmed pairs where delivery_id matches
        try:
            cursor.execute("""
                SELECT 
                    p.id, p.invoice_id, p.delivery_id, p.confidence, p.status, p.created_at, p.decided_at,
                    i.filename as invoice_filename, i.supplier as invoice_supplier,
                    i.invoice_no, i.doc_date as invoice_date, i.total as invoice_total
                FROM pairs p
                JOIN documents i ON p.invoice_id = i.id
                WHERE (p.status = 'accepted' OR p.status = 'confirmed') AND p.delivery_id = ?
                ORDER BY p.decided_at DESC, p.created_at DESC
                LIMIT 100
            """, (dn_doc_id,))
        except sqlite3.OperationalError as e:
            # If pairs table structure is different, return empty
            logger.warning(f"Error querying pairs table for paired invoices: {e}")
            conn.close()
            return {"invoices": []}
        
        rows = cursor.fetchall()
        pairs = []
        if cursor.description:
            column_names = [desc[0] for desc in cursor.description]
            for row in rows:
                pair_dict = {}
                for idx, col_name in enumerate(column_names):
                    pair_dict[col_name] = row[idx]
                pairs.append(pair_dict)
        
        # Get invoice IDs from invoices table
        conn2 = sqlite3.connect(DB_PATH)
        cursor2 = conn2.cursor()
        
        paired_invoices = []
        for pair in pairs:
            invoice_doc_id = str(pair.get("invoice_id", ""))
            
            # Try to get invoice_id from invoices table
            cursor2.execute("SELECT id FROM invoices WHERE doc_id = ?", (invoice_doc_id,))
            invoice_row = cursor2.fetchone()
            
            invoice_id = invoice_row[0] if invoice_row else None
            
            # Format invoice data
            invoice_data = {
                "id": invoice_id or invoice_doc_id,
                "docId": invoice_doc_id,
                "invoiceId": invoice_id or invoice_doc_id,
                "invoiceNumber": pair.get("invoice_no", "") or f"INV-{invoice_doc_id[:8]}",
                "invoice_number": pair.get("invoice_no", ""),
                "supplier": pair.get("invoice_supplier", "Unknown Supplier"),
                "date": pair.get("invoice_date", ""),
                "invoiceDate": pair.get("invoice_date", ""),
                "total": float(pair.get("invoice_total", 0.0)) if pair.get("invoice_total") else 0.0,
                "totalValue": float(pair.get("invoice_total", 0.0)) if pair.get("invoice_total") else 0.0,
                "status": pair.get("status", "accepted"),
                "pairStatus": pair.get("status", "accepted"),
                "confidence": float(pair.get("confidence", 1.0)) if pair.get("confidence") else 1.0,
                "pairedAt": pair.get("decided_at") or pair.get("created_at", ""),
                "createdAt": pair.get("created_at", ""),
            }
            paired_invoices.append(invoice_data)
        
        conn2.close()
        conn.close()
        
        append_audit(datetime.now().isoformat(), "local", "get_paired_invoices_for_dn", f'{{"delivery_note_id": "{delivery_note_id}", "count": {len(paired_invoices)}}}')
        return {"invoices": paired_invoices}
    
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        set_last_error(datetime.now().isoformat(), "get_paired_invoices_for_dn", error_msg, "{}")
        append_audit(datetime.now().isoformat(), "local", "get_paired_invoices_for_dn_error", f'{{"error": "{error_msg}"}}')
        logger.warning(f"Error fetching paired invoices for delivery note {delivery_note_id}: {error_msg}")
        return {"invoices": []}

@app.get("/api/notes/unmatched")
def unmatched_notes():
    """Get unmatched delivery notes - placeholder for now"""
    append_audit(datetime.now().isoformat(), "local", "unmatched_notes", "{}")
    # For now, return empty array since we don't have delivery notes table yet
    return []

class DeleteDeliveryNotesRequest(BaseModel):
    """Request model for deleting delivery notes"""
    delivery_note_ids: List[str]

@app.post("/api/delivery-notes/batch/delete")
def delete_delivery_notes(request: DeleteDeliveryNotesRequest):
    """
    Delete non-paired delivery notes.
    Only deletes delivery notes that are not currently paired with invoices.
    Removes delivery notes, associated line items, and documents.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        delivery_note_ids = request.delivery_note_ids
        if not delivery_note_ids:
            return {"success": False, "deleted_count": 0, "skipped_count": 0, "message": "No delivery note IDs provided"}
        
        logger.info(f"[DELETE_DELIVERY_NOTES] Received request to delete {len(delivery_note_ids)} delivery notes")
        
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        cursor = conn.cursor()
        # Enable foreign keys to get proper constraint error messages
        cursor.execute("PRAGMA foreign_keys=ON")
        
        # Check which columns exist
        cursor.execute("PRAGMA table_info(documents)")
        columns = [row[1] for row in cursor.fetchall()]
        has_doc_type = 'doc_type' in columns
        
        # Check if pairs table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pairs'")
        pairs_table_exists = cursor.fetchone() is not None
        
        deleted_count = 0
        skipped_count = 0
        errors = []
        
        for dn_id in delivery_note_ids:
            try:
                logger.info(f"[DELETE_DELIVERY_NOTES] Processing deletion for DN ID: {dn_id}")
                
                # Verify delivery note exists - first try with doc_type filter, then without
                dn_row = None
                if has_doc_type:
                    cursor.execute("SELECT id, supplier, delivery_no, doc_type FROM documents WHERE id = ?", (dn_id,))
                    dn_row = cursor.fetchone()
                    if dn_row:
                        # Check if it's actually a delivery note
                        doc_type = dn_row[3] if len(dn_row) > 3 else None
                        if doc_type and doc_type != 'delivery_note':
                            error_msg = f"Document {dn_id} exists but is not a delivery note (doc_type='{doc_type}')"
                            logger.warning(f"[DELETE_DELIVERY_NOTES] {error_msg}")
                            errors.append(error_msg)
                            continue
                else:
                    # No doc_type column, just check if document exists
                    cursor.execute("SELECT id, supplier, delivery_no FROM documents WHERE id = ?", (dn_id,))
                    dn_row = cursor.fetchone()
                
                if not dn_row:
                    # Try to see if document exists at all (for debugging)
                    cursor.execute("SELECT id, filename FROM documents WHERE id = ?", (dn_id,))
                    any_doc = cursor.fetchone()
                    if any_doc:
                        error_msg = f"Document {dn_id} exists but may not be a delivery note (check doc_type)"
                    else:
                        error_msg = f"Delivery note {dn_id} not found in documents table"
                    logger.warning(f"[DELETE_DELIVERY_NOTES] {error_msg}")
                    errors.append(error_msg)
                    continue
                
                logger.info(f"[DELETE_DELIVERY_NOTES] Found DN: {dn_id}, supplier: {dn_row[1] if len(dn_row) > 1 else 'N/A'}, delivery_no: {dn_row[2] if len(dn_row) > 2 else 'N/A'}")
                
                # Check if delivery note is paired (exists in pairs table)
                is_paired = False
                pairing_reason = None
                
                if pairs_table_exists:
                    cursor.execute("SELECT id, invoice_id, status FROM pairs WHERE delivery_id = ?", (dn_id,))
                    pair_row = cursor.fetchone()
                    if pair_row:
                        is_paired = True
                        pairing_reason = f"paired in pairs table with invoice {pair_row[1] if len(pair_row) > 1 else 'N/A'}, status: {pair_row[2] if len(pair_row) > 2 else 'N/A'}"
                        logger.info(f"[DELETE_DELIVERY_NOTES] DN {dn_id} is {pairing_reason}")
                
                # Check if documents table has invoice_id column (legacy pairing method)
                if not is_paired:
                    cursor.execute("PRAGMA table_info(documents)")
                    doc_columns = [row[1] for row in cursor.fetchall()]
                    if 'invoice_id' in doc_columns:
                        cursor.execute("SELECT invoice_id FROM documents WHERE id = ?", (dn_id,))
                        invoice_id_row = cursor.fetchone()
                        if invoice_id_row and invoice_id_row[0]:
                            is_paired = True
                            pairing_reason = f"paired via documents.invoice_id: {invoice_id_row[0]}"
                            logger.info(f"[DELETE_DELIVERY_NOTES] DN {dn_id} is {pairing_reason}")
                
                # Check if any invoice references this DN via invoices.delivery_note_id
                if not is_paired:
                    cursor.execute("SELECT id FROM invoices WHERE delivery_note_id = ?", (dn_id,))
                    invoice_ref_row = cursor.fetchone()
                    if invoice_ref_row:
                        is_paired = True
                        pairing_reason = f"referenced by invoice {invoice_ref_row[0]} via invoices.delivery_note_id"
                        logger.info(f"[DELETE_DELIVERY_NOTES] DN {dn_id} is {pairing_reason}")
                
                # Only delete non-paired delivery notes
                if is_paired:
                    skipped_count += 1
                    error_msg = f"Delivery note {dn_id} is {pairing_reason} and cannot be deleted"
                    logger.warning(f"[DELETE_DELIVERY_NOTES] {error_msg}")
                    errors.append(error_msg)
                    continue
                
                # Delete associated line items (where invoice_id IS NULL for delivery note line items)
                # Check if line_items table exists and has invoice_id column
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='line_items'")
                if cursor.fetchone():
                    cursor.execute("PRAGMA table_info(line_items)")
                    line_items_columns = [row[1] for row in cursor.fetchall()]
                    if 'invoice_id' in line_items_columns and 'doc_id' in line_items_columns:
                        deleted_line_items = cursor.execute("DELETE FROM line_items WHERE doc_id = ? AND invoice_id IS NULL", (dn_id,)).rowcount
                        logger.info(f"[DELETE_DELIVERY_NOTES] Deleted {deleted_line_items} line items for DN {dn_id}")
                    elif 'doc_id' in line_items_columns:
                        deleted_line_items = cursor.execute("DELETE FROM line_items WHERE doc_id = ?", (dn_id,)).rowcount
                        logger.info(f"[DELETE_DELIVERY_NOTES] Deleted {deleted_line_items} line items for DN {dn_id}")
                
                # Delete from documents table
                # First verify it still exists (might have been deleted by another process)
                cursor.execute("SELECT id FROM documents WHERE id = ?", (dn_id,))
                if not cursor.fetchone():
                    error_msg = f"Delivery note {dn_id} no longer exists (may have been deleted)"
                    logger.warning(f"[DELETE_DELIVERY_NOTES] {error_msg}")
                    errors.append(error_msg)
                    continue
                
                deleted_docs = cursor.execute("DELETE FROM documents WHERE id = ?", (dn_id,)).rowcount
                logger.info(f"[DELETE_DELIVERY_NOTES] DELETE query executed, rows affected: {deleted_docs} for DN {dn_id}")
                
                if deleted_docs > 0:
                    deleted_count += 1
                    logger.info(f"[DELETE_DELIVERY_NOTES] Successfully deleted DN {dn_id}")
                else:
                    error_msg = f"Failed to delete delivery note {dn_id} from documents table (no rows affected - may be a constraint issue)"
                    logger.warning(f"[DELETE_DELIVERY_NOTES] {error_msg}")
                    errors.append(error_msg)
                
            except Exception as e:
                error_msg = f"Error deleting delivery note {dn_id}: {str(e)}"
                errors.append(error_msg)
                logger.error(f"[DELETE_DELIVERY_NOTES] {error_msg}", exc_info=True)
                continue
        
        conn.commit()
        conn.close()
        
        # Log the deletion
        logger.info(f"[DELETE_DELIVERY_NOTES] Deleted {deleted_count} delivery notes, skipped {skipped_count}")
        append_audit(
            datetime.now().isoformat(),
            "local",
            "delete_delivery_notes",
            f'{{"count": {deleted_count}, "skipped": {skipped_count}, "ids": {delivery_note_ids}, "errors": {errors}}}'
        )
        
        message = f"Successfully deleted {deleted_count} delivery note(s)"
        if skipped_count > 0:
            message += f", skipped {skipped_count} paired delivery note(s)"
        if errors:
            if deleted_count == 0:
                message += f". Errors: {'; '.join(errors[:3])}"
            else:
                message += f". Some errors occurred: {'; '.join(errors[:2])}"
        
        return {
            "success": deleted_count > 0 or skipped_count > 0,  # Success if we processed the request (even if skipped)
            "deleted_count": deleted_count,
            "skipped_count": skipped_count,
            "message": message,
            "errors": errors if errors else []  # Include errors in response for debugging
        }
    
    except Exception as e:
        error_msg = str(e)
        logger.error(f"[DELETE_DELIVERY_NOTES] Error: {error_msg}", exc_info=True)
        append_audit(datetime.now().isoformat(), "local", "delete_delivery_notes_error", f'{{"error": "{error_msg}"}}')
        raise HTTPException(status_code=500, detail=f"Failed to delete delivery notes: {error_msg}")

@app.get("/api/invoices/{invoice_id}/suggestions")
def get_invoice_suggestions(invoice_id: str):
    """Get pairing suggestions for a specific invoice"""
    try:
        from db.pairs import db_list_pairs
        
        # Get actual invoice_id and doc_id from invoices table (handles both string UUIDs and integer IDs)
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Try to find invoice by ID or doc_id
        cursor.execute("SELECT id, doc_id FROM invoices WHERE id = ? OR doc_id = ?", (invoice_id, invoice_id))
        invoice_row = cursor.fetchone()
        
        if not invoice_row:
            conn.close()
            return {"suggestions": []}
        
        actual_invoice_id = invoice_row[0]  # Use the invoice ID from database
        invoice_doc_id = invoice_row[1] if len(invoice_row) > 1 else None
        
        # Pairs table stores invoice_id as document ID, so we need to use doc_id
        # If doc_id is not available, try using invoice_id directly
        doc_id_to_query = invoice_doc_id if invoice_doc_id else str(actual_invoice_id)
        
        # Check if pairs table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pairs'")
        pairs_table_exists = cursor.fetchone() is not None
        
        if not pairs_table_exists:
            conn.close()
            return {"suggestions": []}
        
        # Query pairs table directly using document ID
        try:
            cursor.execute("""
                SELECT 
                    p.id, p.invoice_id, p.delivery_id, p.confidence, p.status, p.created_at,
                    i.filename as invoice_filename, i.supplier as invoice_supplier,
                    i.invoice_no, i.doc_date as invoice_date, i.total as invoice_total,
                    d.filename as delivery_filename, d.delivery_no, d.doc_date as delivery_date
                FROM pairs p
                JOIN documents i ON p.invoice_id = i.id
                JOIN documents d ON p.delivery_id = d.id
                WHERE p.status = 'suggested' AND p.invoice_id = ?
                ORDER BY p.confidence DESC, p.created_at DESC
                LIMIT 100
            """, (doc_id_to_query,))
        except sqlite3.OperationalError as e:
            # If pairs table structure is different or JOIN fails, return empty suggestions
            logger.warning(f"Error querying pairs table: {e}")
            conn.close()
            return {"suggestions": []}
        
        rows = cursor.fetchall()
        pairs = []
        if cursor.description:
            column_names = [desc[0] for desc in cursor.description]
            for row in rows:
                pair_dict = {}
                for idx, col_name in enumerate(column_names):
                    pair_dict[col_name] = row[idx]
                pairs.append(pair_dict)
        
        conn.close()
        
        # Format response to match frontend expectations
        from backend.services.quantity_validator import validate_quantity_match
        
        suggestions = []
        for pair in pairs:
            delivery_note_id = str(pair.get("delivery_id", ""))
            
            # Calculate quantity match and differences for this suggestion
            quantity_match_score = 1.0
            quantity_differences = []
            has_quantity_mismatch = False
            quantity_warnings = []
            try:
                validation_result = validate_quantity_match(actual_invoice_id, delivery_note_id)
                quantity_match_score = validation_result.get("match_score", 1.0)
                discrepancies = validation_result.get("discrepancies", [])
                quantity_warnings = validation_result.get("warnings", [])[:3]  # Limit to first 3 warnings
                
                # Convert discrepancies to quantity differences format
                for disc in discrepancies:
                    quantity_differences.append({
                        "description": disc.get("description", ""),
                        "invoiceQty": disc.get("invoice_qty", 0),
                        "dnQty": disc.get("delivery_qty", 0),
                        "difference": disc.get("difference", 0)
                    })
                
                has_quantity_mismatch = len(discrepancies) > 0 or quantity_match_score < 0.95
            except Exception as e:
                # Log warning but continue without validation
                logger.warning(f"Failed to validate quantities for suggestion (invoice={actual_invoice_id}, delivery={delivery_note_id}): {e}")
                quantity_match_score = 1.0
                quantity_warnings = []
            
            suggestion = {
                "id": str(pair["id"]),
                "deliveryNoteId": delivery_note_id,
                "delivery_note_id": delivery_note_id,
                "deliveryNoteNumber": pair.get("delivery_no", ""),
                "delivery_note_number": pair.get("delivery_no", ""),
                "deliveryDate": pair.get("delivery_date", ""),
                "delivery_date": pair.get("delivery_date", ""),
                "supplier": pair.get("invoice_supplier", ""),
                "totalAmount": float(pair.get("invoice_total", 0.0)) if pair.get("invoice_total") else 0.0,
                "total_amount": float(pair.get("invoice_total", 0.0)) if pair.get("invoice_total") else 0.0,
                "similarity": float(pair.get("confidence", 0.0)),
                "confidence": float(pair.get("confidence", 0.0)),
                "quantityDifferences": quantity_differences,
                "quantity_differences": quantity_differences,
                "hasQuantityMismatch": has_quantity_mismatch,
                "has_quantity_mismatch": has_quantity_mismatch,
                "quantityMatchScore": quantity_match_score,
                "quantity_match_score": quantity_match_score,
                "quantityWarnings": quantity_warnings,
                "quantity_warnings": quantity_warnings,
                "valueDelta": 0,
                "value_delta": 0,  # Calculate if needed
                "dateDeltaDays": 0,
                "date_delta_days": 0,  # Calculate if needed
                "reason": f"Confidence: {pair.get('confidence', 0.0):.0%}",
            }
            suggestions.append(suggestion)
        
        append_audit(datetime.now().isoformat(), "local", "invoice_suggestions", f'{{"invoice_id": "{invoice_id}", "count": {len(suggestions)}}}')
        return {"suggestions": suggestions}
        
    except Exception as e:
        error_msg = str(e)
        set_last_error(datetime.now().isoformat(), "invoice_suggestions", error_msg, "{}")
        append_audit(datetime.now().isoformat(), "local", "invoice_suggestions_error", f'{{"error": "{error_msg}"}}')
        logger.error(f"Error getting invoice suggestions: {error_msg}", exc_info=True)
        # Return empty suggestions instead of raising error to avoid breaking frontend
        return {"suggestions": []}

@app.get("/api/pairs/suggestions")
def get_pair_suggestions(delivery_note_id: str = Query(None, description="Optional: filter by delivery note ID")):
    """Get all pairing suggestions, optionally filtered by delivery note ID"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Build query based on whether delivery_note_id is provided
        if delivery_note_id:
            # Filter by delivery note ID
            query = """
                SELECT 
                    p.id, p.invoice_id, p.delivery_id, p.confidence, p.status, p.created_at,
                    i.filename as invoice_filename, i.supplier as invoice_supplier,
                    i.invoice_no, i.doc_date as invoice_date, i.total as invoice_total,
                    d.filename as delivery_filename, d.delivery_no, d.doc_date as delivery_date
                FROM pairs p
                JOIN documents i ON p.invoice_id = i.id
                JOIN documents d ON p.delivery_id = d.id
                WHERE p.status = 'suggested' AND p.delivery_id = ?
                ORDER BY p.confidence DESC, p.created_at DESC
                LIMIT 100
            """
            cursor.execute(query, (delivery_note_id,))
        else:
            # Get all suggested pairs
            query = """
                SELECT 
                    p.id, p.invoice_id, p.delivery_id, p.confidence, p.status, p.created_at,
                    i.filename as invoice_filename, i.supplier as invoice_supplier,
                    i.invoice_no, i.doc_date as invoice_date, i.total as invoice_total,
                    d.filename as delivery_filename, d.delivery_no, d.doc_date as delivery_date
                FROM pairs p
                JOIN documents i ON p.invoice_id = i.id
                JOIN documents d ON p.delivery_id = d.id
                WHERE p.status = 'suggested'
                ORDER BY p.confidence DESC, p.created_at DESC
                LIMIT 50
            """
            cursor.execute(query)
        
        rows = cursor.fetchall()
        pairs = []
        if cursor.description:
            column_names = [desc[0] for desc in cursor.description]
            for row in rows:
                pair_dict = {}
                for idx, col_name in enumerate(column_names):
                    pair_dict[col_name] = row[idx]
                pairs.append(pair_dict)
        
        conn.close()
        
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
                "delivery_date": pair.get("delivery_date", ""),
                "invoice_id": str(pair.get("invoice_id", "")),
                "delivery_id": str(pair.get("delivery_id", "")),
            }
            suggestions.append(suggestion)
        
        append_audit(datetime.now().isoformat(), "local", "pair_suggestions", f'{{"count": {len(suggestions)}, "delivery_note_id": "{delivery_note_id or "all"}"}}')
        return {"suggestions": suggestions}
        
    except Exception as e:
        error_msg = str(e)
        set_last_error(datetime.now().isoformat(), "pair_suggestions", error_msg, "{}")
        append_audit(datetime.now().isoformat(), "local", "pair_suggestions_error", f'{{"error": "{error_msg}"}}')
        logger.error(f"Error getting pair suggestions: {error_msg}", exc_info=True)
        # Return empty suggestions instead of raising error to avoid breaking frontend
        return {"suggestions": []}

@app.get("/api/discrepancies")
def get_discrepancies(scope: str = Query("dashboard", description="Scope for discrepancies")):
    """
    Get discrepancies for a given scope.
    Currently returns empty list - endpoint exists to prevent 404 errors.
    TODO: Implement actual discrepancy detection logic.
    """
    return {
        "items": [],
        "discrepancies": [],
        "lastUpdated": datetime.now().isoformat(),
        "last_updated": datetime.now().isoformat()
    }

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
async def upload_file(file: UploadFile = File(...), background_tasks: BackgroundTasks = BackgroundTasks()):
    # #region agent log
    with open(r'c:\Users\tedev\FixPack_2025-11-02_133105\.cursor\debug.log', 'a', encoding='utf-8') as f:
        f.write('{"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"main.py:2148","message":"Upload endpoint called","data":{"filename":"' + str(file.filename) + '"},"timestamp":' + str(int(time.time() * 1000)) + '}\n')
    # #endregion
    
    # Check OCR readiness before accepting upload
    from backend.services.ocr_readiness import check_ocr_readiness
    readiness = check_ocr_readiness()
    if not readiness.ready:
        error_msg = f"OCR prerequisites not met. Missing: {', '.join(readiness.missing_required)}"
        logger.error(f"[OCR_NOT_READY] {error_msg}")
        raise HTTPException(
            status_code=503,
            detail={
                "error": "OCR service unavailable",
                "message": error_msg,
                "missing_required": readiness.missing_required,
                "warnings": readiness.warnings
            }
        )
    
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
            
            # Query document status and check if invoice exists
            doc_status = existing_doc.get('status', 'processing')
            invoice_exists = check_invoice_exists(existing_doc["id"])
            
            response = {
                "doc_id": existing_doc["id"],
                "filename": existing_doc["filename"],
                "status": "duplicate",
                "doc_status": doc_status,  # Add actual document status
                "has_invoice": invoice_exists,  # Add invoice existence flag
                "message": "File already uploaded",
                "existing_doc_id": existing_doc["id"],
                "format": file_ext
            }
            
            # If status is 'error' and no invoice, trigger OCR retry automatically
            if doc_status == 'error' and not invoice_exists:
                logger.info(f"[UPLOAD] Duplicate document with error status - triggering OCR retry for doc_id={existing_doc['id']}")
                background_tasks.add_task(_run_ocr_background_sync, existing_doc["id"], existing_doc.get("stored_path"))
            
            return response
        
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
        
        # Trigger OCR processing asynchronously using FastAPI BackgroundTasks
        try:
            logger.info(f"[UPLOAD] Triggering OCR background task for doc_id={doc_id}, file={stored_path}")
            # Use FastAPI BackgroundTasks instead of asyncio.create_task for better reliability
            background_tasks.add_task(_run_ocr_background_sync, doc_id, stored_path)
            logger.info(f"[UPLOAD] OCR background task scheduled for doc_id={doc_id}")
            # #region agent log
            with open(r'c:\Users\tedev\FixPack_2025-11-02_133105\.cursor\debug.log', 'a', encoding='utf-8') as f:
                f.write('{"sessionId":"debug-session","runId":"run1","hypothesisId":"F","location":"main.py:2314","message":"OCR task scheduled via BackgroundTasks","data":{"doc_id":"' + str(doc_id) + '","file_path":"' + str(stored_path) + '"},"timestamp":' + str(int(time.time() * 1000)) + '}\n')
            # #endregion
            
        except Exception as ocr_error:
            # Log OCR trigger failure but don't fail the upload
            error_msg = str(ocr_error)
            logger.error(f"[UPLOAD] Failed to trigger OCR for doc_id={doc_id}: {error_msg}")
            # #region agent log
            with open(r'c:\Users\tedev\FixPack_2025-11-02_133105\.cursor\debug.log', 'a', encoding='utf-8') as f:
                f.write('{"sessionId":"debug-session","runId":"run1","hypothesisId":"F","location":"main.py:2322","message":"Failed to schedule OCR task","data":{"doc_id":"' + str(doc_id) + '","error":' + repr(error_msg) + '},"timestamp":' + str(int(time.time() * 1000)) + '}\n')
            # #endregion
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
        import traceback
        error_msg = str(e)
        error_trace = traceback.format_exc()
        # #region agent log
        with open(r'c:\Users\tedev\FixPack_2025-11-02_133105\.cursor\debug.log', 'a', encoding='utf-8') as f:
            f.write('{"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"main.py:2280","message":"Upload endpoint exception","data":{"error":' + repr(error_msg) + ',"traceback":' + repr(error_trace[:2000]) + '},"timestamp":' + str(int(time.time() * 1000)) + '}\n')
        # #endregion
        set_last_error(datetime.now().isoformat(), "upload", error_msg, "{}")
        append_audit(datetime.now().isoformat(), "local", "upload_error", f'{{"error": "{error_msg}"}}')
        logger.exception(f"Upload endpoint error: {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)

# MOCK REMOVED: returns only real OCR/DB data
@app.get("/api/upload/status")
def upload_status(doc_id: str = Query(..., description="Document ID to check status"), 
                  debug: bool = Query(False, description="Include OCR telemetry report")):
    """
    Return status + parsed summary + line items for a given doc_id.
    Useful for polling during OCR processing.
    MOCK REMOVED: Returns only real data from DB, no mock fallback.
    """
    try:
        con = sqlite3.connect(DB_PATH, check_same_thread=False)
        cur = con.cursor()
        
        # Check if document exists (handle missing status column gracefully)
        doc_row = None
        doc_status = "processing"
        ocr_error = None
        doc_type = None
        doc_type_confidence = None
        doc_type_reasons = None
        try:
            # Try to get all columns including classification
            cur.execute("""
                SELECT id, filename, status, ocr_error, doc_type, doc_type_confidence, doc_type_reasons
                FROM documents
                WHERE id = ?
            """, (doc_id,))
            doc_row = cur.fetchone()
            if doc_row:
                if len(doc_row) > 2:
                    doc_status = doc_row[2] if doc_row[2] else "processing"
                if len(doc_row) > 3:
                    ocr_error = doc_row[3]
                if len(doc_row) > 4:
                    doc_type = doc_row[4]
                if len(doc_row) > 5:
                    doc_type_confidence = doc_row[5]
                if len(doc_row) > 6:
                    doc_type_reasons_str = doc_row[6]
                    if doc_type_reasons_str:
                        try:
                            doc_type_reasons = json.loads(doc_type_reasons_str)
                        except:
                            doc_type_reasons = None
        except sqlite3.OperationalError as e:
            if "no such column: status" in str(e) or "no such column: ocr_error" in str(e):
                # Fallback: query without status/ocr_error columns (for old databases)
                try:
                    cur.execute("""
                        SELECT id, filename, status
                        FROM documents
                        WHERE id = ?
                    """, (doc_id,))
                    doc_row = cur.fetchone()
                    if doc_row and len(doc_row) > 2:
                        doc_status = doc_row[2] if doc_row[2] else "processing"
                except sqlite3.OperationalError:
                    # Final fallback: just id and filename
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
                "items": [],
                "doc_type": doc_type,
                "doc_type_confidence": doc_type_confidence,
                "doc_type_reasons": doc_type_reasons
            }
        
        # Get invoice data if available - use dynamic column detection
        # #region agent log
        try:
            cur.execute("PRAGMA table_info(invoices)")
            schema_info = cur.fetchall()
            column_names = [col[1] for col in schema_info]
            with open(r'c:\Users\tedev\FixPack_2025-11-02_133105\.cursor\debug.log', 'a', encoding='utf-8') as f:
                f.write('{"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"main.py:2392","message":"upload_status schema check","data":{"columns":' + repr(column_names) + '},"timestamp":' + str(int(time.time() * 1000)) + '}\n')
        except Exception as e:
            column_names = []
            with open(r'c:\Users\tedev\FixPack_2025-11-02_133105\.cursor\debug.log', 'a', encoding='utf-8') as f:
                f.write('{"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"main.py:2392","message":"upload_status schema check failed","data":{"error":' + repr(str(e)) + '},"timestamp":' + str(int(time.time() * 1000)) + '}\n')
        # #endregion
        
        # Detect which columns exist
        has_supplier_name = 'supplier_name' in column_names
        has_supplier = 'supplier' in column_names
        has_invoice_date = 'invoice_date' in column_names
        has_date = 'date' in column_names
        has_total_p = 'total_p' in column_names
        has_total_amount_pennies = 'total_amount_pennies' in column_names
        has_value = 'value' in column_names
        
        supplier_col = 'i.supplier_name' if has_supplier_name else ('i.supplier' if has_supplier else 'NULL')
        date_col = 'i.invoice_date' if has_invoice_date else ('i.date' if has_date else 'NULL')
        total_col = 'COALESCE(i.total_p, i.total_amount_pennies, 0)' if (has_total_p or has_total_amount_pennies) else ('i.value' if has_value else '0')
        
        query = f"""
            SELECT i.id, {supplier_col} as supplier, {date_col} as invoice_date, {total_col} as total_value,
                   COALESCE(i.status, 'scanned') as status,
                   COALESCE(i.confidence, 0.9) as confidence
            FROM invoices i
            WHERE i.doc_id = ?
            LIMIT 1
        """
        cur.execute(query, (doc_id,))
        
        inv_row = cur.fetchone()
        
        # Get line items if invoice exists
        items = []
        if inv_row:
            invoice_id = inv_row[0]
            items = get_line_items_for_invoice(invoice_id)
            # If no items by invoice_id, try by doc_id
            if not items:
                items = get_line_items_for_doc(doc_id)
            
            # Shape response with canonical field names
            con.close()
            invoice_value = float(inv_row[3]) if inv_row[3] else 0.0
            # Wrapper structure kept for backward compatibility (parsed, items)
            # But invoice object uses canonical field names
            return {
                "doc_id": doc_id,
                "status": inv_row[4] if inv_row[4] else "scanned",
                "parsed": {
                    "supplier": inv_row[1],
                    "date": inv_row[2],
                    "value": invoice_value,
                    "total": invoice_value,
                    "total_value": invoice_value,
                    "confidence": float(inv_row[5]) if inv_row[5] else 0.9,
                    "id": inv_row[0],
                },
                "items": items,
                "line_items": items,
                "invoice": {
                    "id": inv_row[0],
                    "doc_id": doc_id,
                    "supplier": inv_row[1],
                    "invoice_date": inv_row[2],
                    "total_value": invoice_value,
                    "currency": "GBP",
                    "confidence": float(inv_row[5]) if inv_row[5] else 0.9,
                    "status": inv_row[4],
                    "venue": None,  # TODO: populate from invoices table
                    "issues_count": 0,  # TODO: populate from invoices table
                    "paired": False,  # TODO: populate from invoices table
                    "pairing_status": None,  # TODO: populate from invoices table
                    "delivery_note_id": None,  # TODO: populate from invoices table
                    "line_items": items
                },
                "doc_type": doc_type,
                "doc_type_confidence": doc_type_confidence,
                "doc_type_reasons": doc_type_reasons
            }
        
        # Get OCR report if available
        ocr_report_json = None
        ocr_confidence = 0.0
        try:
            cur.execute("""
                SELECT ocr_confidence, ocr_report_json
                FROM documents
                WHERE id = ?
            """, (doc_id,))
            conf_row = cur.fetchone()
            if conf_row:
                ocr_confidence = float(conf_row[0]) if conf_row[0] is not None else 0.0
                ocr_report_json = conf_row[1] if len(conf_row) > 1 and conf_row[1] else None
        except sqlite3.OperationalError:
            pass  # Column may not exist in old databases
        
        # Document exists but invoice not processed yet
        con.close()
        
        # Determine if we should include OCR report
        include_ocr_report = debug or ocr_confidence < 0.6
        
        response = {
            "doc_id": doc_id,
            "status": doc_status,
            "parsed": None,
            "items": [],
            "doc_type": doc_type,
            "doc_type_confidence": doc_type_confidence,
            "doc_type_reasons": doc_type_reasons,
            "confidence": ocr_confidence
        }
        
        # Include error message if status is error
        if doc_status == "error" and ocr_error:
            response["error"] = ocr_error  # Keep for backward compatibility
            
            # Try to parse structured error metadata
            try:
                error_metadata = json.loads(ocr_error)
                if isinstance(error_metadata, dict):
                    response["error_code"] = error_metadata.get("error_code", "unknown")
                    response["ocr_attempts"] = error_metadata.get("ocr_attempts", [])
                    response["error_metadata"] = error_metadata
            except (json.JSONDecodeError, TypeError):
                # Legacy error format - just string, no structured metadata
                pass
        
        # Include OCR telemetry report if requested or low confidence
        if include_ocr_report and ocr_report_json:
            try:
                from backend.ocr.ocr_telemetry import OCRTelemetryReport
                report = OCRTelemetryReport.from_json(ocr_report_json)
                response["ocr_report"] = report.to_dict()
            except Exception as e:
                logger.warning(f"[UPLOAD_STATUS] Failed to parse OCR report for doc_id={doc_id}: {e}")
                # Include raw JSON as fallback
                response["ocr_report"] = {"raw_json": ocr_report_json}
        
        return response
    
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


@app.get("/api/documents/recent")
def get_recent_documents(
    limit: int = Query(50, description="Number of documents to return"),
    offset: int = Query(0, description="Number of documents to skip"),
    status: Optional[str] = Query(None, description="Filter by status (optional)")
):
    """
    Get recent documents with optional invoice data.
    Returns all documents regardless of whether they have invoice rows.
    This is the primary endpoint for building the document card list.
    """
    try:
        con = sqlite3.connect(DB_PATH, check_same_thread=False)
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        
        # Build WHERE clause
        where_clause = "1=1"
        params = []
        if status:
            where_clause += " AND d.status = ?"
            params.append(status)
        
        # Detect invoice table columns
        cur.execute("PRAGMA table_info(invoices)")
        invoice_columns = [col[1] for col in cur.fetchall()]
        has_supplier_name = 'supplier_name' in invoice_columns
        has_supplier = 'supplier' in invoice_columns
        has_invoice_date = 'invoice_date' in invoice_columns
        has_date = 'date' in invoice_columns
        has_total_p = 'total_p' in invoice_columns
        has_total_amount_pennies = 'total_amount_pennies' in invoice_columns
        has_value = 'value' in invoice_columns
        has_invoice_number = 'invoice_number' in invoice_columns
        
        supplier_col = 'i.supplier_name' if has_supplier_name else ('i.supplier' if has_supplier else 'NULL')
        date_col = 'i.invoice_date' if has_invoice_date else ('i.date' if has_date else 'NULL')
        total_col = 'COALESCE(i.total_p, i.total_amount_pennies, 0)' if (has_total_p or has_total_amount_pennies) else ('i.value' if has_value else '0')
        invoice_number_col = 'i.invoice_number' if has_invoice_number else 'NULL'
        
        # Query documents with LEFT JOIN to invoices
        query = f"""
            SELECT 
                d.id as doc_id,
                d.filename,
                d.uploaded_at,
                COALESCE(d.status, 'processing') as status,
                d.doc_type,
                d.doc_type_confidence,
                d.ocr_error,
                d.ocr_confidence as confidence,
                CASE WHEN i.id IS NOT NULL THEN 1 ELSE 0 END as has_invoice_row,
                {supplier_col} as supplier,
                {date_col} as invoice_date,
                {total_col} as total_value,
                {invoice_number_col} as invoice_number,
                i.confidence as invoice_confidence
            FROM documents d
            LEFT JOIN invoices i ON d.id = i.doc_id
            WHERE {where_clause}
            ORDER BY d.uploaded_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        
        cur.execute(query, params)
        rows = cur.fetchall()
        
        # Get total count
        count_query = f"SELECT COUNT(*) FROM documents d WHERE {where_clause}"
        count_params = params[:-2]  # Remove limit/offset
        cur.execute(count_query, count_params)
        total_count = cur.fetchone()[0]
        
        # Build response
        documents = []
        for row in rows:
            doc = {
                "doc_id": row["doc_id"],
                "filename": row["filename"],
                "uploaded_at": row["uploaded_at"],
                "status": row["status"],
                "doc_type": row["doc_type"],
                "doc_type_confidence": float(row["doc_type_confidence"]) if row["doc_type_confidence"] is not None else 0.0,
                "confidence": float(row["confidence"]) if row["confidence"] is not None else 0.0,
                "ocr_error": row["ocr_error"],
                "error_code": None,
                "has_invoice_row": bool(row["has_invoice_row"])
            }
            
            # Parse error_code from ocr_error if it's JSON
            if row["ocr_error"]:
                try:
                    error_metadata = json.loads(row["ocr_error"])
                    if isinstance(error_metadata, dict):
                        doc["error_code"] = error_metadata.get("error_code")
                        doc["ocr_attempts"] = error_metadata.get("ocr_attempts", [])
                except (json.JSONDecodeError, TypeError):
                    pass
            
            # Include invoice data if available
            if row["has_invoice_row"]:
                total_value = float(row["total_value"]) if row["total_value"] else 0.0
                # Convert from pence to pounds if needed
                if (has_total_p or has_total_amount_pennies) and total_value > 0:
                    total_value = total_value / 100.0
                doc["invoice"] = {
                    "supplier": row["supplier"],
                    "total": total_value,
                    "date": row["invoice_date"],
                    "invoice_number": row["invoice_number"],
                    "confidence": float(row["invoice_confidence"]) if row["invoice_confidence"] is not None else 0.0
                }
            else:
                doc["invoice"] = None
            
            documents.append(doc)
        
        con.close()
        
        return {
            "documents": documents,
            "count": len(documents),
            "total": total_count,
            "limit": limit,
            "offset": offset
        }
    
    except Exception as e:
        error_msg = str(e)
        logger.exception(f"[DOCUMENTS_RECENT] Error fetching recent documents: {error_msg}")
        append_audit(datetime.now().isoformat(), "local", "documents_recent_error", f'{{"error": "{error_msg}"}}')
        raise HTTPException(status_code=500, detail=error_msg)


@app.get("/api/documents/{doc_id}/status")
def get_document_status(doc_id: str, debug: bool = Query(False, description="Include OCR telemetry report")):
    """
    Get document status directly for checking stuck processing states.
    Returns document status, error message, and whether invoice exists.
    Used by frontend to check if a document is stuck in processing or has errored.
    
    Args:
        doc_id: Document ID
        debug: If True, include OCR telemetry report in response
    """
    try:
        con = sqlite3.connect(DB_PATH, check_same_thread=False)
        cur = con.cursor()
        
        # Get document status, error, classification, confidence, and OCR report
        doc_status = "processing"
        ocr_error = None
        doc_type = None
        doc_type_confidence = None
        doc_type_reasons = None
        ocr_confidence = 0.0
        ocr_report_json = None
        try:
            cur.execute("""
                SELECT status, ocr_error, doc_type, doc_type_confidence, doc_type_reasons, 
                       ocr_confidence, ocr_report_json
                FROM documents
                WHERE id = ?
            """, (doc_id,))
            doc_row = cur.fetchone()
            if doc_row:
                doc_status = doc_row[0] if doc_row[0] else "processing"
                ocr_error = doc_row[1] if len(doc_row) > 1 and doc_row[1] else None
                doc_type = doc_row[2] if len(doc_row) > 2 and doc_row[2] else None
                doc_type_confidence = doc_row[3] if len(doc_row) > 3 and doc_row[3] else None
                if len(doc_row) > 4 and doc_row[4]:
                    try:
                        doc_type_reasons = json.loads(doc_row[4])
                    except:
                        doc_type_reasons = None
                ocr_confidence = float(doc_row[5]) if len(doc_row) > 5 and doc_row[5] is not None else 0.0
                ocr_report_json = doc_row[6] if len(doc_row) > 6 and doc_row[6] else None
        except sqlite3.OperationalError as e:
            if "no such column" in str(e):
                # Fallback for old databases - try without new columns
                try:
                    cur.execute("""
                        SELECT status, ocr_error, ocr_confidence
                        FROM documents
                        WHERE id = ?
                    """, (doc_id,))
                    doc_row = cur.fetchone()
                    if doc_row:
                        doc_status = doc_row[0] if doc_row[0] else "processing"
                        ocr_error = doc_row[1] if len(doc_row) > 1 and doc_row[1] else None
                        ocr_confidence = float(doc_row[2]) if len(doc_row) > 2 and doc_row[2] is not None else 0.0
                except sqlite3.OperationalError:
                    doc_status = "processing"
                    ocr_error = None
                    ocr_confidence = 0.0
            else:
                raise
        
        # Check if invoice exists
        invoice_exists = check_invoice_exists(doc_id)
        
        con.close()
        
        # Determine if we should include OCR report
        # Include if debug=true OR confidence is low (< 0.6 = 60%)
        include_ocr_report = debug or ocr_confidence < 0.6
        
        response = {
            "doc_id": doc_id,
            "status": doc_status,
            "has_invoice": invoice_exists,
            "doc_type": doc_type,
            "doc_type_confidence": doc_type_confidence,
            "doc_type_reasons": doc_type_reasons,
            "confidence": ocr_confidence
        }
        
        if ocr_error:
            response["error"] = ocr_error
        
        # Include OCR telemetry report if requested or low confidence
        if include_ocr_report and ocr_report_json:
            try:
                from backend.ocr.ocr_telemetry import OCRTelemetryReport
                report = OCRTelemetryReport.from_json(ocr_report_json)
                response["ocr_report"] = report.to_dict()
            except Exception as e:
                logger.warning(f"[DOC_STATUS] Failed to parse OCR report for doc_id={doc_id}: {e}")
                # Include raw JSON as fallback
                response["ocr_report"] = {"raw_json": ocr_report_json}
        
        return response
    
    except Exception as e:
        error_msg = str(e)
        logger.exception(f"[DOC_STATUS] Error getting document status for doc_id={doc_id}: {error_msg}")
        append_audit(datetime.now().isoformat(), "local", "document_status_error", f'{{"doc_id": "{doc_id}", "error": "{error_msg}"}}')
        return {
            "doc_id": doc_id,
            "status": "error",
            "error": error_msg,
            "has_invoice": False
        }

@app.get("/api/documents/{doc_id}/pipeline-debug")
def get_pipeline_debug(doc_id: str):
    """
    Diagnostic endpoint to trace pipeline end-to-end for a document.
    Returns data from all stages: documents, invoices, line_items tables.
    """
    try:
        con = sqlite3.connect(DB_PATH, check_same_thread=False)
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        
        result = {
            "doc_id": doc_id,
            "timestamp": datetime.now().isoformat(),
            "documents": None,
            "invoices": None,
            "line_items": None,
            "line_items_count": 0,
            "line_items_sample": []
        }
        
        # Query documents table (use uploaded_at, not created_at)
        cur.execute("""
            SELECT id, filename, stored_path, size_bytes, status, ocr_error, 
                   doc_type, doc_type_confidence, ocr_confidence, uploaded_at
            FROM documents
            WHERE id = ?
        """, (doc_id,))
        doc_row = cur.fetchone()
        if doc_row:
            result["documents"] = {
                "id": doc_row["id"],
                "filename": doc_row["filename"],
                "stored_path": doc_row["stored_path"],
                "size_bytes": doc_row["size_bytes"],
                "status": doc_row["status"],
                "ocr_error": doc_row["ocr_error"],
                "doc_type": doc_row["doc_type"],
                "doc_type_confidence": doc_row["doc_type_confidence"],
                "ocr_confidence": doc_row["ocr_confidence"],
                "uploaded_at": doc_row["uploaded_at"]
            }
        
        # Query invoices table
        cur.execute("""
            SELECT id, supplier, date, value, invoice_number, confidence, status, created_at
            FROM invoices
            WHERE id = ?
        """, (doc_id,))
        inv_row = cur.fetchone()
        if inv_row:
            result["invoices"] = {
                "id": inv_row["id"],
                "supplier": inv_row["supplier"],
                "date": inv_row["date"],
                "value": inv_row["value"],
                "invoice_number": inv_row["invoice_number"],
                "confidence": inv_row["confidence"],
                "status": inv_row["status"],
                "created_at": inv_row["created_at"]
            }
        
        # Query line_items table (use correct column names: qty not quantity, description not desc)
        cur.execute("""
            SELECT doc_id, invoice_id, description, qty, unit_price, total, 
                   uom, confidence, bbox
            FROM invoice_line_items
            WHERE doc_id = ?
            ORDER BY rowid
            LIMIT 100
        """, (doc_id,))
        line_item_rows = cur.fetchall()
        result["line_items_count"] = len(line_item_rows)
        result["line_items"] = []
        result["line_items_sample"] = []
        
        for idx, row in enumerate(line_item_rows):
            item = {
                "doc_id": row["doc_id"],
                "invoice_id": row["invoice_id"],
                "description": row["description"],
                "qty": row["qty"],
                "unit_price": row["unit_price"],
                "total": row["total"],
                "uom": row["uom"],
                "confidence": row["confidence"],
                "has_bbox": bool(row["bbox"])
            }
            result["line_items"].append(item)
            if idx < 3:  # First 3 items as sample
                result["line_items_sample"].append(item)
        
        con.close()
        
        return result
        
    except Exception as e:
        import traceback
        logger.exception(f"Pipeline debug endpoint error for doc_id={doc_id}: {e}")
        return {
            "doc_id": doc_id,
            "error": str(e),
            "traceback": traceback.format_exc()
        }


async def _run_ocr_background(doc_id: str, file_path: str):
    """Background task to run OCR processing with concurrency control"""
    # #region agent log
    with open(r'c:\Users\tedev\FixPack_2025-11-02_133105\.cursor\debug.log', 'a', encoding='utf-8') as f:
        f.write('{"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"main.py:2507","message":"OCR background task started","data":{"doc_id":"' + str(doc_id) + '","file_path":"' + str(file_path) + '"},"timestamp":' + str(int(time.time() * 1000)) + '}\n')
    # #endregion
    # Update metrics: queue
    _update_metrics("ocr_queue", _ocr_metrics["ocr_queue"] + 1)
    _update_metrics("last_doc_id", doc_id)
    
    async with _ocr_semaphore:
        # Update metrics: inflight
        _update_metrics("ocr_queue", _ocr_metrics["ocr_queue"] - 1)
        _update_metrics("ocr_inflight", _ocr_metrics["ocr_inflight"] + 1)
        
        try:
            from backend.services.ocr_service import process_document_ocr
            import asyncio
            import concurrent.futures
            
            logger.info(f"[OCR_BG] Starting OCR processing for doc_id={doc_id}, file={file_path}")
            # #region agent log
            with open(r'c:\Users\tedev\FixPack_2025-11-02_133105\.cursor\debug.log', 'a', encoding='utf-8') as f:
                f.write('{"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"main.py:2523","message":"About to run OCR in executor","data":{"doc_id":"' + str(doc_id) + '"},"timestamp":' + str(int(time.time() * 1000)) + '}\n')
            # #endregion
            
            # Run synchronous OCR function in thread pool executor to avoid blocking
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                result = await loop.run_in_executor(executor, process_document_ocr, doc_id, file_path)
            
            logger.info(f"[OCR_BG] OCR processing completed for doc_id={doc_id}, status={result.get('status')}, confidence={result.get('confidence', 0)}")
            # #region agent log
            with open(r'c:\Users\tedev\FixPack_2025-11-02_133105\.cursor\debug.log', 'a', encoding='utf-8') as f:
                f.write('{"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"main.py:2531","message":"OCR processing completed","data":{"doc_id":"' + str(doc_id) + '","status":"' + str(result.get('status', 'unknown')) + '","confidence":' + str(result.get('confidence', 0)) + '},"timestamp":' + str(int(time.time() * 1000)) + '}\n')
            # #endregion
            _update_metrics("total_processed", _ocr_metrics["total_processed"] + 1)
        except Exception as e:
            import traceback
            _update_metrics("total_errors", _ocr_metrics["total_errors"] + 1)
            error_msg = str(e)
            error_trace = traceback.format_exc()
            logger.exception(f"[OCR_BG] OCR processing failed for doc_id={doc_id}: {error_msg}")
            # #region agent log
            with open(r'c:\Users\tedev\FixPack_2025-11-02_133105\.cursor\debug.log', 'a', encoding='utf-8') as f:
                f.write('{"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"main.py:2537","message":"OCR processing failed","data":{"doc_id":"' + str(doc_id) + '","error":' + repr(error_msg) + ',"traceback":' + repr(error_trace[:2000]) + '},"timestamp":' + str(int(time.time() * 1000)) + '}\n')
            # #endregion
            append_audit(datetime.now().isoformat(), "local", "ocr_background_error", f'{{"doc_id": "{doc_id}", "error": "{error_msg}"}}')
            update_document_status(doc_id, "error", "ocr_error", error=error_msg)
        finally:
            _update_metrics("ocr_inflight", _ocr_metrics["ocr_inflight"] - 1)
            # #region agent log
            with open(r'c:\Users\tedev\FixPack_2025-11-02_133105\.cursor\debug.log', 'a', encoding='utf-8') as f:
                f.write('{"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"main.py:2545","message":"OCR background task finished","data":{"doc_id":"' + str(doc_id) + '"},"timestamp":' + str(int(time.time() * 1000)) + '}\n')
            # #endregion

def _run_ocr_background_sync(doc_id: str, file_path: str):
    """Synchronous wrapper for OCR background task (for FastAPI BackgroundTasks)"""
    import asyncio
    import traceback
    try:
        # #region agent log
        with open(r'c:\Users\tedev\FixPack_2025-11-02_133105\.cursor\debug.log', 'a', encoding='utf-8') as f:
            f.write('{"sessionId":"debug-session","runId":"run1","hypothesisId":"F","location":"main.py:2745","message":"_run_ocr_background_sync started","data":{"doc_id":"' + str(doc_id) + '","file_path":"' + str(file_path) + '"},"timestamp":' + str(int(time.time() * 1000)) + '}\n')
        # #endregion
        
        logger.info(f"[OCR_BG_SYNC] Starting OCR background task for doc_id={doc_id}")
        
        # Create new event loop for this background task thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_run_ocr_background(doc_id, file_path))
        finally:
            loop.close()
            
        logger.info(f"[OCR_BG_SYNC] Completed OCR background task for doc_id={doc_id}")
        # #region agent log
        with open(r'c:\Users\tedev\FixPack_2025-11-02_133105\.cursor\debug.log', 'a', encoding='utf-8') as f:
            f.write('{"sessionId":"debug-session","runId":"run1","hypothesisId":"F","location":"main.py:2760","message":"_run_ocr_background_sync completed","data":{"doc_id":"' + str(doc_id) + '"},"timestamp":' + str(int(time.time() * 1000)) + '}\n')
        # #endregion
    except Exception as e:
        error_msg = str(e)
        error_trace = traceback.format_exc()
        logger.exception(f"[OCR_BG_SYNC] Failed to run OCR for doc_id={doc_id}: {error_msg}")
        # #region agent log
        with open(r'c:\Users\tedev\FixPack_2025-11-02_133105\.cursor\debug.log', 'a', encoding='utf-8') as f:
            f.write('{"sessionId":"debug-session","runId":"run1","hypothesisId":"F","location":"main.py:2765","message":"_run_ocr_background_sync failed","data":{"doc_id":"' + str(doc_id) + '","error":' + repr(error_msg) + ',"traceback":' + repr(error_trace[:2000]) + '},"timestamp":' + str(int(time.time() * 1000)) + '}\n')
        # #endregion
        # Update document status to error
        try:
            update_document_status(doc_id, "error", "ocr_error", error=error_msg)
        except Exception as update_error:
            logger.error(f"[OCR_BG_SYNC] Failed to update document status: {update_error}")

@app.post("/api/ocr/retry/{doc_id}")
async def retry_ocr(doc_id: str, background_tasks: BackgroundTasks = BackgroundTasks()):
    """Retry OCR processing for a failed or incomplete document"""
    try:
        # Get document from database
        con = sqlite3.connect(DB_PATH, check_same_thread=False)
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
        
        # Reset document status to pending and clear error
        update_document_status(doc_id, "pending", "retry", error=None)
        append_audit(datetime.now().isoformat(), "local", "ocr_retry", f'{{"doc_id": "{doc_id}", "filename": "{filename}"}}')
        
        # Trigger OCR processing again using BackgroundTasks
        background_tasks.add_task(_run_ocr_background_sync, doc_id, file_path)
        
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


def get_version_info() -> Dict[str, Any]:
    """
    Get version information including git commit or file modification times.
    Returns dict with version info for debugging.
    """
    version_info: Dict[str, Any] = {
        "main_loaded_at": _MAIN_LOAD_ISO,
        "git_commit": None,
        "git_commit_short": None,
        "file_timestamps": {},
    }
    
    # Try to get git commit hash
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
            cwd=BASE_DIR.parent  # Run from project root
        )
        if result.returncode == 0:
            version_info["git_commit"] = result.stdout.strip()
            version_info["git_commit_short"] = version_info["git_commit"][:7] if version_info["git_commit"] else None
    except Exception:
        pass  # Git not available or not in a git repo
    
    # Get file modification times for key files
    key_files = [
        BASE_DIR / "main.py",
        BASE_DIR / "services" / "ocr_service.py",
        BASE_DIR / "ocr" / "owlin_scan_pipeline.py",
    ]
    
    for file_path in key_files:
        try:
            if file_path.exists():
                mtime = file_path.stat().st_mtime
                version_info["file_timestamps"][str(file_path.relative_to(BASE_DIR.parent))] = datetime.fromtimestamp(mtime).isoformat()
        except Exception:
            pass
    
    # Get OCR service version if available
    try:
        from backend.services.ocr_service import _VERSION_ISO as OCR_VERSION
        version_info["ocr_service_loaded_at"] = OCR_VERSION
    except Exception:
        version_info["ocr_service_loaded_at"] = None
    
    # Add Python and app version
    version_info["python_version"] = sys.version.split()[0]  # Just version number
    version_info["app_version"] = os.getenv("APP_VERSION", "1.2.0")
    
    return version_info


def _run_watchdog_periodically():
    """Background task to periodically check for and fix stuck documents"""
    import time
    from backend.services.ocr_service import fix_stuck_documents
    
    while True:
        try:
            # Run watchdog every 5 minutes
            time.sleep(300)  # 5 minutes
            fixed_count = fix_stuck_documents(max_processing_minutes=10)
            if fixed_count > 0:
                logger.info(f"[WATCHDOG] Periodic check fixed {fixed_count} stuck document(s)")
        except Exception as e:
            logger.error(f"[WATCHDOG] Error in periodic watchdog task: {e}", exc_info=True)
            # Continue running even if there's an error
            time.sleep(60)  # Wait 1 minute before retrying on error

@app.on_event("startup")
async def startup_event():
    """Startup event handler to log version information"""
    # Verify Path scoping fix is loaded
    try:
        from backend.ocr.owlin_scan_pipeline import _VERSION_FIX_PATH_SCOPING
        logger.info(f"[STARTUP] Path scoping fix loaded: {_VERSION_FIX_PATH_SCOPING}")
    except ImportError:
        logger.warning("[STARTUP] Path scoping fix version marker not found - code may not be loaded")
    logger.info(f"[BUILD] backend.main startup at {datetime.now().isoformat()}")
    
    # Start watchdog background task
    import threading
    watchdog_thread = threading.Thread(target=_run_watchdog_periodically, daemon=True)
    watchdog_thread.start()
    logger.info("[STARTUP] Watchdog background task started")
    
    # Check OCR readiness and log warnings
    try:
        from backend.services.ocr_readiness import check_ocr_readiness
        readiness = check_ocr_readiness()
        
        if not readiness.ready:
            logger.warning(f"[STARTUP] OCR prerequisites not met. Missing: {', '.join(readiness.missing_required)}")
            for dep in readiness.dependencies:
                if not dep.available and dep.required:
                    logger.warning(f"[STARTUP] Missing required dependency: {dep.name} - {dep.error}")
        else:
            logger.info("[STARTUP] OCR system ready - all prerequisites met")
        
        # Log warnings about disabled critical features
        for warning in readiness.warnings:
            logger.warning(f"[STARTUP] {warning}")
    except Exception as e:
        logger.error(f"[STARTUP] Failed to check OCR readiness: {e}")
    
    # Import ocr_service to trigger its version logging
    try:
        from backend.services.ocr_service import _VERSION_ISO as OCR_VERSION
        logger.info(f"[VERSION] ocr_service loaded at {OCR_VERSION}")
    except Exception as e:
        logger.warning(f"[VERSION] Failed to get ocr_service version: {e}")
    
    # Get and log version info
    version_info = get_version_info()
    logger.info(f"[VERSION] {json.dumps(version_info, indent=2)}")


@app.get("/api/debug/version")
def get_version():
    """
    Debug endpoint to query version information.
    Returns version info including git commit, file timestamps, and module load times.
    """
    try:
        version_info = get_version_info()
        return version_info
    except Exception as e:
        logger.exception(f"[VERSION] Error getting version info: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get version info: {str(e)}")


@app.get("/api/documents/recent")
def recent_documents():
    append_audit(datetime.now().isoformat(), "local", "recent_documents", "{}")
    return {"documents": list_recent_documents()}

@app.get("/api/test/path-resolution")
def test_path_resolution():
    """Test endpoint to verify path resolution"""
    from pathlib import Path
    main_file = Path(__file__).resolve()
    backend_dir = main_file.parent
    project_root = backend_dir.parent
    data_uploads = project_root / "data" / "uploads"
    
    sample_folders = []
    if data_uploads.exists():
        sample_folders = [f.name for f in list(data_uploads.glob("*"))[:5]]
    
    return {
        "main_file": str(main_file),
        "backend_dir": str(backend_dir),
        "project_root": str(project_root),
        "data_uploads": str(data_uploads),
        "data_uploads_exists": data_uploads.exists(),
        "sample_folders": sample_folders
    }

@app.get("/api/ocr/page-image/{doc_id}")
def get_page_image(doc_id: str, page: int = Query(1, description="Page number")):
    """
    Serve OCR page images for visual verification.
    Returns the preprocessed page image that was used for OCR.
    """
    import os
    from pathlib import Path
    
    # Use absolute paths to avoid working directory issues
    # Try multiple possible locations
    # Get the directory where main.py is located
    main_file = Path(__file__).resolve()
    backend_dir = main_file.parent  # backend/
    project_root = backend_dir.parent  # project root
    
    possible_uploads_dirs = [
        project_root / "data" / "uploads",  # Most common: project_root/data/uploads
        Path.cwd() / "data" / "uploads",  # Current working directory
        Path("data") / "uploads",  # Relative to CWD
        backend_dir / "data" / "uploads",  # backend/data/uploads
        Path("backend") / "data" / "uploads",  # Relative backend/data/uploads
    ]
    
    doc_folder = None
    checked_paths = []
    logger.info(f"[PAGE_IMAGE] Looking for doc_id={doc_id}")
    logger.info(f"[PAGE_IMAGE] Backend dir: {backend_dir}, Project root: {project_root}")
    
    for uploads_dir in possible_uploads_dirs:
        try:
            uploads_abs = uploads_dir.resolve()
            checked_paths.append(str(uploads_abs))
            logger.info(f"[PAGE_IMAGE] Checking: {uploads_abs} (exists: {uploads_abs.exists()})")
            
            if uploads_abs.exists() and uploads_abs.is_dir():
                # Try to find the document folder
                glob_pattern = f"{doc_id}*"
                logger.info(f"[PAGE_IMAGE] Searching for pattern: {glob_pattern} in {uploads_abs}")
                doc_folders = list(uploads_abs.glob(glob_pattern))
                logger.info(f"[PAGE_IMAGE] Found {len(doc_folders)} matching folders")
                
                if doc_folders:
                    doc_folder = doc_folders[0]
                    logger.info(f"[PAGE_IMAGE] ✅ Found document folder: {doc_folder}")
                    logger.info(f"[PAGE_IMAGE] Searched in: {uploads_abs}")
                    break
                else:
                    # List some folders for debugging
                    all_folders = list(uploads_abs.glob("*"))
                    sample_folders = [f.name for f in all_folders[:5]]
                    logger.debug(f"[PAGE_IMAGE] Sample folders in {uploads_abs}: {sample_folders}")
        except Exception as e:
            logger.error(f"[PAGE_IMAGE] Path check failed for {uploads_dir}: {e}", exc_info=True)
            continue
    
    if not doc_folder:
        # Log all checked paths for debugging
        logger.error(f"[PAGE_IMAGE] Document folder not found for doc_id={doc_id}")
        logger.error(f"[PAGE_IMAGE] Checked paths: {checked_paths}")
        logger.error(f"[PAGE_IMAGE] Backend dir: {backend_dir}, Project root: {project_root}")
        raise HTTPException(
            status_code=404, 
            detail=f"Document folder not found for doc_id={doc_id}. Checked: {', '.join(checked_paths)}"
        )
    
    # Try preprocessed version first (smaller, faster to serve)
    prep_image = doc_folder / "pages" / f"page_{page:03d}.pre.png"
    if prep_image.exists():
        logger.info(f"[PAGE_IMAGE] Serving preprocessed image: {prep_image}")
        return FileResponse(
            path=str(prep_image.resolve()),
            media_type="image/png",
            headers={"Cache-Control": "public, max-age=3600"}
        )
    
    # Fallback to original page image
    page_image = doc_folder / "pages" / f"page_{page:03d}.png"
    if page_image.exists():
        logger.info(f"[PAGE_IMAGE] Serving original image: {page_image}")
        return FileResponse(
            path=str(page_image.resolve()),
            media_type="image/png",
            headers={"Cache-Control": "public, max-age=3600"}
        )
    
    # Neither file exists
    logger.error(f"[PAGE_IMAGE] Page image not found: {page_image} or {prep_image}")
    raise HTTPException(
        status_code=404, 
        detail=f"Page {page} image not found for doc_id={doc_id}. Checked: {page_image}, {prep_image}"
    )

@app.get("/api/debug/last_error")
def last_error():
    append_audit(datetime.now().isoformat(), "local", "last_error", "{}")
    return get_last_error()

@app.get("/api/analytics/price_history")
def price_history(supplier: str = Query(..., min_length=1)):
    """Return price history for a supplier"""
    try:
        con = sqlite3.connect(DB_PATH, check_same_thread=False)
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
        con = sqlite3.connect(DB_PATH, check_same_thread=False)
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
        con = sqlite3.connect(DB_PATH, check_same_thread=False)
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

@app.get("/api/dev/ocr-test")
def ocr_sanity_test(filename: Optional[str] = Query(None), list_uploads: bool = Query(False)):
    """
    Fast OCR + Extraction Test - Tests OCR and dual-extraction without DB/LLM/pairing.
    
    - ?list_uploads=true: List all available files
    - ?filename=xxx.jpeg: Test OCR + extraction on specific file (fast, no DB writes)
    
    This endpoint uses:
    - OCR processing (same as main pipeline)
    - Enterprise dual-extraction (table + line_fallback)
    - Per-page scoring and best method selection
    
    Does NOT use:
    - Database writes
    - LLM calls
    - Pairing/matching logic
    - Full document processing pipeline
    
    Returns in < 5 seconds for typical invoices.
    """
    try:
        import cv2
        import time
        from pathlib import Path
        from backend.ocr.ocr_processor import get_ocr_processor
        import backend.ocr.table_extractor as table_extractor_module
        from backend.ocr.table_extractor import get_table_extractor
        from backend.ocr.owlin_scan_pipeline import preprocess_image
        
        # TRACE: Log which file is actually being imported
        logger.warning(f"[QUANTITY_TRACE] Using table_extractor module at: {table_extractor_module.__file__}")
        
        start_time = time.time()
        print(f"XXXXXXXXXXXXXXXXXXXX [DEBUG_OCR_TEST] /api/dev/ocr-test called for filename={filename} XXXXXXXXXXXXXXXXXXXX")
        logger.error(f"[DEBUG_OCR_TEST] /api/dev/ocr-test called for filename={filename}")
        logger.info(f"[OCR_TEST] Start: filename={filename}, list_uploads={list_uploads}")
        
        # Construct uploads directory path
        project_root = BASE_DIR.parent
        uploads_dir = project_root / "data" / "uploads"
        
        # List uploads mode
        if list_uploads:
            pdf_files = sorted([f.name for f in uploads_dir.glob("*.pdf") if f.is_file()])
            image_files = sorted([
                f.name for f in uploads_dir.glob("*.*") 
                if f.is_file() and f.suffix.lower() in {".jpg", ".jpeg", ".png", ".jpe"}
            ])
            return {
                "status": "ok",
                "available_pdfs": pdf_files,
                "available_images": image_files,
                "total_count": len(pdf_files) + len(image_files),
                "uploads_dir": str(uploads_dir)
            }
        
        # Check filename provided - be explicit about None vs empty string
        if filename is None or (isinstance(filename, str) and filename.strip() == ""):
            pdf_files = sorted([f.name for f in uploads_dir.glob("*.pdf") if f.is_file()])[:5]
            image_files = sorted([
                f.name for f in uploads_dir.glob("*.*") 
                if f.is_file() and f.suffix.lower() in {".jpg", ".jpeg", ".png", ".jpe"}
            ])[:5]
            return {
                "status": "error",
                "error": "No filename provided. Use ?filename=xxx.jpeg or ?list_uploads=true",
                "sample_files": pdf_files + image_files
            }
        
        # Normalize filename (strip whitespace)
        filename = filename.strip()
        
        # Check file exists
        test_file = uploads_dir / filename
        if not test_file.exists():
            return {
                "status": "error",
                "error": f"File '{filename}' not found in uploads directory",
                "filename": filename,
                "uploads_dir": str(uploads_dir)
            }
        
        # Check file type - only support images for fast processing
        file_ext = test_file.suffix.lower()
        is_image = file_ext in {".jpg", ".jpeg", ".png", ".jpe"}
        
        if not is_image:
            return {
                "status": "error",
                "error": f"Image files only for fast test (got: {file_ext}). Use JPG, JPEG, PNG",
                "filename": filename
            }
        
        logger.info(f"[OCR_TEST] Loading image: {test_file.name} (size: {test_file.stat().st_size / 1024:.1f} KB)")
        
        # Load image
        img_bgr = cv2.imread(str(test_file))
        if img_bgr is None:
            return {
                "status": "error",
                "error": f"Failed to load image file: {filename}",
                "filename": filename
            }
        
        # Preprocess image (same as pipeline, but fast path)
        prep_img_path = preprocess_image(test_file, is_original_image=True)
        
        # Get OCR processor and extract full-page OCR result
        processor = get_ocr_processor()
        h, w = img_bgr.shape[:2]
        block_info = {
            "type": "body",
            "bbox": (0, 0, w, h)  # Full image
        }
        
        logger.info(f"[OCR_TEST] Running OCR on full image...")
        ocr_result = processor.process_block(img_bgr, block_info)
        
        # Use enterprise dual extraction method
        extractor = get_table_extractor()
        
        logger.info(f"[OCR_TEST] Running enterprise dual extraction...")
        best_items, debug_info = extractor.extract_best_line_items(
            ocr_result=ocr_result,
            page_index=0,
            base_confidence=ocr_result.confidence if hasattr(ocr_result, 'confidence') else 0.0,
            image=img_bgr
        )
        
        processing_time = time.time() - start_time
        
        # Convert to dict format
        line_items = [item.to_dict() for item in best_items]
        
        # Calculate confidence
        if best_items:
            avg_confidence = sum(item.confidence for item in best_items) / len(best_items)
        else:
            avg_confidence = ocr_result.confidence if hasattr(ocr_result, 'confidence') else 0.0
        
        # PARITY COMPUTATION: Extract totals and compute mismatch metrics
        invoice_subtotal = None
        invoice_vat_total = None
        invoice_grand_total = None
        sum_line_total = 0.0
        total_mismatch_abs = None
        total_mismatch_pct = None
        parity_rating = "unknown"
        parity_detail = "unknown"
        price_coverage = 0.0
        value_coverage = None
        flags = []
        
        try:
            # Helper function to parse currency strings
            def float_safe(value):
                if value is None:
                    return 0.0
                if isinstance(value, (int, float)):
                    return float(value)
                if not isinstance(value, str):
                    return 0.0
                cleaned = value.replace('£', '').replace('$', '').replace('€', '').replace('Â£', '').replace('â‚¬', '').replace(',', '').strip()
                try:
                    return float(cleaned)
                except (ValueError, TypeError):
                    return 0.0
            
            # Helper function to check if total_price is valid
            def _is_valid_total_price(total_price):
                """Check if total_price is valid (numeric, > 0, within sanity bounds)."""
                if total_price is None or total_price == "" or total_price == "0" or total_price == 0:
                    return False
                try:
                    price_val = float_safe(total_price)
                    # Valid if > 0 and within sanity bounds (0 < value <= 100000)
                    return 0 < price_val <= 100000
                except (ValueError, TypeError):
                    return False
            
            # Compute sum_line_total from extracted line items
            for item in best_items:
                total_price = item.total_price if hasattr(item, 'total_price') else None
                if total_price and total_price not in (None, "", "0", 0):
                    price_val = float_safe(total_price)
                    if price_val > 0:
                        sum_line_total += price_val
            
            # Compute price_coverage: count of items with valid total_price / total items
            valid_price_count = 0
            for item in best_items:
                total_price = item.total_price if hasattr(item, 'total_price') else None
                if _is_valid_total_price(total_price):
                    valid_price_count += 1
            price_coverage = valid_price_count / max(len(best_items), 1) if best_items else 0.0
            
            # Extract document totals from OCR text FIRST (needed for value_coverage calculation)
            ocr_text = ocr_result.ocr_text if hasattr(ocr_result, 'ocr_text') else ""
            
            # Extract supplier, invoice number, and customer from OCR text
            supplier = "Unknown Supplier"
            invoice_number = None
            invoice_number_source = "generated"
            customer = None
            
            if ocr_text.strip():
                totals = extractor.extract_document_totals_from_text(ocr_text)
                invoice_subtotal = totals.get("invoice_subtotal")
                invoice_vat_total = totals.get("invoice_vat_total")
                invoice_grand_total = totals.get("invoice_grand_total")
            
            # FIX: Add value_coverage metric - how much of invoice total is explained by line items
            # This helps identify when we have prices but they don't add up to the invoice total
            # value_coverage = sum(total_price for valid rows) / invoice_grand_total
            # Use grand_total if available, else subtotal, else None
            value_coverage = None
            invoice_total_for_coverage = invoice_grand_total if invoice_grand_total is not None and invoice_grand_total > 0 else (invoice_subtotal if invoice_subtotal is not None and invoice_subtotal > 0 else None)
            
            if invoice_total_for_coverage is not None and invoice_total_for_coverage > 0:
                if sum_line_total > 0:
                    value_coverage = sum_line_total / invoice_total_for_coverage
                else:
                    # If invoice total exists but no line items have prices, return 0.0
                    value_coverage = 0.0
            # If invoice_total_for_coverage is None or 0, value_coverage remains None
                
                # Extract supplier and invoice number using ocr_service functions
                try:
                    from backend.services.ocr_service import _extract_supplier_and_customer
                    import re
                    
                    # Extract supplier and customer
                    supplier, customer = _extract_supplier_and_customer(ocr_text, None)
                    
                    # Extract invoice number (similar to ocr_service logic)
                    header_zone_end = int(len(ocr_text.split('\n')) * 0.25)
                    header_text = "\n".join(ocr_text.split('\n')[:header_zone_end])
                    
                    printed_invoice_patterns = [
                        r'\bVAT\s+Invoice\s+([A-Za-z0-9\-\/]+)',  # VAT Invoice 99471 (NEW - high priority)
                        r'invoice\s*#\s*([A-Za-z0-9\-\/]+)',  # "Invoice #77212" - most specific
                        r'invoice\s*no\.?\s*([A-Za-z0-9\-\/]+)',  # "Invoice No. 77212"
                        r'invoice\s*[#:]?\s*([A-Za-z0-9\-\/]+)',  # "Invoice: 77212" or "Invoice 77212"
                        r'#\s*([0-9]{4,})',  # "#77212" standalone
                        r'Invoice\s+(?:No|Number|#)[:.\s]+([A-Z0-9_-]+)',
                        r'Invoice\s+(?:No|Number|#)[:.\s]+([A-Z0-9-]+)',
                        r'Invoice[:\s]+([A-Z]{2,}[-/]?\d+)',
                        r'INVOICE\s+NO\.?\s*([A-Z0-9_-]+)',
                    ]
                    
                    for pattern in printed_invoice_patterns:
                        match = re.search(pattern, header_text, re.IGNORECASE | re.MULTILINE)
                        if match:
                            if match.lastindex and match.lastindex >= 1:
                                candidate = match.group(1).strip()
                            else:
                                candidate = match.group(0).strip()
                            
                            if candidate and not re.match(r'^\d{1,2}[/-]\d{1,2}', candidate):
                                invoice_number = candidate.lstrip('#').strip()
                                invoice_number_source = "printed"
                                logger.info(f"[OCR_TEST] Found printed invoice number: {invoice_number}")
                                break
                    
                    # Fallback: search entire document
                    if invoice_number is None:
                        fallback_patterns = [
                            r'\bVAT\s+Invoice\s+([A-Za-z0-9\-\/]+)',  # VAT Invoice 99471 (fallback if not in header)
                            r'INV[-/]?(\d+)',
                            r'#\s*([A-Z0-9_-]{4,})',
                            r'(?:^|\n)([A-Z]{2,}\d{4,})',
                        ]
                        
                        for pattern in fallback_patterns:
                            match = re.search(pattern, ocr_text, re.IGNORECASE | re.MULTILINE)
                            if match:
                                if match.lastindex and match.lastindex >= 1:
                                    candidate = match.group(1).strip()
                                else:
                                    candidate = match.group(0).strip()
                                
                                if candidate and not re.match(r'^\d{1,2}[/-]\d{1,2}', candidate):
                                    invoice_number = candidate.lstrip('#').strip()
                                    invoice_number_source = "printed"
                                    logger.info(f"[OCR_TEST] Found invoice number via fallback: {invoice_number}")
                                    break
                    
                except Exception as e:
                    logger.warning(f"[OCR_TEST] Failed to extract supplier/invoice_number: {e}", exc_info=True)
            
            # Compute parity metrics if we have both grand total and line items sum
            if invoice_grand_total is not None and invoice_grand_total > 0 and sum_line_total > 0:
                total_mismatch_abs = abs(invoice_grand_total - sum_line_total)
                denom = max(invoice_grand_total, 1.0)
                total_mismatch_pct = total_mismatch_abs / denom
                
                # Determine parity rating
                if total_mismatch_pct < 0.01:  # < 1%
                    parity_rating = "excellent"
                elif total_mismatch_pct < 0.03:  # < 3%
                    parity_rating = "good"
                elif total_mismatch_pct < 0.08:  # < 8%
                    parity_rating = "ok"
                else:  # >= 8%
                    parity_rating = "poor"
                
                # Add flag if poor
                if parity_rating == "poor":
                    flags.append("total_mismatch_high")
                
                # Determine parity_detail based on rating and price_coverage
                # Check price_coverage first (as per plan)
                if price_coverage < 0.3:
                    parity_detail = "low_price_coverage"
                elif parity_rating == "poor":
                    parity_detail = "high_mismatch_despite_good_coverage"
                else:
                    parity_detail = "ok"
                
                logger.info(
                    f"[OCR_TEST] Parity: invoice_total={invoice_grand_total:.2f}, "
                    f"sum_line_items={sum_line_total:.2f}, "
                    f"mismatch={total_mismatch_pct*100:.2f}%, rating={parity_rating}, detail={parity_detail}"
                )
        except Exception as e:
            logger.warning(f"[OCR_TEST] Parity computation failed: {e}", exc_info=True)
        
        # Add price_coverage_low flag if coverage is low (regardless of parity computation)
        if price_coverage < 0.3:
            flags.append("price_coverage_low")
        
        # Extract skipped_lines, items_region_detected, and items_region from debug_info
        skipped_lines_raw = debug_info.get("skipped_lines", [])
        # CRITICAL FIX: Filter out any excessive_quantity skip reasons - they should never appear
        skipped_lines = [s for s in skipped_lines_raw if "excessive_quantity" not in str(s.get("reason", "")).lower()]
        items_region_detected = debug_info.get("items_region_detected", False)
        items_region = debug_info.get("items_region", None)

        logger.error(
            f"[DEBUG_OCR_TEST] building line_items_debug in {__name__} for filename={filename}, "
            f"method_chosen={debug_info.get('method_chosen')}, skipped_lines_count={len(skipped_lines)}"
        )
        
        # Build response
        response = {
            "status": "ok",
            "filename": filename,
            "confidence": avg_confidence,
            "processing_time": round(processing_time, 3),
            "line_items": line_items,
            "line_items_count": len(line_items),
            "line_items_debug": [debug_info],
            "line_items_confidence": avg_confidence,
            "raw_ocr_preview": (ocr_result.ocr_text if hasattr(ocr_result, 'ocr_text') else "")[:500],
            # Supplier and invoice number (use supplier_name/customer_name for consistency)
            "supplier": supplier,
            "supplier_name": supplier,  # Alias for frontend compatibility
            "invoice_number": invoice_number,
            "invoice_number_source": invoice_number_source,
            "customer": customer,
            "customer_name": customer,  # Alias for frontend compatibility
            "bill_to_name": customer,  # Alternative name
            # PARITY: Add totals and parity metrics
            "invoice_subtotal": invoice_subtotal,
            "invoice_vat_total": invoice_vat_total,
            "invoice_grand_total": invoice_grand_total,
            "sum_line_total": sum_line_total,
            "total_mismatch_abs": total_mismatch_abs,
            "total_mismatch_pct": total_mismatch_pct,
            "parity_rating": parity_rating,
            "parity_detail": parity_detail,
            "price_coverage": price_coverage,
            "value_coverage": value_coverage,
            "flags": flags,
            # Debug fields
            "skipped_lines": skipped_lines,
            "debug_skipped": skipped_lines,  # Alias for compatibility
            "items_region_detected": items_region_detected,
            "items_region": items_region
        }
        
        logger.info(f"[OCR_TEST] Complete: {len(line_items)} items, method={debug_info.get('method_chosen')}, time={processing_time:.2f}s")
        
        return response
        
    except Exception as e:
        logger.exception(f"[OCR_TEST] Error: {e}")
        return {
            "status": "error",
            "filename": filename if filename else "unknown",
            "error": f"{type(e).__name__}: {str(e)}"
        }

@app.get("/api/dev/list-uploads")
def list_uploads():
    """
    List all files in data/uploads/ directory.
    
    Returns:
        {
            "status": "ok",
            "count": N,
            "files": ["filename1", "filename2", ...]
        }
    """
    try:
        project_root = BASE_DIR.parent
        uploads_dir = project_root / "data" / "uploads"
        
        if not uploads_dir.exists():
            return {
                "status": "error",
                "error": f"Uploads directory not found: {uploads_dir}"
            }
        
        all_files = sorted([f.name for f in uploads_dir.glob("*.*") if f.is_file()])
        
        return {
            "status": "ok",
            "count": len(all_files),
            "files": all_files
        }
    except Exception as e:
        logger.exception(f"[LIST_UPLOADS] Error: {e}")
        return {
            "status": "error",
            "error": f"{type(e).__name__}: {str(e)}"
        }

@app.get("/api/dev/ocr-raw")
def ocr_raw(filename: str = Query(...)):
    """
    Return raw OCR text without line-item parsing.
    
    Uses the same OCR preprocessor + PaddleOCR text block extraction as ocr-test,
    but no line-item parsing.
    
    Returns:
        {
            "status": "ok",
            "filename": "...",
            "raw_text": "...",
            "preview_lines": [...]
        }
    """
    try:
        import cv2
        from pathlib import Path
        from backend.ocr.ocr_processor import get_ocr_processor
        from backend.ocr.owlin_scan_pipeline import preprocess_image
        
        logger.info(f"[OCR_RAW] Start: filename={filename}")
        
        # Construct uploads directory path
        project_root = BASE_DIR.parent
        uploads_dir = project_root / "data" / "uploads"
        
        # Check file exists
        test_file = uploads_dir / filename
        if not test_file.exists():
            return {
                "status": "error",
                "error": f"File '{filename}' not found in uploads directory",
                "filename": filename,
                "uploads_dir": str(uploads_dir)
            }
        
        # Check file type - support images and PDFs
        file_ext = test_file.suffix.lower()
        is_image = file_ext in {".jpg", ".jpeg", ".png", ".jpe"}
        is_pdf = file_ext == ".pdf"
        
        if not (is_image or is_pdf):
            return {
                "status": "error",
                "error": f"Unsupported file type: {file_ext}. Use JPG, JPEG, PNG, or PDF",
                "filename": filename
            }
        
        logger.info(f"[OCR_RAW] Loading file: {test_file.name} (size: {test_file.stat().st_size / 1024:.1f} KB)")
        
        # For images, load directly
        if is_image:
            img_bgr = cv2.imread(str(test_file))
            if img_bgr is None:
                return {
                    "status": "error",
                    "error": f"Failed to load image file: {filename}",
                    "filename": filename
                }
            
            # Preprocess image
            prep_img_path = preprocess_image(test_file, is_original_image=True)
            
            # Get OCR processor and extract full-page OCR result
            processor = get_ocr_processor()
            h, w = img_bgr.shape[:2]
            block_info = {
                "type": "body",
                "bbox": (0, 0, w, h)  # Full image
            }
            
            logger.info(f"[OCR_RAW] Running OCR on full image...")
            ocr_result = processor.process_block(img_bgr, block_info)
            raw_text = ocr_result.ocr_text if hasattr(ocr_result, 'ocr_text') else ""
        
        else:  # PDF
            # For PDFs, use the same processing as ocr-test but just return raw text
            from backend.ocr.owlin_scan_pipeline import process_document
            
            logger.info(f"[OCR_RAW] Processing PDF...")
            result = process_document(test_file)
            
            # Extract raw text from all pages
            raw_text_parts = []
            for page in result.get("pages", []):
                for block in page.get("blocks", []):
                    if block.get("ocr_text"):
                        raw_text_parts.append(block["ocr_text"])
            raw_text = "\n".join(raw_text_parts)
        
        # Split into lines for preview
        all_lines = raw_text.split('\n')
        preview_lines = all_lines[:20]  # First 20 lines
        
        logger.info(f"[OCR_RAW] Complete: {len(all_lines)} lines, {len(raw_text)} chars")
        
        return {
            "status": "ok",
            "filename": filename,
            "raw_text": raw_text,
            "preview_lines": preview_lines,
            "total_lines": len(all_lines),
            "total_chars": len(raw_text)
        }
        
    except Exception as e:
        logger.exception(f"[OCR_RAW] Error: {e}")
        return {
            "status": "error",
            "filename": filename if filename else "unknown",
            "error": f"{type(e).__name__}: {str(e)}"
        }

@app.get("/api/dev/ocr-lines")
def ocr_lines_debug(filename: str = Query(None)):
    """
    Debug endpoint for line-item table extraction.
    
    - ?filename=xxx.jpeg: Test table extraction on specific file
    
    Returns debug JSON with:
    - rows_raw: Raw row data with cell positions and text
    - parsed_line_items: Current parsed results
    - extraction_method: Which method was used (spatial/semantic/fallback)
    - column_boundaries: Detected column X positions (if spatial method)
    - column_roles: Column role assignments (if spatial method)
    """
    try:
        import cv2
        import numpy as np
        from pathlib import Path
        from backend.ocr.ocr_processor import get_ocr_processor
        from backend.ocr.owlin_scan_pipeline import detect_layout, preprocess_image
        from backend.ocr.table_extractor import extract_table_from_block
        
        logger.info(f"[OCR_LINES] Start: filename={filename}")
        
        # Construct uploads directory path
        project_root = BASE_DIR.parent
        uploads_dir = project_root / "data" / "uploads"
        
        # Check filename provided
        if not filename:
            image_files = sorted([
                f.name for f in uploads_dir.glob("*.*") 
                if f.is_file() and f.suffix.lower() in {".jpg", ".jpeg", ".png", ".jpe"}
            ])[:5]
            return {
                "status": "error",
                "error": "No filename provided. Use ?filename=xxx.jpeg",
                "sample_files": image_files
            }
        
        # Check file exists
        test_file = uploads_dir / filename
        if not test_file.exists():
            return {
                "status": "error",
                "error": f"File '{filename}' not found in uploads directory",
                "filename": filename
            }
        
        # Check file type - only support images
        file_ext = test_file.suffix.lower()
        is_image = file_ext in {".jpg", ".jpeg", ".png", ".jpe"}
        
        if not is_image:
            return {
                "status": "error",
                "error": f"Image files only (got: {file_ext}). Use JPG, JPEG, PNG",
                "filename": filename
            }
        
        logger.info(f"[OCR_LINES] Loading image: {test_file.name}")
        
        # Load image
        img_bgr = cv2.imread(str(test_file))
        if img_bgr is None:
            return {
                "status": "error",
                "error": f"Failed to load image file: {filename}",
                "filename": filename
            }
        
        # Preprocess image (same as pipeline)
        # preprocess_image returns a Path to the preprocessed image
        prep_img_path = preprocess_image(test_file, is_original_image=True)
        
        # Detect layout to find table blocks
        logger.info(f"[OCR_LINES] Detecting layout...")
        blocks_raw = detect_layout(prep_img_path)
        
        # Get OCR processor and extract full-page OCR result
        processor = get_ocr_processor()
        h, w = img_bgr.shape[:2]
        block_info = {
            "type": "body",
            "bbox": (0, 0, w, h)  # Full image
        }
        
        # Get full-page OCR result with word blocks
        ocr_result = processor.process_block(img_bgr, block_info)
        
        # Use enterprise dual extraction method
        from backend.ocr.table_extractor import get_table_extractor
        extractor = get_table_extractor()
        
        logger.info(f"[OCR_LINES] Running enterprise dual extraction...")
        best_items, debug_info = extractor.extract_best_line_items(
            ocr_result=ocr_result,
            page_index=0,
            base_confidence=ocr_result.confidence if hasattr(ocr_result, 'confidence') else 0.0,
            image=img_bgr
        )
        
        # Convert to dict format
        parsed_line_items = [item.to_dict() for item in best_items]
        
        # Build rows_raw for debugging (from OCR text lines)
        rows_raw = []
        ocr_text = ocr_result.ocr_text if hasattr(ocr_result, 'ocr_text') else ""
        lines = [line.strip() for line in ocr_text.splitlines() if line.strip()]
        
        for i, line in enumerate(lines[:50]):  # Limit to first 50 lines
            rows_raw.append({
                "line_index": i,
                "text": line
            })
        
        # Build response with same format as before
        response = {
            "status": "ok",
            "filename": filename,
            "extraction_method": debug_info.get("method_chosen", "unknown"),
            "confidence": sum(item.confidence for item in best_items) / len(best_items) if best_items else 0.0,
            "rows_raw": rows_raw,
            "parsed_line_items": parsed_line_items,
            "total_rows": len(rows_raw),
            "total_line_items": len(parsed_line_items),
            "debug": debug_info
        }
        
        logger.info(f"[OCR_LINES] Done: method={debug_info.get('method_chosen')}, items={len(parsed_line_items)}")
        return response
        
    except Exception as e:
        logger.exception(f"[OCR_LINES] Error: {e}")
        return {
            "status": "error",
            "filename": filename if filename else "unknown",
            "error": f"{type(e).__name__}: {str(e)}"
        }

@app.get("/api/dev/ocr-blocks")
def ocr_blocks_debug(filename: str = Query(None)):
    """
    Debug endpoint to inspect raw OCR blocks (no layout detection).
    
    - ?filename=xxx.jpeg: Show raw OCR blocks from PaddleOCR
    
    Returns raw OCR blocks exactly as PaddleOCR produced them, without
    any layout detection or table extraction. This helps diagnose why
    layout detection might be returning 0 blocks.
    """
    try:
        import cv2
        import numpy as np
        from pathlib import Path
        from backend.ocr.ocr_processor import get_ocr_processor
        
        logger.info(f"[OCR_BLOCKS] Start: filename={filename}")
        
        # Construct uploads directory path
        project_root = BASE_DIR.parent
        uploads_dir = project_root / "data" / "uploads"
        
        # Check filename provided
        if not filename:
            image_files = sorted([
                f.name for f in uploads_dir.glob("*.*") 
                if f.is_file() and f.suffix.lower() in {".jpg", ".jpeg", ".png", ".jpe"}
            ])[:5]
            return {
                "status": "error",
                "error": "No filename provided. Use ?filename=xxx.jpeg",
                "sample_files": image_files
            }
        
        # Check file exists
        test_file = uploads_dir / filename
        if not test_file.exists():
            return {
                "status": "error",
                "error": f"File '{filename}' not found in uploads directory",
                "filename": filename
            }
        
        # Check file type - only support images
        file_ext = test_file.suffix.lower()
        is_image = file_ext in {".jpg", ".jpeg", ".png", ".jpe"}
        
        if not is_image:
            return {
                "status": "error",
                "error": f"Image files only (got: {file_ext}). Use JPG, JPEG, PNG",
                "filename": filename
            }
        
        logger.info(f"[OCR_BLOCKS] Loading image: {test_file.name}")
        
        # Load image
        img_bgr = cv2.imread(str(test_file))
        if img_bgr is None:
            return {
                "status": "error",
                "error": f"Failed to load image file: {filename}",
                "filename": filename
            }
        
        logger.info(f"[OCR_BLOCKS] Image loaded: shape={img_bgr.shape}")
        
        # Get OCR processor
        processor = get_ocr_processor()
        
        # Process full image as single block to get word-level OCR
        h, w = img_bgr.shape[:2]
        block_info = {
            "type": "table",  # Use "table" type to get detailed word blocks
            "bbox": (0, 0, w, h)  # Full image
        }
        
        logger.info(f"[OCR_BLOCKS] Running OCRProcessor with detailed word blocks...")
        ocr_result = processor.process_block(img_bgr, block_info)
        
        # Extract word blocks
        word_blocks = []
        if ocr_result.word_blocks:
            for wb in ocr_result.word_blocks[:200]:  # Limit to first 200 blocks
                if isinstance(wb, dict):
                    bbox = wb.get('bbox', [0, 0, 0, 0])
                    text = wb.get('text', '')
                    conf = wb.get('confidence', 0.0)
                else:
                    bbox = getattr(wb, 'bbox', [0, 0, 0, 0])
                    text = getattr(wb, 'text', '')
                    conf = getattr(wb, 'confidence', 0.0)
                
                # Convert bbox to [x1, y1, x2, y2] format
                # PaddleOCR returns [x, y, w, h] format
                if len(bbox) == 4:
                    # bbox is [x, y, w, h] format from PaddleOCR
                    x, y, w, h = bbox[0], bbox[1], bbox[2], bbox[3]
                    x1, y1 = int(x), int(y)
                    x2, y2 = int(x + w), int(y + h)
                    
                    center_x = (x1 + x2) / 2
                    center_y = (y1 + y2) / 2
                    
                    word_blocks.append({
                        "text": text,
                        "bbox": [x1, y1, x2, y2],
                        "confidence": float(conf) if conf else 0.0,
                        "center_x": int(center_x),
                        "center_y": int(center_y)
                    })
        
        # If no word blocks, try to extract from OCR text (fallback)
        if not word_blocks and ocr_result.ocr_text:
            # Split text into lines and create simple blocks
            lines = ocr_result.ocr_text.split('\n')
            y_pos = 50
            for i, line in enumerate(lines[:50]):  # Limit to 50 lines
                if line.strip():
                    word_blocks.append({
                        "text": line.strip(),
                        "bbox": [50, y_pos, 500, y_pos + 20],
                        "confidence": ocr_result.confidence,
                        "center_x": 275,
                        "center_y": y_pos + 10
                    })
                    y_pos += 30
        
        logger.info(f"[OCR_BLOCKS] Extracted {len(word_blocks)} word blocks")
        
        return {
            "status": "ok",
            "filename": filename,
            "ocr_confidence": ocr_result.confidence,
            "ocr_text_preview": ocr_result.ocr_text[:500] if ocr_result.ocr_text else "",
            "total_blocks": len(word_blocks),
            "blocks": word_blocks,
            "image_shape": {
                "width": w,
                "height": h
            }
        }
        
    except Exception as e:
        logger.exception(f"[OCR_BLOCKS] Error: {e}")
        return {
            "status": "error",
            "filename": filename if filename else "unknown",
            "error": f"{type(e).__name__}: {str(e)}"
        }

@app.get("/api/dev/ocr-quality")
def ocr_quality_test(filename: str = Query(None)):
    """
    Test OCR quality with dual-path preprocessing comparison.
    
    Runs both minimal and enhanced preprocessing paths on an image file,
    compares OCR results, and returns detailed metrics.
    
    Query params:
        filename: Image filename (JPG, JPEG, PNG) in uploads directory
    
    Returns:
        JSON with comparison results:
        - minimal: {avg_confidence, word_count, sample_text}
        - enhanced: {avg_confidence, word_count, sample_text}
        - chosen_path: "minimal" or "enhanced"
        - comparison_metrics: detailed stats
    """
    try:
        import cv2
        from pathlib import Path
        from backend.image_preprocess import compare_preprocessing_paths
        
        # Construct uploads directory path
        project_root = BASE_DIR.parent
        uploads_dir = project_root / "data" / "uploads"
        
        # Check filename provided
        if not filename:
            # List available image files
            image_files = sorted([
                f.name for f in uploads_dir.glob("*.*") 
                if f.is_file() and f.suffix.lower() in {".jpg", ".jpeg", ".png", ".jpe"}
            ])
            return {
                "status": "error",
                "error": "No filename provided. Use ?filename=xxx.jpg",
                "available_images": image_files[:10],
                "hint": f"Try: /api/dev/ocr-quality?filename={image_files[0] if image_files else 'your-image.jpg'}"
            }
        
        # Check file exists
        test_file = uploads_dir / filename
        if not test_file.exists():
            image_files = sorted([
                f.name for f in uploads_dir.glob("*.*") 
                if f.is_file() and f.suffix.lower() in {".jpg", ".jpeg", ".png", ".jpe"}
            ])
            return {
                "status": "error",
                "error": f"File '{filename}' not found in uploads directory",
                "available_images": image_files[:10],
                "uploads_dir": str(uploads_dir),
                "hint": "Use ?filename=xxx.jpg to test a specific image"
            }
        
        # Check it's an image file
        if test_file.suffix.lower() not in {".jpg", ".jpeg", ".png", ".jpe"}:
            return {
                "status": "error",
                "error": f"File '{filename}' is not an image file (expected JPG, JPEG, PNG)",
                "file_extension": test_file.suffix
            }
        
        logger.info(f"[OCR_QUALITY] Testing preprocessing paths for: {test_file.name}")
        
        # Load image
        img_bgr = cv2.imread(str(test_file))
        if img_bgr is None:
            return {
                "status": "error",
                "error": f"Failed to load image file: {filename}"
            }
        
        logger.info(f"[OCR_QUALITY] Loaded image: shape={img_bgr.shape}, dtype={img_bgr.dtype}, size={img_bgr.size} bytes")
        
        # Quick test: Try OCR on original image to verify PaddleOCR works
        try:
            from backend.image_preprocess import _run_ocr_on_image
            logger.info("[OCR_QUALITY] Testing OCR on original image (no preprocessing)...")
            orig_text, orig_conf, orig_words, _ = _run_ocr_on_image(img_bgr)
            logger.info(f"[OCR_QUALITY] Original image OCR test: {orig_words} words, confidence: {orig_conf:.3f}")
        except Exception as e:
            logger.warning(f"[OCR_QUALITY] Original image OCR test failed: {e}")
        
        # Run dual-path comparison
        comparison = compare_preprocessing_paths(img_bgr)
        
        # Format response - include diagnostic info
        minimal_data = comparison.get("minimal", {})
        enhanced_data = comparison.get("enhanced", {})
        
        result = {
            "status": "ok",
            "filename": filename,
            "minimal": {
                "avg_confidence": minimal_data.get("avg_confidence", 0.0),
                "word_count": minimal_data.get("word_count", 0),
                "sample_text": minimal_data.get("sample_text", ""),
                "error": minimal_data.get("error"),
                "image_shape": minimal_data.get("image_shape"),
                "image_dtype": minimal_data.get("image_dtype")
            },
            "enhanced": {
                "avg_confidence": enhanced_data.get("avg_confidence", 0.0),
                "word_count": enhanced_data.get("word_count", 0),
                "sample_text": enhanced_data.get("sample_text", ""),
                "error": enhanced_data.get("error"),
                "image_shape": enhanced_data.get("image_shape"),
                "image_dtype": enhanced_data.get("image_dtype")
            },
            "chosen_path": comparison.get("chosen_path", "enhanced"),
            "comparison_metrics": comparison.get("comparison_metrics", {}),
            "errors": comparison.get("errors", []),
            "diagnostics": {
                "original_image_shape": list(img_bgr.shape) if img_bgr is not None else None,
                "original_image_dtype": str(img_bgr.dtype) if img_bgr is not None else None
            }
        }
        
        logger.info(
            f"[OCR_QUALITY] Comparison complete: chosen={result['chosen_path']}, "
            f"minimal_conf={result['minimal']['avg_confidence']:.3f}, "
            f"enhanced_conf={result['enhanced']['avg_confidence']:.3f}"
        )
        
        return result
        
    except Exception as e:
        logger.exception(f"[OCR_QUALITY] Error: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

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
    
    # Serve index.html for all SPA routes
    spa_file = BASE_DIR / "static" / "index.html"
    
    if spa_file.exists() and spa_file.is_file():
        return FileResponse(
            str(spa_file),
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    
    raise HTTPException(status_code=404, detail="Not found")

# Log that SPA routes are registered
logger.info("[STATIC] SPA fallback route registered at /{full_path:path}")





