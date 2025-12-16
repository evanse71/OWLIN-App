import sqlite3
import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

LOGGER = logging.getLogger("owlin.db")

# Resolve DB_PATH as absolute path relative to project root
# backend/app/db.py -> backend/app -> backend -> project root
_BACKEND_APP_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _BACKEND_APP_DIR.parent
_PROJECT_ROOT = _BACKEND_DIR.parent
DB_PATH = str(_PROJECT_ROOT / "data" / "owlin.db")
_last_error = {"when": "", "route": "", "message": "", "detail": ""}


def _table_has_column(cursor: sqlite3.Cursor, table: str, column: str) -> bool:
    """Return True if a column exists on the table."""
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())


def _add_column_if_missing(cursor: sqlite3.Cursor, table: str, column: str, definition: str):
    """Add a column to a table if it is missing.
    
    Args:
        cursor: SQLite cursor
        table: Table name
        column: Column name
        definition: Column definition (type and constraints), e.g., "REAL DEFAULT 0.0"
                   If definition already includes column name, it will be used as-is
    """
    if not _table_has_column(cursor, table, column):
        try:
            # If definition already includes column name, use as-is; otherwise prepend column name
            if definition.strip().startswith(column):
                full_definition = definition
            else:
                full_definition = f"{column} {definition}"
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {full_definition}")
            LOGGER.info(f"[DB] Added missing column {column} to {table}")
        except sqlite3.OperationalError as exc:
            # Another concurrent initializer might have added it already
            LOGGER.debug(f"[DB] Skipped adding column {column} to {table}: {exc}")

