"""
Database operations for Owlin App
Handles invoice data loading, management, and status tracking.

Usage:
    from app.database import load_invoices_from_db, get_invoice_details
    invoices = load_invoices_from_db()
    details = get_invoice_details(invoice_id)
"""
import streamlit as st
import sqlite3
import pandas as pd
import logging
import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from app.file_processor import get_uploaded_files

logger = logging.getLogger(__name__)

def get_db_connection():
    """Get database connection."""
    db_path = os.path.join("data", "owlin.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return sqlite3.connect(db_path, check_same_thread=False)

def create_invoices_table():
    """Create invoices table if it doesn't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoices (
            id TEXT PRIMARY KEY,
            invoice_number TEXT,
            invoice_date TEXT,
            supplier TEXT,
            total_amount REAL,
            status TEXT DEFAULT 'pending',
            file_id TEXT,
            extracted_text TEXT,
            confidence REAL,
            upload_timestamp TEXT NOT NULL,
            processing_status TEXT DEFAULT 'pending',
            FOREIGN KEY (file_id) REFERENCES uploaded_files (id)
        )
    ''')
    
    conn.commit()
    conn.close()

def create_invoice_line_items_table():
    """Create invoice line items table if it doesn't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoice_line_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id TEXT NOT NULL,
            item TEXT NOT NULL,
            qty REAL NOT NULL,
            price REAL NOT NULL,
            total REAL NOT NULL,
            delivery_qty REAL,
            flagged INTEGER DEFAULT 0,
            source TEXT DEFAULT 'invoice',
            upload_timestamp TEXT NOT NULL,
            FOREIGN KEY (invoice_id) REFERENCES invoices (id)
        )
    ''')
    
    conn.commit()
    conn.close()

def create_delivery_notes_table():
    """Create delivery notes table if it doesn't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS delivery_notes (
            id TEXT PRIMARY KEY,
            delivery_number TEXT,
            delivery_date TEXT,
            supplier TEXT,
            invoice_id TEXT,
            file_id TEXT,
            extracted_text TEXT,
            confidence REAL,
            upload_timestamp TEXT NOT NULL,
            processing_status TEXT DEFAULT 'pending',
            FOREIGN KEY (invoice_id) REFERENCES invoices (id),
            FOREIGN KEY (file_id) REFERENCES uploaded_files (id)
        )
    ''')
    
    conn.commit()
    conn.close()

def load_invoices_from_db() -> List[Dict]:
    """
    Load all invoices from database with status information.
    
    Returns:
        List of invoice dictionaries
    """
    try:
        conn = get_db_connection()
        
        # Query invoices with file information
        query = '''
            SELECT 
                i.id,
                i.invoice_number,
                i.invoice_date,
                i.supplier,
                i.total_amount,
                i.status,
                i.processing_status,
                uf.original_filename,
                uf.confidence,
                uf.upload_timestamp
            FROM invoices i
            LEFT JOIN uploaded_files uf ON i.file_id = uf.id
            ORDER BY uf.upload_timestamp DESC
        '''
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        # Convert to list of dictionaries
        invoices = []
        for _, row in df.iterrows():
            invoice = {
                'id': row['id'],
                'invoice_number': row['invoice_number'] or f"INV-{row['id'][:8]}",
                'date': row['invoice_date'] or 'Unknown',
                'supplier': row['supplier'] or 'Unknown',
                'total': row['total_amount'] or 0.0,
                'status': row['status'],
                'processing_status': row['processing_status'],
                'filename': row['original_filename'],
                'confidence': row['confidence'],
                'upload_timestamp': row['upload_timestamp']
            }
            invoices.append(invoice)
        
        logger.info(f"Loaded {len(invoices)} invoices from database")
        return invoices
        
    except Exception as e:
        logger.error(f"Failed to load invoices from database: {e}")
        return []

def get_invoice_details(invoice_id: str) -> Optional[Dict]:
    """
    Get detailed information for a specific invoice.
    
    Args:
        invoice_id: Invoice ID
        
    Returns:
        Invoice details dictionary or None if not found
    """
    try:
        conn = get_db_connection()
        
        # Get invoice information
        invoice_query = '''
            SELECT 
                i.*,
                uf.original_filename,
                uf.extracted_text,
                uf.confidence
            FROM invoices i
            LEFT JOIN uploaded_files uf ON i.file_id = uf.id
            WHERE i.id = ?
        '''
        
        invoice_df = pd.read_sql_query(invoice_query, conn, params=[invoice_id])
        
        if invoice_df.empty:
            conn.close()
            return None
        
        invoice_row = invoice_df.iloc[0]
        
        # Get line items
        line_items_query = '''
            SELECT * FROM invoice_line_items 
            WHERE invoice_id = ?
            ORDER BY id
        '''
        
        line_items_df = pd.read_sql_query(line_items_query, conn, params=[invoice_id])
        conn.close()
        
        # Build invoice details
        invoice_details = {
            'id': invoice_row['id'],
            'invoice_number': invoice_row['invoice_number'],
            'invoice_date': invoice_row['invoice_date'],
            'supplier': invoice_row['supplier'],
            'total_amount': invoice_row['total_amount'],
            'status': invoice_row['status'],
            'processing_status': invoice_row['processing_status'],
            'filename': invoice_row['original_filename'],
            'extracted_text': invoice_row['extracted_text'],
            'confidence': invoice_row['confidence'],
            'upload_timestamp': invoice_row['upload_timestamp'],
            'line_items': []
        }
        
        # Add line items
        for _, item in line_items_df.iterrows():
            line_item = {
                'id': item['id'],
                'item': item['item'],
                'invoice_qty': item['qty'],
                'delivery_qty': item['delivery_qty'],
                'unit_price': item['price'],
                'total': item['total'],
                'flagged': bool(item['flagged']),
                'source': item['source']
            }
            invoice_details['line_items'].append(line_item)
        
        return invoice_details
        
    except Exception as e:
        logger.error(f"Failed to get invoice details: {e}")
        return None

