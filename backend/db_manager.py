"""
db_manager.py
==============

This module manages interactions with the local SQLite database used
by Owlin.  It encapsulates initialisation of the database schema,
insertion of new invoice records and simple role-based permission
checks.  The functions defined here can be imported by other
components (such as the upload UI) to persist data and enforce
access control.

The invoices table stores basic invoice metadata: supplier name,
invoice number, date, amounts and currency.  Additional fields can
be added as needed.  Each invoice is timestamped upon insertion.
"""

from __future__ import annotations

import os
import sqlite3
import logging
from typing import Any, Dict, Optional, List, Tuple
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Default database path
DEFAULT_DB_PATH = "data/owlin.db"

# Supported user roles
SUPPORTED_ROLES = {"viewer", "finance", "admin", "GM"}

def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    """Initialise the SQLite database, creating tables if necessary.

    If the database file or the invoices table does not exist, this
    function will create them.  It is safe to call this function
    multiple times; subsequent calls will have no effect.

    Parameters
    ----------
    db_path: str
        Path to the SQLite database file.
    """
    try:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create invoices table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                supplier_name TEXT,
                invoice_number TEXT UNIQUE,
                invoice_date TEXT,
                net_amount REAL,
                vat_amount REAL,
                total_amount REAL,
                currency TEXT,
                file_path TEXT,
                file_hash TEXT,
                ocr_confidence REAL,
                processing_status TEXT DEFAULT 'processed',
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        
        # Create delivery_notes table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS delivery_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                supplier_name TEXT,
                delivery_number TEXT UNIQUE,
                delivery_date TEXT,
                total_items INTEGER,
                file_path TEXT,
                file_hash TEXT,
                ocr_confidence REAL,
                processing_status TEXT DEFAULT 'processed',
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        
        # Create file_hashes table for duplicate detection
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS file_hashes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_hash TEXT UNIQUE,
                file_path TEXT,
                file_size INTEGER,
                mime_type TEXT,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        
        # Create processing_logs table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS processing_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT,
                processing_status TEXT,
                ocr_confidence REAL,
                error_message TEXT,
                processing_time REAL,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        
        # Create indexes for better performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_invoices_number ON invoices(invoice_number);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_invoices_supplier ON invoices(supplier_name);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_invoices_date ON invoices(invoice_date);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_delivery_number ON delivery_notes(delivery_number);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_file_hashes ON file_hashes(file_hash);")
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Database initialized successfully: {db_path}")
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise


def save_invoice(extracted_data: Dict[str, Any], db_path: str = DEFAULT_DB_PATH) -> bool:
    """Persist extracted invoice data into the database.

    This function inserts a new record into the invoices table.  It
    assumes that ``init_db`` has been called beforehand.  If an
    invoice with the same number already exists, the insertion will
    silently fail due to the UNIQUE constraint, preventing duplicate
    records from being created.

    Parameters
    ----------
    extracted_data: Dict[str, Any]
        Dictionary containing invoice metadata as returned by
        ``extract_invoice_fields``.
    db_path: str
        Path to the SQLite database file.
        
    Returns
    -------
    bool
        True if invoice was saved successfully, False if duplicate or error
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Convert line_items to JSON string if present
        line_items_json = None
        if 'line_items' in extracted_data and extracted_data['line_items']:
            import json
            line_items_json = json.dumps(extracted_data['line_items'])
        
        # Convert page_numbers to string if present
        page_numbers_str = None
        if 'page_numbers' in extracted_data and extracted_data['page_numbers']:
            page_numbers_str = ','.join(map(str, extracted_data['page_numbers']))
        
        cursor.execute(
            """
            INSERT OR IGNORE INTO invoices (
                supplier_name,
                invoice_number,
                invoice_date,
                net_amount,
                vat_amount,
                total_amount,
                currency,
                file_path,
                file_hash,
                ocr_confidence,
                ocr_text,
                page_numbers,
                line_items,
                subtotal,
                vat,
                vat_rate,
                total_incl_vat
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                extracted_data.get("supplier_name"),
                extracted_data.get("invoice_number"),
                extracted_data.get("invoice_date"),
                extracted_data.get("net_amount"),
                extracted_data.get("vat_amount"),
                extracted_data.get("total_amount"),
                extracted_data.get("currency"),
                extracted_data.get("file_path"),
                extracted_data.get("file_hash"),
                extracted_data.get("ocr_confidence", 0.0),
                extracted_data.get("ocr_text"),
                page_numbers_str,
                line_items_json,
                extracted_data.get("subtotal"),
                extracted_data.get("vat"),
                extracted_data.get("vat_rate"),
                extracted_data.get("total_incl_vat")
            ),
        )
        
        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        if rows_affected > 0:
            logger.info(f"✅ Invoice saved successfully: {extracted_data.get('invoice_number')}")
            return True
        else:
            logger.warning(f"⚠️ Invoice already exists: {extracted_data.get('invoice_number')}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Failed to save invoice: {e}")
        return False


