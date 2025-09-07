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
import json
import re
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from app.file_processor import get_uploaded_files
from app.db_migrations import log_audit_event, get_current_user_id

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

def normalize_units(unit_descriptor: str) -> int:
    """
    Normalize unit descriptors to a standard unit count.
    
    Examples:
        "24 x 275ml" -> 24
        "12 pack" -> 12
        "1 case" -> 1
        "6 bottles" -> 6
    """
    if not unit_descriptor:
        return 1
    
    # Extract numbers from unit descriptors
    patterns = [
        r'(\d+)\s*[x×]\s*\d+',  # "24 x 275ml"
        r'(\d+)\s*pack',        # "12 pack"
        r'(\d+)\s*case',        # "1 case"
        r'(\d+)\s*bottles?',    # "6 bottles"
        r'(\d+)\s*cans?',       # "4 cans"
        r'(\d+)\s*units?',      # "8 units"
        r'^(\d+)$'              # Just a number
    ]
    
    for pattern in patterns:
        match = re.search(pattern, unit_descriptor.lower())
        if match:
            return int(match.group(1))
    
    return 1

def calculate_confidence_score(extracted_text: str, line_items: List[Dict]) -> float:
    """
    Calculate confidence score based on extraction quality.
    
    Args:
        extracted_text: Raw OCR text
        line_items: Extracted line items
        
    Returns:
        Confidence score (0-100)
    """
    if not extracted_text or not line_items:
        return 0.0
    
    base_score = 50.0
    
    # Text quality indicators
    if len(extracted_text) > 100:
        base_score += 10
    if any(keyword in extracted_text.lower() for keyword in ['invoice', 'total', 'amount', 'vat']):
        base_score += 15
    if re.search(r'\d+\.\d{2}', extracted_text):  # Price patterns
        base_score += 10
    
    # Line item quality
    if len(line_items) > 0:
        base_score += 10
        for item in line_items:
            if item.get('qty', 0) > 0 and item.get('price', 0) > 0:
                base_score += 5
    
    return min(100.0, base_score)

def detect_issues(invoice_data: Dict, line_items: List[Dict]) -> List[Dict]:
    """
    Detect issues in invoice data and line items.
    
    Args:
        invoice_data: Invoice information
        line_items: List of line items
        
    Returns:
        List of detected issues
    """
    issues = []
    
    # Calculate expected totals
    calculated_total = sum(item.get('total_pennies', 0) for item in line_items)
    invoice_total = invoice_data.get('total_amount_pennies', 0)
    
    # Total mismatch check
    if invoice_total > 0 and abs(calculated_total - invoice_total) > invoice_total * 0.01:  # >1% difference
        issues.append({
            'type': 'total_mismatch',
            'severity': 'high',
            'description': f'Calculated total ({calculated_total/100:.2f}) does not match invoice total ({invoice_total/100:.2f})',
            'line_item_id': None
        })
    
    # Line item checks
    for item in line_items:
        # Price mismatch
        expected_total = item.get('qty', 0) * item.get('unit_price_pennies', 0)
        actual_total = item.get('total_pennies', 0)
        
        if actual_total > 0 and abs(expected_total - actual_total) > actual_total * 0.01:
            issues.append({
                'type': 'price_mismatch',
                'severity': 'medium',
                'description': f'Line item total mismatch: expected {expected_total/100:.2f}, got {actual_total/100:.2f}',
                'line_item_id': item.get('id')
            })
        
        # Quantity mismatch
        if item.get('delivery_qty') and item.get('qty'):
            qty_diff = abs(item['qty'] - item['delivery_qty'])
            if qty_diff > 0:
                issues.append({
                    'type': 'qty_mismatch',
                    'severity': 'medium',
                    'description': f'Quantity mismatch: invoice {item["qty"]}, delivery {item["delivery_qty"]}',
                    'line_item_id': item.get('id')
                })
        
        # Unit math check
        unit_descriptor = item.get('unit_descriptor', '')
        normalized_units = normalize_units(unit_descriptor)
        if normalized_units > 1 and item.get('qty', 0) > 0:
            # Check if the math makes sense for pack quantities
            if item['qty'] % normalized_units != 0:
                issues.append({
                    'type': 'unit_math_suspect',
                    'severity': 'low',
                    'description': f'Unit math suspicious: {item["qty"]} items with {normalized_units} units per pack',
                    'line_item_id': item.get('id')
                })
    
    return issues