def get_flagged_issues() -> List[Dict]:
    """
    Get all flagged invoice line items.
    
    Returns:
        List of flagged items
    """
    try:
        conn = get_db_connection()
        
        query = '''
            SELECT 
                ili.*,
                i.invoice_number,
                i.supplier,
                i.invoice_date
            FROM invoice_line_items ili
            JOIN invoices i ON ili.invoice_id = i.id
            WHERE ili.flagged = 1
            ORDER BY ili.upload_timestamp DESC
        '''
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        flagged_items = []
        for _, row in df.iterrows():
            item = {
                'id': row['id'],
                'item': row['item'],
                'qty': row['qty'],
                'price': row['price'],
                'source': row['source'],
                'upload_timestamp': row['upload_timestamp'],
                'invoice_number': row['invoice_number'],
                'supplier': row['supplier'],
                'invoice_date': row['invoice_date']
            }
            flagged_items.append(item)
        
        return flagged_items
        
    except Exception as e:
        logger.error(f"Failed to get flagged issues: {e}")
        return []

def get_processing_status_summary() -> Dict:
    """
    Get summary of file processing status.
    
    Returns:
        Dictionary with processing statistics
    """
    try:
        # Get uploaded files by status
        pending_files = get_uploaded_files(status='pending')
        processing_files = get_uploaded_files(status='processing')
        completed_files = get_uploaded_files(status='completed')
        failed_files = get_uploaded_files(status='failed')
        
        # Get invoices by status
        invoices = load_invoices_from_db()
        matched_invoices = [inv for inv in invoices if inv['status'] == 'matched']
        discrepancy_invoices = [inv for inv in invoices if inv['status'] == 'discrepancy']
        not_paired_invoices = [inv for inv in invoices if inv['status'] == 'not_paired']
        
        summary = {
            'files': {
                'pending': len(pending_files),
                'processing': len(processing_files),
                'completed': len(completed_files),
                'failed': len(failed_files),
                'total': len(pending_files) + len(processing_files) + len(completed_files) + len(failed_files)
            },
            'invoices': {
                'total': len(invoices),
                'matched': len(matched_invoices),
                'discrepancy': len(discrepancy_invoices),
                'not_paired': len(not_paired_invoices)
            },
            'flagged_issues': len(get_flagged_issues())
        }
        
        return summary
        
    except Exception as e:
        logger.error(f"Failed to get processing status summary: {e}")
        return {
            'files': {'pending': 0, 'processing': 0, 'completed': 0, 'failed': 0, 'total': 0},
            'invoices': {'total': 0, 'matched': 0, 'discrepancy': 0, 'not_paired': 0},
            'flagged_issues': 0
        }

def create_invoice_from_file(file_id: str, extracted_text: str, confidence: float) -> str:
    """
    Create a new invoice record from processed file.
    
    Args:
        file_id: ID of the uploaded file
        extracted_text: Text extracted from the file
        confidence: OCR confidence score
        
    Returns:
        Invoice ID
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Generate invoice ID
        invoice_id = f"INV-{datetime.now().strftime('%Y%m%d')}-{file_id[:8]}"
        
        # Insert invoice record
        cursor.execute('''
            INSERT INTO invoices 
            (id, file_id, extracted_text, confidence, upload_timestamp, processing_status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (invoice_id, file_id, extracted_text, confidence, 
              datetime.now().isoformat(), 'completed'))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Created invoice: {invoice_id}")
        return invoice_id
        
    except Exception as e:
        logger.error(f"Failed to create invoice: {e}")
        raise

def update_invoice_status(invoice_id: str, status: str, **kwargs) -> bool:
    """
    Update invoice status and metadata.
    
    Args:
        invoice_id: Invoice ID to update
        status: New status ('pending', 'matched', 'discrepancy', 'not_paired')
        **kwargs: Additional fields to update
        
    Returns:
        True if successful, False otherwise
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Build update query
        update_fields = ['status = ?']
        params = [status]
        
        for key, value in kwargs.items():
            if key in ['invoice_number', 'invoice_date', 'supplier', 'total_amount']:
                update_fields.append(f'{key} = ?')
                params.append(value)
        
        params.append(invoice_id)
        
        query = f'UPDATE invoices SET {", ".join(update_fields)} WHERE id = ?'
        cursor.execute(query, params)
        
        conn.commit()
        conn.close()
        
        logger.info(f"Updated invoice {invoice_id} status to {status}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to update invoice status: {e}")
        return False

# Initialize database tables
create_invoices_table()
create_invoice_line_items_table()
create_delivery_notes_table() 