def save_delivery_note(extracted_data: Dict[str, Any], db_path: str = DEFAULT_DB_PATH) -> bool:
    """Persist extracted delivery note data into the database.
    
    Parameters
    ----------
    extracted_data: Dict[str, Any]
        Dictionary containing delivery note metadata
    db_path: str
        Path to the SQLite database file
        
    Returns
    -------
    bool
        True if delivery note was saved successfully, False if duplicate or error
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            """
            INSERT OR IGNORE INTO delivery_notes (
                supplier_name,
                delivery_number,
                delivery_date,
                total_items,
                file_path,
                file_hash,
                ocr_confidence
            ) VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            (
                extracted_data.get("supplier_name"),
                extracted_data.get("delivery_number"),
                extracted_data.get("delivery_date"),
                extracted_data.get("total_items"),
                extracted_data.get("file_path"),
                extracted_data.get("file_hash"),
                extracted_data.get("ocr_confidence", 0.0)
            ),
        )
        
        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        if rows_affected > 0:
            logger.info(f"✅ Delivery note saved successfully: {extracted_data.get('delivery_number')}")
            return True
        else:
            logger.warning(f"⚠️ Delivery note already exists: {extracted_data.get('delivery_number')}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Failed to save delivery note: {e}")
        return False


def save_file_hash(file_hash: str, file_path: str, file_size: int, mime_type: str, 
                  db_path: str = DEFAULT_DB_PATH) -> bool:
    """Save file hash for duplicate detection.
    
    Parameters
    ----------
    file_hash: str
        MD5 hash of the file content
    file_path: str
        Path to the uploaded file
    file_size: int
        Size of the file in bytes
    mime_type: str
        MIME type of the file
    db_path: str
        Path to the SQLite database file
        
    Returns
    -------
    bool
        True if file hash was saved successfully, False if duplicate or error
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            """
            INSERT OR IGNORE INTO file_hashes (
                file_hash,
                file_path,
                file_size,
                mime_type
            ) VALUES (?, ?, ?, ?);
            """,
            (file_hash, file_path, file_size, mime_type)
        )
        
        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        if rows_affected > 0:
            logger.info(f"✅ File hash saved successfully: {file_hash[:8]}...")
            return True
        else:
            logger.warning(f"⚠️ File hash already exists: {file_hash[:8]}...")
            return False
            
    except Exception as e:
        logger.error(f"❌ Failed to save file hash: {e}")
        return False


def check_duplicate_invoice(invoice_number: str, db_path: str = DEFAULT_DB_PATH) -> bool:
    """Check if an invoice number already exists in the database.
    
    Parameters
    ----------
    invoice_number: str
        Invoice number to check
    db_path: str
        Path to the SQLite database file
        
    Returns
    -------
    bool
        True if invoice number exists, False otherwise
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT COUNT(*) FROM invoices WHERE invoice_number = ?",
            (invoice_number,)
        )
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return count > 0
        
    except Exception as e:
        logger.error(f"❌ Failed to check duplicate invoice: {e}")
        return False