def init_db():
    """Initialize database with WAL mode and create tables if they don't exist"""
    os.makedirs(Path(DB_PATH).parent, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Enable WAL mode for better concurrency and crash safety
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")  # Faster than FULL, safe with WAL
    cursor.execute("PRAGMA foreign_keys=ON")     # Enforce FK constraints
    
    # Verify WAL mode enabled
    cursor.execute("PRAGMA journal_mode")
    mode = cursor.fetchone()[0]
    print(f"[DB] Initialized with journal_mode={mode}, synchronous=NORMAL, foreign_keys=ON")
    
    # Create documents table
    # documents.status intended values:
    # - 'pending'    : file uploaded, waiting for OCR
    # - 'processing' : OCR running
    # - 'ready'      : OCR done, invoices available
    # - 'error'      : OCR failed
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            filename TEXT,
            stored_path TEXT,
            size_bytes INTEGER,
            uploaded_at TEXT,
            status TEXT DEFAULT 'pending',
            ocr_confidence REAL DEFAULT 0.0,
            ocr_stage TEXT DEFAULT 'upload',
            ocr_error TEXT DEFAULT NULL,
            sha256 TEXT,
            invoice_id TEXT,
            FOREIGN KEY(invoice_id) REFERENCES invoices(id)
        )
    """)
    # Add sha256 column if it doesn't exist (for existing databases)
    try:
        cursor.execute("ALTER TABLE documents ADD COLUMN sha256 TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    # Add status column if it doesn't exist (for existing databases)
    try:
        cursor.execute("ALTER TABLE documents ADD COLUMN status TEXT DEFAULT 'pending'")
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    # Add ocr_stage column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE documents ADD COLUMN ocr_stage TEXT DEFAULT 'upload'")
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    # Add ocr_confidence column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE documents ADD COLUMN ocr_confidence REAL DEFAULT 0.0")
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    # Add ocr_error column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE documents ADD COLUMN ocr_error TEXT DEFAULT NULL")
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    # Add ocr_report_json column if it doesn't exist (for OCR telemetry)
    try:
        cursor.execute("ALTER TABLE documents ADD COLUMN ocr_report_json TEXT DEFAULT NULL")
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    # Add doc_type_confidence column if it doesn't exist (for document classification)
    _add_column_if_missing(cursor, "documents", "doc_type_confidence", "doc_type_confidence REAL DEFAULT 0.0")
    
    # Add doc_type_reasons column if it doesn't exist (JSON array of strings)
    _add_column_if_missing(cursor, "documents", "doc_type_reasons", "doc_type_reasons TEXT")
    
    # Create index on sha256 for duplicate detection
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_sha256 ON documents(sha256)")
    
    # Create index on doc_type_confidence for filtering/sorting (only if column exists)
    if _table_has_column(cursor, "documents", "doc_type_confidence"):
        try:
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_doc_type_confidence ON documents(doc_type_confidence)")
        except sqlite3.OperationalError:
            pass  # Index might already exist or column issue
    
    # Create invoices table
    # invoices.status intended values:
    # - 'scanned'    : OCR populated fields
    # - 'ready'      : ready for submission / review
    # - 'submitted'  : fully processed / exported
    # - 'error'      : invoice-level failure
    # - 'needs_review': validation errors detected (math errors > 10%, etc.)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id TEXT PRIMARY KEY,
            doc_id TEXT,
            supplier TEXT,
            date TEXT,
            value REAL,
            confidence REAL DEFAULT 0.9,
            status TEXT DEFAULT 'scanned',
            venue TEXT DEFAULT 'Main Restaurant',
            issues_count INTEGER DEFAULT 0,
            paired INTEGER DEFAULT 0,
            created_at TEXT DEFAULT NULL,
            delivery_note_id TEXT,
            pairing_status TEXT DEFAULT 'unpaired' CHECK(
                pairing_status IN ('unpaired','suggested','auto_paired','manual_paired')
            ),
            pairing_confidence REAL,
            pairing_model_version TEXT,
            FOREIGN KEY(doc_id) REFERENCES documents(id),
            FOREIGN KEY(delivery_note_id) REFERENCES documents(id)
        )
    """)
    _add_column_if_missing(cursor, "invoices", "delivery_note_id", "TEXT")
    _add_column_if_missing(
        cursor,
        "invoices",
        "pairing_status",
        "TEXT DEFAULT 'unpaired'"
    )
    _add_column_if_missing(cursor, "invoices", "pairing_confidence", "REAL")
    _add_column_if_missing(cursor, "invoices", "pairing_model_version", "TEXT")
    _add_column_if_missing(cursor, "invoices", "confidence_breakdown", "TEXT")
    if _table_has_column(cursor, "invoices", "pairing_status"):
        cursor.execute("""
            UPDATE invoices
            SET pairing_status = 'unpaired'
            WHERE pairing_status IS NULL
        """)
    _add_column_if_missing(cursor, "documents", "invoice_id", "TEXT REFERENCES invoices(id)")
    if _table_has_column(cursor, "invoices", "delivery_note_id"):
        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_invoices_delivery_note_unique
            ON invoices(delivery_note_id)
            WHERE delivery_note_id IS NOT NULL
        """)
    if _table_has_column(cursor, "documents", "invoice_id"):
        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_documents_invoice_unique
            ON documents(invoice_id)
            WHERE invoice_id IS NOT NULL
        """)
    if _table_has_column(cursor, "invoices", "pairing_status"):
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_invoices_pairing_status
            ON invoices(pairing_status)
        """)
    
    # Create invoice_line_items table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invoice_line_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_id TEXT NOT NULL,
            invoice_id TEXT,
            line_number INTEGER NOT NULL,
            description TEXT,
            qty REAL,
            unit_price REAL,
            total REAL,
            uom TEXT,
            sku TEXT,
            confidence REAL DEFAULT 0.9,
            created_at TEXT DEFAULT NULL,
            FOREIGN KEY(doc_id) REFERENCES documents(id),
            FOREIGN KEY(invoice_id) REFERENCES invoices(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pairing_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL DEFAULT (datetime('now')),
            invoice_id TEXT NOT NULL,
            delivery_note_id TEXT,
            action TEXT NOT NULL,
            actor_type TEXT NOT NULL,
            user_id TEXT,
            previous_delivery_note_id TEXT,
            feature_vector_json TEXT,
            model_version TEXT,
            FOREIGN KEY(invoice_id) REFERENCES invoices(id),
            FOREIGN KEY(delivery_note_id) REFERENCES documents(id),
            FOREIGN KEY(previous_delivery_note_id) REFERENCES documents(id)
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_pairing_events_invoice_id
        ON pairing_events(invoice_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_pairing_events_delivery_note_id
        ON pairing_events(delivery_note_id)
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS supplier_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier_id TEXT NOT NULL,
            venue_id TEXT NOT NULL DEFAULT '__default__',
            typical_delivery_weekdays TEXT,
            avg_days_between_deliveries REAL,
            std_days_between_deliveries REAL,
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(supplier_id, venue_id)
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_supplier_stats_supplier
        ON supplier_stats(supplier_id)
    """)
    
    # Create audit_log table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            ts TEXT,
            actor TEXT,
            action TEXT,
            detail TEXT
        )
    """)
    
    # Create indexes for performance (with error handling for existing tables)
    try:
        # Check if doc_id column exists before creating index
        cursor.execute("PRAGMA table_info(invoice_line_items)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'doc_id' in columns:
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_line_items_doc_id ON invoice_line_items(doc_id)")
        if 'invoice_id' in columns:
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_line_items_invoice_id ON invoice_line_items(invoice_id)")
        if 'sku' in columns:
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_line_items_sku ON invoice_line_items(sku) WHERE sku IS NOT NULL")
    except Exception as e:
        LOGGER.warning(f"[DB] Error creating indexes (may already exist or table structure differs): {e}")
    
    # Run migration 0004 for System Bible tables
    try:
        migration_path = Path(__file__).parent.parent.parent / "migrations" / "0004_complete_system_bible.sql"
        if migration_path.exists():
            with open(migration_path, 'r', encoding='utf-8') as f:
                migration_sql = f.read()
            cursor.executescript(migration_sql)
            LOGGER.info("[DB] Migration 0004 applied successfully")
    except Exception as e:
        LOGGER.warning(f"[DB] Error applying migration 0004: {e}")

    # Apply pairing schema migration (010)
    try:
        pairing_migration_path = Path(__file__).parent.parent.parent / "migrations" / "010_invoice_dn_pairing.sql"
        if pairing_migration_path.exists():
            with open(pairing_migration_path, 'r', encoding='utf-8') as f:
                migration_sql = f.read()
            cursor.executescript(migration_sql)
            LOGGER.info("[DB] Migration 010 applied successfully")
    except Exception as e:
        LOGGER.warning(f"[DB] Error applying migration 010: {e}")
    
    conn.commit()
    conn.close()

def insert_document(doc_id, filename, stored_path, size_bytes, sha256=None):
    """Insert a new document record"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO documents (id, filename, stored_path, size_bytes, uploaded_at, sha256)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (doc_id, filename, stored_path, size_bytes, datetime.now().isoformat(), sha256))
    
    conn.commit()
    conn.close()

