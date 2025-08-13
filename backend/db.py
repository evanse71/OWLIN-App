import sqlite3
import os
from datetime import datetime
from typing import Optional, List

# Ensure data directory exists
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "owlin.db")

def get_db_connection():
    """Get a database connection."""
    return sqlite3.connect(DB_PATH)

def init_database():
    """Initialize the database with required tables."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create invoices table with enhanced fields for multi-invoice support
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id TEXT PRIMARY KEY,
            invoice_number TEXT,
            invoice_date TEXT,
            supplier_name TEXT,
            total_amount REAL,
            status TEXT,
            confidence REAL,
            upload_timestamp TEXT,
            ocr_text TEXT,
            parent_pdf_filename TEXT,
            page_numbers TEXT,
            line_items TEXT,
            subtotal REAL,
            vat REAL,
            vat_rate REAL,
            total_incl_vat REAL
        )
    """)
    
    # Create delivery_notes table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS delivery_notes (
            id TEXT PRIMARY KEY,
            delivery_note_number TEXT,
            delivery_date TEXT,
            supplier_name TEXT,
            total_amount REAL,
            status TEXT,
            confidence REAL,
            upload_timestamp TEXT,
            ocr_text TEXT,
            parent_pdf_filename TEXT
        )
    """)
    
    # Create uploaded_files table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS uploaded_files (
            id TEXT PRIMARY KEY,
            original_filename TEXT,
            file_type TEXT,
            processing_status TEXT,
            confidence REAL,
            upload_timestamp TEXT,
            error_message TEXT,
            document_status TEXT
        )
    """)
    
    # Add new columns to existing invoices table if they don't exist
    try:
        cursor.execute("ALTER TABLE invoices ADD COLUMN page_numbers TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    try:
        cursor.execute("ALTER TABLE invoices ADD COLUMN line_items TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    try:
        cursor.execute("ALTER TABLE invoices ADD COLUMN subtotal REAL")
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    try:
        cursor.execute("ALTER TABLE invoices ADD COLUMN vat REAL")
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    try:
        cursor.execute("ALTER TABLE invoices ADD COLUMN vat_rate REAL")
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    try:
        cursor.execute("ALTER TABLE invoices ADD COLUMN total_incl_vat REAL")
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    try:
        cursor.execute("ALTER TABLE invoices ADD COLUMN page_range TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    conn.commit()
    conn.close()

def insert_invoice_record(
    invoice_number: str,
    supplier_name: str,
    invoice_date: str,
    total_amount: float,
    confidence: float,
    ocr_text: str,
    filename: str,
    status: str = "scanned",
    upload_time: Optional[str] = None,
    parent_pdf_filename: Optional[str] = None,
    page_numbers: Optional[List[int]] = None,
    line_items: Optional[List[dict]] = None,
    subtotal: Optional[float] = None,
    vat: Optional[float] = None,
    vat_rate: Optional[float] = None,
    total_incl_vat: Optional[float] = None
):
    """Insert an invoice record into the database with enhanced multi-invoice support."""
    if upload_time is None:
        upload_time = datetime.utcnow().isoformat()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Generate unique ID
    import uuid
    invoice_id = str(uuid.uuid4())
    
    # Convert page_numbers list to string
    page_numbers_str = ",".join(map(str, page_numbers)) if page_numbers else None
    
    # Convert line_items to JSON string
    import json
    line_items_str = json.dumps(line_items) if line_items else None
    
    cursor.execute("""
        INSERT INTO invoices (
            id,
            invoice_number,
            supplier_name,
            invoice_date,
            total_amount,
            confidence,
            ocr_text,
            parent_pdf_filename,
            status,
            upload_timestamp,
            page_numbers,
            line_items,
            subtotal,
            vat,
            vat_rate,
            total_incl_vat
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        invoice_id,
        invoice_number,
        supplier_name,
        invoice_date,
        total_amount,
        confidence,
        ocr_text,
        parent_pdf_filename or filename,
        status,
        upload_time,
        page_numbers_str,
        line_items_str,
        subtotal,
        vat,
        vat_rate,
        total_incl_vat
    ))
    
    conn.commit()
    conn.close()
    
    return invoice_id

def get_all_invoices():
    """Get all invoices from the database with enhanced fields."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            id,
            invoice_number,
            invoice_date,
            supplier_name,
            total_amount,
            status,
            confidence,
            upload_timestamp,
            parent_pdf_filename,
            page_numbers,
            line_items,
            subtotal,
            vat,
            vat_rate,
            total_incl_vat,
            ocr_text,
            page_range,
            addresses,
            signature_regions,
            verification_status
        FROM invoices
        ORDER BY upload_timestamp DESC
    """)
    
    rows = cursor.fetchall()
    conn.close()
    
    invoices = []
    for row in rows:
        # Parse page_numbers string back to list
        page_numbers = []
        if row[9]:  # page_numbers
            try:
                page_numbers = [int(x) for x in row[9].split(",")]
            except (ValueError, AttributeError):
                page_numbers = []
        
        # Parse line_items JSON string back to list
        line_items = []
        if row[10]:  # line_items
            try:
                import json
                line_items = json.loads(row[10])
            except (json.JSONDecodeError, TypeError):
                line_items = []
        
        # Normalize confidence to 0-100 scale
        raw_conf = row[6]
        try:
            conf_pct = float(raw_conf) if raw_conf is not None else 0.0
            if conf_pct <= 1.0:
                conf_pct = conf_pct * 100.0
            conf_pct = max(0.0, min(100.0, conf_pct))
        except Exception:
            conf_pct = 0.0
        
        # Parse addresses JSON string back to dict
        addresses = {}
        if row[17]:  # addresses
            try:
                addresses = json.loads(row[17])
            except (json.JSONDecodeError, TypeError):
                addresses = {}
        
        # Parse signature_regions JSON string back to list
        signature_regions = []
        if row[18]:  # signature_regions
            try:
                signature_regions = json.loads(row[18])
            except (json.JSONDecodeError, TypeError):
                signature_regions = []
        
        invoices.append({
            "id": row[0],
            "invoice_number": row[1],
            "invoice_date": row[2],
            "supplier_name": row[3],
            "total_amount": row[4],
            "status": row[5],
            "confidence": conf_pct,
            "upload_timestamp": row[7],
            "parent_pdf_filename": row[8],
            "page_numbers": page_numbers,
            "line_items": line_items,
            "subtotal": row[11],
            "vat": row[12],
            "vat_rate": row[13],
            "total_incl_vat": row[14],
            "ocr_text": row[15],
            "page_range": row[16],
            "addresses": addresses,
            "signature_regions": signature_regions,
            "verification_status": row[19]
        })
    
    return invoices

def get_all_delivery_notes():
    """Get all delivery notes from the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            id,
            delivery_note_number,
            delivery_date,
            supplier_name,
            total_amount,
            status,
            confidence,
            upload_timestamp,
            parent_pdf_filename,
            ocr_text
        FROM delivery_notes
        ORDER BY upload_timestamp DESC
    """)
    
    rows = cursor.fetchall()
    conn.close()
    
    delivery_notes = []
    for row in rows:
        # Normalize confidence
        raw_conf = row[6]
        try:
            conf_pct = float(raw_conf) if raw_conf is not None else 0.0
            if conf_pct <= 1.0:
                conf_pct = conf_pct * 100.0
            conf_pct = max(0.0, min(100.0, conf_pct))
        except Exception:
            conf_pct = 0.0
        
        delivery_notes.append({
            "id": row[0],
            "delivery_note_number": row[1],
            "delivery_date": row[2],
            "supplier_name": row[3],
            "total_amount": row[4],
            "status": row[5],
            "confidence": conf_pct,
            "upload_timestamp": row[7],
            "parent_pdf_filename": row[8],
            "ocr_text": row[9]
        })
    
    return delivery_notes

# Initialize database on import
init_database() 