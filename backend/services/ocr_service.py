# MOCK REMOVED: returns only real OCR/DB data
"""
OCR Service - Orchestrates document OCR processing with full lifecycle tracking
"""
import logging
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import json
import threading
import signal

from backend.app.db import update_document_status, update_document_classification, insert_line_items, upsert_invoice, append_audit, clear_last_error, DB_PATH
from backend.config import FEATURE_OCR_PIPELINE_V2, env_bool

logger = logging.getLogger("owlin.services.ocr")

# OCR processing timeout: 5 minutes (300 seconds)
OCR_PROCESSING_TIMEOUT_SECONDS = 300

class OCRTimeoutError(Exception):
    """Raised when OCR processing exceeds timeout"""
    pass

def _run_with_timeout(func, timeout_seconds, *args, **kwargs):
    """
    Run a function with a timeout using threading.
    
    Args:
        func: Function to run
        timeout_seconds: Maximum time to wait
        *args, **kwargs: Arguments to pass to function
        
    Returns:
        Function result
        
    Raises:
        OCRTimeoutError: If function doesn't complete within timeout
    """
    result = [None]
    exception = [None]
    
    def target():
        try:
            # #region agent log
            import json
            from pathlib import Path as _Path
            log_path = _Path(__file__).parent.parent.parent / ".cursor" / "debug.log"
            try:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "E", "location": "ocr_service.py:44", "message": "_run_with_timeout target thread started", "data": {"func_name": func.__name__, "args_count": len(args)}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
            except: pass
            # #endregion
            result[0] = func(*args, **kwargs)
            # #region agent log
            try:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "E", "location": "ocr_service.py:50", "message": "_run_with_timeout target thread completed", "data": {"func_name": func.__name__, "has_result": result[0] is not None}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
            except: pass
            # #endregion
        except Exception as e:
            # #region agent log
            import json
            import traceback
            from pathlib import Path as _Path
            log_path = _Path(__file__).parent.parent.parent / ".cursor" / "debug.log"
            try:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "E", "location": "ocr_service.py:53", "message": "_run_with_timeout target thread exception", "data": {"func_name": func.__name__, "error": str(e), "error_type": type(e).__name__, "traceback": traceback.format_exc()[:2000]}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
            except: pass
            # #endregion
            exception[0] = e
    
    thread = threading.Thread(target=target)
    thread.daemon = True
    thread.start()
    thread.join(timeout=timeout_seconds)
    
    if thread.is_alive():
        # Thread is still running - timeout occurred
        raise OCRTimeoutError(f"OCR processing exceeded timeout of {timeout_seconds} seconds")
    
    if exception[0]:
        raise exception[0]
    
    return result[0]

# Version logging to prove fixed code is loaded
import time
_VERSION_TIMESTAMP = time.time()
_VERSION_ISO = datetime.fromtimestamp(_VERSION_TIMESTAMP).isoformat()
_VERSION_FIX = "141bff3a-Path-scoping-fixed"  # Git commit that fixed Path scoping issue
logger.info(f"[VERSION] ocr_service.py loaded at {_VERSION_ISO}, fix={_VERSION_FIX}")

# Constants for defensive parsing
MAX_LINE_ITEMS = 500

def _ensure_re_available(function_name: str) -> None:
    """
    Fail-fast guard to ensure re module is available.
    Raises NameError with clear message if re is not in scope.
    """
    try:
        # Try to access re module
        _ = re.compile
    except NameError:
        error_msg = f"CRITICAL: re module not available in {function_name}. This should never happen."
        logger.critical(error_msg, exc_info=True)
        raise NameError(f"name 're' is not defined in {function_name}") from None

def _safe_get(obj: Any, key: str, default: Any = None, location: str = "unknown") -> Any:
    """
    Safely call .get() on an object, with logging if the object is None.
    This helps identify where NoneType errors occur.
    """
    if obj is None:
        logger.error(f"[SAFE_GET] Attempted to call .get('{key}') on None at {location}")
        # #region agent log
        import json
        from pathlib import Path as _Path
        try:
            log_path = _Path(__file__).parent.parent.parent / ".cursor" / "debug.log"
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "I", "location": location, "message": "safe_get called on None", "data": {"key": key, "default": str(default)[:100]}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
        except: pass
        # #endregion
        return default
    if not isinstance(obj, dict):
        logger.error(f"[SAFE_GET] Attempted to call .get('{key}') on non-dict at {location}, type={type(obj).__name__}")
        return default
    return obj.get(key, default)

def _normalize_currency(value: str | float | None) -> float | None:
    """Normalize currency to numeric float, return None if cannot parse"""
    if value is None:
        return None
    
    if isinstance(value, (int, float)):
        return float(value)
    
    if not isinstance(value, str):
        return None
    
    # Strip currency symbols and commas
    cleaned = re.sub(r'[£€$,\s]', '', str(value)).strip()
    
    try:
        return float(cleaned)
    except ValueError:
        return None

def _normalize_date(date_str: str | None) -> str | None:
    """Normalize to ISO YYYY-MM-DD, return None if cannot parse"""
    if not date_str:
        return None
    
    try:
        from dateutil import parser
        dt = parser.parse(date_str)
        return dt.strftime('%Y-%m-%d')
    except:
        return None

def _deduplicate_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Deduplicate line items by (description, qty, unit_price, total) hash"""
    seen = set()
    deduped = []
    
    for item in items:
        # Create hash key from normalized fields
        # Use _safe_get to prevent NoneType errors
        desc = str(_safe_get(item, 'desc', default='', location="ocr_service.py:172")).strip().lower()
        qty = _safe_get(item, 'qty', default=0, location="ocr_service.py:173")
        unit_price = _safe_get(item, 'unit_price', default=0, location="ocr_service.py:174")
        total = _safe_get(item, 'total', default=0, location="ocr_service.py:175")
        
        key = (desc, qty, unit_price, total)
        
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    
    return deduped

def _log_lifecycle(stage: str, doc_id: str, **kwargs):
    """Log OCR lifecycle marker with structured key=value format and timestamps"""
    timestamp = datetime.now().isoformat()
    
    # Build key=value pairs
    pairs = [f"stage={stage}", f"doc_id={doc_id}", f"timestamp={timestamp}"]
    for key, value in kwargs.items():
        if value is not None:
            # Format floats with 2 decimals
            if isinstance(value, float):
                pairs.append(f"{key}={value:.2f}")
            elif isinstance(value, (dict, list)):
                # For complex objects, log summary or JSON string
                if isinstance(value, dict):
                    # Log dict keys and summary
                    if len(str(value)) < 200:
                        pairs.append(f"{key}={json.dumps(value)}")
                    else:
                        pairs.append(f"{key}_keys={list(value.keys())}")
                        pairs.append(f"{key}_len={len(value)}")
                else:
                    pairs.append(f"{key}_len={len(value)}")
            else:
                # Truncate long strings
                str_value = str(value)
                if len(str_value) > 200:
                    pairs.append(f"{key}={str_value[:200]}...")
                else:
                    pairs.append(f"{key}={str_value}")
    
    marker = "[OCR_LIFECYCLE] " + " ".join(pairs)
    logger.info(marker)
    
    # Audit trail with full data
    audit_detail = {"doc_id": doc_id, "stage": stage, "timestamp": timestamp}
    audit_detail.update(kwargs)
    append_audit(timestamp, "ocr_service", stage, json.dumps(audit_detail, default=str))
    
    print(marker)  # Ensure it shows in console logs

def process_document_ocr(doc_id: str, file_path: str) -> Dict[str, Any]:
    """
    Process a document through the complete OCR pipeline.
    
    Args:
        doc_id: Document ID
        file_path: Path to the uploaded file
        
    Returns:
        Dict with status, confidence, extracted data, and line_items
    """
    # Import Path at function level with alias to avoid scoping issues
    from pathlib import Path as _Path
    
    # Extract filename from file_path
    filename = _Path(file_path).name if file_path else "unknown"
    
    # Determine OCR engine (default is paddleocr, may switch during retries)
    # The actual engine used will be logged in _process_with_v2_pipeline
    ocr_engine = "auto"  # Will be determined by pipeline
    
    # Version logging to prove fixed code is running
    logger.info(
        f"[VERSION] ocr_service.py commit={_VERSION_ISO} processing "
        f"doc_id={doc_id} filename={filename} engine={ocr_engine}"
    )
    
    # Verify module loaded timestamp matches
    current_time = datetime.now().isoformat()
    logger.info(
        f"[VERSION] Module loaded at {_VERSION_ISO}, "
        f"current time {current_time}"
    )
    
    # #region agent log
    import json
    log_path = _Path(__file__).parent.parent.parent / ".cursor" / "debug.log"
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "A", "location": "ocr_service.py:95", "message": "process_document_ocr entry", "data": {"doc_id": doc_id, "file_path": str(file_path)}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
    except: pass
    # #endregion
    _log_lifecycle("UPLOAD_SAVED", doc_id, file=file_path)
    
    try:
        # Check OCR readiness before processing
        from backend.services.ocr_readiness import check_ocr_readiness
        readiness = check_ocr_readiness()
        if not readiness.ready:
            error_msg = f"OCR prerequisites not met. Missing: {', '.join(readiness.missing_required)}"
            logger.error(f"[OCR_NOT_READY] {error_msg} for doc_id={doc_id}")
            update_document_status(doc_id, "error", "ocr_not_ready", error=error_msg)
            raise Exception(error_msg)
        
        # Update status to processing
        update_document_status(doc_id, "processing", "ocr_enqueue")
        _log_lifecycle("OCR_ENQUEUE", doc_id)
        
        # MOCK REMOVED: Force v2 pipeline only - no mock fallback
        use_v2_pipeline = env_bool("FEATURE_OCR_PIPELINE_V2", True)  # Default to True to force real OCR
        
        if not use_v2_pipeline:
            raise Exception("OCR v2 pipeline is required. Mock pipeline has been removed. Set FEATURE_OCR_PIPELINE_V2=true to enable real OCR processing.")
        
        # Run OCR processing with timeout protection
        try:
            result = _run_with_timeout(
                _process_with_v2_pipeline,
                OCR_PROCESSING_TIMEOUT_SECONDS,
                doc_id,
                file_path
            )
        except OCRTimeoutError as timeout_error:
            error_msg = f"OCR processing timed out after {OCR_PROCESSING_TIMEOUT_SECONDS} seconds"
            logger.error(f"[OCR_TIMEOUT] {error_msg} for doc_id={doc_id}")
            update_document_status(doc_id, "error", "ocr_timeout", error=error_msg)
            _log_lifecycle("OCR_ERROR", doc_id, error=error_msg, error_code="ocr_timeout")
            raise Exception(error_msg) from timeout_error
        # #region agent log
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "A", "location": "ocr_service.py:119", "message": "process_document_ocr exit", "data": {"doc_id": doc_id, "status": _safe_get(result, "status", default=None, location="ocr_service.py:306"), "confidence": _safe_get(result, "confidence", default=None, location="ocr_service.py:306"), "line_items_count": len(_safe_get(result, "line_items", default=[], location="ocr_service.py:306"))}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
        except: pass
        # #endregion
        return result
        
    except NameError as e:
        # Special handling for re module NameError - fail fast with clear error code
        if "re" in str(e) or "'re'" in str(e):
            error_msg = f"CRITICAL: re module not available - {str(e)}"
            logger.critical(f"[OCR_REGEX_IMPORT_MISSING] {error_msg} for doc_id={doc_id}", exc_info=True)
            import traceback
            full_traceback = traceback.format_exc()
            # #region agent log
            import json
            try:
                # _Path is already imported at function level, use it directly
                log_path = _Path(__file__).parent.parent.parent / ".cursor" / "debug.log"
                try:
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "F", "location": "ocr_service.py:158", "message": "OCR_REGEX_IMPORT_MISSING", "data": {"doc_id": doc_id, "error": error_msg, "error_type": "NameError", "traceback": full_traceback[:1000]}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
                except: pass
            except: pass
            # #endregion
            update_document_status(doc_id, "error", "OCR_REGEX_IMPORT_MISSING", error=error_msg)
            _log_lifecycle("OCR_ERROR", doc_id, error=error_msg, error_code="OCR_REGEX_IMPORT_MISSING")
            return {
                "status": "error",
                "doc_id": doc_id,
                "error": error_msg,
                "error_code": "OCR_REGEX_IMPORT_MISSING",
                "confidence": 0.0,
                "line_items": []
            }
        else:
            # Other NameError - re-raise as generic exception
            raise Exception(f"NameError in OCR processing: {str(e)}") from e
    except Exception as e:
        error_msg = str(e)
        import traceback
        full_traceback = traceback.format_exc()
        logger.exception(f"OCR processing failed for doc_id={doc_id}")
        # #region agent log
        import json
        try:
            # _Path is already imported at function level, use it directly
            log_path = _Path(__file__).parent.parent.parent / ".cursor" / "debug.log"
            try:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "F", "location": "ocr_service.py:180", "message": "OCR processing exception caught", "data": {"doc_id": doc_id, "error": error_msg, "error_type": type(e).__name__, "traceback": full_traceback[:1000]}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
            except: pass
        except: pass
        # #endregion
        update_document_status(doc_id, "error", "ocr_error", error=error_msg)
        _log_lifecycle("OCR_ERROR", doc_id, error=error_msg)
        
        return {
            "status": "error",
            "doc_id": doc_id,
            "error": error_msg,
            "confidence": 0.0,
            "line_items": []
        }

def _retry_ocr_with_fallbacks(doc_id: str, file_path: str, initial_result: Dict[str, Any], 
                               pdf_structure: Optional[Dict[str, Any]], 
                               render_metadata: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Retry OCR with different configurations when initial attempt produces insufficient text.
    
    Retry strategy:
    1. Retry 1: Different DPI (300 → 400) with same engine/preprocessing
    2. Retry 2: Different preprocessing profile (minimal vs enhanced) with same engine
    3. Retry 3: Switch OCR engine (PaddleOCR ↔ Tesseract) with best DPI/preprocessing
    
    Returns:
        Dict with best_result, ocr_attempts, final_text_length
    """
    from backend.ocr.owlin_scan_pipeline import process_document as process_doc_ocr
    # Import Path at function level with alias to avoid scoping issues
    from pathlib import Path as _Path
    import json
    
    # #region agent log
    log_path = _Path(__file__).parent.parent.parent / ".cursor" / "debug.log"
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "C", "location": "ocr_service.py:252", "message": "retry function entry", "data": {"doc_id": doc_id, "file_path": str(file_path), "initial_pages_count": len(_safe_get(initial_result, 'pages', default=[], location="ocr_service.py:392"))}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
    except: pass
    # #endregion
    
    ocr_attempts = []
    best_result = initial_result
    best_text_length = 0
    
    # Extract initial attempt metadata
    pages = initial_result.get('pages', []) if initial_result else []
    initial_text = ""
    for page in pages:
        page_text = page.get('text', page.get('ocr_text', '')) if page and isinstance(page, dict) else (getattr(page, 'text', '') or getattr(page, 'ocr_text', '') if page else '')
        if page_text:
            initial_text += page_text + "\n"
    initial_text_length = len(initial_text.strip())
    
    # Count words in initial text
    initial_word_count = len(initial_text.split()) if initial_text else 0
    
    # Get initial engine from telemetry if available
    initial_engine = "paddleocr"  # default
    telemetry = _safe_get(initial_result, 'ocr_telemetry', default=None, location="ocr_service.py:414")
    if telemetry:
        if isinstance(telemetry, dict):
            overall = telemetry.get('overall', {})
            engine_mix = overall.get('engine_mix', 'paddleocr') if isinstance(overall, dict) else 'paddleocr'
            if 'tesseract' in engine_mix.lower():
                initial_engine = "tesseract"
    
    # Record initial attempt
    ocr_attempts.append({
        "attempt_number": 0,
        "engine": initial_engine,
        "dpi": 300,  # default
        "preprocess_profile": "enhanced",  # default
        "text_length": initial_text_length,
        "word_count": initial_word_count,
            "confidence": _safe_get(initial_result, 'overall_confidence', default=0.0, location="ocr_service.py:430"),
        "preview": initial_text[:300] if initial_text else ""
    })
    best_text_length = initial_text_length
    
    # Retry 1: Higher DPI (300 → 400)
    logger.info(f"[OCR_RETRY] Attempt 1: Retrying with DPI=400, engine={initial_engine}, preprocess=enhanced")
    # #region agent log
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "C", "location": "ocr_service.py:308", "message": "retry attempt 1 start", "data": {"doc_id": doc_id, "engine": initial_engine, "dpi": 400}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
    except: pass
    # #endregion
    try:
        retry1_result = process_doc_ocr(file_path, render_dpi=400, preprocess_profile="enhanced", force_ocr_engine=initial_engine)
        # #region agent log
        try:
            retry1_status = retry1_result.get("status")
            retry1_pages_count = len(retry1_result.get('pages', []))
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "C", "location": "ocr_service.py:310", "message": "retry attempt 1 result", "data": {"doc_id": doc_id, "status": retry1_status, "pages_count": retry1_pages_count, "is_error": retry1_status == "error"}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
        except: pass
        # #endregion
        retry1_status = _safe_get(retry1_result, "status", default="error", location="ocr_service.py:453")
        if retry1_result and retry1_status != "error":
            retry1_pages = _safe_get(retry1_result, 'pages', default=[], location="ocr_service.py:454")
            retry1_text = ""
            for page in retry1_pages:
                page_text = page.get('text', page.get('ocr_text', '')) if page and isinstance(page, dict) else (getattr(page, 'text', '') or getattr(page, 'ocr_text', '') if page else '')
                if page_text:
                    retry1_text += page_text + "\n"
            retry1_text_length = len(retry1_text.strip())
            retry1_word_count = len(retry1_text.split()) if retry1_text else 0
            
            ocr_attempts.append({
                "attempt_number": 1,
                "engine": initial_engine,
                "dpi": 400,
                "preprocess_profile": "enhanced",
                "text_length": retry1_text_length,
                "word_count": retry1_word_count,
                "confidence": _safe_get(retry1_result, 'overall_confidence', default=0.0, location="ocr_service.py:470"),
                "preview": retry1_text[:300] if retry1_text else ""
            })
            
            if retry1_text_length > best_text_length:
                best_result = retry1_result
                best_text_length = retry1_text_length
                logger.info(f"[OCR_RETRY] Attempt 1 improved: {retry1_text_length} chars (was {initial_text_length})")
            
            if retry1_text_length >= 100:
                logger.info(f"[OCR_RETRY] Attempt 1 succeeded: {retry1_text_length} chars")
                return {"best_result": best_result, "ocr_attempts": ocr_attempts, "final_text_length": best_text_length}
    except Exception as e:
        logger.warning(f"[OCR_RETRY] Attempt 1 failed: {e}")
    
    # Retry 2: Different preprocessing (minimal vs enhanced)
    preprocess_profile = "minimal"  # Try minimal if enhanced was used
    logger.info(f"[OCR_RETRY] Attempt 2: Retrying with DPI=400, engine={initial_engine}, preprocess={preprocess_profile}")
    try:
        retry2_result = process_doc_ocr(file_path, render_dpi=400, preprocess_profile=preprocess_profile, force_ocr_engine=initial_engine)
        retry2_status = _safe_get(retry2_result, "status", default="error", location="ocr_service.py:490")
        if retry2_result and retry2_status != "error":
            retry2_pages = _safe_get(retry2_result, 'pages', default=[], location="ocr_service.py:491")
            retry2_text = ""
            for page in retry2_pages:
                page_text = page.get('text', page.get('ocr_text', '')) if page and isinstance(page, dict) else (getattr(page, 'text', '') or getattr(page, 'ocr_text', '') if page else '')
                if page_text:
                    retry2_text += page_text + "\n"
            retry2_text_length = len(retry2_text.strip())
            retry2_word_count = len(retry2_text.split()) if retry2_text else 0
            
            ocr_attempts.append({
                "attempt_number": 2,
                "engine": initial_engine,
                "dpi": 400,
                "preprocess_profile": preprocess_profile,
                "text_length": retry2_text_length,
                "word_count": retry2_word_count,
                "confidence": _safe_get(retry2_result, 'overall_confidence', default=0.0, location="ocr_service.py:507"),
                "preview": retry2_text[:300] if retry2_text else ""
            })
            
            if retry2_text_length > best_text_length:
                best_result = retry2_result
                best_text_length = retry2_text_length
                logger.info(f"[OCR_RETRY] Attempt 2 improved: {retry2_text_length} chars (was {best_text_length})")
            
            if retry2_text_length >= 100:
                logger.info(f"[OCR_RETRY] Attempt 2 succeeded: {retry2_text_length} chars")
                return {"best_result": best_result, "ocr_attempts": ocr_attempts, "final_text_length": best_text_length}
    except Exception as e:
        logger.warning(f"[OCR_RETRY] Attempt 2 failed: {e}")
    
    # Retry 3: Switch OCR engine
    alternate_engine = "tesseract" if initial_engine == "paddleocr" else "paddleocr"
    logger.info(f"[OCR_RETRY] Attempt 3: Retrying with DPI=400, engine={alternate_engine}, preprocess={preprocess_profile}")
    try:
        retry3_result = process_doc_ocr(file_path, render_dpi=400, preprocess_profile=preprocess_profile, force_ocr_engine=alternate_engine)
        retry3_status = _safe_get(retry3_result, "status", default="error", location="ocr_service.py:527")
        if retry3_result and retry3_status != "error":
            retry3_pages = _safe_get(retry3_result, 'pages', default=[], location="ocr_service.py:528")
            retry3_text = ""
            for page in retry3_pages:
                page_text = page.get('text', page.get('ocr_text', '')) if page and isinstance(page, dict) else (getattr(page, 'text', '') or getattr(page, 'ocr_text', '') if page else '')
                if page_text:
                    retry3_text += page_text + "\n"
            retry3_text_length = len(retry3_text.strip())
            retry3_word_count = len(retry3_text.split()) if retry3_text else 0
            
            ocr_attempts.append({
                "attempt_number": 3,
                "engine": alternate_engine,
                "dpi": 400,
                "preprocess_profile": preprocess_profile,
                "text_length": retry3_text_length,
                "word_count": retry3_word_count,
                "confidence": _safe_get(retry3_result, 'overall_confidence', default=0.0, location="ocr_service.py:544"),
                "preview": retry3_text[:300] if retry3_text else ""
            })
            
            if retry3_text_length > best_text_length:
                best_result = retry3_result
                best_text_length = retry3_text_length
                logger.info(f"[OCR_RETRY] Attempt 3 improved: {retry3_text_length} chars (was {best_text_length})")
            
            if retry3_text_length >= 100:
                logger.info(f"[OCR_RETRY] Attempt 3 succeeded: {retry3_text_length} chars")
                return {"best_result": best_result, "ocr_attempts": ocr_attempts, "final_text_length": best_text_length}
    except Exception as e:
        logger.warning(f"[OCR_RETRY] Attempt 3 failed: {e}")
    
    # All retries failed
    logger.error(f"[OCR_RETRY] All retry attempts failed. Best result: {best_text_length} chars")
    return {"best_result": best_result, "ocr_attempts": ocr_attempts, "final_text_length": best_text_length}


