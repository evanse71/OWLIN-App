# backend/services.py
import json, uuid, threading, pathlib, os, re, hashlib, time, traceback, logging
from typing import Dict, Union, List, Optional
from db import get_conn
from datetime import datetime
from difflib import SequenceMatcher

# Lazy import of OCR to avoid import-time failures
def _load_ocr():
    try:
        from robust_ocr import parse_invoice_file as _run_ocr
    except Exception:
        from robust_ocr import run_full_ocr_pipeline as _run_ocr  # fallback alias
    return _run_ocr

log = logging.getLogger("services")
log.setLevel(logging.INFO)

# JSONL diagnostics setup
DIAG_DIR = os.environ.get("OWLIN_DIAG_DIR", "backups/diagnostics")
os.makedirs(DIAG_DIR, exist_ok=True)

# Storage configuration
STORAGE_ROOT = os.environ.get("OWLIN_STORAGE", "storage/uploads")
os.makedirs(STORAGE_ROOT, exist_ok=True)

def _append_diag(obj):
    """Append a diagnostic record to the daily JSONL file"""
    try:
        p = os.path.join(DIAG_DIR, datetime.now().strftime("diagnostics_%Y%m%d.jsonl"))
        with open(p, "a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
        
        # Clean up old diagnostic files (14-day retention)
        _cleanup_old_diagnostics()
    except Exception as e:
        log.warning(f"Failed to write diagnostic record: {e}")

def _cleanup_old_diagnostics():
    """Delete diagnostic files older than 14 days"""
    try:
        from datetime import timedelta
        cutoff_date = datetime.now() - timedelta(days=14)
        
        for filename in os.listdir(DIAG_DIR):
            if filename.startswith("diagnostics_") and filename.endswith(".jsonl"):
                file_path = os.path.join(DIAG_DIR, filename)
                file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                
                if file_time < cutoff_date:
                    os.remove(file_path)
                    log.info(f"Cleaned up old diagnostic file: {filename}")
    except Exception as e:
        log.warning(f"Failed to cleanup old diagnostics: {e}")

def _store_upload(temp_path: str, file_hash: str, original_name: str) -> str:
    """Store uploaded file with canonical naming and record in uploaded_files table"""
    os.makedirs(STORAGE_ROOT, exist_ok=True)
    # Canonical name = <hash><ext>
    ext = os.path.splitext(original_name)[1].lower() or ""
    canonical = f"{file_hash}{ext}"
    abs_path = os.path.abspath(os.path.join(STORAGE_ROOT, canonical))
    
    # Move temp file to canonical location
    import shutil
    shutil.move(temp_path, abs_path)
    
    # Record in uploaded_files table
    _record_uploaded_file(file_hash, abs_path)
    
    return abs_path

def _record_uploaded_file(file_hash: str, abs_path: str):
    """Record uploaded file in uploaded_files table"""
    try:
        with get_conn() as c:
            c.execute("""
               INSERT OR REPLACE INTO uploaded_files(file_hash, absolute_path, size_bytes, created_at)
               VALUES (?, ?, ?, COALESCE( (SELECT created_at FROM uploaded_files WHERE file_hash=?), CURRENT_TIMESTAMP ))
            """, (file_hash, abs_path, os.path.getsize(abs_path), file_hash))
    except Exception as e:
        log.warning(f"Failed to record uploaded file: {e}")

def resolve_path_for_reprocess(file_hash: str, fallback_name: str = None) -> str:
    """Robust path resolver for reprocessing - works even if files moved or renamed"""
    # 1) Look up canonical path from uploaded_files table
    with get_conn() as c:
        row = c.execute("SELECT absolute_path FROM uploaded_files WHERE file_hash=?", (file_hash,)).fetchone()
    if row and row["absolute_path"] and os.path.exists(row["absolute_path"]):
        return row["absolute_path"]

    # 2) Search storage by hash prefix (hash + any ext)
    if os.path.isdir(STORAGE_ROOT):
        for name in os.listdir(STORAGE_ROOT):
            if name.startswith(file_hash):
                p = os.path.abspath(os.path.join(STORAGE_ROOT, name))
                if os.path.exists(p):
                    # Update uploaded_files table with found path
                    _record_uploaded_file(file_hash, p)
                    return p

    # 3) Last-ditch: search recursively (expensive; OK for dev)
    for root, _, files in os.walk(STORAGE_ROOT):
        for n in files:
            if n.startswith(file_hash):
                p = os.path.abspath(os.path.join(root, n))
                if os.path.exists(p):
                    # Update uploaded_files table with found path
                    _record_uploaded_file(file_hash, p)
                    return p

    # 4) If we only have a display filename, try exact match in storage
    if fallback_name:
        candidate = os.path.abspath(os.path.join(STORAGE_ROOT, fallback_name))
        if os.path.exists(candidate):
            # Update uploaded_files table with found path
            _record_uploaded_file(file_hash, candidate)
            return candidate

    return None

_ALIAS_PATH = os.path.join("data", "supplier_aliases.json")
_alias_map = None

def _load_alias_map():
    global _alias_map
    if _alias_map is None:
        if os.path.exists(_ALIAS_PATH):
            try:
                with open(_ALIAS_PATH, "r", encoding="utf-8") as f:
                    _alias_map = json.load(f)  # {"canonical": ["alias1","alias2",...]}
            except Exception as e:
                log.warning(f"Failed to load supplier aliases: {e}")
                _alias_map = {}
        else:
            _alias_map = {}
    return _alias_map

def normalize_supplier_name(name: str) -> str:
    """Normalize supplier name using alias mapping and fuzzy matching"""
    if not name:
        return name
    alias_map = _load_alias_map()
    nm = re.sub(r"[^a-z0-9]+", "", name.lower())
    # hard match
    for canonical, aliases in alias_map.items():
        for a in aliases + [canonical]:
            if re.sub(r"[^a-z0-9]+", "", a.lower()) == nm:
                return canonical
    # fuzzy best
    best_name, best = name, 0.0
    for canonical, aliases in alias_map.items():
        for a in aliases + [canonical]:
            r = SequenceMatcher(None,
                re.sub(r"[^a-z0-9]+", "", a.lower()), nm).ratio()
            if r > best:
                best, best_name = r, canonical
    return best_name if best >= 0.92 else name

def _log_audit(actor: str, action: str, entity: str, before: Optional[Dict] = None, after: Optional[Dict] = None):
    """Log audit events to database"""
    try:
        with get_conn() as c:
            c.execute("""
                INSERT INTO audit_log(actor, action, entity, before_json, after_json, at)
                VALUES(?, ?, ?, ?, ?, datetime('now'))
            """, (
                actor,
                action,
                entity,
                json.dumps(before) if before else None,
                json.dumps(after) if after else None
            ))
    except Exception as e:
        log.warning(f"Failed to log audit event: {e}")

def _sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256(); h.update(b); return h.hexdigest()

def compute_totals_fallback(line_items: List[Dict]) -> Dict:
    """Compute totals fallback when backend totals are missing but line items exist"""
    try:
        subtotal = sum(
            float(li.get("line_total") or (float(li.get("qty", 0)) * float(li.get("unit_price", 0)))) 
            for li in line_items
        )
        return {"subtotal": round(subtotal, 2)}
    except Exception:
        return {"subtotal": 0.0}

def _sum_lines(lines):
    """Sum line totals from line items"""
    s = 0.0
    for li in (lines or []):
        try:
            lt = li.get("line_total")
            if lt is None:
                q = float(li.get("qty", 0))
                up = float(li.get("unit_price", 0))
                lt = q * up
            s += float(lt)
        except Exception:
            continue
    return round(s, 2)

def enrich_totals_and_flags(inv: dict) -> dict:
    """Enrich invoice with totals validation and confidence scoring"""
    lines = inv.get("items") or []
    totals = inv.get("totals") or {}
    subtotal = totals.get("subtotal")

    sum_lines = _sum_lines(lines)
    flags = []
    c_totals = 0

    if subtotal is None:
        totals["subtotal"] = sum_lines
        flags.append("SUBTOTAL_FALLBACK")
        c_totals += 60
    else:
        # 3% tolerance
        if subtotal == 0:
            delta_ratio = 1.0 if sum_lines > 0 else 0.0
        else:
            delta_ratio = abs(sum_lines - float(subtotal)) / max(1.0, float(subtotal))
        if delta_ratio <= 0.03:
            c_totals += 90
        else:
            flags.append("TOTAL_MISMATCH")

    inv["totals"] = totals
    inv["validation_flags"] = flags
    inv["c_totals"] = c_totals
    return inv

def _new_job(conn, *, kind="ocr", status="queued", progress=10, meta_json=None, result_json=None):
    job_id = f"job_{uuid.uuid4().hex[:8]}"
    conn.execute(
        "INSERT INTO jobs(id, kind, status, progress, meta_json, result_json, created_at, updated_at) "
        "VALUES(?,?,?,?,?,?,datetime('now'),datetime('now'))",
        (job_id, kind, status, progress, meta_json, result_json),
    )
    return job_id

def _update_job(job_id: str, *, status=None, progress=None, result_json=None, error=None, duration_ms=None):
    sets, vals = [], []
    if status is not None:      sets.append("status=?");      vals.append(status)
    if progress is not None:    sets.append("progress=?");    vals.append(progress)
    if result_json is not None: sets.append("result_json=?"); vals.append(result_json)
    if error is not None:       sets.append("error=?");       vals.append(error)
    if duration_ms is not None: sets.append("duration_ms=?"); vals.append(duration_ms)
    sets.append("updated_at=datetime('now')")
    vals.append(job_id)
    with get_conn() as c:
        c.execute(f"UPDATE jobs SET {', '.join(sets)} WHERE id=?", vals)

def new_job_for_existing_file(path: str, file_hash: str) -> str:
    """Create a new job for reprocessing an existing file"""
    with get_conn() as c:
        job_id = _new_job(c, status="queued", progress=0, meta_json=json.dumps({"source": "reprocess", "file_hash": file_hash}))
        c.commit()
    
    # Same processing pipeline as uploads
    th = threading.Thread(target=_process_job_with_retry, args=(job_id, path, file_hash), daemon=True)
    th.start()
    return job_id

def handle_upload_and_queue(path: str, original_name: Optional[str] = None) -> Dict:
    # hash file for dedupe
    with open(path, "rb") as f:
        hb = f.read()
    file_hash = _sha256_bytes(hb)

    with get_conn() as c:
        row = c.execute("SELECT id FROM invoices WHERE file_hash=?", (file_hash,)).fetchone()
        if row:
            inv_id = row["id"] if isinstance(row, dict) else row[0]
            job_id = _new_job(c, status="done", progress=100, result_json=json.dumps({"invoice_id": inv_id}))
            c.commit()
            log.info(f"Duplicate upload -> invoice {inv_id}")
            
            # Audit log duplicate detection
            _log_audit(
                actor="system",
                action="duplicate_detected",
                entity=f"invoice:{inv_id}",
                before={"file_hash": file_hash, "original_name": original_name},
                after={"job_id": job_id, "invoice_id": inv_id}
            )
            
            return {"duplicate": True, "invoice_id": inv_id, "job_id": job_id}
        
        # Store file with canonical naming and record in uploaded_files
        canonical_path = _store_upload(path, file_hash, original_name or "unknown")
        
        job_id = _new_job(c, status="queued", progress=10, meta_json=json.dumps({"filename": original_name}))
        c.commit()
        
        # Audit log new job creation
        _log_audit(
            actor="system",
            action="job_created",
            entity=f"job:{job_id}",
            before={"file_hash": file_hash, "original_name": original_name},
            after={"job_id": job_id, "status": "queued", "canonical_path": canonical_path}
        )

    th = threading.Thread(target=_process_job_with_retry, args=(job_id, canonical_path, file_hash), daemon=True)
    th.start()
    return {"duplicate": False, "job_id": job_id}

def _money_to_minor(s: Optional[str]) -> Optional[int]:
    if not s: return None
    s = re.sub(r"[£€$,\s]", "", str(s))
    try:
        if "." in s:
            pounds, pence = s.split(".", 1)
            pence = (pence + "0")[:2]
            return int(pounds) * 100 + int(pence)
        return int(s)
    except Exception:
        return None

def _normalize_items(items_raw: list) -> list:
    norm = []
    for it in items_raw or []:
        qty = float(it.get("qty") or 1)
        unit = _money_to_minor(it.get("unit_price_str"))
        line = _money_to_minor(it.get("line_total_str"))
        if unit is None and line is not None and qty > 0:
            unit = int(round(line / qty))
        if line is None and unit is not None:
            line = int(round(unit * qty))
        norm.append({
            "description": it.get("description",""),
            "qty": qty,
            "unit_price": int(unit or 0),
            "total": int(line or 0),
            "vat_rate": int(it.get("vat_rate") or 0),
            "conf": int(it.get("conf") or 0),
        })
    return norm

def _persist_invoice(invoice: Dict, items: list, *, file_hash: str, filename: str) -> str:
    inv_id = f"inv_{uuid.uuid4().hex[:8]}"
    
    # Observability: Log high confidence but zero line items
    if (invoice.get("confidence") or 0) >= 80 and not (items or []):
        log.warning(f"High confidence but 0 line items - invoice_id: {inv_id}, filename: {filename}, confidence: {invoice.get('confidence')}")
    
    # Audit log before invoice creation
    _log_audit(
        actor="system",
        action="invoice_created",
        entity=f"invoice:{inv_id}",
        before={"file_hash": file_hash, "filename": filename},
        after={"invoice_id": inv_id, "supplier": invoice.get("supplier_name"), "items_count": len(items)}
    )
    
    with get_conn() as c:
        c.execute("""
          INSERT INTO invoices(id, status, confidence, paired, processing_progress,
                               supplier_name, invoice_date, total_amount,
                               subtotal_p, vat_total_p, total_p, filename, issues_count, file_hash, parsed_at)
          VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            inv_id,
            "parsed",  # Always set to parsed when persisting
            int(invoice.get("confidence",0) or 0),
            0, 100,
            invoice.get("supplier_name",""),
            invoice.get("invoice_date",""),
            int(invoice.get("total_p") or 0),
            invoice.get("subtotal_p"),
            invoice.get("vat_total_p"),
            invoice.get("total_p"),
            filename,
            int(invoice.get("issues_count",0) or 0),
            file_hash,
            datetime.utcnow().isoformat(),  # Add parsed_at timestamp
        ))
        for it in items:
            c.execute("""
              INSERT INTO invoice_items(invoice_id, description, qty, unit_price, total, vat_rate, confidence)
              VALUES(?,?,?,?,?,?,?)
            """, (
                inv_id,
                it["description"],
                float(it["qty"]),
                int(it["unit_price"]),
                int(it["total"]),
                int(it["vat_rate"]),
                int(it["conf"]),
            ))
        c.commit()
    return inv_id

def _process_job_with_retry(job_id: str, path: str, file_hash: str):
    t0 = time.time()
    backoffs = [2, 4]
    CAP = int(os.environ.get("OWLIN_JOB_CAP_S", "60"))  # 60 second hard cap
    
    # Audit log job start
    _log_audit(
        actor="system",
        action="job_started",
        entity=f"job:{job_id}",
        before={"file_hash": file_hash},
        after={"status": "processing"}
    )
    
    log.info("JOB_START %s", job_id)
    
    for i in range(len(backoffs) + 1):
        try:
            # Check timeout before starting
            if time.time() - t0 > CAP:
                log.error("JOB_TIMEOUT %s", job_id)
                dur = int((time.time() - t0) * 1000)
                _update_job(job_id, status="timeout", progress=100, error="Job exceeded time limit", duration_ms=dur)
                
                # Add diagnostic logging for timeout
                _append_diag({
                    "type": "job",
                    "id": job_id,
                    "status": "timeout",
                    "duration_ms": dur,
                    "created_at": datetime.now().isoformat(),
                    "result": None,
                    "error": "Job exceeded time limit"
                })
                return
            
            _update_job(job_id, status="processing", progress=30)
            inv_id = _process_single_job(job_id, path, file_hash)
            
            # Check timeout after processing
            if time.time() - t0 > CAP:
                log.error("JOB_TIMEOUT %s", job_id)
                dur = int((time.time() - t0) * 1000)
                _update_job(job_id, status="timeout", progress=100, error="Job exceeded time limit", duration_ms=dur)
                
                # Add diagnostic logging for timeout
                _append_diag({
                    "type": "job",
                    "id": job_id,
                    "status": "timeout",
                    "duration_ms": dur,
                    "created_at": datetime.now().isoformat(),
                    "result": None,
                    "error": "Job exceeded time limit"
                })
                return
            
            dur = int((time.time() - t0) * 1000)
            _update_job(job_id, status="done", progress=100,
                        result_json=json.dumps({"invoice_id": inv_id}), duration_ms=dur)
            
            log.info("JOB_END %s status=done inv_count=1 ms=%d", job_id, dur)
            
            # Add diagnostic logging
            _append_diag({
                "type": "job",
                "id": job_id,
                "status": "done",
                "duration_ms": dur,
                "created_at": datetime.now().isoformat(),
                "result": {"invoice_id": inv_id},
                "timing": {"ocr_ms": ocr_dt if 'ocr_dt' in locals() else None}
            })
            
            # Audit log job success
            _log_audit(
                actor="system",
                action="job_completed",
                entity=f"job:{job_id}",
                before={"status": "processing"},
                after={"status": "done", "invoice_id": inv_id, "duration_ms": dur}
            )
            
            return
        except Exception as e:
            if i < len(backoffs):
                time.sleep(backoffs[i])
                continue
            dur = int((time.time() - t0) * 1000)
            _update_job(job_id, status="failed", progress=100, error=str(e), duration_ms=dur)
            
            log.info("JOB_END %s status=failed inv_count=0 ms=%d", job_id, dur)
            
            # Add diagnostic logging for failed jobs
            _append_diag({
                "type": "job",
                "id": job_id,
                "status": "failed",
                "duration_ms": dur,
                "created_at": datetime.now().isoformat(),
                "result": None,
                "error": str(e),
                "timing": {"ocr_ms": ocr_dt if 'ocr_dt' in locals() else None}
            })
            
            # Audit log job failure
            _log_audit(
                actor="system",
                action="job_failed",
                entity=f"job:{job_id}",
                before={"status": "processing"},
                after={"status": "failed", "error": str(e), "duration_ms": dur}
            )
            
            return

def _process_single_job(job_id: str, path: str, file_hash: str) -> str:
    t0 = time.perf_counter()
    _update_job(job_id, progress=60)
    
    # OCR timing
    ocr_start = time.perf_counter()
    run_ocr = _load_ocr()
    res = run_ocr(path)
    ocr_dt = (time.perf_counter() - ocr_start) * 1000
    log.info("TIMING OCR %.1fms", ocr_dt)
    
    if not isinstance(res, dict):
        raise ValueError("OCR returned invalid structure")

    # Check if OCR returned multiple invoices
    if "invoices" in res and isinstance(res["invoices"], list):
        # Multi-invoice processing
        log.info(f"Processing {len(res['invoices'])} invoices from {path}")
        invoice_ids = []
        
        for i, invoice_data in enumerate(res["invoices"]):
            items_raw = invoice_data.get("items") or invoice_data.get("items_raw") or []
            subtotal_p = _money_to_minor(invoice_data.get("subtotal_raw")) or sum(_money_to_minor(i.get("line_total_str")) or 0 for i in items_raw)
            vat_total_p = _money_to_minor(invoice_data.get("vat_total_raw"))
            total_p = _money_to_minor(invoice_data.get("total_raw")) or (subtotal_p + (vat_total_p or 0))

            # Normalize supplier name
            supplier_name = normalize_supplier_name(invoice_data.get("supplier_name","") or "Unknown supplier")

            invoice = {
                "status": "parsed",  # Set to parsed instead of scanned
                "confidence": int(invoice_data.get("confidence", 0) or 0),
                "supplier_name": supplier_name,
                "invoice_date": invoice_data.get("invoice_date") or invoice_data.get("invoice_date_raw") or "",
                "subtotal_p": subtotal_p,
                "vat_total_p": vat_total_p if vat_total_p is not None else max(0, (total_p or 0) - (subtotal_p or 0)),
                "total_p": total_p,
                "issues_count": int(invoice_data.get("issues_count", 0) or 0),
                # Add confidence scores if available
                "c_split": invoice_data.get("c_split"),
                "c_header": invoice_data.get("c_header"),
                "c_lines": invoice_data.get("c_lines"),
                "c_totals": invoice_data.get("c_totals"),
                "validation_flags": invoice_data.get("validation_flags", []),
                "reason": invoice_data.get("reason"),
            }
            
            # Enrich with totals validation
            invoice = enrich_totals_and_flags(invoice)
            
            # Add page range info to filename for multi-invoice files
            page_range = invoice_data.get("page_range")
            if page_range:
                filename = f"{file_hash[:8]}_{os.path.basename(path)}_pages_{page_range[0]}-{page_range[1]}"
            else:
                filename = f"{file_hash[:8]}_{os.path.basename(path)}"
            
            inv_id = _persist_invoice(invoice, _normalize_items(items_raw), file_hash=file_hash, filename=filename)
            invoice_ids.append(inv_id)
            # Explicitly update status to parsed for each invoice created
            with get_conn() as c:
                c.execute("UPDATE invoices SET status='parsed', parsed_at=datetime('now') WHERE id=?", (inv_id,))
            log.info(f"Created invoice {inv_id} for chunk {i+1}")
        
        # Return the first invoice ID for backward compatibility
        return invoice_ids[0] if invoice_ids else "inv_none"
    else:
        # Single invoice processing (existing logic)
        items_raw = res.get("items") or res.get("items_raw") or []
        subtotal_p = _money_to_minor(res.get("subtotal_raw")) or sum(_money_to_minor(i.get("line_total_str")) or 0 for i in items_raw)
        vat_total_p = _money_to_minor(res.get("vat_total_raw"))
        total_p = _money_to_minor(res.get("total_raw")) or (subtotal_p + (vat_total_p or 0))

        # Normalize supplier name
        supplier_name = normalize_supplier_name(res.get("supplier_name","") or "Unknown supplier")

        invoice = {
            "status": "parsed",  # Set to parsed instead of scanned
            "confidence": int(res.get("confidence", 0) or 0),
            "supplier_name": supplier_name,
            "invoice_date": res.get("invoice_date") or res.get("invoice_date_raw") or "",
            "subtotal_p": subtotal_p,
            "vat_total_p": vat_total_p if vat_total_p is not None else max(0, (total_p or 0) - (subtotal_p or 0)),
            "total_p": total_p,
            "issues_count": int(res.get("issues_count", 0) or 0),
        }
        
        # Enrich with totals validation
        invoice = enrich_totals_and_flags(invoice)
        
        filename = f"{file_hash[:8]}_{os.path.basename(path)}"
        inv_id = _persist_invoice(invoice, _normalize_items(items_raw), file_hash=file_hash, filename=filename)
        with get_conn() as c:
            c.execute("UPDATE invoices SET status='parsed', parsed_at=datetime('now') WHERE id=?", (inv_id,))
        _update_job(job_id, progress=80)
        return inv_id

# Back-compat shim used by some callers
def start_ocr_job_with_dedupe(file_path: str, original_name: Optional[str] = None):
    res = handle_upload_and_queue(file_path, original_name)
    out = {}
    if "job_id" in res: out["job_id"] = res["job_id"]
    if res.get("duplicate"):
        out["duplicate"] = True
        out["invoice_id"] = res.get("invoice_id")
    return out

# Minimal analytics helpers (kept for app endpoints)
def get_job_analytics() -> Dict:
    with get_conn() as c:
        job_stats = c.execute("""
          SELECT COUNT(*) as total_jobs,
                 SUM(CASE WHEN status='done' THEN 1 ELSE 0 END) as completed,
                 SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) as failed
          FROM jobs
        """).fetchone()
        invoice_stats = c.execute("""
          SELECT COUNT(*) as total_invoices,
                 AVG(confidence) as avg_confidence
          FROM invoices
        """).fetchone()
    return {
        "job_stats": dict(job_stats) if job_stats else {},
        "invoice_stats": dict(invoice_stats) if invoice_stats else {},
    }

def compare_dn_invoice(dn_id: str, inv_id: str):
    with get_conn() as c:
        dn_items = c.execute("SELECT description, qty, unit_price, vat_rate FROM dn_items WHERE dn_id=?", (dn_id,)).fetchall()
        inv_items = c.execute("SELECT description, qty, unit_price, vat_rate FROM invoice_items WHERE invoice_id=?", (inv_id,)).fetchall()
    diffs = []
    by_dn = {r["description"]: r for r in dn_items}
    by_inv = {r["description"]: r for r in inv_items}
    for desc, dn in by_dn.items():
        inv = by_inv.get(desc)
        if not inv:
            diffs.append({"kind":"missing_on_invoice","item":desc}); continue
        if float(dn["qty"] or 0) != float(inv["qty"] or 0):
            diffs.append({"kind":"qty_diff","item":desc,"dn":dn["qty"],"inv":inv["qty"]})
        if (dn["unit_price"] or 0) != (inv["unit_price"] or 0):
            diffs.append({"kind":"price_diff","item":desc,"dn":dn["unit_price"],"inv":inv["unit_price"]})
        if (dn["vat_rate"] or 0) != (inv["vat_rate"] or 0):
            diffs.append({"kind":"vat_diff","item":desc,"dn":dn["vat_rate"],"inv":inv["vat_rate"]})
    for desc in by_inv:
        if desc not in by_dn:
            diffs.append({"kind":"extra_on_invoice","item":desc})
    return diffs 

def _sum_lines(lines):
    """Sum line totals from line items"""
    s = 0.0
    for li in (lines or []):
        try:
            lt = li.get("line_total")
            if lt is None:
                q = float(li.get("qty", 0))
                up = float(li.get("unit_price", 0))
                lt = q * up
            s += float(lt)
        except Exception:
            continue
    return round(s, 2)

def enrich_totals_and_flags(inv: dict) -> dict:
    """Enrich invoice with totals validation and confidence scoring"""
    lines = inv.get("items") or []
    totals = inv.get("totals") or {}
    subtotal = totals.get("subtotal")

    sum_lines = _sum_lines(lines)
    flags = []
    c_totals = 0

    if subtotal is None:
        totals["subtotal"] = sum_lines
        flags.append("SUBTOTAL_FALLBACK")
        c_totals += 60
    else:
        # 3% tolerance
        if subtotal == 0:
            delta_ratio = 1.0 if sum_lines > 0 else 0.0
        else:
            delta_ratio = abs(sum_lines - float(subtotal)) / max(1.0, float(subtotal))
        if delta_ratio <= 0.03:
            c_totals += 90
        else:
            flags.append("TOTAL_MISMATCH")

    inv["totals"] = totals
    inv["validation_flags"] = flags
    inv["c_totals"] = c_totals
    return inv 