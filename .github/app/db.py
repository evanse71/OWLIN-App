import sqlite3
import os
import json
from datetime import datetime
from pathlib import Path

DB_PATH = "data/owlin.db"
_last_error = {"when": "", "route": "", "message": "", "detail": ""}

def init_db():
    """Initialize database and create tables if they don't exist"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create documents table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            filename TEXT,
            stored_path TEXT,
            size_bytes INTEGER,
            uploaded_at TEXT
        )
    """)
    
    # Create invoices table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id TEXT PRIMARY KEY,
            doc_id TEXT,
            supplier TEXT,
            date TEXT,
            value REAL,
            FOREIGN KEY(doc_id) REFERENCES documents(id)
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
    
    conn.commit()
    conn.close()

def insert_document(doc_id, filename, stored_path, size_bytes):
    """Insert a new document record"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO documents (id, filename, stored_path, size_bytes, uploaded_at)
        VALUES (?, ?, ?, ?, ?)
    """, (doc_id, filename, stored_path, size_bytes, datetime.now().isoformat()))
    
    conn.commit()
    conn.close()

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