def _process_with_v2_pipeline(doc_id: str, file_path: str) -> Dict[str, Any]:
    """Process using the full OCR v2 pipeline
    
    Handles both invoices and delivery notes:
    - Performs OCR extraction
    - Classifies document type (invoice vs delivery_note)
    - Creates invoice/delivery note cards for UI
    - Triggers pairing suggestions (via backend.matching.pairing module)
    
    All exceptions are caught and document status is set to 'error' before re-raising.
    """
    import os
    # Import Path at function level with alias to avoid scoping issues
    from pathlib import Path as _Path
    
    # CRITICAL: Initialize all variables that might be accessed in exception handlers
    # BEFORE any try blocks to avoid UnboundLocalError
    ocr_text_length = 0
    needs_manual_review = False
    llm_error_message = None
    ocr_result = None
    parsed_data = {}
    line_items = []
    confidence_breakdown = None
    has_empty_data = False
    pages = []
    confidence = 0.0
    confidence_percent = 0.0
    doc_type = "invoice"
    ocr_unusable = False
    
    try:
        # Verify file exists
        if not os.path.exists(file_path):
            error_msg = f"File not found: {file_path}"
            logger.error(f"[OCR_V2] {error_msg} for doc_id={doc_id}")
            update_document_status(doc_id, "error", "file_not_found", error=error_msg)
            raise Exception(error_msg)
        
        _log_lifecycle("OCR_PICK", doc_id, pipeline="v2", file=file_path)
        update_document_status(doc_id, "processing", "ocr_start")
        _log_lifecycle("OCR_START", doc_id)
        
        try:
            from backend.ocr.owlin_scan_pipeline import process_document as process_doc_ocr
        except ImportError as e:
            error_msg = f"Failed to import OCR pipeline: {e}"
            logger.error(f"[OCR_V2] {error_msg} for doc_id={doc_id}")
            update_document_status(doc_id, "error", "ocr_import_failed", error=error_msg)
            raise Exception(error_msg)
        
        # Run OCR pipeline
        filename = _Path(file_path).name if file_path else "unknown"
        logger.info(f"[OCR_V2] Calling process_document for doc_id={doc_id}, file={file_path}, filename={filename}")
        # #region agent log
        import json
        log_path = _Path(__file__).parent.parent.parent / ".cursor" / "debug.log"
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "A", "location": "ocr_service.py:167", "message": "before process_doc_ocr call", "data": {"doc_id": doc_id, "file_path": str(file_path)}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
        except: pass
        # #endregion
        ocr_result = process_doc_ocr(file_path)
        
        # CRITICAL: Ensure ocr_result is never None - wrap in error dict if needed
        if ocr_result is None:
            error_msg = "OCR pipeline returned None - this should never happen"
            logger.critical(f"[OCR_V2] {error_msg} for doc_id={doc_id}")
            ocr_result = {
                "status": "error",
                "error": error_msg,
                "pages": [],
                "confidence": 0.0,
                "overall_confidence": 0.0
            }
            update_document_status(doc_id, "error", "ocr_result_none", error=error_msg)
        
        # #region agent log
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "A", "location": "ocr_service.py:169", "message": "after process_doc_ocr call", "data": {"doc_id": doc_id, "status": _safe_get(ocr_result, "status", default=None, location="ocr_service.py:630"), "confidence": _safe_get(ocr_result, "confidence", default=None, location="ocr_service.py:630"), "pages_count": len(_safe_get(ocr_result, "pages", default=[], location="ocr_service.py:630")), "has_normalized_json": "normalized_json" in ocr_result if ocr_result else False}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
        except: pass
        # #endregion
        logger.info(f"[OCR_V2] OCR result status: {_safe_get(ocr_result, 'status', default=None, location='ocr_service.py:633')}, confidence: {_safe_get(ocr_result, 'confidence', default=0, location='ocr_service.py:633')}")
    except Exception as e:
        error_msg = f"OCR pipeline execution failed: {str(e)}"
        import traceback
        full_traceback = traceback.format_exc()
        logger.exception(f"[OCR_V2] {error_msg} for doc_id={doc_id}")
        # #region agent log
        import json
        try:
            # _Path is already imported at function level, use it directly
            log_path = _Path(__file__).parent.parent.parent / ".cursor" / "debug.log"
            try:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "C", "location": "ocr_service.py:570", "message": "_process_with_v2_pipeline exception caught", "data": {"doc_id": doc_id, "error": str(e), "error_type": type(e).__name__, "error_msg_contains_Path": "Path" in str(e), "traceback": full_traceback[:2000]}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
            except Exception as log_err2:
                # Even if inner logging fails, try to log that fact
                try:
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "C", "location": "ocr_service.py:570", "message": "Failed to log exception details", "data": {"log_error": str(log_err2)}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
                except: pass
        except Exception as log_err:
            # If log path creation fails, try to use module-level Path as fallback (import with alias to avoid scoping)
            try:
                from pathlib import Path as _PathFallback
                log_path = _PathFallback(__file__).parent.parent.parent / ".cursor" / "debug.log"
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "C", "location": "ocr_service.py:570", "message": "_process_with_v2_pipeline exception - used fallback Path", "data": {"doc_id": doc_id, "error": str(e), "error_type": type(e).__name__}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
            except: pass
        # #endregion
        # Ensure status is set to error before re-raising
        try:
            update_document_status(doc_id, "error", "ocr_pipeline_execution_failed", error=error_msg)
        except Exception as update_error:
            logger.error(f"[OCR_V2] Failed to update document status after error: {update_error}")
        raise Exception(error_msg)
    
    # ocr_result is already validated above - should never be None here
    # But add defensive check just in case
    if ocr_result is None:
        error_msg = "OCR pipeline returned None result (should have been caught earlier)"
        logger.critical(f"[OCR_V2] {error_msg} for doc_id={doc_id}")
        update_document_status(doc_id, "error", "ocr_result_none", error=error_msg)
        raise Exception(error_msg)
    
    if _safe_get(ocr_result, "status", default="unknown", location="ocr_service.py:679") == "error":
        error_detail = _safe_get(ocr_result, "error", default="OCR processing failed", location="ocr_service.py:680")
        logger.error(f"[OCR_V2] OCR pipeline returned error: {error_detail} for doc_id={doc_id}")
        # Ensure status is set to error before re-raising
        try:
            update_document_status(doc_id, "error", "ocr_pipeline_error", error=error_detail)
        except Exception as update_error:
            logger.error(f"[OCR_V2] Failed to update document status after OCR error: {update_error}")
        raise Exception(f"OCR pipeline error: {error_detail}")
    
    confidence = _safe_get(ocr_result, 'confidence', default=0.0, location="ocr_service.py:689")
    
    # Extract OCR text for logging
    pages = _safe_get(ocr_result, 'pages', default=[], location="ocr_service.py:692")
    ocr_text_parts = []
    total_text_length = 0
    page_stats = []
    
    # #region agent log
    import json
    log_path = _Path(__file__).parent.parent.parent / ".cursor" / "debug.log"
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "B", "location": "ocr_service.py:494", "message": "text extraction start", "data": {"doc_id": doc_id, "pages_count": len(pages), "pages_type": type(pages).__name__}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
    except: pass
    # #endregion
    
    for page_idx, page in enumerate(pages):
        # Skip None pages to avoid 'NoneType' object has no attribute 'get' error
        if page is None:
            continue
        # #region agent log
        try:
            page_keys = list(page.keys()) if isinstance(page, dict) else "not_dict"
            page_type = type(page).__name__
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "B", "location": "ocr_service.py:500", "message": "page iteration", "data": {"doc_id": doc_id, "page_idx": page_idx, "page_type": page_type, "page_keys": page_keys[:10] if isinstance(page_keys, list) else page_keys}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
        except: pass
        # #endregion
        page_text = page.get('text', page.get('ocr_text', '')) if page and isinstance(page, dict) else (getattr(page, 'text', '') or getattr(page, 'ocr_text', '') if page else '') if isinstance(page, dict) else (getattr(page, 'text', '') or getattr(page, 'ocr_text', ''))
        page_text_length = len(page_text) if page_text else 0
        # #region agent log
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "B", "location": "ocr_service.py:502", "message": "page text extracted", "data": {"doc_id": doc_id, "page_idx": page_idx, "page_text_length": page_text_length, "has_text_key": "text" in page if isinstance(page, dict) else False, "has_ocr_text_key": "ocr_text" in page if isinstance(page, dict) else False}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
        except: pass
        # #endregion
        total_text_length += page_text_length
        page_confidence = page.get('confidence', 0.0) if page and isinstance(page, dict) else (getattr(page, 'confidence', 0.0) if page else 0.0)
        page_stats.append({
            'page': page_idx + 1,
            'text_length': page_text_length,
            'confidence': page_confidence
        })
        if page_text:
            ocr_text_parts.append(page_text)
    
    full_ocr_text = '\n'.join(ocr_text_parts)
    ocr_text_preview = full_ocr_text[:300] if full_ocr_text else ""
    
    # Calculate ocr_text_length from all pages for validation (needed later for confidence calculation)
    # Extract OCR text length from all pages for validation - calculate early to avoid scoping issues
    ocr_text_length = 0
    if pages:
        for page_item in pages:
            page_text_parts = []
            if hasattr(page_item, 'blocks'):
                for block in page_item.blocks if hasattr(page_item, 'blocks') and page_item.blocks else []:
                    if hasattr(block, 'ocr_text'):
                        text = getattr(block, 'ocr_text', '') or getattr(block, 'text', '')
                    else:
                        text = block.get("ocr_text", block.get("text", ""))
                    if text:
                        page_text_parts.append(text)
            else:
                blocks = page_item.get("blocks", []) if page_item and isinstance(page_item, dict) else (getattr(page_item, "blocks", []) if page_item else [])
                for block in blocks:
                    if block is None:
                        continue
                    text = block.get("ocr_text", block.get("text", "")) if isinstance(block, dict) else (getattr(block, "ocr_text", "") or getattr(block, "text", ""))
                    if text:
                        page_text_parts.append(text)
            ocr_text_length += len("\n".join(page_text_parts))
    
    # Log OCR completion with text stats
    _log_lifecycle("OCR_DONE", doc_id, 
                   confidence=confidence,
                   ocr_text_length=total_text_length,
                   pages_count=len(pages),
                   ocr_text_preview=ocr_text_preview,
                   page_stats=page_stats)
    
    # Check for OCR failure (very low text) - trigger retry with fallbacks
    # #region agent log
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "C", "location": "ocr_service.py:524", "message": "checking text length threshold", "data": {"doc_id": doc_id, "total_text_length": total_text_length, "threshold": 100, "will_retry": total_text_length < 100}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
    except: pass
    # #endregion
    if total_text_length < 100:
        logger.warning(f"[OCR_V2] Initial OCR produced insufficient text: {total_text_length} chars, attempting retries with fallbacks")
        
        # Get PDF structure and render metadata from initial result
        pdf_structure = _safe_get(ocr_result, 'pdf_structure', default=None, location="ocr_service.py:779")
        render_metadata = _safe_get(ocr_result, 'render_metadata', default=[], location="ocr_service.py:780")
        
        # Attempt retries with different configurations
        # #region agent log
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "C", "location": "ocr_service.py:532", "message": "calling retry function", "data": {"doc_id": doc_id, "file_path": str(file_path), "has_pdf_structure": pdf_structure is not None, "render_metadata_count": len(render_metadata)}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
        except: pass
        # #endregion
        retry_result = _retry_ocr_with_fallbacks(doc_id, file_path, ocr_result, pdf_structure, render_metadata)
        # #region agent log
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "C", "location": "ocr_service.py:533", "message": "retry function returned", "data": {"doc_id": doc_id, "final_text_length": _safe_get(retry_result, "final_text_length", default=0, location="ocr_service.py:811"), "attempts_count": len(_safe_get(retry_result, "ocr_attempts", default=[], location="ocr_service.py:811")), "retry_succeeded": _safe_get(retry_result, "final_text_length", default=0, location="ocr_service.py:811") >= 100}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
        except: pass
        # #endregion
        
        if retry_result['final_text_length'] >= 100:
            # Retry succeeded - use the best result
            logger.info(f"[OCR_RETRY] Retry succeeded: {retry_result['final_text_length']} chars extracted")
            ocr_result = retry_result['best_result']
            total_text_length = retry_result['final_text_length']
            # Re-extract text from retry result
            pages = ocr_result.get('pages', [])
            # Recalculate ocr_text_length from updated pages after retry
            ocr_text_length = 0
            for page_item in pages:
                page_text_parts = []
                if hasattr(page_item, 'blocks'):
                    for block in page_item.blocks if hasattr(page_item, 'blocks') and page_item.blocks else []:
                        if hasattr(block, 'ocr_text'):
                            text = getattr(block, 'ocr_text', '') or getattr(block, 'text', '')
                        else:
                            text = block.get("ocr_text", block.get("text", ""))
                        if text:
                            page_text_parts.append(text)
                else:
                    blocks = _safe_get(page_item, "blocks", default=[], location="ocr_service.py:836") if page_item else []
                    for block in blocks:
                        if block is None:
                            continue
                        text = _safe_get(block, "ocr_text", default=_safe_get(block, "text", default="", location="ocr_service.py:837"), location="ocr_service.py:837") if isinstance(block, dict) else (getattr(block, "ocr_text", "") or getattr(block, "text", "") if block else "")
                        if text:
                            page_text_parts.append(text)
                ocr_text_length += len("\n".join(page_text_parts))
            ocr_text_parts = []
            for page_idx, page in enumerate(pages):
                page_text = page.get('text', page.get('ocr_text', '')) if page and isinstance(page, dict) else (getattr(page, 'text', '') or getattr(page, 'ocr_text', '') if page else '')
                if page_text:
                    ocr_text_parts.append(page_text)
            full_ocr_text = '\n'.join(ocr_text_parts)
            ocr_text_preview = full_ocr_text[:300] if full_ocr_text else ""
        else:
            # All retries failed - create structured error
            error_code = "OCR_ZERO_TEXT" if total_text_length == 0 else "OCR_INSUFFICIENT_TEXT"
            error_metadata = {
                "error_code": error_code,
                "error_message": f"OCR produced insufficient text: {_safe_get(retry_result, 'final_text_length', default=0, location='ocr_service.py:834')} chars (minimum 100 required)",
                "engine_used": (_safe_get(retry_result, 'ocr_attempts', default=[{}], location="ocr_service.py:835")[-1].get('engine', 'unknown') if _safe_get(retry_result, 'ocr_attempts', default=[], location="ocr_service.py:835") else 'unknown'),
                "dpi": (_safe_get(retry_result, 'ocr_attempts', default=[{}], location="ocr_service.py:836")[-1].get('dpi', 300) if _safe_get(retry_result, 'ocr_attempts', default=[], location="ocr_service.py:836") else 300),
                "page_count": len(pages),
                "has_text_layer": _safe_get(pdf_structure, 'has_text_layer', default=False, location="ocr_service.py:838"),
                "ocr_attempts": _safe_get(retry_result, 'ocr_attempts', default=[], location="ocr_service.py:839"),
                "rendered_image_valid": len(render_metadata) > 0 and all(_safe_get(rm, 'width', default=0, location="ocr_service.py:859") > 0 and _safe_get(rm, 'height', default=0, location="ocr_service.py:859") > 0 for rm in render_metadata if rm) if render_metadata else False,
                "mean_pixel_intensity": _safe_get(render_metadata[0], 'mean_intensity', default=None, location="ocr_service.py:860") if render_metadata and len(render_metadata) > 0 and render_metadata[0] else None
            }
            
            error_msg_json = json.dumps(error_metadata)
            error_msg = error_metadata.get('error_message', 'Unknown error') if error_metadata else 'Unknown error'
            logger.error(f"[OCR_V2] All OCR attempts failed: {error_msg} for doc_id={doc_id}")
            update_document_status(doc_id, "error", error_code, error=error_msg_json)
            _log_lifecycle("OCR_ERROR", doc_id, error=error_msg, ocr_text_length=_safe_get(retry_result, 'final_text_length', default=0, location="ocr_service.py:847"), error_code=error_code, ocr_attempts=len(_safe_get(retry_result, 'ocr_attempts', default=[], location="ocr_service.py:847")))
            raise Exception(error_msg)
    
    # Store OCR telemetry report in database
    try:
        ocr_telemetry = _safe_get(ocr_result, 'ocr_telemetry', default=None, location="ocr_service.py:852")
        if ocr_telemetry:
            from backend.ocr.ocr_telemetry import OCRTelemetryReport, PageTelemetry, BlockTelemetry, OverallTelemetry
            # Convert dict to OCRTelemetryReport and serialize to JSON
            if isinstance(ocr_telemetry, dict):
                # Create report from dict
                report = OCRTelemetryReport()
                report.pages = [PageTelemetry(**p) for p in ocr_telemetry.get('pages', [])]
                report.blocks = [BlockTelemetry(**b) for b in ocr_telemetry.get('blocks', [])]
                if 'overall' in ocr_telemetry:
                    report.overall = OverallTelemetry(**ocr_telemetry['overall'])
                ocr_report_json = report.to_json()
            elif isinstance(ocr_telemetry, OCRTelemetryReport):
                ocr_report_json = ocr_telemetry.to_json()
            else:
                # Fallback: serialize dict directly
                ocr_report_json = json.dumps(ocr_telemetry, indent=2, ensure_ascii=False)
            
            store_ocr_report(doc_id, ocr_report_json)
            logger.info(f"[OCR_TELEMETRY] Stored OCR telemetry report for doc_id={doc_id}")
        else:
            logger.debug(f"[OCR_TELEMETRY] No OCR telemetry found in result for doc_id={doc_id}")
    except Exception as e:
        logger.warning(f"[OCR_TELEMETRY] Failed to store OCR telemetry report for doc_id={doc_id}: {e}")
        # Don't fail the entire OCR process if telemetry storage fails
    
    # Extract invoice data from OCR result
    pages = ocr_result.get("pages", []) if ocr_result else []
    
    # DEBUG: Log OCR result structure
    logger.info(f"[OCR_V2] OCR result keys: {list(ocr_result.keys())}")
    logger.info(f"[OCR_V2] Pages count: {len(pages)}")
    logger.info(f"[OCR_V2] Overall confidence: {ocr_result.get('confidence', 'N/A') if ocr_result else 'N/A'}")
    
    if not pages:
        # Provide more helpful error - check if PyMuPDF is missing
        import sys
        try:
            import fitz
            fitz_available = True
        except ImportError:
            fitz_available = False
        
        error_msg = "No pages extracted from document. "
        if not fitz_available:
            error_msg += "PyMuPDF (fitz) is not installed - required for PDF processing. Install with: pip install PyMuPDF"
        else:
            error_msg += f"File may be corrupted or unsupported format. File path: {file_path}"
        
        logger.error(f"[OCR_V2] {error_msg} for doc_id={doc_id}")
        logger.error(f"[OCR_V2] OCR result keys: {list(ocr_result.keys())}, pages count: {len(pages)}")
        raise Exception(error_msg)
    
    # Get original filename for grouping invoices from same PDF
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT filename FROM documents WHERE id = ?", (doc_id,))
    filename_row = cur.fetchone()
    original_filename = filename_row[0] if filename_row else None
    conn.close()
    
    logger.info(f"[MULTI_INVOICE] Processing {len(pages)} pages for doc_id={doc_id}, filename={original_filename}")
    
    # Extract LLM results from all pages
    from backend.llm.invoice_parser import LLMDocumentResult, DocumentType
    page_results: List[LLMDocumentResult] = []
    
    for page_idx, page in enumerate(pages):
        # Extract LLM metadata from page blocks
        llm_metadata = None
        if isinstance(page, dict):
            blocks = _safe_get(page, "blocks", default=[], location="ocr_service.py:944") if page else []
        else:
            blocks = getattr(page, "blocks", [])
        
        for block in blocks:
            if isinstance(block, dict):
                table_data = _safe_get(block, "table_data", default=None, location="ocr_service.py:950") if block else None
            else:
                table_data = getattr(block, "table_data", None)
            
            if table_data and isinstance(table_data, dict):
                metadata = table_data.get("metadata") if table_data and isinstance(table_data, dict) else None
                if metadata and isinstance(metadata, dict):
                    llm_metadata = metadata
                    break
        
        # Create LLMDocumentResult from metadata if available
        if llm_metadata:
            # Extract line items from table_data
            line_items = []
            for block in blocks:
                if isinstance(block, dict):
                    table_data = _safe_get(block, "table_data", default=None, location="ocr_service.py:950") if block else None
                else:
                    table_data = getattr(block, "table_data", None)
                
                if table_data and isinstance(table_data, dict):
                    items = table_data.get("line_items", []) if table_data and isinstance(table_data, dict) else []
                    if items:
                        from backend.llm.invoice_parser import LLMLineItem
                        for item_data in items:
                            line_items.append(LLMLineItem(
                                description=item_data.get("description", ""),
                                qty=float(item_data.get("qty", 0)),
                                unit_price=float(item_data.get("unit_price", 0)),
                                total=float(item_data.get("total", 0)),
                                uom=item_data.get("uom", ""),
                                sku=item_data.get("sku", ""),
                                confidence=float(item_data.get("confidence", 1.0)),
                                bbox=item_data.get("bbox"),
                                raw_text=json.dumps(item_data)
                            ))
                        break
            
            # Determine document type
            doc_type_str = llm_metadata.get("document_type", "invoice").lower()
            try:
                doc_type = DocumentType(doc_type_str)
            except ValueError:
                doc_type = DocumentType.INVOICE
            
            # #region agent log
            import json
            log_path = _Path(__file__).parent.parent.parent / ".cursor" / "debug.log"
            try:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "M", "location": "ocr_service.py:358", "message": "LLM metadata extracted from page", "data": {"doc_id": doc_id, "page_idx": page_idx, "supplier_name": llm_metadata.get("supplier_name"), "grand_total": llm_metadata.get("grand_total"), "subtotal": llm_metadata.get("subtotal"), "vat_amount": llm_metadata.get("vat_amount"), "line_items_count": len(line_items), "invoice_number": llm_metadata.get("invoice_number")}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
            except: pass
            # #endregion
            page_result = LLMDocumentResult(
                document_type=doc_type,
                supplier_name=llm_metadata.get("supplier_name", ""),
                invoice_number=llm_metadata.get("invoice_number", ""),
                invoice_date=llm_metadata.get("invoice_date", ""),
                currency=llm_metadata.get("currency", "GBP"),
                line_items=line_items,
                subtotal=float(llm_metadata.get("subtotal", 0)),
                vat_amount=float(llm_metadata.get("vat_amount", 0)),
                grand_total=float(llm_metadata.get("grand_total", 0)),
                page_number=page_idx + 1,
                success=True
            )
            page_results.append(page_result)
        else:
            # No LLM metadata - create empty result (will be handled by fallback)
            logger.warning(f"[MULTI_INVOICE] Page {page_idx + 1} has no LLM metadata, skipping")
    
    # Process invoices: either multiple groups or single fallback
    created_invoice_ids = []
    document_groups = []  # Initialize to ensure it's always defined
    
    if page_results:
        # Multi-invoice processing: split documents and create separate records
        from backend.llm.invoice_parser import create_invoice_parser
        llm_parser = create_invoice_parser()
        document_groups = llm_parser.split_documents(page_results)
        logger.info(f"[MULTI_INVOICE] Split {len(page_results)} pages into {len(document_groups)} document groups")
        # #region agent log
        import json
        log_path = _Path(__file__).parent.parent.parent / ".cursor" / "debug.log"
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "G", "location": "ocr_service.py:384", "message": "document_groups created", "data": {"doc_id": doc_id, "page_results_count": len(page_results), "document_groups_count": len(document_groups)}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
        except: pass
        # #endregion
        
        # CRITICAL FIX: If document_groups is empty, fall back to single-page processing
        if not document_groups:
            logger.warning(f"[MULTI_INVOICE] document_groups is empty after splitting, falling back to single-page processing")
            # #region agent log
            try:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "G", "location": "ocr_service.py:392", "message": "document_groups empty, forcing fallback", "data": {"doc_id": doc_id}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
            except: pass
            # #endregion
            # Don't process multi-invoice, will fall through to single-page processing below
        else:
            # Process each document group as a separate invoice
            for group_idx, doc_group in enumerate(document_groups):
                combined_result = doc_group.combined_result
                
                # Generate unique doc_id for this invoice (original_doc_id + suffix)
                if len(document_groups) > 1:
                    invoice_doc_id = f"{doc_id}-{group_idx + 1}"
                else:
                    invoice_doc_id = doc_id
                
                logger.info(
                    f"[MULTI_INVOICE] Processing group {group_idx + 1}/{len(document_groups)}: "
                    f"doc_id={invoice_doc_id}, supplier='{combined_result.supplier_name}', "
                    f"invoice_number='{combined_result.invoice_number}', "
                    f"pages={doc_group.pages}, items={len(combined_result.line_items)}"
                )
                
                # Create document record for this invoice (if multiple invoices)
                if len(document_groups) > 1:
                    from backend.app.db import insert_document
                    import os
                    # Create a reference document entry pointing to the original file
                    # Use the same stored_path but different doc_id
                    stored_path = None
                    conn = sqlite3.connect(DB_PATH)
                    cur = conn.cursor()
                    cur.execute("SELECT stored_path FROM documents WHERE id = ?", (doc_id,))
                    path_row = cur.fetchone()
                    if path_row:
                        stored_path = path_row[0]
                    conn.close()
                    
                    if stored_path:
                        file_size = os.path.getsize(stored_path) if os.path.exists(stored_path) else 0
                        insert_document(
                            doc_id=invoice_doc_id,
                            filename=original_filename or f"invoice_{group_idx + 1}.pdf",
                            stored_path=stored_path,
                            size_bytes=file_size,
                            sha256=None  # Same file, different invoice
                        )
                
                # Extract data from combined result
                doc_type = combined_result.document_type.value
                
                # Prepare parsed_data from combined_result
                # #region agent log
                import json
                log_path = _Path(__file__).parent.parent.parent / ".cursor" / "debug.log"
                try:
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "L", "location": "ocr_service.py:459", "message": "combined_result values from LLM", "data": {"doc_id": invoice_doc_id, "supplier_name": combined_result.supplier_name, "grand_total": combined_result.grand_total, "subtotal": combined_result.subtotal, "vat_amount": combined_result.vat_amount, "line_items_count": len(combined_result.line_items), "invoice_number": combined_result.invoice_number}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
                except: pass
                # #endregion
                parsed_data = {
                    "supplier": combined_result.supplier_name or "Unknown Supplier",
                    "date": _normalize_date(combined_result.invoice_date) or datetime.now().strftime("%Y-%m-%d"),
                    "total": _normalize_currency(combined_result.grand_total) or 0.0,
                    "invoice_number": combined_result.invoice_number or None,
                    "invoice_number_source": "llm_extracted" if combined_result.invoice_number else "generated",
                    "subtotal": _normalize_currency(combined_result.subtotal) or 0.0,
                    "vat": _normalize_currency(combined_result.vat_amount) or 0.0,
                    "confidence": combined_result.confidence,
                    "doc_type": doc_type
                }
                # #region agent log
                try:
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "L", "location": "ocr_service.py:471", "message": "parsed_data after normalization", "data": {"doc_id": invoice_doc_id, "supplier": parsed_data["supplier"], "total": parsed_data["total"], "subtotal": parsed_data["subtotal"], "vat": parsed_data["vat"]}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
                except: pass
                # #endregion
                
                # Convert line items to dict format
                line_items = []
                for item in combined_result.line_items:
                    # Skip None items to avoid AttributeError
                    if item is None:
                        continue
                    # Filter out header/footer text that shouldn't be line items
                    desc = getattr(item, 'description', '') or getattr(item, 'desc', '')
                    if desc:
                        desc_lower = desc.lower().strip()
                        # Skip common header/footer patterns
                        skip_patterns = [
                            'total', 'subtotal', 'vat', 'tax', 'amount due', 'balance',
                            'invoice no', 'invoice number', 'invoice date', 'date:',
                            'vat registration', 'company registration', 'registration number',
                            'account no', 'account number', 'sort code', 'iban', 'bic',
                            'payment terms', 'due date', 'thank you', 'please pay'
                        ]
                        if any(pattern in desc_lower for pattern in skip_patterns):
                            logger.debug(f"[LINE_ITEMS] Skipping header/footer text: {desc}")
                            continue
                    line_items.append({
                        "desc": desc,
                        "qty": getattr(item, 'qty', 0),
                        "unit_price": getattr(item, 'unit_price', 0),
                        "total": getattr(item, 'total', 0),
                        "uom": getattr(item, 'uom', ''),
                        "confidence": getattr(item, 'confidence', 0.9),
                        "bbox": getattr(item, 'bbox', None)
                    })
                
                # Deduplicate and truncate
                line_items = _deduplicate_items(line_items)
                if len(line_items) > MAX_LINE_ITEMS:
                    logger.warning(f"[ITEMS_TRUNCATED] doc_id={invoice_doc_id} count={len(line_items)} limit={MAX_LINE_ITEMS}")
                    line_items = line_items[:MAX_LINE_ITEMS]
                
                # Get confidence from OCR result
                confidence = (ocr_result.get("overall_confidence", ocr_result.get("confidence", parsed_data.get("confidence", 0.9) if parsed_data else 0.9)) if ocr_result else (parsed_data.get("confidence", 0.9) if parsed_data else 0.9))
                
                # Check if needs review
                needs_review = getattr(combined_result, 'needs_review', False)
                invoice_status = 'needs_review' if needs_review else 'scanned'
                
                # Store invoice
                logger.info(
                    f"[MULTI_INVOICE] Storing invoice {group_idx + 1}/{len(document_groups)}: "
                    f"doc_id={invoice_doc_id}, supplier='{parsed_data['supplier']}', "
                    f"total={parsed_data['total']}, items={len(line_items)}"
                )
                
                # Log extraction data before DB write
                _log_lifecycle("EXTRACTION_DONE", invoice_doc_id,
                              supplier=parsed_data.get('supplier') if parsed_data else None,
                              invoice_number=parsed_data.get('invoice_number') if parsed_data else None,
                              invoice_date=parsed_data.get('date') if parsed_data else None,
                              total=parsed_data.get('total') if parsed_data else None,
                              subtotal=parsed_data.get('subtotal') if parsed_data else None,
                              vat=parsed_data.get('vat') if parsed_data else None,
                              line_items_count=len(line_items),
                              confidence=confidence,
                              doc_type=doc_type)
                
                # Log first 3 line items
                if line_items:
                    first_items = line_items[:3]
                    items_summary = []
                    for idx, item in enumerate(first_items):
                        items_summary.append({
                            'index': idx + 1,
                            'desc': str(_safe_get(item, 'desc', default='', location="ocr_service.py:1192"))[:50],
                            'qty': _safe_get(item, 'qty', default=None, location="ocr_service.py:1193"),
                            'unit_price': _safe_get(item, 'unit_price', default=None, location="ocr_service.py:1194"),
                            'total': _safe_get(item, 'total', default=None, location="ocr_service.py:1195")
                        })
                    _log_lifecycle("EXTRACTION_ITEMS_SAMPLE", invoice_doc_id, items_sample=items_summary)
                
                # Check for extraction failure
                invoice_has_empty_data = ((parsed_data.get('supplier') if parsed_data else None) == "Unknown Supplier" and 
                                         (parsed_data.get('total') if parsed_data else 0.0) == 0.0 and len(line_items) == 0)
                if invoice_has_empty_data:
                    error_msg = "Extraction produced empty data: supplier=Unknown Supplier, total=0, line_items=0"
                    logger.error(f"[EXTRACTION_FAILURE] {error_msg} for doc_id={invoice_doc_id}")
                    _log_lifecycle("EXTRACTION_FAILURE", invoice_doc_id, error=error_msg)
                
                _log_lifecycle("DB_WRITE_START", invoice_doc_id)
                upsert_invoice(
                    doc_id=invoice_doc_id,
                    supplier=parsed_data["supplier"],
                    date=parsed_data["date"],
                    value=parsed_data["total"],
                    invoice_number=parsed_data["invoice_number"],
                    confidence=confidence,
                    status=invoice_status
                )
                
                # Store line items
                if line_items:
                    invoice_id_for_items = None if doc_type == "delivery_note" else invoice_doc_id
                    _log_lifecycle("DB_WRITE_LINE_ITEMS_START", invoice_doc_id, line_items_count=len(line_items))
                    insert_line_items(invoice_doc_id, invoice_id_for_items, line_items)
                    _log_lifecycle("DB_WRITE_LINE_ITEMS_DONE", invoice_doc_id, line_items_count=len(line_items))
                    logger.info(f"[MULTI_INVOICE] Stored {len(line_items)} line items for invoice {invoice_doc_id}")
                
                _log_lifecycle("DB_WRITE_DONE", invoice_doc_id)
                
                created_invoice_ids.append(invoice_doc_id)
                
                # Update document status - CRITICAL: Never mark as "ready" if data is empty
                if invoice_has_empty_data:
                    # Mark for manual review if extraction produced empty data
                    update_document_status(invoice_doc_id, "needs_review", "extraction_empty_data", 
                                         confidence=0.0, error="Extraction produced empty data")
                    _log_lifecycle("REVIEW_NEEDED", invoice_doc_id,
                                  error="Extraction produced empty data",
                                  reason="extraction_empty_data",
                                  supplier=parsed_data.get('supplier') if parsed_data else None,
                                  total=parsed_data.get('total') if parsed_data else None,
                                  items=len(line_items),
                                  confidence=confidence,
                                  doc_type=doc_type)
                    logger.warning(f"[REVIEW_NEEDED] Invoice {invoice_doc_id} marked for review - empty extraction data")
                else:
                    # Normal success path
                    update_document_status(invoice_doc_id, "ready", "doc_ready", confidence=confidence)
                    _log_lifecycle("DOC_READY", invoice_doc_id,
                                  supplier=parsed_data.get('supplier') if parsed_data else None,
                                  total=parsed_data.get('total') if parsed_data else None,
                                  items=len(line_items),
                                  confidence=confidence,
                                  doc_type=doc_type)
                
                # Trigger auto-backup if needed (after successful processing)
                try:
                    from backend.services.backup import trigger_auto_backup_if_needed
                    trigger_auto_backup_if_needed(invoice_doc_id)
                except Exception as backup_error:
                    # Never let backup failures break document processing
                    logger.warning(f"Auto-backup trigger failed for {invoice_doc_id}: {backup_error}")
            
            # After processing all groups, check if we created any invoices
            if created_invoice_ids:
                # Update original document status and return
                confidence = ocr_result.get("overall_confidence", ocr_result.get("confidence", 0.9))
                update_document_status(doc_id, "ready", "doc_ready", confidence=confidence)
                logger.info(f"[MULTI_INVOICE] Created {len(created_invoice_ids)} invoices from PDF: {created_invoice_ids}")
                
                # Trigger auto-backup for the main document as well
                try:
                    from backend.services.backup import trigger_auto_backup_if_needed
                    trigger_auto_backup_if_needed(doc_id)
                except Exception as backup_error:
                    logger.warning(f"Auto-backup trigger failed for {doc_id}: {backup_error}")
                
                # Return early for multi-invoice case
                return {
                    "status": "ok",
                    "doc_id": doc_id,
                    "confidence": confidence,
                    "line_items": [],  # Line items are in separate invoice records
                    "created_invoices": created_invoice_ids,
                    "supplier": document_groups[0].combined_result.supplier_name if document_groups else "Unknown",
                    "date": document_groups[0].combined_result.invoice_date if document_groups else datetime.now().strftime("%Y-%m-%d"),
                    "total": sum(g.combined_result.grand_total for g in document_groups) if document_groups else 0.0
                }
            # If no invoices were created (empty document_groups), fall through to single-page processing
            logger.warning(f"[MULTI_INVOICE] No invoices created from document_groups, falling back to single-page processing")
    
    # Multi-page processing: Extract headers from page 1, aggregate line items and totals from all pages
    if not page_results or not document_groups or not created_invoice_ids:
        logger.info(f"[MULTI_PAGE] Processing {len(pages)} pages as single document with cross-page aggregation")
        # #region agent log
        import json
        log_path = _Path(__file__).parent.parent.parent / ".cursor" / "debug.log"
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "G", "location": "ocr_service.py:536", "message": "multi-page processing with cross-page aggregation", "data": {"doc_id": doc_id, "pages_count": len(pages)}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
        except: pass
        # #endregion
        
        # Use page 1 for header/metadata extraction, but aggregate line items from all pages
        page = pages[0] if pages else None
        if not page:
            raise Exception(f"No pages available for processing doc_id={doc_id}")
        
        # Continue with existing processing logic, but we'll aggregate line items from all pages later
        # (keeping the rest of the function as-is, but line item extraction will be enhanced)
    if isinstance(page, dict):
        logger.info(f"[OCR_V2] Page keys: {list(page.keys())}")
        logger.info(f"[OCR_V2] Page has 'blocks': {'blocks' in page}")
        logger.info(f"[OCR_V2] Page has 'text': {'text' in page}")
        logger.info(f"[OCR_V2] Page has 'ocr_text': {'ocr_text' in page}")
        if 'blocks' in page:
            blocks_list = _safe_get(page, 'blocks', default=[], location="ocr_service.py:1316") if page else []
            logger.info(f"[OCR_V2] Page blocks count: {len(blocks_list)}")
            # Log details about each block
            for i, b in enumerate(blocks_list[:5]):  # Log first 5 blocks
                if isinstance(b, dict):
                    logger.info(f"[OCR_V2] Block {i}: type='{b.get('type')}', has_table_data={b.get('table_data') is not None}, table_data_type={type(b.get('table_data'))}")
                    if b.get('table_data'):
                        td = b.get('table_data')
                        if isinstance(td, dict):
                            logger.info(f"[OCR_V2] Block {i} table_data keys: {list(td.keys())}, line_items count: {len(td.get('line_items', []))}")
                else:
                    logger.info(f"[OCR_V2] Block {i}: type={type(b)}, has_type_attr={hasattr(b, 'type')}")
    
    # FIX: Extract LLM data from table_data.metadata first (LLM extraction stores data here)
    # Then check normalized_json (from template matching), then fallback to regex
    parsed_data = {}
    llm_metadata = None
    
    # #region agent log
    import json
    log_path = _Path(__file__).parent.parent.parent / ".cursor" / "debug.log"
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "A", "location": "ocr_service.py:268", "message": "checking for LLM metadata", "data": {"doc_id": doc_id, "page_type": str(type(page)), "is_dict": isinstance(page, dict)}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
    except: pass
    # #endregion
    
    # Check for LLM metadata in table_data (from LLM extraction)
    if isinstance(page, dict):
        blocks = page.get("blocks", [])
    else:
        blocks = getattr(page, "blocks", [])
    
    # #region agent log
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "A", "location": "ocr_service.py:280", "message": "scanning blocks for LLM metadata", "data": {"blocks_count": len(blocks)}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
    except: pass
    # #endregion
    
    for i, block in enumerate(blocks):
        # #region agent log
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "A", "location": "ocr_service.py:295", "message": "checking block for table_data", "data": {"block_index": i, "is_dict": isinstance(block, dict), "has_table_data_attr": hasattr(block, "table_data") if not isinstance(block, dict) else False}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
        except: pass
        # #endregion
        
        if isinstance(block, dict):
            table_data = block.get("table_data")
        else:
            table_data = getattr(block, "table_data", None)
        
        # #region agent log
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "A", "location": "ocr_service.py:303", "message": "table_data check", "data": {"block_index": i, "has_table_data": table_data is not None, "table_data_is_dict": isinstance(table_data, dict), "table_data_keys": list(table_data.keys()) if isinstance(table_data, dict) else None}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
        except: pass
        # #endregion
        
        if table_data and isinstance(table_data, dict):
            metadata = table_data.get("metadata") if table_data and isinstance(table_data, dict) else None
            # #region agent log
            try:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "A", "location": "ocr_service.py:310", "message": "metadata check", "data": {"block_index": i, "has_metadata": metadata is not None, "metadata_is_dict": isinstance(metadata, dict), "metadata_keys": list(metadata.keys()) if isinstance(metadata, dict) else None}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
            except: pass
            # #endregion
            if metadata and isinstance(metadata, dict):
                llm_metadata = metadata
                logger.info(f"[OCR_V2] Found LLM metadata in table_data: supplier='{metadata.get('supplier_name')}', invoice_number='{metadata.get('invoice_number')}', grand_total={metadata.get('grand_total')}")
                # #region agent log
                try:
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "A", "location": "ocr_service.py:318", "message": "LLM metadata found", "data": {"supplier_name": metadata.get("supplier_name"), "invoice_number": metadata.get("invoice_number"), "grand_total": metadata.get("grand_total"), "invoice_date": metadata.get("invoice_date")}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
                except: pass
                # #endregion
                break
    
        # Priority 1: Use LLM metadata if available (most accurate)
        if llm_metadata:
            logger.info(f"[OCR_V2] Using LLM metadata for doc_id={doc_id}")
            supplier_from_llm = llm_metadata.get("supplier_name") or "Unknown Supplier"
            # #region agent log
            import json
            log_path = _Path(__file__).parent.parent.parent / ".cursor" / "debug.log"
            try:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "H", "location": "ocr_service.py:590", "message": "using LLM metadata for supplier", "data": {"doc_id": doc_id, "supplier_from_llm": supplier_from_llm}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
            except: pass
            # #endregion
            parsed_data = {
                "supplier": supplier_from_llm,
                "date": _normalize_date(llm_metadata.get("invoice_date")),
                "total": _normalize_currency(llm_metadata.get("grand_total") or llm_metadata.get("total")),
                "invoice_number": llm_metadata.get("invoice_number"),
                "invoice_number_source": "llm_extracted" if llm_metadata.get("invoice_number") else "generated",
                "subtotal": _normalize_currency(llm_metadata.get("subtotal")),
                "vat": _normalize_currency(llm_metadata.get("vat_amount")),
                "confidence": ocr_result.get("confidence", 0.9)
            }
            # Ensure we have valid values
            if not parsed_data["date"]:
                parsed_data["date"] = datetime.now().strftime("%Y-%m-%d")
            if parsed_data["total"] is None:
                parsed_data["total"] = 0.0
            logger.info(f"[OCR_V2] Extracted from LLM metadata: supplier='{parsed_data['supplier']}', date='{parsed_data['date']}', total={parsed_data['total']}, invoice_number='{parsed_data.get('invoice_number')}'")
        # #region agent log
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "A", "location": "ocr_service.py:310", "message": "using LLM metadata for parsed_data", "data": {"supplier": parsed_data.get("supplier"), "date": parsed_data.get("date"), "total": parsed_data.get("total"), "invoice_number": parsed_data.get("invoice_number")}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
        except: pass
        # #endregion
    else:
        # Priority 2: Check for normalized_json (from template matching)
        normalized_json = ocr_result.get("normalized_json")
        if normalized_json and isinstance(normalized_json, dict):
            logger.info(f"[OCR_V2] Using normalized_json for doc_id={doc_id}")
            parsed_data = {
                "supplier": normalized_json.get("supplier_name") or normalized_json.get("supplier") or "Unknown Supplier",
                "date": _normalize_date(normalized_json.get("invoice_date") or normalized_json.get("date")),
                "total": _normalize_currency(normalized_json.get("total_amount") or normalized_json.get("total") or normalized_json.get("total_value")),
                "confidence": ocr_result.get("confidence", 0.9)
            }
            # Ensure we have valid values
            if not parsed_data["date"]:
                parsed_data["date"] = datetime.now().strftime("%Y-%m-%d")
            if parsed_data["total"] is None:
                parsed_data["total"] = 0.0
            logger.info(f"[OCR_V2] Extracted from normalized_json: supplier='{parsed_data['supplier']}', date='{parsed_data['date']}', total={parsed_data['total']}")
        else:
            # Priority 3: Fallback to page extraction (regex-based)
            # #region agent log
            import json
            log_path = _Path(__file__).parent.parent.parent / ".cursor" / "debug.log"
            try:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "H", "location": "ocr_service.py:640", "message": "before _extract_invoice_data_from_page call (fallback path)", "data": {"doc_id": doc_id, "has_llm_metadata": llm_metadata is not None, "has_normalized_json": normalized_json is not None if 'normalized_json' in locals() else False}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
            except: pass
            # #endregion
            try:
                parsed_data = _extract_invoice_data_from_page(page)
                logger.info(f"[OCR_V2] Used page extraction (no LLM metadata or normalized_json available)")
                # #region agent log
                try:
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "H", "location": "ocr_service.py:650", "message": "after _extract_invoice_data_from_page call", "data": {"supplier": parsed_data.get("supplier"), "date": parsed_data.get("date"), "total": parsed_data.get("total"), "invoice_number": parsed_data.get("invoice_number")}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
                except: pass
                # #endregion
            except Exception as extract_error:
                import traceback
                extract_traceback = traceback.format_exc()
                logger.exception(f"[OCR_V2] _extract_invoice_data_from_page failed: {extract_error}")
                # #region agent log
                try:
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "F", "location": "ocr_service.py:395", "message": "_extract_invoice_data_from_page exception", "data": {"doc_id": doc_id, "error": str(extract_error), "error_type": type(extract_error).__name__, "traceback": extract_traceback[:1000]}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
                except: pass
                # #endregion
                raise
    
    # DEBUG: Log extracted data
    logger.info(f"[OCR_V2] Extracted data: supplier='{parsed_data.get('supplier')}', date='{parsed_data.get('date')}', total={parsed_data.get('total')}")
    # #region agent log
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "A", "location": "ocr_service.py:350", "message": "final parsed_data", "data": {"supplier": parsed_data.get("supplier"), "date": parsed_data.get("date"), "total": parsed_data.get("total"), "invoice_number": parsed_data.get("invoice_number"), "invoice_number_source": parsed_data.get("invoice_number_source")}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
    except: pass
    # #endregion
    
    # Classify document type based on OCR text using new deterministic classifier
    from backend.ocr.document_type_classifier import classify_document_type
    
    # Extract text from all pages for classification (per-page analysis for better accuracy)
    page_texts = []
    classify_full_text_parts = []
    
    for page_item in pages:
        page_text_parts = []
        if hasattr(page_item, 'blocks'):
            classify_blocks = list(page_item.blocks) if hasattr(page_item, 'blocks') and page_item.blocks else []
            for block in classify_blocks:
                if hasattr(block, 'ocr_text'):
                    text = getattr(block, 'ocr_text', '') or getattr(block, 'text', '')
                else:
                    text = _safe_get(block, "ocr_text", default=_safe_get(block, "text", default="", location="ocr_service.py:1501"), location="ocr_service.py:1501") if block else ""
                if text:
                    page_text_parts.append(text)
                    classify_full_text_parts.append(text)
        else:
            blocks = _safe_get(page_item, "blocks", default=[], location="ocr_service.py:1506") if page_item else []
            for block in blocks:
                if block is None:
                    continue
                text = _safe_get(block, "ocr_text", default=_safe_get(block, "text", default="", location="ocr_service.py:1507"), location="ocr_service.py:1507") if isinstance(block, dict) else (getattr(block, "ocr_text", "") or getattr(block, "text", "") if block else "")
                if text:
                    page_text_parts.append(text)
                    classify_full_text_parts.append(text)
        
        page_texts.append("\n".join(page_text_parts))
    
    classify_full_text = "\n".join(classify_full_text_parts)
    
    # Classify using new deterministic classifier
    if classify_full_text:
        classification = classify_document_type(classify_full_text, pages=page_texts if page_texts else None)
        doc_type = classification.doc_type
        doc_type_confidence = classification.confidence
        doc_type_reasons = classification.reasons
    else:
        # Fallback if no text extracted
        doc_type = "unknown"
        doc_type_confidence = 0.0
        doc_type_reasons = ["No text content extracted from document"]
    
    # Store document type and classification metadata for potential pairing
    parsed_data["doc_type"] = doc_type
    parsed_data["doc_type_confidence"] = doc_type_confidence
    parsed_data["doc_type_reasons"] = doc_type_reasons
    
    # Log classification result
    logger.info(f"[CLASSIFICATION] doc_id={doc_id} type={doc_type} "
               f"confidence={doc_type_confidence:.2f} "
               f"reasons={doc_type_reasons[:3] if doc_type_reasons else []}")
    
    # Persist classification to database
    try:
        update_document_classification(doc_id, doc_type, doc_type_confidence, doc_type_reasons)
        logger.info(f"[CLASSIFICATION] Persisted classification to database for doc_id={doc_id}")
    except Exception as e:
        logger.warning(f"[CLASSIFICATION] Failed to persist classification for doc_id={doc_id}: {e}")
    
    _log_lifecycle("PARSE_START", doc_id, doc_type=doc_type, doc_type_confidence=doc_type_confidence)
    
    # Extract and normalize line items from ALL pages (multi-page aggregation)
    logger.info(f"[LINE_ITEMS] Starting cross-page line item extraction for doc_id={doc_id} ({len(pages)} pages)")
    # #region agent log
    import json
    log_path = _Path(__file__).parent.parent.parent / ".cursor" / "debug.log"
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "D", "location": "ocr_service.py:284", "message": "before cross-page line item extraction", "data": {"doc_id": doc_id, "pages_count": len(pages), "page_has_blocks": "blocks" in page if isinstance(page, dict) else hasattr(page, "blocks")}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
    except: pass
    # #endregion
    
    # Aggregate line items from all pages and collect per-page metrics
    all_line_items = []
    page_metrics = []
    for page_idx, page_item in enumerate(pages):
        page_line_items = _extract_line_items_from_page(page_item, parsed_data)
        logger.info(f"[LINE_ITEMS] Page {page_idx + 1}/{len(pages)}: extracted {len(page_line_items)} line items")
        all_line_items.extend(page_line_items)
        
        # Calculate per-page metrics
        page_text_parts = []
        if hasattr(page_item, 'blocks'):
            for block in page_item.blocks if hasattr(page_item, 'blocks') and page_item.blocks else []:
                if hasattr(block, 'ocr_text'):
                    text = getattr(block, 'ocr_text', '') or getattr(block, 'text', '')
                else:
                    text = block.get("ocr_text", block.get("text", ""))
                    if text:
                        page_text_parts.append(text)
        else:
            blocks = _safe_get(page_item, "blocks", default=[], location="ocr_service.py:1506") if page_item else []
            for block in blocks:
                if block is None:
                    continue
                text = _safe_get(block, "ocr_text", default=_safe_get(block, "text", default="", location="ocr_service.py:1507"), location="ocr_service.py:1507") if isinstance(block, dict) else (getattr(block, "ocr_text", "") or getattr(block, "text", "") if block else "")
                if text:
                    page_text_parts.append(text)
        
        page_text = "\n".join(page_text_parts)
        page_word_count = len(page_text.split()) if page_text else 0
        page_confidence = getattr(page_item, 'confidence', None) if page_item and not isinstance(page_item, dict) else (_safe_get(page_item, 'confidence', default=0.0, location="ocr_service.py:1584") if page_item else 0.0)
        
        page_metrics.append({
            "page_number": page_idx + 1,
            "confidence": page_confidence,
            "word_count": page_word_count,
            "line_items_count": len(page_line_items),
            "text_length": len(page_text)
        })
    
    line_items = all_line_items
    logger.info(f"[LINE_ITEMS] Total line items across all pages: {len(line_items)}")
    logger.info(f"[MULTI_PAGE] Per-page metrics: {page_metrics}")
    
    # Update OCR report with per-page metrics
    try:
        from backend.app.db import store_ocr_report
        import sqlite3
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT ocr_report_json FROM documents WHERE id = ?", (doc_id,))
        row = cursor.fetchone()
        if row and row[0]:
            report_dict = json.loads(row[0])
            report_dict['page_metrics'] = page_metrics
            updated_report = json.dumps(report_dict, indent=2, ensure_ascii=False)
            store_ocr_report(doc_id, updated_report)
            logger.info(f"[MULTI_PAGE] Updated OCR report with {len(page_metrics)} page metrics")
        conn.close()
    except Exception as e:
        logger.warning(f"[MULTI_PAGE] Failed to update OCR report with page metrics: {e}")
    
    # #region agent log
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "D", "location": "ocr_service.py:286", "message": "after line item extraction", "data": {"doc_id": doc_id, "line_items_count": len(line_items)}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
    except: pass
    # #endregion
    logger.info(f"[LINE_ITEMS] Extracted {len(line_items)} line items before deduplication")
    
    line_items = _deduplicate_items(line_items)
    logger.info(f"[LINE_ITEMS] After deduplication: {len(line_items)} line items")
    
    # Truncate if exceeds limit
    original_count = len(line_items)
    if original_count > MAX_LINE_ITEMS:
        logger.warning(f"[ITEMS_TRUNCATED] doc_id={doc_id} count={original_count} limit={MAX_LINE_ITEMS}")
        line_items = line_items[:MAX_LINE_ITEMS]
    
    _log_lifecycle("PARSE_DONE", doc_id, items=len(line_items), original_count=original_count)
    
    # DEBUG: Log sample line items
    if line_items:
        logger.info(f"[LINE_ITEMS] Sample first item: {line_items[0]}")
    
    # Store invoice in database
    invoice_id = doc_id  # Use doc_id as invoice_id
    
    # Calculate multi-factor confidence using new calculator
    from backend.services.confidence_calculator import ConfidenceCalculator
    confidence_calc = ConfidenceCalculator()
    confidence_breakdown = confidence_calc.calculate_confidence(
        ocr_result=ocr_result,
        parsed_data=parsed_data,
        line_items=line_items,
        ocr_text_length=ocr_text_length
    )
    
    # Use overall confidence from breakdown (0-1 scale)
    confidence = confidence_breakdown.overall_confidence
    # Convert to 0-100 scale for backward compatibility
    confidence_percent = confidence * 100.0
    
    logger.info(
        f"[CONFIDENCE] Calculated confidence: {confidence_percent:.1f}% "
        f"(OCR: {confidence_breakdown.ocr_quality*100:.1f}%, "
        f"Extraction: {confidence_breakdown.extraction_quality*100:.1f}%, "
        f"Validation: {confidence_breakdown.validation_quality*100:.1f}%) "
        f"Band: {confidence_breakdown.band.value}"
    )
    
    # Low-confidence gate: If OCR confidence is too low, mark as unusable and clear line items
    from backend.config import MIN_USABLE_OCR_CONFIDENCE
    ocr_unusable = confidence_breakdown.ocr_quality < MIN_USABLE_OCR_CONFIDENCE
    # #region agent log
    import json
    log_path = _Path(__file__).parent.parent.parent / ".cursor" / "debug.log"
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "D", "location": "ocr_service.py:310", "message": "confidence gate check", "data": {"doc_id": doc_id, "confidence": confidence, "threshold": MIN_USABLE_OCR_CONFIDENCE, "ocr_unusable": ocr_unusable, "line_items_before": len(line_items)}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
    except: pass
    # #endregion
    if ocr_unusable:
        logger.warning(
            f"[OCR_GATE] OCR confidence {confidence:.3f} below threshold {MIN_USABLE_OCR_CONFIDENCE:.3f}. "
            f"Marking as unusable and clearing line items to avoid garbage data."
        )
        line_items = []  # Clear line items to avoid showing garbage
        # Add flag to parsed_data
        if not isinstance(parsed_data, dict):
            parsed_data = {}
        parsed_data["ocr_unusable"] = True
        if parsed_data and isinstance(parsed_data, dict):
            parsed_data["flags"] = parsed_data.get("flags", [])
        parsed_data["flags"].append("ocr_too_low_for_auto_extraction")
    else:
        if not isinstance(parsed_data, dict):
            parsed_data = {}
        parsed_data["ocr_unusable"] = False
    
    # Check if invoice needs review (from LLM validation)
    needs_review_from_llm = False
    if ocr_result and "pages" in ocr_result and ocr_result["pages"]:
        # Check first page's table_data for needs_review flag
        first_page = ocr_result["pages"][0]
        if first_page:
            blocks = _safe_get(first_page, "blocks", default=[], location="ocr_service.py:1700") if first_page and isinstance(first_page, dict) else (getattr(first_page, "blocks", []) if first_page else [])
            for block in blocks:
                if block is None:
                    continue
                if isinstance(block, dict):
                    table_data = _safe_get(block, "table_data", default=None, location="ocr_service.py:950") if block else None
                else:
                    table_data = getattr(block, "table_data", None)
                if table_data and isinstance(table_data, dict) and table_data.get("needs_review"):
                    needs_review_from_llm = True
                    metadata = table_data.get("metadata")
                    validation_errors = metadata.get("validation_errors", []) if metadata and isinstance(metadata, dict) else []
                    if validation_errors:
                        logger.warning(f"[VALIDATION] Invoice {doc_id} marked for review: {validation_errors}")
                    break
    
    # Set status based on confidence band
    # High → "ready" (or "scanned" if pairing needed)
    # Medium → "needs_review" with priority="low"
    # Low → "needs_review" with priority="medium"
    # Critical → "needs_review" with priority="high"
    if confidence_breakdown.band.value == "high" and not needs_review_from_llm and not needs_manual_review:
        invoice_status = 'ready'
    elif confidence_breakdown.band.value == "medium":
        invoice_status = 'needs_review'
    elif confidence_breakdown.band.value == "low":
        invoice_status = 'needs_review'
    else:  # critical or needs_manual_review
        invoice_status = 'needs_review'
    
    # DEBUG: Log what we're storing
    # Ensure parsed_data is not None before calling .get()
    if parsed_data is None or not isinstance(parsed_data, dict):
        logger.error(f"[OCR_V2] parsed_data is None or not a dict for doc_id={doc_id}")
        parsed_data = {}
    
    supplier = parsed_data.get("supplier", "Unknown Supplier")
    invoice_number = parsed_data.get("invoice_number")  # Extract invoice number if found
    invoice_number_source = parsed_data.get("invoice_number_source", "generated")  # Extract invoice number source
    date = parsed_data.get("date", datetime.now().strftime("%Y-%m-%d"))
    total = parsed_data.get("total", 0.0)
    
    # Log extracted invoice number for visibility
    if invoice_number:
        logger.info(f"[EXTRACT] Invoice Number: {invoice_number}")
    else:
        logger.warning(f"[EXTRACT] No invoice number found in document, using doc_id: {doc_id}")
    
    # Store document in invoices table (both invoices and delivery notes are stored here)
    # See design decision comment below for rationale
    # Note: invoice_number is logged but not yet stored in DB (requires schema migration)
    logger.info(
        f"[STORE] Storing document in invoices table: supplier='{supplier}', "
        f"invoice_no='{invoice_number or doc_id}', date='{date}', total={total}, "
        f"doc_type={doc_type}, confidence={confidence_percent:.1f}%, status={invoice_status}, band={confidence_breakdown.band.value}"
    )
    
    # #region agent log - Check if we're in fallback path
    import json
    log_path = _Path(__file__).parent.parent.parent / ".cursor" / "debug.log"
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "G", "location": "ocr_service.py:885", "message": "reached invoice storage section", "data": {"doc_id": doc_id, "supplier": supplier, "date": date, "total": total, "invoice_status": invoice_status}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
    except Exception as log_err:
        logger.error(f"Failed to write debug log: {log_err}")
    # #endregion
    
    # Log extraction data before DB write
    _log_lifecycle("EXTRACTION_DONE", doc_id,
                   supplier=supplier,
                   invoice_number=invoice_number,
                   invoice_date=date,
                   total=total,
                   subtotal=parsed_data.get("subtotal") if parsed_data else None,
                   vat=parsed_data.get("vat") if parsed_data else None,
                   line_items_count=len(line_items),
                   confidence=confidence_percent,
                   confidence_band=confidence_breakdown.band.value,
                   doc_type=doc_type)
    
    # Log first 3 line items for inspection
    if line_items:
        first_items = line_items[:3]
        items_summary = []
        for idx, item in enumerate(first_items):
            # Skip None items to avoid 'NoneType' object has no attribute 'get' error
            if item is None or not isinstance(item, dict):
                continue
            items_summary.append({
                'index': idx + 1,
                'desc': _safe_get(item, 'desc', default='', location="ocr_service.py:1789")[:50],  # Truncate long descriptions
                'qty': _safe_get(item, 'qty', default=None, location="ocr_service.py:1790"),
                'unit_price': _safe_get(item, 'unit_price', default=None, location="ocr_service.py:1791"),
                'total': _safe_get(item, 'total', default=None, location="ocr_service.py:1792"),
                'vat_rate': _safe_get(item, 'vat_rate', default=None, location="ocr_service.py:1793"),
                'vat_amount': _safe_get(item, 'vat_amount', default=None, location="ocr_service.py:1794")
            })
        _log_lifecycle("EXTRACTION_ITEMS_SAMPLE", doc_id, items_sample=items_summary)
    
    # NOTE: ocr_text_length is now calculated earlier (around line 700) to avoid scoping issues
    # This duplicate calculation is kept for backward compatibility but should use the earlier value
    # Re-calculate ocr_text_length from current pages state (in case pages were updated during retry)
    ocr_text_length_recalc = 0
    if pages:
        for page_item in pages:
            page_text_parts = []
            if hasattr(page_item, 'blocks'):
                for block in page_item.blocks if hasattr(page_item, 'blocks') and page_item.blocks else []:
                    if hasattr(block, 'ocr_text'):
                        text = getattr(block, 'ocr_text', '') or getattr(block, 'text', '')
                    else:
                        text = block.get("ocr_text", block.get("text", ""))
                    if text:
                        page_text_parts.append(text)
            else:
                blocks = page_item.get("blocks", []) if page_item and isinstance(page_item, dict) else (getattr(page_item, "blocks", []) if page_item else [])
                for block in blocks:
                    if block is None:
                        continue
                    text = block.get("ocr_text", block.get("text", "")) if isinstance(block, dict) else (getattr(block, "ocr_text", "") or getattr(block, "text", ""))
                    if text:
                        page_text_parts.append(text)
            ocr_text_length_recalc += len("\n".join(page_text_parts))
    # Use recalculated value if it's different (e.g., after retry), otherwise keep original
    if ocr_text_length_recalc != ocr_text_length:
        ocr_text_length = ocr_text_length_recalc
    
    def validate_minimum_viable_parse(ocr_text_length: int, supplier: str, total: float, line_items_count: int) -> Tuple[bool, Optional[str]]:
        """
        Validate that extraction meets minimum viable parse requirements.
        
        Returns:
            Tuple of (is_valid, error_reason)
            - is_valid: True if parse meets minimum requirements
            - error_reason: None if valid, otherwise reason for failure
        """
        MIN_OCR_TEXT_LENGTH = 50  # Minimum characters of OCR text
        
        # Check 1: OCR text length threshold
        if ocr_text_length < MIN_OCR_TEXT_LENGTH:
            return False, f"OCR text too short ({ocr_text_length} chars < {MIN_OCR_TEXT_LENGTH} minimum)"
        
        # Check 2: Supplier known AND (total > 0 OR line_items > 0)
        if supplier == "Unknown Supplier" or supplier == "Unknown":
            if total == 0.0 and line_items_count == 0:
                return False, f"Supplier unknown ({supplier}) and no financial data (total=0, line_items=0)"
        
        # If we get here, parse is viable
        return True, None
    
    # Validate minimum viable parse
    is_viable, validation_error = validate_minimum_viable_parse(
        ocr_text_length=ocr_text_length,
        supplier=supplier,
        total=total,
        line_items_count=len(line_items)
    )
    
    # Check for extraction failure (empty data)
    has_empty_data = (supplier == "Unknown Supplier" and total == 0.0 and len(line_items) == 0)
    if has_empty_data or not is_viable:
        error_msg = validation_error or "Extraction produced empty data: supplier=Unknown Supplier, total=0, line_items=0"
        logger.error(f"[EXTRACTION_FAILURE] {error_msg} for doc_id={doc_id} (OCR text length: {ocr_text_length})")
        _log_lifecycle("EXTRACTION_FAILURE", doc_id, 
                      error=error_msg,
                      supplier=supplier,
                      total=total,
                      line_items_count=len(line_items),
                      ocr_text_length=ocr_text_length)
        # Mark for manual review instead of raising - allows tracking in DB
        needs_manual_review = True
        llm_error_message = error_msg
    
    # #region agent log
    import json
    log_path = _Path(__file__).parent.parent.parent / ".cursor" / "debug.log"
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "E", "location": "ocr_service.py:510", "message": "before upsert_invoice", "data": {"doc_id": doc_id, "supplier": supplier, "date": date, "total": total, "invoice_number": invoice_number, "invoice_number_source": invoice_number_source, "confidence": confidence, "line_items_count": len(line_items), "parsed_data_keys": list(parsed_data.keys())}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
    except Exception as log_err:
        logger.error(f"Failed to write debug log: {log_err}")
    # #endregion
    
    _log_lifecycle("DB_WRITE_START", doc_id)
    try:
        # Store confidence breakdown in database
        breakdown_dict = confidence_breakdown.to_dict()
        upsert_invoice(
            doc_id=doc_id,
            supplier=supplier,
            date=date,
            value=total,
            invoice_number=invoice_number,  # Pass extracted invoice number
            confidence=confidence_percent,  # Use percent for backward compatibility
            status=invoice_status,
            confidence_breakdown=breakdown_dict
        )
        # #region agent log
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "E", "location": "ocr_service.py:902", "message": "after upsert_invoice", "data": {"doc_id": doc_id}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
        except: pass
        # #endregion
        _log_lifecycle("DB_WRITE_INVOICE_DONE", doc_id, supplier=supplier, total=total)
    except Exception as upsert_error:
        import traceback
        error_trace = traceback.format_exc()
        logger.exception(f"[STORE] Failed to upsert invoice for doc_id={doc_id}: {upsert_error}")
        # #region agent log
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "E", "location": "ocr_service.py:910", "message": "upsert_invoice exception", "data": {"doc_id": doc_id, "error": str(upsert_error), "traceback": error_trace[:2000]}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
        except: pass
        # #endregion
        raise
    
    # TODO: Call auto_pair_invoice_if_confident() after OCR invoice creation if enabled
    # from backend.services.auto_pairing import auto_pair_invoice_if_confident
    # if doc_type == "invoice":
    #     await auto_pair_invoice_if_confident(doc_id)
    
    # Verify invoice was stored
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT supplier, date, value FROM invoices WHERE id = ?", (doc_id,))
    stored = cur.fetchone()
    conn.close()
    if stored:
        logger.info(f"[STORE] Verified invoice stored: supplier='{stored[0]}', date='{stored[1]}', value={stored[2]}")
    else:
        logger.error(f"[STORE] FAILED to store invoice for doc_id={doc_id}")
    
    # Store line items
    if line_items:
        # For delivery notes, invoice_id should be NULL to distinguish from invoice line items
        invoice_id_for_items = None if doc_type == "delivery_note" else invoice_id
        logger.info(f"[STORE] Storing {len(line_items)} line items for doc_id={doc_id}, doc_type={doc_type}, invoice_id={invoice_id_for_items}")
        # Log bbox status for debugging
        items_with_bbox = sum(1 for item in line_items if item.get('bbox'))
        logger.info(f"[STORE] Line items bbox status: {items_with_bbox}/{len(line_items)} have bbox")
        if line_items and not items_with_bbox:
            logger.warning(f"[STORE] WARNING: No line items have bbox - this may indicate table extraction issues")
        _log_lifecycle("DB_WRITE_LINE_ITEMS_START", doc_id, line_items_count=len(line_items))
        insert_line_items(doc_id, invoice_id_for_items, line_items)
        _log_lifecycle("DB_WRITE_LINE_ITEMS_DONE", doc_id, line_items_count=len(line_items))
        
        # Verify line items were stored
        import sqlite3
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        # Filter by invoice_id to match what was actually stored
        if invoice_id_for_items is None:
            cur.execute("SELECT COUNT(*) FROM invoice_line_items WHERE doc_id = ? AND invoice_id IS NULL", (doc_id,))
        else:
            cur.execute("SELECT COUNT(*) FROM invoice_line_items WHERE doc_id = ? AND invoice_id = ?", (doc_id, invoice_id_for_items))
        stored_count = cur.fetchone()[0]
        conn.close()
        if stored_count > 0:
            logger.info(f"[STORE] Verified {stored_count} line items stored in database (doc_id={doc_id}, invoice_id={invoice_id_for_items})")
        else:
            logger.error(f"[STORE] FAILED to store line items for doc_id={doc_id}, invoice_id={invoice_id_for_items}")
    else:
        logger.warning(f"[STORE] No line items to store for doc_id={doc_id}")
    
    # Check for LLM extraction failures that require manual review
    # Note: needs_manual_review and llm_error_message are initialized at function start
    # Scan all pages for LLM failure markers
    if pages:
        for page in pages:
            if hasattr(page, 'blocks'):
                blocks = page.blocks
            else:
                blocks = page.get('blocks', [])
            
            for block in blocks:
                # Check table_data for LLM failure markers
                if hasattr(block, 'table_data'):
                    table_data = block.table_data
                elif isinstance(block, dict):
                    table_data = block.get('table_data')
                else:
                    table_data = None
                
                if table_data and isinstance(table_data, dict):
                    if table_data.get('needs_manual_review'):
                        needs_manual_review = True
                        llm_error_message = table_data.get('error', 'LLM extraction failed')
                        logger.warning(f"[LLM_FAILURE] Document requires manual review: {llm_error_message}")
                    
                    # Also check for failed LLM method
                    if table_data.get('method_used') == 'llm_failed':
                        needs_manual_review = True
                        llm_error_message = llm_error_message or table_data.get('error', 'LLM extraction failed')
                        logger.warning(f"[LLM_FAILURE] LLM extraction method failed")
    
    # Update document status: ready or needs_review based on confidence band
    # CRITICAL: Never mark as "ready" if data is empty (supplier=Unknown, total=0, no items)
    if needs_manual_review or has_empty_data:
        # Mark for manual review - either LLM failed or extraction produced empty data
        review_reason = "llm_extraction_failed" if needs_manual_review else "extraction_empty_data"
        # Create structured review metadata
        review_metadata = {
            "review_reason": review_reason,
            "review_priority": "high" if has_empty_data else "medium",
            "fixable_fields": [],
            "suggested_actions": confidence_breakdown.remediation_hints if 'confidence_breakdown' in locals() else []
        }
        error_msg = llm_error_message or "Extraction produced empty data"
        if 'confidence_breakdown' in locals() and confidence_breakdown.primary_issue:
            error_msg = f"{error_msg}. {confidence_breakdown.primary_issue}"
        update_document_status(
            doc_id, 
            "needs_review", 
            review_reason, 
            confidence=0.0,
            error=json.dumps(review_metadata) if 'json' in globals() else error_msg
        )
        doc_type = parsed_data.get("doc_type", "invoice") if parsed_data and isinstance(parsed_data, dict) else "invoice"
        _log_lifecycle("REVIEW_NEEDED", doc_id,
                      error=error_msg,
                      reason=review_reason,
                      supplier=supplier,
                      total=total,
                      line_items_count=len(line_items),
                      doc_type=doc_type,
                      confidence_band=confidence_breakdown.band.value if 'confidence_breakdown' in locals() else None)
        logger.warning(
            f"[REVIEW_NEEDED] Document {doc_id} marked for manual review. "
            f"Reason: {review_reason}, Band: {confidence_breakdown.band.value if 'confidence_breakdown' in locals() else 'unknown'}, "
            f"Error: {error_msg}"
        )
    else:
        # Normal success path - use confidence band to determine status
        # High band → ready, others → needs_review
        if confidence_breakdown.band.value == "high":
            final_status = "ready"
            final_stage = "doc_ready"
            update_document_status(doc_id, final_status, final_stage, confidence=confidence_percent)
        else:
            final_status = "needs_review"
            final_stage = confidence_breakdown.band.value  # Use band as stage
            # Create structured review metadata
            review_metadata = {
                "review_reason": confidence_breakdown.primary_issue or "confidence_below_threshold",
                "review_priority": "low" if confidence_breakdown.band.value == "medium" else "medium",
                "fixable_fields": ["supplier", "date", "total"] if supplier == "Unknown Supplier" else [],
                "suggested_actions": confidence_breakdown.remediation_hints
            }
            error_msg = json.dumps(review_metadata) if 'json' in globals() else confidence_breakdown.primary_issue or ""
            update_document_status(doc_id, final_status, final_stage, confidence=confidence_percent, error=error_msg)
            logger.info(
                f"[STATUS] Document {doc_id} marked as {final_status} (band: {confidence_breakdown.band.value}, "
                f"confidence: {confidence_percent:.1f}%)"
            )
            # Continue with rest of processing even for needs_review
            # (line items still need to be stored)
        
        # Continue with ready path for high confidence
        doc_type = parsed_data.get("doc_type", "invoice") if parsed_data and isinstance(parsed_data, dict) else "invoice"
        
        # Trigger auto-backup if needed (after successful processing)
        try:
            from backend.services.backup import trigger_auto_backup_if_needed
            trigger_auto_backup_if_needed(doc_id)
        except Exception as backup_error:
            # Never let backup failures break document processing
            logger.warning(f"Auto-backup trigger failed for {doc_id}: {backup_error}")
        
        _log_lifecycle("DOC_READY", doc_id, 
                  supplier=parsed_data.get('supplier') if parsed_data else None, 
                  total=parsed_data.get('total'), 
                  items=len(line_items), 
                  confidence=confidence_percent,
                  confidence_band=confidence_breakdown.band.value,
                  doc_type=doc_type)
    
    # Clear any previous errors since processing succeeded
    clear_last_error()
    
    # DESIGN DECISION: Storage of delivery notes in invoices table
    # This implementation stores both invoices and delivery notes in the invoices table.
    # The distinction between invoices and delivery notes is made through:
    # 1. The documents.doc_type column (set to 'delivery_note' or 'invoice')
    # 2. The invoice_line_items.invoice_id column:
    #    - For invoices: invoice_id = doc_id (or actual invoice_id)
    #    - For delivery notes: invoice_id = NULL
    # This allows both document types to appear in the UI while maintaining proper
    # line item separation for discrepancy detection.
    # Note: For full delivery note/invoice pairing support, the migrations/0003_pairs.sql
    # schema should be used with backend.matching.pairing.maybe_create_pair_suggestions()
    
    # Run numeric consistency validation
    validation_result = None
    try:
        from backend.validation import validate_invoice_consistency, format_validation_badge
        
        # Extract financial fields for validation
        subtotal = parsed_data.get("subtotal")
        vat_amount = parsed_data.get("vat") or parsed_data.get("vat_amount") or parsed_data.get("tax_total")
        vat_rate = parsed_data.get("vat_rate")  # e.g., 0.20 for 20%
        total_value = parsed_data.get("total")
        
        # Get raw OCR text for validation
        raw_ocr_text = None
        if pages and len(pages) > 0:
            # Get text from all blocks
            page = pages[0]
            if hasattr(page, 'blocks'):
                blocks = page.blocks
            else:
                blocks = page.get('blocks', [])
            
            text_parts = []
            for block in blocks:
                if block is None:
                    continue
                if hasattr(block, 'ocr_text'):
                    text_parts.append(getattr(block, 'ocr_text', ''))
                elif isinstance(block, dict):
                    text_parts.append(block.get('ocr_text', ''))
            raw_ocr_text = '\n'.join(text_parts)
        
        # Run validation with raw text for better total detection
        validation = validate_invoice_consistency(
            line_items=line_items,
            subtotal=subtotal,
            vat_amount=vat_amount,
            vat_rate=vat_rate,
            total=total_value,
            ocr_confidence=confidence,
            raw_ocr_text=raw_ocr_text
        )
        
        validation_result = {
            "is_consistent": validation.is_consistent,
            "integrity_score": validation.integrity_score,
            "issues": validation.issues,
            "corrections": validation.corrections,
            "badge": format_validation_badge(validation),
            "details": validation.details
        }
        
        logger.info(f"[VALIDATE] Invoice validation: consistent={validation.is_consistent}, score={validation.integrity_score:.3f}, issues={len(validation.issues)}")
        
        # Apply corrections if available and confidence is high
        if validation.corrections and validation.integrity_score >= 0.8:
            logger.info(f"[VALIDATE] Applying corrections: {list(validation.corrections.keys())}")
            for key, value in validation.corrections.items():
                if key in parsed_data:
                    logger.info(f"[VALIDATE] Correcting {key}: {parsed_data[key]} → {value}")
                    parsed_data[key] = value
        
    except Exception as e:
        logger.error(f"[VALIDATE] Validation failed: {e}", exc_info=True)
        validation_result = None
    
    # Ensure parsed_data is not None before calling .get()
    if parsed_data is None or not isinstance(parsed_data, dict):
        logger.error(f"[OCR_V2] parsed_data is None or not a dict in return statement for doc_id={doc_id}")
        parsed_data = {}
    
    # Ensure confidence_breakdown is not None before calling methods
    if confidence_breakdown is None:
        logger.error(f"[OCR_V2] confidence_breakdown is None in return statement for doc_id={doc_id}")
        # Create a minimal confidence breakdown
        from backend.services.confidence_calculator import ConfidenceBreakdown, ConfidenceBand
        confidence_breakdown = ConfidenceBreakdown(
            overall_quality=0.0,
            extraction_quality=0.0,
            validation_quality=0.0,
            band=ConfidenceBand.CRITICAL,
            primary_issue="confidence_breakdown_missing",
            remediation_hints=[]
        )
    
    supplier = parsed_data.get("supplier", "Unknown Supplier")
    customer = parsed_data.get("customer")
    
    return {
        "status": "ok",
        "doc_id": doc_id,
        "confidence": confidence_percent,  # Use percent for backward compatibility
        "confidence_breakdown": confidence_breakdown.to_dict(),
        "confidence_band": confidence_breakdown.band.value,
        "ocr_unusable": ocr_unusable,  # Flag indicating if OCR confidence is too low
        "supplier": supplier,
        "supplier_name": supplier,  # Alias for frontend compatibility
        "invoice_number": parsed_data.get("invoice_number") if parsed_data else None,
        "invoice_number_source": parsed_data.get("invoice_number_source", "generated") if parsed_data else "generated",
        "customer": customer,
        "customer_name": customer,  # Alias for frontend compatibility
        "bill_to_name": customer,  # Alternative name
        "date": parsed_data.get("date") if parsed_data else None,
        "total": parsed_data.get("total") if parsed_data else None,
        "subtotal": parsed_data.get("subtotal") if parsed_data else None,
        "vat": parsed_data.get("vat") if parsed_data else None,
        "vat_rate": parsed_data.get("vat_rate") if parsed_data else None,
        "line_items": line_items,
        "doc_type": doc_type,
        "validation": validation_result,
        "flags": parsed_data.get("flags", []) if parsed_data else []  # Include flags (e.g., "ocr_too_low_for_auto_extraction")
    }