def check_duplicate_file_hash(file_hash: str, db_path: str = DEFAULT_DB_PATH) -> bool:
    """Check if a file hash already exists in the database.
    
    Parameters
    ----------
    file_hash: str
        File hash to check
    db_path: str
        Path to the SQLite database file
        
    Returns
    -------
    bool
        True if file hash exists, False otherwise
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT COUNT(*) FROM file_hashes WHERE file_hash = ?",
            (file_hash,)
        )
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return count > 0
        
    except Exception as e:
        logger.error(f"❌ Failed to check duplicate file hash: {e}")
        return False


def get_all_invoices(db_path: str = DEFAULT_DB_PATH) -> List[Dict[str, Any]]:
    """Retrieve all invoices from the database.
    
    Parameters
    ----------
    db_path: str
        Path to the SQLite database file
        
    Returns
    -------
    List[Dict[str, Any]]
        List of invoice records
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT 
                id, supplier_name, invoice_number, invoice_date,
                net_amount, vat_amount, total_amount, currency,
                file_path, ocr_confidence, processing_status, uploaded_at
            FROM invoices 
            ORDER BY uploaded_at DESC
            """
        )
        
        columns = [description[0] for description in cursor.description]
        invoices = []
        
        for row in cursor.fetchall():
            invoice = dict(zip(columns, row))
            # Map ocr_confidence to confidence for frontend compatibility
            if 'ocr_confidence' in invoice:
                invoice['confidence'] = invoice['ocr_confidence']
            invoices.append(invoice)
        
        conn.close()
        return invoices
        
    except Exception as e:
        logger.error(f"❌ Failed to retrieve invoices: {e}")
        return []


def get_all_delivery_notes(db_path: str = DEFAULT_DB_PATH) -> List[Dict[str, Any]]:
    """Retrieve all delivery notes from the database.
    
    Parameters
    ----------
    db_path: str
        Path to the SQLite database file
        
    Returns
    -------
    List[Dict[str, Any]]
        List of delivery note records
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT 
                id, supplier_name, delivery_number, delivery_date,
                total_items, file_path, ocr_confidence, processing_status, uploaded_at
            FROM delivery_notes 
            ORDER BY uploaded_at DESC
            """
        )
        
        columns = [description[0] for description in cursor.description]
        delivery_notes = []
        
        for row in cursor.fetchall():
            delivery_note = dict(zip(columns, row))
            delivery_notes.append(delivery_note)
        
        conn.close()
        return delivery_notes
        
    except Exception as e:
        logger.error(f"❌ Failed to retrieve delivery notes: {e}")
        return []


def get_invoice_by_number(invoice_number: str, db_path: str = DEFAULT_DB_PATH) -> Optional[Dict[str, Any]]:
    """Retrieve a specific invoice by invoice number.
    
    Parameters
    ----------
    invoice_number: str
        Invoice number to retrieve
    db_path: str
        Path to the SQLite database file
        
    Returns
    -------
    Optional[Dict[str, Any]]
        Invoice record if found, None otherwise
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT 
                id, supplier_name, invoice_number, invoice_date,
                net_amount, vat_amount, total_amount, currency,
                file_path, ocr_confidence, processing_status, uploaded_at
            FROM invoices 
            WHERE invoice_number = ?
            """,
            (invoice_number,)
        )
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            columns = ['id', 'supplier_name', 'invoice_number', 'invoice_date',
                      'net_amount', 'vat_amount', 'total_amount', 'currency',
                      'file_path', 'ocr_confidence', 'processing_status', 'uploaded_at']
            return dict(zip(columns, row))
        else:
            return None
            
    except Exception as e:
        logger.error(f"❌ Failed to retrieve invoice: {e}")
        return None


def delete_invoice(invoice_id: int, db_path: str = DEFAULT_DB_PATH) -> bool:
    """Delete an invoice from the database.
    
    Parameters
    ----------
    invoice_id: int
        ID of the invoice to delete
    db_path: str
        Path to the SQLite database file
        
    Returns
    -------
    bool
        True if invoice was deleted successfully, False otherwise
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "DELETE FROM invoices WHERE id = ?",
            (invoice_id,)
        )
        
        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        if rows_affected > 0:
            logger.info(f"✅ Invoice deleted successfully: ID {invoice_id}")
            return True
        else:
            logger.warning(f"⚠️ Invoice not found: ID {invoice_id}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Failed to delete invoice: {e}")
        return False