def create_issue_record(issue_data: Dict, invoice_id: str) -> str:
    """Create an issue record in the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    issue_id = f"ISS-{datetime.now().strftime('%Y%m%d%H%M%S')}-{invoice_id[:8]}"
    
    cursor.execute('''
        INSERT INTO issues 
        (id, invoice_id, line_item_id, issue_type, severity, description, 
         status, created_by, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        issue_id, invoice_id, issue_data.get('line_item_id'),
        issue_data['type'], issue_data['severity'], issue_data['description'],
        'open', get_current_user_id(), datetime.now().isoformat()
    ))
    
    conn.commit()
    conn.close()
    
    # Log audit event
    log_audit_event(
        user_id=get_current_user_id(),
        action='create_issue',
        entity_type='issue',
        entity_id=issue_id,
        new_values=issue_data
    )
    
    return issue_id

def resolve_issue(issue_id: str, resolution_notes: str, user_id: str = None) -> bool:
    """Resolve an issue."""
    if not user_id:
        user_id = get_current_user_id()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE issues 
        SET status = 'resolved', resolved_by = ?, resolved_at = ?, resolution_notes = ?
        WHERE id = ?
    ''', (user_id, datetime.now().isoformat(), resolution_notes, issue_id))
    
    conn.commit()
    conn.close()
    
    # Log audit event
    log_audit_event(
        user_id=user_id,
        action='resolve_issue',
        entity_type='issue',
        entity_id=issue_id,
        new_values={'status': 'resolved', 'resolution_notes': resolution_notes}
    )
    
    return True

def escalate_issue(issue_id: str, escalation_notes: str, user_id: str = None) -> bool:
    """Escalate an issue."""
    if not user_id:
        user_id = get_current_user_id()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE issues 
        SET status = 'escalated', resolved_by = ?, resolved_at = ?, resolution_notes = ?
        WHERE id = ?
    ''', (user_id, datetime.now().isoformat(), escalation_notes, issue_id))
    
    conn.commit()
    conn.close()
    
    # Log audit event
    log_audit_event(
        user_id=user_id,
        action='escalate_issue',
        entity_type='issue',
        entity_id=issue_id,
        new_values={'status': 'escalated', 'resolution_notes': escalation_notes}
    )
    
    return True

def get_issues_for_invoice(invoice_id: str) -> List[Dict]:
    """Get all issues for a specific invoice."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM issues 
        WHERE invoice_id = ? 
        ORDER BY created_at DESC
    ''', (invoice_id,))
    
    issues = []
    for row in cursor.fetchall():
        issues.append({
            'id': row[0],
            'invoice_id': row[1],
            'line_item_id': row[2],
            'issue_type': row[3],
            'severity': row[4],
            'description': row[5],
            'status': row[6],
            'created_by': row[7],
            'created_at': row[8],
            'resolved_by': row[9],
            'resolved_at': row[10],
            'resolution_notes': row[11]
        })
    
    conn.close()
    return issues

def create_pairing_suggestion(invoice_id: str, delivery_note_id: str, similarity_score: float) -> str:
    """Create a pairing suggestion."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    pairing_id = f"PAIR-{datetime.now().strftime('%Y%m%d%H%M%S')}-{invoice_id[:8]}"
    
    cursor.execute('''
        INSERT INTO pairings 
        (id, invoice_id, delivery_note_id, similarity_score, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (pairing_id, invoice_id, delivery_note_id, similarity_score, 'suggested', datetime.now().isoformat()))
    
    conn.commit()
    conn.close()
    
    # Log audit event
    log_audit_event(
        user_id=get_current_user_id(),
        action='create_pairing_suggestion',
        entity_type='pairing',
        entity_id=pairing_id,
        new_values={'invoice_id': invoice_id, 'delivery_note_id': delivery_note_id, 'similarity_score': similarity_score}
    )
    
    return pairing_id

def confirm_pairing(pairing_id: str, user_id: str = None) -> bool:
    """Confirm a pairing suggestion."""
    if not user_id:
        user_id = get_current_user_id()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE pairings 
        SET status = 'confirmed', confirmed_by = ?, confirmed_at = ?
        WHERE id = ?
    ''', (user_id, datetime.now().isoformat(), pairing_id))
    
    conn.commit()
    conn.close()
    
    # Log audit event
    log_audit_event(
        user_id=user_id,
        action='confirm_pairing',
        entity_type='pairing',
        entity_id=pairing_id,
        new_values={'status': 'confirmed'}
    )
    
    return True

def reject_pairing(pairing_id: str, rejection_reason: str, user_id: str = None) -> bool:
    """Reject a pairing suggestion."""
    if not user_id:
        user_id = get_current_user_id()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE pairings 
        SET status = 'rejected', rejected_by = ?, rejected_at = ?, rejection_reason = ?
        WHERE id = ?
    ''', (user_id, datetime.now().isoformat(), rejection_reason, pairing_id))
    
    conn.commit()
    conn.close()
    
    # Log audit event
    log_audit_event(
        user_id=user_id,
        action='reject_pairing',
        entity_type='pairing',
        entity_id=pairing_id,
        new_values={'status': 'rejected', 'rejection_reason': rejection_reason}
    )
    
    return True

def get_pairing_suggestions(invoice_id: str) -> List[Dict]:
    """Get pairing suggestions for an invoice."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT p.*, dn.delivery_number, dn.delivery_date, dn.supplier
        FROM pairings p
        JOIN delivery_notes dn ON p.delivery_note_id = dn.id
        WHERE p.invoice_id = ? AND p.status = 'suggested'
        ORDER BY p.similarity_score DESC
    ''', (invoice_id,))
    
    suggestions = []
    for row in cursor.fetchall():
        suggestions.append({
            'id': row[0],
            'invoice_id': row[1],
            'delivery_note_id': row[2],
            'similarity_score': row[3],
            'status': row[4],
            'created_at': row[5],
            'delivery_number': row[8],
            'delivery_date': row[9],
            'supplier': row[10]
        })
    
    conn.close()
    return suggestions

# Initialize database tables
create_invoices_table()
create_invoice_line_items_table()
create_delivery_notes_table() 