def find_document_by_hash(sha256_hash):
    """Find existing document by SHA-256 hash"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, filename, stored_path, size_bytes, uploaded_at, status
        FROM documents
        WHERE sha256 = ?
        LIMIT 1
    """, (sha256_hash,))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            "id": row[0],
            "filename": row[1],
            "stored_path": row[2],
            "size_bytes": row[3],
            "uploaded_at": row[4],
            "status": row[5] if len(row) > 5 else None
        }
    return None

# LEGACY: Used only by owlin_mvp.py (Streamlit prototype). Not used by main API.
def list_invoices():
    """Get all invoices with document info"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT i.id, i.doc_id, i.supplier, i.date, i.value, d.filename
        FROM invoices i
        LEFT JOIN documents d ON i.doc_id = d.id
        ORDER BY i.id DESC
    """)
    
    results = cursor.fetchall()
    conn.close()
    
    invoices = []
    for row in results:
        invoices.append({
            "id": row[0],
            "doc_id": row[1],
            "supplier": row[2],
            "date": row[3],
            "value": row[4],
            "filename": row[5]
        })
    
    return {"invoices": invoices}

def list_recent_documents(limit=10):
    """Get recent documents"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, filename, size_bytes, uploaded_at
        FROM documents
        ORDER BY uploaded_at DESC
        LIMIT ?
    """, (limit,))
    
    results = cursor.fetchall()
    conn.close()
    
    documents = []
    for row in results:
        documents.append({
            "doc_id": row[0],
            "filename": row[1],
            "size_kb": round(row[2] / 1024, 1),
            "uploaded_at": row[3]
        })
    
    return documents