def get_database_stats(db_path: str = DEFAULT_DB_PATH) -> Dict[str, Any]:
    """Get database statistics.
    
    Parameters
    ----------
    db_path: str
        Path to the SQLite database file
        
    Returns
    -------
    Dict[str, Any]
        Database statistics
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Count invoices
        cursor.execute("SELECT COUNT(*) FROM invoices")
        invoice_count = cursor.fetchone()[0]
        
        # Count delivery notes
        cursor.execute("SELECT COUNT(*) FROM delivery_notes")
        delivery_count = cursor.fetchone()[0]
        
        # Count file hashes
        cursor.execute("SELECT COUNT(*) FROM file_hashes")
        file_hash_count = cursor.fetchone()[0]
        
        # Get total invoice amount
        cursor.execute("SELECT SUM(total_amount) FROM invoices WHERE total_amount IS NOT NULL")
        total_amount = cursor.fetchone()[0] or 0
        
        # Get recent uploads (last 7 days)
        cursor.execute(
            """
            SELECT COUNT(*) FROM invoices 
            WHERE uploaded_at >= datetime('now', '-7 days')
            """
        )
        recent_uploads = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "invoice_count": invoice_count,
            "delivery_count": delivery_count,
            "file_hash_count": file_hash_count,
            "total_amount": total_amount,
            "recent_uploads": recent_uploads,
            "database_path": db_path
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get database stats: {e}")
        return {}


def user_has_permission(user_role: Optional[str]) -> bool:
    """Return True if the given role is allowed to upload invoices.

    Only roles 'GM', 'Finance', and 'admin' are permitted to upload invoices.
    Other roles (including None) are denied.

    Parameters
    ----------
    user_role: Optional[str]
        The role of the current user, if any.

    Returns
    -------
    bool
        True if upload is permitted, False otherwise.
    """
    allowed_roles = {"GM", "Finance", "admin"}
    return user_role in allowed_roles


def get_user_permissions(user_role: Optional[str]) -> Dict[str, bool]:
    """Get comprehensive user permissions based on role.
    
    Parameters
    ----------
    user_role: Optional[str]
        The role of the current user, if any.
        
    Returns
    -------
    Dict[str, bool]
        Dictionary of permissions for the user
    """
    if not user_role:
        return {
            "upload_invoices": False,
            "upload_delivery_notes": False,
            "view_invoices": True,
            "view_delivery_notes": True,
            "delete_invoices": False,
            "delete_delivery_notes": False,
            "view_statistics": True,
            "manage_users": False
        }
    
    permissions = {
        "viewer": {
            "upload_invoices": False,
            "upload_delivery_notes": False,
            "view_invoices": True,
            "view_delivery_notes": True,
            "delete_invoices": False,
            "delete_delivery_notes": False,
            "view_statistics": True,
            "manage_users": False
        },
        "finance": {
            "upload_invoices": True,
            "upload_delivery_notes": True,
            "view_invoices": True,
            "view_delivery_notes": True,
            "delete_invoices": False,
            "delete_delivery_notes": False,
            "view_statistics": True,
            "manage_users": False
        },
        "admin": {
            "upload_invoices": True,
            "upload_delivery_notes": True,
            "view_invoices": True,
            "view_delivery_notes": True,
            "delete_invoices": True,
            "delete_delivery_notes": True,
            "view_statistics": True,
            "manage_users": True
        },
        "GM": {
            "upload_invoices": True,
            "upload_delivery_notes": True,
            "view_invoices": True,
            "view_delivery_notes": True,
            "delete_invoices": True,
            "delete_delivery_notes": True,
            "view_statistics": True,
            "manage_users": False
        }
    }
    
    return permissions.get(user_role, permissions["viewer"])


def save_line_items(invoice_id: str, line_items: List[Dict[str, Any]], db_path: str = DEFAULT_DB_PATH) -> bool:
    """
    Save line items to the database
    
    Args:
        invoice_id: Invoice ID
        line_items: List of line item dictionaries
        db_path: Database path
        
    Returns:
        True if successful, False otherwise
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        for item in line_items:
            cursor.execute("""
                INSERT INTO invoice_line_items (
                    invoice_id, item_description, quantity, unit_price, 
                    total_price, source, confidence
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                invoice_id,
                item.get('description', ''),
                item.get('quantity', 1.0),
                item.get('unit_price', 0.0),
                item.get('total_price', 0.0),
                'ocr',
                item.get('confidence', 0.0)
            ))
        
        conn.commit()
        conn.close()
        logger.info(f"✅ Saved {len(line_items)} line items for invoice {invoice_id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to save line items: {e}")
        return False

def log_processing_result(file_path: str, status: str, ocr_confidence: float = 0.0, 
                        error_message: str = "", processing_time: float = 0.0,
                        db_path: str = DEFAULT_DB_PATH) -> None:
    """Log processing results for debugging and monitoring"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS processing_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT,
                processing_status TEXT,
                ocr_confidence REAL,
                error_message TEXT,
                processing_time REAL,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        
        cursor.execute(
            """
            INSERT INTO processing_logs 
            (file_path, processing_status, ocr_confidence, error_message, processing_time)
            VALUES (?, ?, ?, ?, ?)
            """,
            (file_path, status, ocr_confidence, error_message, processing_time)
        )
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        logger.error(f"Failed to log processing result: {e}")

def save_invoice_to_db(invoice_id: str, supplier_name: str, invoice_number: str, 
                      invoice_date: str, total_amount: float, confidence: float,
                      ocr_text: str, line_items: List[Any], db_path: str = DEFAULT_DB_PATH) -> bool:
    """Save invoice data to database with enhanced fields"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Convert line items to JSON string
        import json
        line_items_json = json.dumps([item.__dict__ if hasattr(item, '__dict__') else item for item in line_items])
        
        # Use the existing table structure
        cursor.execute("""
            INSERT OR REPLACE INTO invoices 
            (supplier_name, invoice_number, invoice_date, total_amount, ocr_confidence, ocr_text, line_items, processing_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            supplier_name, invoice_number, invoice_date, 
            total_amount, confidence, ocr_text, line_items_json, 'processed'
        ))
        
        conn.commit()
        conn.close()
        logger.info(f"✅ Invoice saved to database: {invoice_id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to save invoice to database: {e}")
        return False

