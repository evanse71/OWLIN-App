import sqlite3
import os
from datetime import datetime
from typing import Optional

# Ensure data directory exists
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "owlin.db")

def get_db_connection():
    """Get a database connection."""
    return sqlite3.connect(DB_PATH)

def init_database():
    """Initialize the database with required tables."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create invoices table
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
            parent_pdf_filename TEXT
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
    upload_time: Optional[str] = None
):
    """Insert an invoice record into the database."""
    if upload_time is None:
        upload_time = datetime.utcnow().isoformat()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Generate unique ID
    import uuid
    invoice_id = str(uuid.uuid4())
    
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
            upload_timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        invoice_id,
        invoice_number,
        supplier_name,
        invoice_date,
        total_amount,
        confidence,
        ocr_text,
        filename,
        status,
        upload_time
    ))
    
    conn.commit()
    conn.close()
    
    return invoice_id

def get_all_invoices():
    """Get all invoices from the database."""
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
            ocr_text,
            parent_pdf_filename
        FROM invoices
        ORDER BY upload_timestamp DESC
    """)
    
    rows = cursor.fetchall()
    conn.close()
    
    invoices = []
    for row in rows:
        invoices.append({
            "id": row[0],
            "invoice_number": row[1],
            "invoice_date": row[2],
            "supplier_name": row[3],
            "total_amount": row[4],
            "status": row[5],
            "confidence": row[6],
            "upload_timestamp": row[7],
            "ocr_text": row[8],
            "parent_pdf_filename": row[9]
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
            ocr_text,
            parent_pdf_filename
        FROM delivery_notes
        ORDER BY upload_timestamp DESC
    """)
    
    rows = cursor.fetchall()
    conn.close()
    
    delivery_notes = []
    for row in rows:
        delivery_notes.append({
            "id": row[0],
            "delivery_note_number": row[1],
            "delivery_date": row[2],
            "supplier_name": row[3],
            "total_amount": row[4],
            "status": row[5],
            "confidence": row[6],
            "upload_timestamp": row[7],
            "ocr_text": row[8],
            "parent_pdf_filename": row[9]
        })
    
    return delivery_notes

# Initialize database on import
init_database() 