def upsert_invoice(doc_id, supplier, date, value, invoice_number=None, confidence=0.9, status='scanned', confidence_breakdown=None):
    """
    Insert or update an invoice with optional invoice_number, confidence, status, and confidence breakdown.
    
    Args:
        doc_id: Document ID
        supplier: Supplier name
        date: Invoice date (YYYY-MM-DD)
        value: Total invoice value
        invoice_number: Optional invoice number
        confidence: OCR/LLM confidence score (default 0.9)
        status: Invoice status ('scanned', 'needs_review', 'ready', 'submitted', 'error')
        confidence_breakdown: Optional confidence breakdown dict or JSON string
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Validate status
    valid_statuses = ['scanned', 'needs_review', 'ready', 'submitted', 'error']
    if status not in valid_statuses:
        status = 'scanned'  # Default to scanned if invalid
    
    # Check if invoice_number and confidence_breakdown columns exist (for backward compatibility)
    cursor.execute("PRAGMA table_info(invoices)")
    columns = [row[1] for row in cursor.fetchall()]
    has_invoice_number_column = 'invoice_number' in columns
    has_confidence_breakdown_column = 'confidence_breakdown' in columns
    
    # Serialize confidence_breakdown if it's a dict
    breakdown_json = None
    if confidence_breakdown:
        if isinstance(confidence_breakdown, dict):
            breakdown_json = json.dumps(confidence_breakdown)
        elif isinstance(confidence_breakdown, str):
            breakdown_json = confidence_breakdown
    
    if has_invoice_number_column and has_confidence_breakdown_column:
        # Use doc_id as invoice id for simplicity
        cursor.execute("""
            INSERT OR REPLACE INTO invoices (id, doc_id, supplier, date, value, invoice_number, confidence, status, created_at, confidence_breakdown)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (doc_id, doc_id, supplier, date, value, invoice_number, confidence, status, datetime.now().isoformat(), breakdown_json))
    elif has_invoice_number_column:
        cursor.execute("""
            INSERT OR REPLACE INTO invoices (id, doc_id, supplier, date, value, invoice_number, confidence, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (doc_id, doc_id, supplier, date, value, invoice_number, confidence, status, datetime.now().isoformat()))
    elif has_confidence_breakdown_column:
        cursor.execute("""
            INSERT OR REPLACE INTO invoices (id, doc_id, supplier, date, value, confidence, status, created_at, confidence_breakdown)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (doc_id, doc_id, supplier, date, value, confidence, status, datetime.now().isoformat(), breakdown_json))
    else:
        # Fallback for databases without invoice_number or confidence_breakdown columns
        cursor.execute("""
            INSERT OR REPLACE INTO invoices (id, doc_id, supplier, date, value, confidence, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (doc_id, doc_id, supplier, date, value, confidence, status, datetime.now().isoformat()))
    
    conn.commit()
    conn.close()

def append_audit(ts, actor, action, detail):
    """Append to audit log"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO audit_log (ts, actor, action, detail)
        VALUES (?, ?, ?, ?)
    """, (ts, actor, action, detail))
    
    conn.commit()
    conn.close()
    
    # Also write to file
    log_path = "logs/audit.log"
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"{ts} | {actor} | {action} | {detail}\n")

def set_last_error(when, route, message, detail):
    """Set last error"""
    global _last_error
    _last_error = {
        "when": when,
        "route": route,
        "message": message,
        "detail": detail
    }

def get_last_error():
    """Get last error"""
    return _last_error

def clear_last_error():
    """Clear the last error"""
    global _last_error
    _last_error = {"when": "", "route": "", "message": "", "detail": ""}

def store_ocr_report(doc_id: str, ocr_report_json: str) -> bool:
    """
    Store OCR telemetry report in database.
    
    Args:
        doc_id: Document ID
        ocr_report_json: JSON string of OCR telemetry report
        
    Returns:
        True if successful, False otherwise
    """
    try:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE documents
            SET ocr_report_json = ?
            WHERE id = ?
        """, (ocr_report_json, doc_id))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        LOGGER.error(f"[DB] Failed to store OCR report for doc_id={doc_id}: {e}")
        return False