def save_uploaded_file_to_db(file_id: str, original_filename: str, file_path: str,
                            file_type: str, confidence: float, db_path: str = DEFAULT_DB_PATH) -> bool:
    """Save uploaded file record to database"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Ensure uploaded_files table exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS uploaded_files (
                id TEXT PRIMARY KEY,
                original_filename TEXT,
                file_path TEXT,
                file_type TEXT,
                confidence REAL,
                upload_timestamp TEXT,
                status TEXT DEFAULT 'processed'
            )
        """)
        
        cursor.execute("""
            INSERT OR REPLACE INTO uploaded_files 
            (id, original_filename, file_path, file_type, confidence, upload_timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            file_id, original_filename, file_path, file_type, 
            confidence, datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
        logger.info(f"✅ Uploaded file saved to database: {file_id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to save uploaded file to database: {e}")
        return False

def get_all_uploaded_files(db_path: str = DEFAULT_DB_PATH) -> List[Dict[str, Any]]:
    """Get all uploaded files from database"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, original_filename, file_path, file_type, confidence, upload_timestamp, status
            FROM uploaded_files
            ORDER BY upload_timestamp DESC
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        files = []
        for row in rows:
            files.append({
                "id": row[0],
                "original_filename": row[1],
                "file_path": row[2],
                "file_type": row[3],
                "confidence": row[4],
                "upload_timestamp": row[5],
                "status": row[6]
            })
        
        return files
        
    except Exception as e:
        logger.error(f"❌ Failed to get uploaded files: {e}")
        return [] 