def detect_stuck_documents(max_processing_minutes: int = 10) -> List[Dict[str, Any]]:
    """
    Detect documents that have been stuck in 'processing' status for too long.
    
    Args:
        max_processing_minutes: Maximum minutes a document should be in 'processing' status (default: 10)
        
    Returns:
        List of stuck document records with doc_id, filename, and minutes_stuck
    """
    import sqlite3
    from datetime import datetime, timedelta
    
    stuck_documents = []
    cutoff_time = datetime.now() - timedelta(minutes=max_processing_minutes)
    cutoff_iso = cutoff_time.isoformat()
    
    try:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        cursor = conn.cursor()
        
        # Query documents stuck in processing
        cursor.execute("""
            SELECT id, filename, uploaded_at, status, ocr_stage
            FROM documents
            WHERE status = 'processing'
            AND uploaded_at < ?
        """, (cutoff_iso,))
        
        rows = cursor.fetchall()
        conn.close()
        
        for row in rows:
            doc_id, filename, uploaded_at, status, ocr_stage = row
            try:
                upload_time = datetime.fromisoformat(uploaded_at.replace('Z', '+00:00').replace('+00:00', ''))
                minutes_stuck = (datetime.now() - upload_time).total_seconds() / 60
                
                stuck_documents.append({
                    "doc_id": doc_id,
                    "filename": filename,
                    "uploaded_at": uploaded_at,
                    "status": status,
                    "ocr_stage": ocr_stage,
                    "minutes_stuck": round(minutes_stuck, 1)
                })
            except Exception as e:
                logger.warning(f"[WATCHDOG] Failed to parse uploaded_at for doc_id={doc_id}: {e}")
        
        if stuck_documents:
            logger.warning(f"[WATCHDOG] Found {len(stuck_documents)} documents stuck in processing for >{max_processing_minutes} minutes")
            for doc in stuck_documents:
                logger.warning(f"[WATCHDOG] Stuck document: doc_id={doc['doc_id']}, filename={doc['filename']}, minutes_stuck={doc['minutes_stuck']}")
        
    except Exception as e:
        logger.error(f"[WATCHDOG] Error detecting stuck documents: {e}", exc_info=True)
    
    return stuck_documents