def update_document_status(doc_id, status, stage, confidence=None, error=None):
    """Update document OCR status"""
    import json
    import time
    import traceback
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        if confidence is not None:
            cursor.execute("""
                UPDATE documents 
                SET status = ?, ocr_stage = ?, ocr_confidence = ?, ocr_error = ?
                WHERE id = ?
            """, (status, stage, confidence, error, doc_id))
        else:
            cursor.execute("""
                UPDATE documents 
                SET status = ?, ocr_stage = ?, ocr_error = ?
                WHERE id = ?
            """, (status, stage, error, doc_id))
        
        conn.commit()
        conn.close()
        
        # #region agent log
        try:
            # Import Path at function level with alias to avoid scoping issues
            from pathlib import Path as _Path
            log_path = _Path(__file__).parent.parent.parent / ".cursor" / "debug.log"
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"db.py:503","message":"update_document_status success","data":{"doc_id":doc_id,"status":status,"stage":stage,"confidence":confidence},"timestamp":int(time.time()*1000)}) + "\n")
        except: pass
        # #endregion
    except Exception as e:
        error_msg = str(e)
        error_trace = traceback.format_exc()
        LOGGER.error(f"Failed to update document status for {doc_id}: {error_msg}")
        LOGGER.error(error_trace)
        # #region agent log
        try:
            import json
            import time
            log_path = Path(__file__).parent.parent.parent / ".cursor" / "debug.log"
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"db.py:503","message":"update_document_status failed","data":{"doc_id":doc_id,"status":status,"stage":stage,"error":error_msg,"traceback":error_trace[:1000]},"timestamp":int(time.time()*1000)}) + "\n")
        except: pass
        # #endregion
        raise

def update_document_classification(doc_id, doc_type, doc_type_confidence, doc_type_reasons):
    """Update document classification (type, confidence, reasons)"""
    import json
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Convert reasons list to JSON string
    reasons_json = json.dumps(doc_type_reasons) if doc_type_reasons else None
    
    cursor.execute("""
        UPDATE documents 
        SET doc_type = ?, 
            doc_type_confidence = ?,
            doc_type_reasons = ?
        WHERE id = ?
    """, (doc_type, doc_type_confidence, reasons_json, doc_id))
    
    conn.commit()
    conn.close()

