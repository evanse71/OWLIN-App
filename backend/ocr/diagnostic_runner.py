from __future__ import annotations
import os, glob, uuid, platform, subprocess, shutil
from typing import Dict, Any, List
from .score import compute_total
from .diag import LOG_DIR, log_stage, StageRecord, _now_ms

SCENARIOS = {
    "hospitality_invoice": "data/test_docs/hospitality_invoices/*.*",
    "supermarket_receipt": "data/test_docs/supermarket_receipts/*.*",
    "delivery_note": "data/test_docs/delivery_notes/*.*",
    "multi_invoice_pdf": "data/test_docs/multi_invoice_pdfs/*.pdf",
    "utility_bill": "data/test_docs/utility_bills/*.*",
    "lowres_rotated": "data/test_docs/lowres_rotated/*.*",
}

os.makedirs(LOG_DIR, exist_ok=True)

def _exists(cmd: str) -> bool:
    try:
        subprocess.run([cmd, "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3)
        return True
    except Exception:
        return False

def _try_import(name: str) -> bool:
    try:
        __import__(name); return True
    except Exception:
        return False

def env_check() -> Dict[str, Any]:
    checks: Dict[str, Any] = {}
    # PaddleOCR presence and model dir hint
    checks["paddleocr_pkg"] = _try_import("paddleocr")
    checks["paddle_model_dir"] = os.environ.get("PADDLE_MODEL_DIR", "(env var not set)")
    # Tesseract binary and languages
    checks["tesseract_bin"] = _exists("tesseract")
    try:
        langs = subprocess.run(["tesseract", "--list-langs"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
        checks["tesseract_langs_contains_eng"] = (b"eng" in langs.stdout)
    except Exception:
        checks["tesseract_langs_contains_eng"] = False
    # Poppler pdftoppm
    poppler_in_path = shutil.which("pdftoppm") is not None
    checks["pdftoppm_available"] = poppler_in_path
    checks["poppler_path_hint"] = os.environ.get("POPPLER_PATH", "(not set; ensure poppler is installed and in PATH)")
    # Ghostscript
    checks["ghostscript"] = _exists("gs") or _exists("gswin64c")
    # OpenCV package
    checks["opencv_pkg"] = _try_import("cv2")
    # System info
    try:
        import psutil
        checks["cpu_count"] = psutil.cpu_count(logical=True)
        checks["mem_total_mb"] = int(psutil.virtual_memory().total / (1024*1024))
    except Exception:
        checks["cpu_count"] = os.cpu_count()
        checks["mem_total_mb"] = "psutil missing"
    checks["python"] = platform.python_version()
    # Friendly hints
    hints: List[str] = []
    if not checks["tesseract_bin"]:
        hints.append("Install Tesseract: brew install tesseract (macOS) or apt-get install tesseract-ocr")
    if not checks["tesseract_langs_contains_eng"]:
        hints.append("Install English language data: e.g., tesseract-ocr-eng package")
    if not checks["pdftoppm_available"]:
        hints.append("Install Poppler: brew install poppler (macOS) or apt-get install poppler-utils; set POPPLER_PATH if needed")
    if not checks["ghostscript"]:
        hints.append("Install Ghostscript: brew install ghostscript or apt-get install ghostscript")
    if not checks["opencv_pkg"]:
        hints.append("pip install opencv-python-headless")
    if not checks["paddleocr_pkg"]:
        hints.append("pip install paddleocr; set PADDLE_MODEL_DIR to model path if offline")
    checks["hints"] = hints
    return checks 

def run_pipeline_on_file(file_path: str, run_id: str, doc_id: str) -> Dict[str, Any]:
    stages: List[Dict[str, Any]] = []
    # ingest
    started = _now_ms(); ok = True; meta = {}
    try:
        page_count = 1
        if file_path.lower().endswith('.pdf'):
            try:
                import fitz
                doc = fitz.open(file_path); page_count = len(doc); doc.close()
            except Exception:
                ok = False
        meta = {"page_count": page_count}
    except Exception:
        ok = False
    ended = _now_ms(); stages.append({"stage": "ingest", "ok": ok, "meta": meta, "duration_ms": ended-started}); log_stage(StageRecord(run_id, doc_id, "ingest", ok, started, ended, ended-started, meta, None if ok else "ingest failed"))
    # preprocess (light probe)
    started = _now_ms(); ok = True
    try:
        from PIL import Image  # noqa
    except Exception:
        ok = False
    ended = _now_ms(); stages.append({"stage": "preprocess", "ok": ok, "meta": {}, "duration_ms": ended-started}); log_stage(StageRecord(run_id, doc_id, "preprocess", ok, started, ended, ended-started, {}, None if ok else "preprocess failed"))
    # ocr
    started = _now_ms(); ok = True; ocr_text = ""; conf_pct = 0; doc_type = None
    try:
        from .unified_ocr_engine import get_unified_ocr_engine
        engine = get_unified_ocr_engine()
        result = engine.process_document(file_path)
        ocr_text = result.raw_text or ""
        conf_pct = float(result.overall_confidence) * (100.0 if result.overall_confidence <= 1.0 else 1.0)
        doc_type = getattr(result, 'document_type', None)
    except Exception:
        ok = False
    ended = _now_ms(); meta = {"text_len": len(ocr_text), "confidence": round(conf_pct,1), "doc_type": doc_type or "unknown"}; stages.append({"stage": "ocr", "ok": ok, "meta": meta, "duration_ms": ended-started}); log_stage(StageRecord(run_id, doc_id, "ocr", ok, started, ended, ended-started, meta, None if ok else "ocr failed"))
    # parse
    started = _now_ms(); ok = True; items_count = 0; supplier_found=False; date_found=False; total_found=False
    try:
        from .parse_invoice import parse_invoice
        parsed = parse_invoice(ocr_text)
        items = getattr(parsed, 'line_items', []) or []
        items_count = len(items)
        supplier_found = bool(getattr(parsed, 'supplier', None))
        date_found = bool(getattr(parsed, 'date', None))
        total_found = bool(getattr(parsed, 'gross_total', None))
    except Exception:
        ok = False
    ended = _now_ms(); meta = {"items_count": items_count, "supplier_found": supplier_found, "date_found": date_found, "total_found": total_found}; stages.append({"stage": "parse", "ok": ok, "meta": meta, "duration_ms": ended-started}); log_stage(StageRecord(run_id, doc_id, "parse", ok, started, ended, ended-started, meta, None if ok else "parse failed"))
    # normalize
    started = _now_ms(); ok = True; currency_found=False
    try:
        currency_found = True if total_found else False
    except Exception:
        ok = False
    ended = _now_ms(); meta = {"currency_found": currency_found}; stages.append({"stage": "normalize", "ok": ok, "meta": meta, "duration_ms": ended-started}); log_stage(StageRecord(run_id, doc_id, "normalize", ok, started, ended, ended-started, meta, None if ok else "normalize failed"))
    # classify
    started = _now_ms(); ok = True
    try:
        ok = True
    except Exception:
        ok = False
    ended = _now_ms(); meta = {"doc_type": doc_type or "unknown"}; stages.append({"stage": "classify", "ok": ok, "meta": meta, "duration_ms": ended-started}); log_stage(StageRecord(run_id, doc_id, "classify", ok, started, ended, ended-started, meta, None if ok else "classify failed"))
    # persist (write excerpt)
    started = _now_ms(); ok = True
    try:
        out_path = os.path.join(LOG_DIR, f"{run_id}-{doc_id}-persist.txt")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(ocr_text[:500])
    except Exception:
        ok = False
    ended = _now_ms(); stages.append({"stage": "persist", "ok": ok, "meta": {}, "duration_ms": ended-started}); log_stage(StageRecord(run_id, doc_id, "persist", ok, started, ended, ended-started, {}, None if ok else "persist failed"))
    summary = compute_total(stages)
    return {"doc_id": doc_id, "file": os.path.basename(file_path), "stages": stages, **summary}


def run_diagnostics(scenarios: List[str] | None = None) -> Dict[str, Any]:
    if not scenarios:
        scenarios = list(SCENARIOS.keys())
    run_id = str(uuid.uuid4())
    report: Dict[str, Any] = {"run_id": run_id, "env": env_check(), "scenarios": {}, "aggregate": {}}
    per_doc_totals: List[int] = []
    for sc in scenarios:
        pattern = SCENARIOS.get(sc)
        if not pattern:
            continue
        files = sorted(glob.glob(pattern))
        sc_results: List[Dict[str, Any]] = []
        for f in files:
            doc_id = str(uuid.uuid4())
            try:
                res = run_pipeline_on_file(f, run_id=run_id, doc_id=doc_id)
                sc_results.append(res)
                per_doc_totals.append(res.get("total_percent", 0))
            except Exception as e:
                sc_results.append({"doc_id": doc_id, "file": os.path.basename(f), "error": str(e), "total_percent": 0})
        avg = round(sum(r.get("total_percent", 0) for r in sc_results) / max(1, len(sc_results)))
        report["scenarios"][sc] = {"avg_total_percent": avg, "docs": sc_results}
    overall = round(sum(per_doc_totals) / max(1, len(per_doc_totals)))
    report["aggregate"] = {"overall_total_percent": overall}

    out_json = os.path.join(LOG_DIR, f"{run_id}-summary.json")
    with open(out_json, "w", encoding="utf-8") as f:
        import json; json.dump(report, f, ensure_ascii=False, indent=2)
    return report 