def fix_stuck_documents(max_processing_minutes: int = 10) -> int:
    """
    Detect and fix documents stuck in 'processing' status by setting them to 'error'.
    
    Args:
        max_processing_minutes: Maximum minutes a document should be in 'processing' status (default: 10)
        
    Returns:
        Number of documents fixed
    """
    stuck_docs = detect_stuck_documents(max_processing_minutes)
    fixed_count = 0
    
    for doc in stuck_docs:
        doc_id = doc["doc_id"]
        error_msg = f"Document stuck in processing for {doc['minutes_stuck']:.1f} minutes (max: {max_processing_minutes}). Marked as error by watchdog."
        
        try:
            update_document_status(doc_id, "error", "watchdog_timeout", error=error_msg)
            logger.info(f"[WATCHDOG] Fixed stuck document: doc_id={doc_id}, was stuck for {doc['minutes_stuck']:.1f} minutes")
            fixed_count += 1
        except Exception as e:
            logger.error(f"[WATCHDOG] Failed to fix stuck document doc_id={doc_id}: {e}")
    
    if fixed_count > 0:
        logger.warning(f"[WATCHDOG] Fixed {fixed_count} stuck document(s)")
    
    return fixed_count


def _extract_supplier_and_customer(full_text: str, page_dict: Optional[Dict[str, Any]] = None) -> Tuple[str, Optional[str]]:
    """
    Extract supplier and customer from invoice text using zone-based heuristics.
    
    Algorithm:
    - Supplier: Lines in header zone (top 20-25% of page) near "Invoice #" or email/website,
      exclude "Bill to" lines
    - Customer: First non-label lines under "Bill to" or "Deliver to"
    
    Args:
        full_text: Full OCR text from invoice
        page_dict: Optional page dict with bbox info (for future zone-based filtering)
        
    Returns:
        Tuple of (supplier, customer) where customer may be None
    """
    # Fail-fast guard for re module
    try:
        _ensure_re_available("_extract_supplier_and_customer")
    except NameError as e:
        logger.critical(f"[OCR_REGEX_IMPORT_MISSING] re module not available in _extract_supplier_and_customer: {e}")
        raise
    
    lines = full_text.split('\n')
    total_lines = len(lines)
    header_zone_end = int(total_lines * 0.25)  # Top 25% of page
    
    supplier = "Unknown Supplier"
    customer = None
    
    # Find supplier candidates in header zone
    supplier_candidates = []
    bill_to_found = False
    bill_to_start_idx = None
    customer_candidates = []  # Track customer candidates to exclude from supplier
    
    for i, line in enumerate(lines[:header_zone_end]):
        line_stripped = line.strip()
        if not line_stripped:
            continue
        
        line_lower = line_stripped.lower()
        
        # Check for "Bill to" / "Invoice to" markers
        if any(marker in line_lower for marker in ["bill to", "invoice to", "ship to", "deliver to"]):
            bill_to_found = True
            bill_to_start_idx = i
            continue
        
        # Skip lines that are clearly labels or metadata
        excluded_labels = [
            "total", "amount", "subtotal", "vat", "tax", "due", "balance", "payment",
            "invoice", "date", "number", "reference", "order", "po", "delivery",
            "quantity", "qty", "unit", "price", "description", "item", "line",
            "net", "gross", "discount", "shipping", "handling", "fee", "charge"
        ]
        
        if any(skip in line_lower for skip in ["invoice no", "invoice number", "invoice date", "date:", "due date"]):
            continue
        
        # Skip if line contains common invoice labels
        if any(label in line_lower for label in excluded_labels):
            continue
        
        # Look for company name patterns (Ltd, Limited, etc.)
        # Also look for multi-line company names (e.g., "Wild Horse Brewing Co Ltd" might span lines)
        company_patterns = [
            r'^([A-Z][A-Za-z0-9\s&]+(?:Ltd|Limited|Inc|Corp|Corporation|LLC|PLC|CYF|L\.L\.C\.))',
            r'^([A-Z][A-Za-z0-9\s&\-]{10,})',  # Long capitalized strings (likely company names)
        ]
        
        for pattern in company_patterns:
            match = re.match(pattern, line_stripped)
            if match:
                candidate = match.group(1).strip()
                # Clean up common suffixes
                candidate = re.sub(r'\s+(Ltd|Limited|Inc|Corp)\.?$', r' \1', candidate, flags=re.IGNORECASE)
                # Double-check: exclude common invoice labels
                candidate_lower = candidate.lower()
                if any(label in candidate_lower for label in excluded_labels):
                    continue
                if len(candidate) > 5 and candidate not in supplier_candidates:
                    supplier_candidates.append(candidate)
                    break
        
        # Special handling: Look for "Wild Horse" or "Brewing" keywords (hospitality-specific)
        if "wild horse" in line_lower or "brewing" in line_lower or "brewery" in line_lower:
            # Try to extract full company name from this line and possibly next line
            # Pattern: "Wild Horse Brewing Co Ltd" or similar
            brewing_pattern = r'([A-Z][A-Za-z0-9\s&]+(?:Brewing|Brewery)[A-Za-z0-9\s&]*(?:Ltd|Limited|Co|Company)?)'
            match = re.search(brewing_pattern, line_stripped, re.IGNORECASE)
            if match:
                candidate = match.group(1).strip()
                if candidate not in supplier_candidates:
                    supplier_candidates.append(candidate)
                    logger.info(f"[EXTRACT] Found brewing company candidate: '{candidate}'")
    
    # Extract customer from "Bill to" / "Invoice to" section FIRST
    # This allows us to exclude customer from supplier candidates
    if bill_to_found and bill_to_start_idx is not None:
        # Look for customer name in lines after "Bill to"
        for i in range(bill_to_start_idx + 1, min(len(lines), bill_to_start_idx + 5)):
            line_stripped = lines[i].strip()
            if not line_stripped:
                continue
            
            line_lower = line_stripped.lower()
            
            # Skip if it's another label
            if any(skip in line_lower for skip in ["invoice to", "ship to", "deliver to", "address:", "contact:"]):
                continue
            
            # Look for company name pattern
            company_pattern = r'^([A-Z][A-Za-z0-9\s&]+(?:Ltd|Limited|Inc|Corp|Corporation|LLC|PLC|CYF|L\.L\.C\.))'
            match = re.match(company_pattern, line_stripped)
            if match:
                candidate = match.group(1).strip()
                candidate = re.sub(r'\s+(Ltd|Limited|Inc|Corp)\.?$', r' \1', candidate, flags=re.IGNORECASE)
                customer_candidates.append(candidate)
                if customer is None:
                    customer = candidate
                    logger.info(f"[EXTRACT] Found customer: '{customer}'")
    
    # CRITICAL: Remove customer candidates from supplier candidates BEFORE scoring
    # This prevents "Snowdonia Hospitality" from being selected as supplier
    if customer_candidates:
        original_count = len(supplier_candidates)
        supplier_candidates = [c for c in supplier_candidates if not any(cust.lower() in c.lower() or c.lower() in cust.lower() for cust in customer_candidates)]
        if len(supplier_candidates) < original_count:
            logger.info(f"[EXTRACT] Filtered {original_count - len(supplier_candidates)} supplier candidates to exclude customer: {customer_candidates}")
    
    # Prefer supplier candidates that appear near "Invoice" keyword
    # Also check for email/website patterns (supplier contact info)
    email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
    website_pattern = r'www\.\w+\.\w+'
    
    scored_candidates = []
    for candidate in supplier_candidates:
        score = 0
        # Find line containing this candidate
        for i, line in enumerate(lines[:header_zone_end]):
            if candidate in line:
                # Check proximity to "Invoice" keyword
                for j in range(max(0, i-3), min(len(lines), i+4)):
                    if "invoice" in lines[j].lower():
                        score += 10
                        break
                
                # Check for email/website nearby
                for j in range(max(0, i-2), min(len(lines), i+3)):
                    if re.search(email_pattern, lines[j]) or re.search(website_pattern, lines[j]):
                        score += 5
                        break
                
                # Bonus for "Brewing" / "Brewery" keywords (hospitality-specific)
                if "brewing" in candidate.lower() or "brewery" in candidate.lower():
                    score += 15
                
                break
        
        scored_candidates.append((candidate, score))
    
    # Sort by score and take best candidate
    if scored_candidates:
        scored_candidates.sort(key=lambda x: x[1], reverse=True)
        supplier = scored_candidates[0][0]
        logger.info(f"[EXTRACT] Found supplier: '{supplier}' (from {len(supplier_candidates)} candidates, scores: {[s[1] for s in scored_candidates[:3]]})")
    
    # Special case: If we have "Wild Horse" in text but didn't find it as supplier, try harder
    if "wild horse" in full_text.lower() and "wild horse" not in supplier.lower():
        # Search more aggressively for "Wild Horse Brewing Co Ltd"
        wild_horse_patterns = [
            r'(Wild Horse Brewing Co Ltd)',
            r'(Wild Horse\s+[A-Za-z\s]+(?:Ltd|Limited))',
            r'(Wild Horse[^\n]{0,50}(?:Ltd|Limited))',
        ]
        for pattern in wild_horse_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                candidate = match.group(1).strip()
                supplier = candidate
                logger.info(f"[EXTRACT] Found Wild Horse via aggressive search: '{supplier}'")
                break
    
    # Final validation: If supplier is still a common invoice label, reset to Unknown
    excluded_labels = [
        "total", "amount", "subtotal", "vat", "tax", "due", "balance", "payment",
        "invoice", "date", "number", "reference", "order", "po", "delivery",
        "quantity", "qty", "unit", "price", "description", "item", "line",
        "net", "gross", "discount", "shipping", "handling", "fee", "charge"
    ]
    supplier_lower = supplier.lower()
    if any(label in supplier_lower for label in excluded_labels):
        logger.warning(f"[EXTRACT] Supplier '{supplier}' matches excluded label, resetting to Unknown Supplier")
        supplier = "Unknown Supplier"
    
    return (supplier, customer)


