import sqlite3
import os
import json
import logging
from datetime import datetime
from pathlib import Path

LOGGER = logging.getLogger("owlin.db")

DB_PATH = "data/owlin.db"
_last_error = {"when": "", "route": "", "message": "", "detail": ""}

def init_db():
    """Initialize database with WAL mode and create tables if they don't exist"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
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
            sha256 TEXT
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
    
    # Create index on sha256 for duplicate detection
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_sha256 ON documents(sha256)")
    
    # Create invoices table
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
            FOREIGN KEY(doc_id) REFERENCES documents(id)
        )
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
            confidence REAL DEFAULT 0.9,
            created_at TEXT DEFAULT NULL,
            FOREIGN KEY(doc_id) REFERENCES documents(id),
            FOREIGN KEY(invoice_id) REFERENCES invoices(id)
        )
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
        SELECT id, filename, stored_path, size_bytes, uploaded_at
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
            "uploaded_at": row[4]
        }
    return None

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

def upsert_invoice(doc_id, supplier, date, value):
    """Insert or update an invoice"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Use doc_id as invoice id for simplicity
    cursor.execute("""
        INSERT OR REPLACE INTO invoices (id, doc_id, supplier, date, value)
        VALUES (?, ?, ?, ?, ?)
    """, (doc_id, doc_id, supplier, date, value))
    
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

def update_document_status(doc_id, status, stage, confidence=None, error=None):
    """Update document OCR status"""
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

def insert_line_items(doc_id, invoice_id, line_items):
    """Insert line items for an invoice"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    for idx, item in enumerate(line_items):
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
        line_items.append({
            "line_number": row[0],
            "desc": row[1] or "",
            "qty": row[2] or 0,
            "unit_price": row[3] or 0,
            "total": row[4] or 0,
            "uom": row[5] or "",
            "confidence": row[6] or 0.9
        })
    
    return line_items

def get_line_items_for_doc(doc_id):
    """Get line items for a specific document"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT line_number, description, qty, unit_price, total, uom, confidence
        FROM invoice_line_items
        WHERE doc_id = ?
        ORDER BY line_number
    """, (doc_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    line_items = []
    for row in rows:
        line_items.append({
            "line_number": row[0],
            "desc": row[1] or "",
            "qty": row[2] or 0,
            "unit_price": row[3] or 0,
            "total": row[4] or 0,
            "uom": row[5] or "",
            "confidence": row[6] or 0.9
        })
    
    return line_items

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
