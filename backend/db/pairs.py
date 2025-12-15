"""
Database operations for Invoice ↔ Delivery-Note pairing

This module uses the unified schema from backend/app/db.py:
- documents table: stores file metadata (id, filename, stored_path, status, etc.)
- invoices table: stores extracted invoice data (supplier, date, value, etc.)
- Both tables are linked via documents.invoice_id or invoices.doc_id
"""
import sqlite3
import json
from datetime import datetime, date
from typing import List, Dict, Optional, Tuple
import os
from pathlib import Path

# Use same DB_PATH as app/db.py
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_PROJECT_ROOT = _BACKEND_DIR.parent
DB_PATH = str(_PROJECT_ROOT / "data" / "owlin.db")

def get_db_connection():
    """Get database connection with proper configuration"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn

def run_migration():
    """Run the pairs migration"""
    conn = get_db_connection()
    try:
        with open("migrations/0003_pairs.sql", "r") as f:
            migration_sql = f.read()
        conn.executescript(migration_sql)
        conn.commit()
        print("✅ Pairs migration completed")
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        conn.close()

def db_insert_document(doc: Dict) -> int:
    """Insert or update document, return document ID"""
    conn = get_db_connection()
    try:
        # Check if document already exists by sha256
        cursor = conn.execute(
            "SELECT id FROM documents WHERE sha256 = ?", 
            (doc["sha256"],)
        )
        existing = cursor.fetchone()
        
        if existing:
            # Update existing document
            conn.execute("""
                UPDATE documents SET 
                    filename = ?, bytes = ?, supplier = ?, invoice_no = ?, 
                    delivery_no = ?, doc_date = ?, total = ?, currency = ?, doc_type = ?
                WHERE sha256 = ?
            """, (
                doc["filename"], doc["bytes"], doc["supplier"], doc["invoice_no"],
                doc["delivery_no"], doc["doc_date"], doc["total"], doc["currency"], 
                doc["doc_type"], doc["sha256"]
            ))
            doc_id = existing["id"]
        else:
            # Insert new document
            cursor = conn.execute("""
                INSERT INTO documents (sha256, filename, bytes, supplier, invoice_no, 
                                    delivery_no, doc_date, total, currency, doc_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                doc["sha256"], doc["filename"], doc["bytes"], doc["supplier"], 
                doc["invoice_no"], doc["delivery_no"], doc["doc_date"], 
                doc["total"], doc["currency"], doc["doc_type"]
            ))
            doc_id = cursor.lastrowid
        
        conn.commit()
        return doc_id
    finally:
        conn.close()

def db_get_document(doc_id: int) -> Optional[Dict]:
    """Get document by ID"""
    conn = get_db_connection()
    try:
        cursor = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def db_recent_docs(doc_type: str, supplier: Optional[str] = None, days: int = 14) -> List[Dict]:
    """Get recent documents of specific type"""
    conn = get_db_connection()
    try:
        query = """
            SELECT * FROM documents 
            WHERE doc_type = ? AND created_at >= datetime('now', '-{} days')
        """.format(days)
        params = [doc_type]
        
        if supplier:
            query += " AND supplier = ?"
            params.append(supplier)
        
        query += " ORDER BY created_at DESC LIMIT 50"
        
        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

def db_upsert_pair_suggest(invoice_doc: Dict, delivery_id: int, confidence: float):
    """Create or update pair suggestion"""
    conn = get_db_connection()
    try:
        # Check if pair already exists
        cursor = conn.execute(
            "SELECT id FROM pairs WHERE invoice_id = ? AND delivery_id = ?",
            (invoice_doc["id"], delivery_id)
        )
        existing = cursor.fetchone()
        
        if existing:
            # Update existing suggestion
            conn.execute(
                "UPDATE pairs SET confidence = ?, status = 'suggested', created_at = datetime('now') WHERE id = ?",
                (confidence, existing["id"])
            )
        else:
            # Create new suggestion
            conn.execute("""
                INSERT INTO pairs (invoice_id, delivery_id, confidence, status)
                VALUES (?, ?, ?, 'suggested')
            """, (invoice_doc["id"], delivery_id, confidence))
        
        conn.commit()
    finally:
        conn.close()

def db_list_pairs(status: str = "suggested", limit: int = 50, invoice_id: Optional[int] = None) -> List[Dict]:
    """
    List pairs with document details using unified schema.
    
    Uses documents table for file metadata and invoices table for extracted data.
    """
    conn = get_db_connection()
    try:
        # Check if pairs table exists and has the expected schema
        cursor = conn.execute("PRAGMA table_info(pairs)")
        pairs_columns = [row[1] for row in cursor.fetchall()]
        
        # Check if documents table has the old schema (supplier column) or new schema
        cursor.execute("PRAGMA table_info(documents)")
        doc_columns = [row[1] for row in cursor.fetchall()]
        has_old_schema = 'supplier' in doc_columns
        
        if has_old_schema:
            # Old schema: documents table has supplier, invoice_no, etc.
            query = """
                SELECT 
                    p.id, p.invoice_id, p.delivery_id, p.confidence, p.status, p.created_at,
                    i.filename as invoice_filename, i.supplier as invoice_supplier,
                    i.invoice_no, i.doc_date as invoice_date, i.total as invoice_total,
                    d.filename as delivery_filename, d.delivery_no, d.doc_date as delivery_date
                FROM pairs p
                JOIN documents i ON p.invoice_id = i.id
                JOIN documents d ON p.delivery_id = d.id
                WHERE p.status = ?
            """
        else:
            # New unified schema: join documents with invoices table
            query = """
                SELECT 
                    p.id, p.invoice_id, p.delivery_id, p.confidence, p.status, p.created_at,
                    di.filename as invoice_filename, inv.supplier as invoice_supplier,
                    inv.date as invoice_date, inv.value as invoice_total,
                    dd.filename as delivery_filename, dd.uploaded_at as delivery_date
                FROM pairs p
                JOIN documents di ON p.invoice_id = di.id
                LEFT JOIN invoices inv ON di.id = inv.doc_id
                JOIN documents dd ON p.delivery_id = dd.id
                WHERE p.status = ?
            """
        
        params = [status]
        
        if invoice_id is not None:
            query += " AND p.invoice_id = ?"
            params.append(invoice_id)
        
        query += " ORDER BY p.confidence DESC, p.created_at DESC LIMIT ?"
        params.append(limit)
        
        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

def db_set_pair_status(pair_id: int, status: str):
    """Set pair status (accepted/rejected)"""
    conn = get_db_connection()
    try:
        conn.execute(
            "UPDATE pairs SET status = ?, decided_at = datetime('now') WHERE id = ?",
            (status, pair_id)
        )
        conn.commit()
    finally:
        conn.close()

def date_from(date_str: str) -> date:
    """Parse ISO date string to date object"""
    try:
        return datetime.fromisoformat(date_str.replace('Z', '+00:00')).date()
    except:
        return None