def insert_line_items(doc_id, invoice_id, line_items):
    """Insert line items for an invoice"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if bbox column exists (for backward compatibility)
    cursor.execute("PRAGMA table_info(invoice_line_items)")
    columns = [row[1] for row in cursor.fetchall()]
    has_bbox_column = 'bbox' in columns
    
    for idx, item in enumerate(line_items):
        # Extract bbox if present (handle both list and string formats)
        bbox_value = None
        if 'bbox' in item and item['bbox']:
            bbox = item['bbox']
            if isinstance(bbox, list) and len(bbox) >= 4:
                # Convert list to JSON string: "[x,y,w,h]"
                bbox_value = json.dumps(bbox)
            elif isinstance(bbox, str):
                # Already a string, validate it's valid JSON
                try:
                    json.loads(bbox)  # Validate JSON
                    bbox_value = bbox
                except (json.JSONDecodeError, TypeError):
                    bbox_value = None
        
        if has_bbox_column:
            cursor.execute("""
                INSERT INTO invoice_line_items 
                (doc_id, invoice_id, line_number, description, qty, unit_price, total, uom, confidence, bbox)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                doc_id,
                invoice_id,
                idx + 1,
                item.get('description', item.get('desc', '')),
                item.get('qty', item.get('quantity', None)),
                item.get('unit_price', None),
                item.get('total', None),
                item.get('uom', item.get('unit', '')),
                item.get('confidence', 0.9),
                bbox_value
            ))
        else:
            # Fallback for databases without bbox column
            cursor.execute("""
                INSERT INTO invoice_line_items 
                (doc_id, invoice_id, line_number, description, qty, unit_price, total, uom, confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                doc_id,
                invoice_id,
                idx + 1,
                item.get('description', item.get('desc', '')),
                item.get('qty', item.get('quantity', None)),
                item.get('unit_price', None),
                item.get('total', None),
                item.get('uom', item.get('unit', '')),
                item.get('confidence', 0.9)
            ))
    
    conn.commit()
    conn.close()

def get_line_items_for_invoice(invoice_id):
    """Get line items for a specific invoice"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if bbox column exists
    cursor.execute("PRAGMA table_info(invoice_line_items)")
    columns = [row[1] for row in cursor.fetchall()]
    has_bbox_column = 'bbox' in columns
    
    if has_bbox_column:
        cursor.execute("""
            SELECT line_number, description, qty, unit_price, total, uom, confidence, bbox
            FROM invoice_line_items
            WHERE invoice_id = ?
            ORDER BY line_number
        """, (invoice_id,))
    else:
        cursor.execute("""
            SELECT line_number, description, qty, unit_price, total, uom, confidence
            FROM invoice_line_items
            WHERE invoice_id = ?
            ORDER BY line_number
        """, (invoice_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    line_items = []
    for row in rows:
        item = {
            "line_number": row[0],
            "desc": row[1] or "",
            "qty": row[2] or 0,
            "unit_price": row[3] or 0,
            "total": row[4] or 0,
            "uom": row[5] or "",
            "confidence": row[6] or 0.9
        }
        
        # Parse bbox if present
        if has_bbox_column and len(row) > 7 and row[7]:
            try:
                bbox_str = row[7]
                if isinstance(bbox_str, str):
                    bbox = json.loads(bbox_str)
                    if isinstance(bbox, list) and len(bbox) >= 4:
                        item["bbox"] = bbox
            except (json.JSONDecodeError, TypeError, IndexError):
                pass  # Invalid bbox, skip it
        
        line_items.append(item)
    
    return line_items

def get_line_items_for_doc(doc_id, invoice_id=None):
    """
    Get line items for a specific document.
    
    Args:
        doc_id: Document ID
        invoice_id: Optional invoice ID. If provided, filters by both doc_id and invoice_id.
                   If None, determines document type and applies appropriate filter.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if bbox column exists
    cursor.execute("PRAGMA table_info(invoice_line_items)")
    columns = [row[1] for row in cursor.fetchall()]
    has_bbox_column = 'bbox' in columns
    
    # If invoice_id is provided, use it directly
    if invoice_id is not None:
        if has_bbox_column:
            cursor.execute("""
                SELECT line_number, description, qty, unit_price, total, uom, confidence, bbox
                FROM invoice_line_items
                WHERE doc_id = ? AND invoice_id = ?
                ORDER BY line_number
            """, (doc_id, invoice_id))
        else:
            cursor.execute("""
                SELECT line_number, description, qty, unit_price, total, uom, confidence
                FROM invoice_line_items
                WHERE doc_id = ? AND invoice_id = ?
                ORDER BY line_number
            """, (doc_id, invoice_id))
    else:
        # Check document type to determine appropriate filter
        cursor.execute("PRAGMA table_info(documents)")
        columns_doc = [row[1] for row in cursor.fetchall()]
        has_doc_type = 'doc_type' in columns_doc
        
        is_delivery_note = False
        if has_doc_type:
            cursor.execute("SELECT doc_type FROM documents WHERE id = ?", (doc_id,))
            doc_type_row = cursor.fetchone()
            if doc_type_row and doc_type_row[0] == 'delivery_note':
                is_delivery_note = True
        
        # Apply filter based on document type
        if is_delivery_note:
            # For delivery notes, filter by invoice_id IS NULL
            if has_bbox_column:
                cursor.execute("""
                    SELECT line_number, description, qty, unit_price, total, uom, confidence, bbox
                    FROM invoice_line_items
                    WHERE doc_id = ? AND invoice_id IS NULL
                    ORDER BY line_number
                """, (doc_id,))
            else:
                cursor.execute("""
                    SELECT line_number, description, qty, unit_price, total, uom, confidence
                    FROM invoice_line_items
                    WHERE doc_id = ? AND invoice_id IS NULL
                    ORDER BY line_number
                """, (doc_id,))
        else:
            # For invoices or documents without doc_type, filter by invoice_id IS NOT NULL
            # This ensures we get invoice line items, not delivery note items
            if has_bbox_column:
                cursor.execute("""
                    SELECT line_number, description, qty, unit_price, total, uom, confidence, bbox
                    FROM invoice_line_items
                    WHERE doc_id = ? AND invoice_id IS NOT NULL
                    ORDER BY line_number
                """, (doc_id,))
            else:
                cursor.execute("""
                    SELECT line_number, description, qty, unit_price, total, uom, confidence
                    FROM invoice_line_items
                    WHERE doc_id = ? AND invoice_id IS NOT NULL
                    ORDER BY line_number
                """, (doc_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    line_items = []
    for row in rows:
        item = {
            "line_number": row[0],
            "desc": row[1] or "",
            "qty": row[2] or 0,
            "unit_price": row[3] or 0,
            "total": row[4] or 0,
            "uom": row[5] or "",
            "confidence": row[6] or 0.9
        }
        
        # Parse bbox if present
        if has_bbox_column and len(row) > 7 and row[7]:
            try:
                bbox_str = row[7]
                if isinstance(bbox_str, str):
                    bbox = json.loads(bbox_str)
                    if isinstance(bbox, list) and len(bbox) >= 4:
                        item["bbox"] = bbox
            except (json.JSONDecodeError, TypeError, IndexError):
                pass  # Invalid bbox, skip it
        
        line_items.append(item)
    
    return line_items


def _normalize_venue_id(venue_id: Optional[str]) -> str:
    return venue_id or "__default__"


def _serialize_feature_vector(feature_vector: Optional[Any]) -> Optional[str]:
    if feature_vector is None:
        return None
    if isinstance(feature_vector, str):
        return feature_vector
    try:
        return json.dumps(feature_vector)
    except TypeError:
        return json.dumps({"value": str(feature_vector)})


def insert_pairing_event(
    invoice_id: str,
    action: str,
    actor_type: str,
    delivery_note_id: Optional[str] = None,
    user_id: Optional[str] = None,
    previous_delivery_note_id: Optional[str] = None,
    feature_vector: Optional[Any] = None,
    model_version: Optional[str] = None,
) -> None:
    """Persist a pairing event for auditing and analytics."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO pairing_events (
            timestamp,
            invoice_id,
            delivery_note_id,
            action,
            actor_type,
            user_id,
            previous_delivery_note_id,
            feature_vector_json,
            model_version
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            datetime.utcnow().isoformat(),
            invoice_id,
            delivery_note_id,
            action,
            actor_type,
            user_id,
            previous_delivery_note_id,
            _serialize_feature_vector(feature_vector),
            model_version,
        ),
    )
    conn.commit()
    conn.close()


def get_supplier_stats(supplier_id: str, venue_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Retrieve supplier delivery cadence stats.

    Returns the most specific record (exact venue match) or falls back to the
    default aggregate when none exists.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT supplier_id,
               venue_id,
               typical_delivery_weekdays,
               avg_days_between_deliveries,
               std_days_between_deliveries,
               updated_at
        FROM supplier_stats
        WHERE supplier_id = ?
        ORDER BY CASE
            WHEN venue_id = ? THEN 0
            WHEN venue_id = '__default__' THEN 1
            ELSE 2
        END
        LIMIT 1
        """,
        (supplier_id, _normalize_venue_id(venue_id)),
    )
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    weekdays = json.loads(row[2]) if row[2] else None
    return {
        "supplier_id": row[0],
        "venue_id": None if row[1] == "__default__" else row[1],
        "typical_delivery_weekdays": weekdays,
        "avg_days_between_deliveries": row[3],
        "std_days_between_deliveries": row[4],
        "updated_at": row[5],
    }


def upsert_supplier_stats(
    supplier_id: str,
    venue_id: Optional[str],
    typical_delivery_weekdays: Optional[Any],
    avg_days_between_deliveries: Optional[float],
    std_days_between_deliveries: Optional[float],
) -> None:
    """Insert or update supplier cadence stats."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO supplier_stats (
            supplier_id,
            venue_id,
            typical_delivery_weekdays,
            avg_days_between_deliveries,
            std_days_between_deliveries,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(supplier_id, venue_id) DO UPDATE SET
            typical_delivery_weekdays = excluded.typical_delivery_weekdays,
            avg_days_between_deliveries = excluded.avg_days_between_deliveries,
            std_days_between_deliveries = excluded.std_days_between_deliveries,
            updated_at = excluded.updated_at
        """,
        (
            supplier_id,
            _normalize_venue_id(venue_id),
            json.dumps(typical_delivery_weekdays) if typical_delivery_weekdays is not None else None,
            avg_days_between_deliveries,
            std_days_between_deliveries,
            datetime.utcnow().isoformat(),
        ),
    )
    conn.commit()
    conn.close()

def get_db_wal_mode() -> str:
    """Get current database journal mode"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode")
        result = cursor.fetchone()
        conn.close()
        return result[0].upper() if result else "UNKNOWN"
    except Exception:
        return "ERROR"


def check_invoice_exists(doc_id: str) -> bool:
    """Check if an invoice exists for the given document ID"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM invoices WHERE doc_id = ?", (doc_id,))
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0
