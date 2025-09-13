"""
OCR confidence persistence layer
"""
import sqlite3
from typing import Optional
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

def get_db_connection():
    """Get database connection."""
    db_path = Path("data/owlin.db")
    return sqlite3.connect(str(db_path))

def persist_page_confidence(page_id: str, avg: float, minc: float) -> None:
    """Persist page-level confidence scores."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Update invoice_pages table
        cursor.execute("""
            UPDATE invoice_pages 
            SET ocr_avg_conf_page = ?, ocr_min_conf_line = ?
            WHERE id = ?
        """, (avg, minc, page_id))
        
        # If page doesn't exist, create it
        if cursor.rowcount == 0:
            cursor.execute("""
                INSERT INTO invoice_pages (id, ocr_avg_conf_page, ocr_min_conf_line)
                VALUES (?, ?, ?)
            """, (page_id, avg, minc))
        
        conn.commit()
    finally:
        conn.close()

def persist_invoice_confidence(invoice_id: str, avg: float, minc: float) -> None:
    """Persist invoice-level confidence scores (roll-up from pages)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            UPDATE invoices 
            SET ocr_avg_conf = ?, ocr_min_conf = ?
            WHERE id = ?
        """, (avg, minc, invoice_id))
        
        conn.commit()
    finally:
        conn.close()

def get_invoice_pages(invoice_id: str) -> list:
    """Get all pages for an invoice."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT id, page_no FROM invoice_pages 
            WHERE invoice_id = ? 
            ORDER BY page_no
        """, (invoice_id,))
        
        return [{"id": row[0], "page_no": row[1]} for row in cursor.fetchall()]
    finally:
        conn.close()

def mark_page_blocked(page_id: str, reason: str = "OCR_BLOCKED") -> None:
    """Mark a page as blocked due to low OCR confidence."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Add blocked flag to page
        cursor.execute("""
            UPDATE invoice_pages 
            SET ocr_avg_conf_page = 0, ocr_min_conf_line = 0
            WHERE id = ?
        """, (page_id,))
        
        conn.commit()
    finally:
        conn.close() 