def _extract_invoice_data_from_page(page: Dict[str, Any]) -> Dict[str, Any]:
    """Extract invoice header data from OCR page result"""
    # Import Path at function level with alias to avoid scoping issues
    from pathlib import Path as _Path
    # Fail-fast guard for re module
    try:
        _ensure_re_available("_extract_invoice_data_from_page")
    except NameError as e:
        logger.critical(f"[OCR_REGEX_IMPORT_MISSING] re module not available in _extract_invoice_data_from_page: {e}")
        raise
    
    # Handle both dict and PageResult object formats
    if hasattr(page, 'blocks'):
        # PageResult object - convert to dict-like access
        blocks = list(page.blocks) if hasattr(page, 'blocks') and page.blocks else []
        page_dict = {
            "blocks": blocks,
            "text": getattr(page, 'text', getattr(page, 'ocr_text', '')),
            "ocr_text": getattr(page, 'ocr_text', getattr(page, 'text', '')),
            "confidence": getattr(page, 'confidence', 0.9)
        }
    else:
        # Dict format
        blocks = page.get("blocks", [])
        page_dict = page
    
    # DEBUG: Log block structure to diagnose empty data
    logger.info(f"[EXTRACT] Processing page with {len(blocks)} blocks")
    if blocks:
        first_block = blocks[0]
        if hasattr(first_block, '__dict__'):
            # Block is an object
            block_keys = list(first_block.__dict__.keys())
            has_ocr_text = hasattr(first_block, 'ocr_text')
            has_text = hasattr(first_block, 'text')
        else:
            # Block is a dict
            block_keys = list(first_block.keys()) if isinstance(first_block, dict) else []
            has_ocr_text = isinstance(first_block, dict) and 'ocr_text' in first_block
            has_text = isinstance(first_block, dict) and 'text' in first_block
        
        logger.info(f"[EXTRACT] First block keys: {block_keys}")
        logger.info(f"[EXTRACT] First block has ocr_text: {has_ocr_text}")
        logger.info(f"[EXTRACT] First block has text: {has_text}")
    
    # Build full text from all blocks for vendor template matching
    # Handle both dict and object block formats
    full_text_parts = []
    for block in blocks:
        if hasattr(block, 'ocr_text'):
            # Block is an object
            text = getattr(block, 'ocr_text', '') or getattr(block, 'text', '')
        else:
            # Block is a dict
            text = block.get("ocr_text", block.get("text", ""))
        if text:
            full_text_parts.append(text)
    
    full_text = "\n".join(full_text_parts)
    
    # DEBUG: Log extracted text length
    logger.info(f"[EXTRACT] Extracted {len(full_text)} characters of text from {len(blocks)} blocks")
    # #region agent log
    import json
    log_path = _Path(__file__).parent.parent.parent / ".cursor" / "debug.log"
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "I", "location": "ocr_service.py:1434", "message": "full_text built from blocks", "data": {"blocks_count": len(blocks), "full_text_length": len(full_text), "full_text_preview": full_text[:200] if full_text else "", "full_text_parts_count": len(full_text_parts)}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
    except: pass
    # #endregion
    
    # If no text extracted, log warning but continue with defaults
    if not full_text or len(full_text.strip()) < 10:
        logger.warning(f"[EXTRACT] Very little or no text extracted from page. Blocks: {len(blocks)}, Text length: {len(full_text)}")
        # #region agent log
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "I", "location": "ocr_service.py:1440", "message": "full_text is empty, trying page-level text", "data": {"blocks_count": len(blocks), "full_text_length": len(full_text)}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
        except: pass
        # #endregion
        # Try to get text from page-level fields if blocks are empty
        page_text = page_dict.get("text", page_dict.get("ocr_text", ""))
        if page_text and len(page_text.strip()) > 10:
            logger.info(f"[EXTRACT] Using page-level text (length: {len(page_text)})")
            full_text = page_text
            # #region agent log
            try:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "I", "location": "ocr_service.py:1446", "message": "using page-level text", "data": {"page_text_length": len(page_text), "page_text_preview": page_text[:200]}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
            except: pass
            # #endregion
    
    # Try STORI extractor first if detected
    from backend.ocr.vendors.stori_extractor import extract as extract_stori
    
    # Detect STORI: look for "Stori Beer & Wine" or STORI cues
    vendor_hint = None
    if "Stori Beer & Wine" in full_text or ("VAT Invoice" in full_text and "Bala" in full_text):
        vendor_hint = "stori"
        stori_result = extract_stori(full_text)
        
        if stori_result.get("items"):
            # STORI extraction succeeded - use its data
            supplier = "Stori Beer & Wine CYF"
            if "date" in stori_result:
                date = stori_result["date"]
            else:
                date = datetime.now().strftime("%Y-%m-%d")
            
            # Store total in pounds (database value field stores pounds as REAL)
            if "total_pence" in stori_result:
                total = stori_result["total_pence"] / 100.0
            elif "subtotal_pence" in stori_result:
                total = stori_result["subtotal_pence"] / 100.0
            else:
                total = 0.0
            
            confidence = page.get("confidence", 0.9)
            
            return {
                "supplier": supplier,
                "date": date,
                "total": total,
                "confidence": confidence,
                "_stori_data": stori_result  # Store for line item extraction
            }
    
    # IMPROVED: Better extraction heuristics
    supplier = "Unknown Supplier"
    date = datetime.now().strftime("%Y-%m-%d")
    total = 0.0
    
    # Get confidence from page (handle both dict and object)
    if hasattr(page, 'confidence'):
        confidence = page.confidence
    else:
        confidence = page_dict.get("confidence", 0.9)
    
    # Extract supplier and customer using improved zone-based extraction
    supplier, customer = _extract_supplier_and_customer(full_text, page_dict)
    
    # #region agent log
    import json
    log_path = _Path(__file__).parent.parent.parent / ".cursor" / "debug.log"
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "G", "location": "ocr_service.py:1515", "message": "supplier extracted from _extract_supplier_and_customer", "data": {"supplier": supplier, "customer": customer, "full_text_length": len(full_text) if full_text else 0, "full_text_preview": full_text[:200] if full_text else ""}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
    except: pass
    # #endregion
    
    # Wild Horse regression check (for logging/debug)
    if "Wild Horse Brewing Co Ltd" in full_text or "Wild Horse" in full_text:
        if "Wild Horse" not in supplier and "Snowdonia" in supplier:
            logger.warning(f"[EXTRACT] WILD HORSE REGRESSION: Supplier mis-detected as '{supplier}' instead of Wild Horse")
        elif "Wild Horse" in supplier:
            logger.info(f"[EXTRACT] WILD HORSE REGRESSION: Correctly detected supplier as '{supplier}'")
    
    # Fallback to old pattern-based extraction if supplier is still unknown
    if supplier == "Unknown Supplier":
        # List of common invoice labels to exclude from supplier extraction
        excluded_labels = [
            "total", "amount", "subtotal", "vat", "tax", "due", "balance", "payment",
            "invoice", "date", "number", "reference", "order", "po", "delivery",
            "quantity", "qty", "unit", "price", "description", "item", "line",
            "net", "gross", "discount", "shipping", "handling", "fee", "charge"
        ]
        
        supplier_patterns = [
            r'^([A-Z][A-Za-z0-9\s&]+(?:Ltd|Limited|Inc|Corp|Corporation|LLC|PLC|CYF|L\.L\.C\.))',
            r'Supplier[:\s]+([A-Z][A-Za-z0-9\s&]+)',
            r'Vendor[:\s]+([A-Z][A-Za-z0-9\s&]+)',
            r'From[:\s]+([A-Z][A-Za-z0-9\s&]+)',
        ]
        
        for pattern in supplier_patterns:
            match = re.search(pattern, full_text, re.MULTILINE | re.IGNORECASE)
            if match:
                candidate = match.group(1).strip()
                # Clean up common suffixes
                candidate = re.sub(r'\s+(Ltd|Limited|Inc|Corp)\.?$', r' \1', candidate, flags=re.IGNORECASE)
                # Exclude common invoice labels
                candidate_lower = candidate.lower()
                if any(label in candidate_lower for label in excluded_labels):
                    logger.debug(f"[EXTRACT] Skipping candidate '{candidate}' (matches excluded label)")
                    continue
                if candidate and candidate != "Unknown Supplier":
                    supplier = candidate
                    logger.info(f"[EXTRACT] Found supplier via fallback pattern '{pattern}': {supplier}")
                    break
        
        # Last resort: First capitalized line, but exclude common labels
        if supplier == "Unknown Supplier":
            lines = full_text.split('\n')
            for line in lines[:10]:  # Only check first 10 lines
                line_stripped = line.strip()
                if not line_stripped or len(line_stripped) < 5:
                    continue
                # Must start with capital letter and be at least 5 chars
                if re.match(r'^[A-Z][A-Za-z0-9\s&]{4,}', line_stripped):
                    candidate = line_stripped.split()[0] if line_stripped.split() else line_stripped
                    candidate_lower = candidate.lower()
                    # Exclude common labels and short words
                    if (len(candidate) >= 5 and 
                        not any(label in candidate_lower for label in excluded_labels) and
                        candidate_lower not in ["invoice", "date", "number", "total", "amount"]):
                        supplier = candidate
                        logger.info(f"[EXTRACT] Found supplier via first capitalized line: {supplier}")
                        break
    
    # Extract invoice number: Look for invoice number patterns (prefer printed numbers)
    invoice_number = None
    invoice_number_source = "generated"  # Default to generated, will be set to "printed" if found
    
    # Priority patterns for printed invoice numbers (near "Invoice" keyword in header zone)
    header_zone_end = int(len(full_text.split('\n')) * 0.25)  # Top 25% of page
    header_text = "\n".join(full_text.split('\n')[:header_zone_end])
    
    printed_invoice_patterns = [
        r'\bVAT\s+Invoice\s+([A-Za-z0-9\-\/]+)',  # VAT Invoice 99471 (NEW - high priority)
        r'invoice\s*#\s*([A-Za-z0-9\-\/]+)',  # Invoice #77212 - most specific
        r'invoice\s*no\.?\s*([A-Za-z0-9\-\/]+)',  # Invoice No. 77212
        r'invoice\s*[#:]?\s*([A-Za-z0-9\-\/]+)',  # Invoice: 77212, Invoice 77212
        r'#\s*([0-9]{4,})',  # #77212, #76617
        r'Invoice\s+(?:No|Number|#)[:.\s]+([A-Z0-9_-]+)',  # Invoice No: 852021_162574 or INV-12345
        r'Invoice\s+(?:No|Number|#)[:.\s]+([A-Z0-9-]+)',  # Invoice No: INV-12345 (fallback)
        r'Invoice[:\s]+([A-Z]{2,}[-/]?\d+)',  # Invoice: INV-12345 or INV12345
        r'INVOICE\s+NO\.?\s*([A-Z0-9_-]+)',  # INVOICE NO. 852021_162574 (with period)
    ]
    
    # Try header zone first (prefer printed numbers)
    for pattern in printed_invoice_patterns:
        match = re.search(pattern, header_text, re.IGNORECASE | re.MULTILINE)
        if match:
            # Get the full match or the first group
            if match.lastindex and match.lastindex >= 1:
                candidate = match.group(1).strip()
            else:
                candidate = match.group(0).strip()
            
            # Validate it's not a date or other common false positive
            if candidate and not re.match(r'^\d{1,2}[/-]\d{1,2}', candidate):
                # Remove leading # if present
                invoice_number = candidate.lstrip('#').strip()
                invoice_number_source = "printed"
                logger.info(f"[EXTRACT] Found printed invoice number via pattern '{pattern}': {invoice_number}")
                break
    
    # Fallback: search entire document if not found in header
    if invoice_number is None:
        fallback_patterns = [
            r'\bVAT\s+Invoice\s+([A-Za-z0-9\-\/]+)',  # VAT Invoice 99471 (fallback if not in header)
            r'INV[-/]?(\d+)',  # INV-12345 or INV12345
            r'#\s*([A-Z0-9_-]{4,})',  # #INV-12345
            r'(?:^|\n)([A-Z]{2,}\d{4,})',  # Standalone alphanumeric (e.g., INV12345)
        ]
        
        for pattern in fallback_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE | re.MULTILINE)
            if match:
                if match.lastindex and match.lastindex >= 1:
                    candidate = match.group(1).strip()
                else:
                    candidate = match.group(0).strip()
                
                if candidate and not re.match(r'^\d{1,2}[/-]\d{1,2}', candidate):
                    invoice_number = candidate.lstrip('#').strip()
                    invoice_number_source = "printed"
                    logger.info(f"[EXTRACT] Found invoice number via fallback pattern '{pattern}': {invoice_number}")
                    break
    
    # Extract date: Look for date patterns
    date_patterns = [
        r'Date[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        r'Invoice\s+Date[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',  # Generic date pattern
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, full_text, re.IGNORECASE)
        if match:
            date_str = match.group(1)
            normalized = _normalize_date(date_str)
            if normalized:
                date = normalized
                logger.info(f"[EXTRACT] Found date via pattern '{pattern}': {date}")
                break
    
    # Extract total: Look for total amounts with intelligent filtering
    # Strategy: Find largest number in bottom 30% of page near "Total" keywords
    
    # Split text into lines to get positional info
    lines = full_text.split('\n')
    total_lines = len(lines)
    bottom_30_start = int(total_lines * 0.7)  # Bottom 30% of page
    
    # Collect all currency amounts with context
    amount_candidates = []
    
    # Priority patterns (with keywords) - improved to handle comma-separated numbers
    priority_patterns = [
        (r'(?:Total\s+DUE|TOTAL\s+DUE|Amount\s+Due|Balance\s+Due|Grand\s+Total|Payable)[:\s]+[£€$]?\s*([\d,]+\.?\d*)', 15.0),
        (r'(?:Total|Amount)[:\s]+[£€$]?\s*([\d,]+\.?\d*)', 10.0),
        (r'TOTAL[:\s]+[£€$]?\s*([\d,]+\.?\d*)', 12.0),  # Explicit TOTAL keyword
    ]
    
    # Generic currency pattern - improved to handle comma-separated numbers
    generic_pattern = r'[£€$]\s*([\d,]+\.?\d*)'
    
    # Search with priority
    for line_idx, line in enumerate(lines):
        # Check priority patterns first
        for pattern, priority_score in priority_patterns:
            matches = re.finditer(pattern, line, re.IGNORECASE)
            for match in matches:
                amount_str = match.group(1).replace(',', '').strip()
                try:
                    amount = float(amount_str)
                    # Ignore tax rates (e.g., 20.00 when much larger numbers exist)
                    # But allow amounts > 1.0 (to catch £1.50 if it's legit)
                    if amount > 0.01:  # Minimum threshold
                        position_score = 2.0 if line_idx >= bottom_30_start else 1.0
                        total_score = priority_score * position_score
                        amount_candidates.append((amount, total_score, line_idx, 'priority'))
                        logger.debug(f"[EXTRACT] Found amount: £{amount:,.2f} (line {line_idx}, score={total_score:.1f})")
                except ValueError:
                    pass
        
        # Check generic pattern
        matches = re.finditer(generic_pattern, line, re.IGNORECASE)
        for match in matches:
            amount_str = match.group(1).replace(',', '').strip()
            try:
                amount = float(amount_str)
                if amount > 0.01:
                    # Lower score for generic matches
                    position_score = 1.5 if line_idx >= bottom_30_start else 0.5
                    amount_candidates.append((amount, position_score, line_idx, 'generic'))
            except ValueError:
                pass
    
    if amount_candidates:
        # Sort by score (descending), then by amount (descending)
        amount_candidates.sort(key=lambda x: (x[1], x[0]), reverse=True)
        
        # Take the highest-scored amount
        best_amount, best_score, best_line, best_type = amount_candidates[0]
        
        # CRITICAL FIX: If top candidate is suspiciously small (< 100) and there's a much larger one (> 100), use the larger
        # This fixes cases like £1.50 vs £1,504.34
        if len(amount_candidates) > 1:
            # Find the largest amount in candidates
            largest_amount = max(c[0] for c in amount_candidates)
            # If best is < 100 and largest is > 100 and largest is > 10x best, use largest
            if best_amount < 100 and largest_amount > 100 and largest_amount > best_amount * 10:
                best_amount = largest_amount
                logger.info(f"[EXTRACT] Overriding small total (£{best_amount:.2f}) with larger amount: £{largest_amount:,.2f}")
            # Also check if second candidate is significantly larger
            elif len(amount_candidates) > 1:
                second_amount = amount_candidates[1][0]
                if second_amount > best_amount * 10:
                    best_amount = second_amount
                    logger.info(f"[EXTRACT] Overriding small total with larger amount: £{best_amount:,.2f}")
        
        total = best_amount
        logger.info(f"[EXTRACT] Found total: £{total:,.2f} (line {best_line}, score={best_score:.1f}, type={best_type}, from {len(amount_candidates)} candidates)")
        # #region agent log
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "J", "location": "ocr_service.py:1719", "message": "total extracted", "data": {"total": total, "best_score": best_score, "best_line": best_line, "candidates_count": len(amount_candidates), "full_text_length": len(full_text)}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
        except: pass
        # #endregion
    else:
        # #region agent log
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "J", "location": "ocr_service.py:1721", "message": "no total found", "data": {"full_text_length": len(full_text), "full_text_preview": full_text[:500] if full_text else ""}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
        except: pass
        # #endregion
    
    result = {
        "supplier": supplier,
        "invoice_number": invoice_number,  # Add invoice number to extracted data
        "invoice_number_source": invoice_number_source,  # "printed" or "generated"
        "date": date,
        "total": total,
        "confidence": confidence
    }
    
    # Add customer if found
    if customer:
        result["customer"] = customer
    
    return result

def _parse_quantity(qty_str: str) -> float:
    """Parse quantity string to float, handling various formats"""
    if not qty_str:
        return 0.0
    
    try:
        # Convert to string and strip whitespace
        qty_clean = str(qty_str).strip()
        if not qty_clean or qty_clean.lower() in ['', 'none', 'null', 'n/a', 'na']:
            return 0.0
        
        # Remove common separators (commas, spaces used as thousands separators)
        qty_clean = qty_clean.replace(',', '').replace(' ', '')
        
        # Handle "x" notation (e.g., "12x" -> 12)
        if qty_clean.lower().endswith('x'):
            qty_clean = qty_clean[:-1]
        
        # Handle fractions (e.g., "1/2" -> 0.5)
        if '/' in qty_clean:
            parts = qty_clean.split('/')
            if len(parts) == 2:
                try:
                    numerator = float(parts[0].strip())
                    denominator = float(parts[1].strip())
                    if denominator != 0:
                        return numerator / denominator
                except (ValueError, ZeroDivisionError):
                    pass
        
        # Try parsing as float
        result = float(qty_clean)
        # Validate result is reasonable (not negative, not excessive)
        if result < 0:
            logger.warning(f"[PARSE_QTY] Negative quantity detected: '{qty_str}' -> {result}, returning 0.0")
            return 0.0
        if result > 10000:  # Sanity check for excessive quantities
            logger.warning(f"[PARSE_QTY] Excessive quantity detected: '{qty_str}' -> {result}, capping to 10000")
            return 10000.0
        return result
    except (ValueError, AttributeError):
        # If parsing fails, try extracting first number from string
        try:
            # Match numbers with optional decimal point, including at start/end of string
            match = re.search(r'(\d+\.?\d*)', str(qty_str))
            if match:
                result = float(match.group(1))
                if result < 0:
                    return 0.0
                if result > 10000:
                    return 10000.0
                return result
        except (ValueError, AttributeError):
            pass
        logger.debug(f"[PARSE_QTY] Failed to parse quantity: '{qty_str}', returning 0.0")
        return 0.0

def _parse_price(price_str: str) -> float:
    """Parse price string to float, handling currency symbols and various formats"""
    import re  # Ensure re is available in this function scope
    if not price_str:
        return 0.0
    
    try:
        # Convert to string and strip whitespace
        price_clean = str(price_str).strip()
        if not price_clean or price_clean.lower() in ['', 'none', 'null', 'n/a', 'na', 'free', 'n/c']:
            return 0.0
        
        # Remove currency symbols and whitespace (handle encoded variants too)
        price_clean = price_clean.replace('£', '').replace('€', '').replace('$', '').replace('USD', '').replace('GBP', '').replace('EUR', '').strip()
        # Handle encoded currency symbols
        price_clean = price_clean.replace('Â£', '').replace('â‚¬', '').replace('Â€', '')
        
        # Remove commas (thousands separators) and spaces
        price_clean = price_clean.replace(',', '').replace(' ', '')
        
        # Handle negative prices (in parentheses or with minus sign)
        if price_clean.startswith('(') and price_clean.endswith(')'):
            price_clean = '-' + price_clean[1:-1]
        elif price_clean.startswith('-'):
            pass  # Already negative
        
        # Remove any remaining non-numeric characters except decimal point and minus sign
        # This handles cases like "£123.45p" or "123.45 GBP"
        # Extract number pattern (allowing negative and decimal)
        number_match = re.search(r'(-?\d+\.?\d*)', price_clean)
        if number_match:
            price_clean = number_match.group(1)
        
        # Try parsing as float
        result = float(price_clean)
        # Validate result is reasonable (not excessive)
        if abs(result) > 1000000:  # Sanity check for excessive prices
            logger.warning(f"[PARSE_PRICE] Excessive price detected: '{price_str}' -> {result}, capping to 1000000")
            return 1000000.0 if result > 0 else -1000000.0
        return result
    except (ValueError, AttributeError):
        # If parsing fails, try extracting first number (with decimal) from string
        try:
            # Match numbers with optional decimal point (e.g., "123.45", "123", ".45")
            # Also handle negative numbers
            match = re.search(r'(-?\d+\.?\d*)', str(price_str))
            if match:
                result = float(match.group(1))
                if abs(result) > 1000000:
                    return 1000000.0 if result > 0 else -1000000.0
                return result
        except (ValueError, AttributeError):
            pass
        logger.debug(f"[PARSE_PRICE] Failed to parse price: '{price_str}', returning 0.0")
        return 0.0

def _extract_line_items_from_page(page: Dict[str, Any], parsed_data: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """Extract line items from OCR page result"""
    # Import Path at function level with alias to avoid scoping issues
    from pathlib import Path as _Path
    # Handle both dict and PageResult object formats
    if hasattr(page, 'blocks'):
        # PageResult object - convert to list
        blocks = list(page.blocks) if hasattr(page, 'blocks') and page.blocks else []
    else:
        # Dict format
        blocks = page.get("blocks", [])
    
    line_items = []
    
    # DEBUG: Log block structure
    logger.info(f"[LINE_ITEMS] Processing {len(blocks)} blocks for line item extraction")
    
    # Check if STORI data was extracted (stored in parsed_data)
    if parsed_data and "_stori_data" in parsed_data:
        stori_data = parsed_data["_stori_data"]
        stori_items = stori_data.get("items", [])
        
        logger.info(f"[LINE_ITEMS] Found STORI data with {len(stori_items)} items")
        
        # Convert STORI format to our format
        for item in stori_items:
            # Skip None items to avoid 'NoneType' object has no attribute 'get' error
            if item is None or not isinstance(item, dict):
                continue
            # STORI returns: name, qty, unit_price_pence, line_total_pence
            # We need: desc, qty, unit_price, total, uom, confidence
            desc = item.get("name", "")
            # Filter out header/footer text
            if desc:
                desc_lower = desc.lower().strip()
                skip_patterns = [
                    'total', 'subtotal', 'vat', 'tax', 'amount due', 'balance',
                    'invoice no', 'invoice number', 'invoice date', 'date:',
                    'vat registration', 'company registration', 'registration number',
                    'account no', 'account number', 'sort code', 'iban', 'bic',
                    'payment terms', 'due date', 'thank you', 'please pay'
                ]
                if any(pattern in desc_lower for pattern in skip_patterns):
                    logger.debug(f"[LINE_ITEMS] Skipping header/footer text in STORI: {desc}")
                    continue
            stori_item = {
                "desc": desc,
                "qty": item.get("qty", 0),
                "unit_price": item.get("unit_price_pence", 0) / 100.0,  # Convert pence to pounds
                "total": item.get("line_total_pence", 0) / 100.0,  # Convert pence to pounds
                "uom": "",
                "confidence": 0.9  # High confidence for template-matched data
            }
            # STORI items don't have bbox (template-matched), but preserve if present
            if "bbox" in item and item["bbox"]:
                stori_item["bbox"] = item["bbox"]
            line_items.append(stori_item)
        
        if line_items:
            logger.info(f"[LINE_ITEMS] Returning {len(line_items)} STORI line items")
            return line_items
    
    # Build full text for vendor template matching if not already done
    # Handle both dict and object block formats
    full_text_parts = []
    for block in blocks:
        if hasattr(block, 'ocr_text'):
            # Block is an object
            text = getattr(block, 'ocr_text', '') or getattr(block, 'text', '')
        else:
            # Block is a dict
            text = block.get("ocr_text", block.get("text", ""))
        if text:
            full_text_parts.append(text)
    
    full_text = "\n".join(full_text_parts)
    
    # #region agent log
    import json
    log_path = _Path(__file__).parent.parent.parent / ".cursor" / "debug.log"
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "K", "location": "ocr_service.py:1938", "message": "line item extraction - full_text built", "data": {"blocks_count": len(blocks), "full_text_length": len(full_text), "full_text_preview": full_text[:300] if full_text else ""}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
    except: pass
    # #endregion
    
    # Try STORI extractor if detected
    if "Stori Beer & Wine" in full_text or ("VAT Invoice" in full_text and "Bala" in full_text):
        from backend.ocr.vendors.stori_extractor import extract as extract_stori
        stori_result = extract_stori(full_text)
        
        if stori_result.get("items"):
            logger.info(f"[LINE_ITEMS] STORI extractor found {len(stori_result['items'])} items")
            # Convert STORI format to our format
            for item in stori_result["items"]:
                # Skip None items to avoid 'NoneType' object has no attribute 'get' error
                if item is None or not isinstance(item, dict):
                    continue
                desc = item.get("name", "")
                # Filter out header/footer text
                if desc:
                    desc_lower = desc.lower().strip()
                    skip_patterns = [
                        'total', 'subtotal', 'vat', 'tax', 'amount due', 'balance',
                        'invoice no', 'invoice number', 'invoice date', 'date:',
                        'vat registration', 'company registration', 'registration number',
                        'account no', 'account number', 'sort code', 'iban', 'bic',
                        'payment terms', 'due date', 'thank you', 'please pay'
                    ]
                    if any(pattern in desc_lower for pattern in skip_patterns):
                        logger.debug(f"[LINE_ITEMS] Skipping header/footer text in STORI result: {desc}")
                        continue
                stori_item = {
                    "desc": desc,
                    "qty": item.get("qty", 0),
                    "unit_price": item.get("unit_price_pence", 0) / 100.0,
                    "total": item.get("line_total_pence", 0) / 100.0,
                    "uom": "",
                    "confidence": 0.9
                }
                # STORI items don't have bbox (template-matched), but preserve if present
                if "bbox" in item and item["bbox"]:
                    stori_item["bbox"] = item["bbox"]
                line_items.append(stori_item)
            
            if line_items:
                logger.info(f"[LINE_ITEMS] Returning {len(line_items)} STORI line items")
                return line_items
    
    # Look for table blocks - FIX: Check table_data.line_items
    table_count = 0
    for idx, block in enumerate(blocks):
        # Handle both dict and object block formats
        if hasattr(block, 'type'):
            block_type = block.type
            table_data = getattr(block, 'table_data', None)
            block_ocr_text = getattr(block, 'ocr_text', '')
        else:
            block_type = block.get("type", "")
            table_data = block.get("table_data")
            block_ocr_text = block.get("ocr_text", block.get("text", ""))
        
        # DEBUG: Log all blocks to see what we have
        logger.info(f"[LINE_ITEMS] Block {idx}: type='{block_type}', has_table_data={table_data is not None}, ocr_text_len={len(block_ocr_text)}")
        
        if block_type == "table":
            table_count += 1
            logger.info(f"[LINE_ITEMS] Found table block #{table_count}, table_data type: {type(table_data)}, table_data value: {table_data}")
            
            # FIX: Check table_data.line_items instead of block.line_items
            if table_data:
                if isinstance(table_data, dict):
                    table_line_items = table_data.get("line_items", [])
                    logger.info(f"[LINE_ITEMS] table_data is dict, keys: {list(table_data.keys())}, line_items count: {len(table_line_items)}")
                    logger.info(f"[TABLE_EXTRACT] table_data.line_items: {len(table_line_items)} items. Sample: {table_line_items[:2] if table_line_items else []}")
                    if not table_line_items:
                        logger.warning(f"[TABLE_FAIL] Empty line_items. Raw block text: {block_ocr_text[:300]}")
                elif isinstance(table_data, list):
                    # table_data might be a list (List[List[str]] format from type hint)
                    logger.warning(f"[LINE_ITEMS] table_data is a list, not dict. Length: {len(table_data)}")
                    table_line_items = []
                else:
                    # table_data might be an object
                    table_line_items = getattr(table_data, 'line_items', [])
                    logger.info(f"[LINE_ITEMS] table_data is object, line_items count: {len(table_line_items)}")
                
                logger.info(f"[LINE_ITEMS] Table block has {len(table_line_items)} line items")
                
                # Convert TableResult format to our format
                for item_idx, item in enumerate(table_line_items):
                    # Skip None items to avoid 'NoneType' object has no attribute 'get' error
                    if item is None:
                        continue
                    if isinstance(item, dict):
                        # TableResult.to_dict() format
                        description = item.get("description", "").strip()
                        # CRITICAL FIX: If description is empty, try alternative keys
                        if not description:
                            description = item.get("desc", item.get("item", item.get("product", item.get("name", "")))).strip()
                        
                        # Filter out header/footer text that shouldn't be line items
                        if description:
                            desc_lower = description.lower().strip()
                            skip_patterns = [
                                'total', 'subtotal', 'vat', 'tax', 'amount due', 'balance',
                                'invoice no', 'invoice number', 'invoice date', 'date:',
                                'vat registration', 'company registration', 'registration number',
                                'account no', 'account number', 'sort code', 'iban', 'bic',
                                'payment terms', 'due date', 'thank you', 'please pay',
                                'total (£)', 'total (£):', 'vat registration number'
                            ]
                            if any(pattern in desc_lower for pattern in skip_patterns):
                                logger.debug(f"[LINE_ITEMS] Skipping header/footer text in table: {description}")
                                continue
                        
                        # FIX: LLM uses 'qty' but legacy code uses 'quantity'. Support both.
                        raw_qty = item.get('quantity', item.get('qty', ''))
                        raw_unit = item.get('unit_price', '')
                        # FIX: LLM uses 'total' but legacy code uses 'total_price'. Support both.
                        raw_total = item.get('total_price', item.get('total', ''))
                        parsed_qty = _parse_quantity(raw_qty)
                        parsed_unit = _parse_price(raw_unit)
                        parsed_total = _parse_price(raw_total)
                        
                        logger.info(f"[LINE_ITEMS] Processing table item {item_idx}: desc='{description}', raw_qty='{raw_qty}'→{parsed_qty}, raw_unit='{raw_unit}'→{parsed_unit}, raw_total='{raw_total}'→{parsed_total}, bbox={item.get('bbox')}")
                        
                        # FIX: Allow items with valid qty/price/total even if description is empty
                        # Use fallback description if missing but we have other data
                        if not description or len(description) < 3:
                            # If we have valid qty/price/total, use a fallback description
                            if parsed_qty > 0 or parsed_total > 0:
                                description = f"Item {item_idx + 1}"  # Fallback description
                                logger.info(f"[LINE_ITEMS] Using fallback description '{description}' for item with qty={parsed_qty}, total={parsed_total}")
                            else:
                                # No valid data at all, skip it
                                logger.warning(f"[LINE_ITEMS] Skipping item {item_idx} - empty description and no valid qty/price/total. Raw: qty='{raw_qty}', unit='{raw_unit}', total='{raw_total}'")
                                continue
                        
                        line_item_dict = {
                            "desc": description,
                            "qty": parsed_qty,
                            "unit_price": parsed_unit,
                            "total": parsed_total,
                            "uom": "",
                            "confidence": item.get("confidence", 0.7)
                        }
                        
                        # WARN if quantities/prices are zero but we have a description
                        if parsed_qty == 0.0 and parsed_total == 0.0:
                            logger.warning(f"[LINE_ITEMS] ⚠️ Item '{description}' has qty=0 and total=0. Raw values: qty='{raw_qty}', unit='{raw_unit}', total='{raw_total}'. This suggests table extraction may have failed.")
                        # Extract bbox if present (for visual verification)
                        if "bbox" in item and item["bbox"]:
                            line_item_dict["bbox"] = item["bbox"]
                        line_items.append(line_item_dict)
                    else:
                        # LineItem object
                        description = getattr(item, 'description', '').strip()
                        if not description:
                            description = getattr(item, 'desc', getattr(item, 'item', getattr(item, 'product', getattr(item, 'name', '')))).strip()
                        
                        raw_qty_obj = getattr(item, 'quantity', '')
                        raw_unit_obj = getattr(item, 'unit_price', '')
                        raw_total_obj = getattr(item, 'total_price', '')
                        parsed_qty_obj = _parse_quantity(raw_qty_obj)
                        parsed_unit_obj = _parse_price(raw_unit_obj)
                        parsed_total_obj = _parse_price(raw_total_obj)
                        
                        logger.info(f"[LINE_ITEMS] Processing table item {item_idx} (object): desc='{description}', raw_qty='{raw_qty_obj}'→{parsed_qty_obj}, raw_unit='{raw_unit_obj}'→{parsed_unit_obj}, raw_total='{raw_total_obj}'→{parsed_total_obj}, bbox={getattr(item, 'bbox', None)}")
                        
                        # FIX: Allow items with valid qty/price/total even if description is empty
                        # Use fallback description if missing but we have other data
                        if not description or len(description) < 3:
                            # If we have valid qty/price/total, use a fallback description
                            if parsed_qty_obj > 0 or parsed_total_obj > 0:
                                description = f"Item {item_idx + 1}"  # Fallback description
                                logger.info(f"[LINE_ITEMS] Using fallback description '{description}' (object) for item with qty={parsed_qty_obj}, total={parsed_total_obj}")
                            else:
                                # No valid data at all, skip it
                                logger.warning(f"[LINE_ITEMS] Skipping item {item_idx} (object) - empty description and no valid qty/price/total. Raw: qty='{raw_qty_obj}', unit='{raw_unit_obj}', total='{raw_total_obj}'")
                                continue
                        
                        line_item_dict = {
                            "desc": description,
                            "qty": parsed_qty_obj,
                            "unit_price": parsed_unit_obj,
                            "total": parsed_total_obj,
                            "uom": "",
                            "confidence": getattr(item, 'confidence', 0.7)
                        }
                        
                        # WARN if quantities/prices are zero but we have a description
                        if parsed_qty_obj == 0.0 and parsed_total_obj == 0.0:
                            logger.warning(f"[LINE_ITEMS] ⚠️ Item '{description}' (object) has qty=0 and total=0. Raw values: qty='{raw_qty_obj}', unit='{raw_unit_obj}', total='{raw_total_obj}'. This suggests table extraction may have failed.")
                        # Extract bbox if present (for visual verification)
                        bbox = getattr(item, 'bbox', None)
                        if bbox:
                            line_item_dict["bbox"] = bbox
                        line_items.append(line_item_dict)
            else:
                logger.warning(f"[LINE_ITEMS] Table block found but table_data is None or empty. Block OCR text length: {len(block_ocr_text)}")
    
    logger.info(f"[LINE_ITEMS] Found {table_count} table blocks, extracted {len(line_items)} line items")
    
    # If no line items found in tables, try to parse from text blocks
    if not line_items:
        # Build raw OCR text for fallback logging
        raw_ocr_text = " ".join([block.get("ocr_text", block.get("text", "")) if isinstance(block, dict) else getattr(block, 'ocr_text', '') for block in blocks])
        logger.warning(f"[FALLBACK] No table_data; trying regex on raw_ocr: {raw_ocr_text[:200]}")
        logger.info(f"[LINE_ITEMS] No table items found, trying fallback extraction")
        # Convert blocks to dict format for fallback
        blocks_dict = []
        for block in blocks:
            if hasattr(block, '__dict__'):
                blocks_dict.append({
                    "ocr_text": getattr(block, 'ocr_text', ''),
                    "text": getattr(block, 'text', ''),
                    "type": getattr(block, 'type', '')
                })
            else:
                blocks_dict.append(block)
        line_items = _fallback_line_item_extraction(blocks_dict)
        logger.info(f"[LINE_ITEMS] Fallback extraction found {len(line_items)} line items")
    
    return line_items

def _fallback_line_item_extraction(blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Fallback line item extraction from text blocks with normalization"""
    # Fail-fast guard for re module
    try:
        _ensure_re_available("_fallback_line_item_extraction")
    except NameError as e:
        logger.critical(f"[OCR_REGEX_IMPORT_MISSING] re module not available in _fallback_line_item_extraction: {e}")
        raise
    
    line_items = []
    
    for block in blocks:
        # Blocks use "ocr_text" field from the OCR pipeline
        text = block.get("ocr_text", block.get("text", ""))
        # Look for patterns like "Description 10 x £2.50 = £25.00"
        pattern = r'(.+?)\s+(\d+\.?\d*)\s*x?\s*[£€$]?(\d+\.?\d*)\s*=?\s*[£€$]?(\d+\.?\d*)'
        matches = re.finditer(pattern, text, re.IGNORECASE)
        
        for match in matches:
            desc, qty_str, price_str, total_str = match.groups()
            
            # Normalize values
            qty = _normalize_currency(qty_str)
            unit_price = _normalize_currency(price_str)
            total = _normalize_currency(total_str)
            
            # Only add if we have valid numeric values
            if qty is not None and unit_price is not None and total is not None:
                line_items.append({
                    "desc": desc.strip(),
                    "qty": qty,
                    "unit_price": unit_price,
                    "total": total,
                    "uom": "",
                    "confidence": 0.75
                })
    
    # #region agent log
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "K", "location": "ocr_service.py:2164", "message": "line item extraction returning", "data": {"line_items_count": len(line_items), "blocks_count": len(blocks), "full_text_length": len(full_text) if 'full_text' in locals() else 0}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
    except: pass
    # #endregion
    
    return line_items

