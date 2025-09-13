"""
Enhanced File Processor for Owlin App
Handles file upload, OCR processing, multi-invoice PDF splitting, and database storage.
Implements the complete upload pipeline with issue detection and pairing suggestions.
"""
import streamlit as st
import os
import uuid
import sqlite3
import logging
import cv2
import numpy as np
import re
import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any
from io import BytesIO
import fitz  # PyMuPDF for PDF processing
from app.ocr_factory import get_ocr_recognizer
from app.database import (
    normalize_units, calculate_confidence_score, detect_issues, 
    create_issue_record, create_pairing_suggestion, log_audit_event, get_current_user_id
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# File storage configuration
UPLOAD_DIR = "data/uploads"
INVOICES_DIR = os.path.join(UPLOAD_DIR, "invoices")
DELIVERY_DIR = os.path.join(UPLOAD_DIR, "delivery_notes")

# Ensure upload directories exist
os.makedirs(INVOICES_DIR, exist_ok=True)
os.makedirs(DELIVERY_DIR, exist_ok=True)

def generate_file_id() -> str:
    """Generate a unique file ID."""
    return str(uuid.uuid4())

def save_file_to_disk(uploaded_file, file_type: str) -> str:
    """
    Save uploaded file to disk with unique ID.
    
    Args:
        uploaded_file: Streamlit uploaded file object
        file_type: 'invoice' or 'delivery_note'
        
    Returns:
        File ID (UUID string)
    """
    try:
        # Generate unique file ID
        file_id = generate_file_id()
        
        # Determine save directory
        if file_type == 'invoice':
            save_dir = INVOICES_DIR
        elif file_type == 'delivery_note':
            save_dir = DELIVERY_DIR
        else:
            raise ValueError(f"Invalid file type: {file_type}")
        
        # Create filename with original extension
        file_extension = os.path.splitext(uploaded_file.name)[1]
        filename = f"{file_id}{file_extension}"
        filepath = os.path.join(save_dir, filename)
        
        # Save file
        with open(filepath, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        logger.info(f"File saved: {filepath}")
        return file_id
        
    except Exception as e:
        logger.error(f"Failed to save file: {e}")
        raise

def extract_images_from_pdf(pdf_path: str) -> List[np.ndarray]:
    """
    Extract images from PDF file.
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        List of images as numpy arrays
    """
    images = []
    try:
        doc = fitz.open(pdf_path)
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            pix = page.get_pixmap()
            img_data = pix.tobytes("png")
            
            # Convert to numpy array
            nparr = np.frombuffer(img_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            images.append(img)
        
        doc.close()
        logger.info(f"Extracted {len(images)} images from PDF")
        return images
        
    except Exception as e:
        logger.error(f"Failed to extract images from PDF: {e}")
        return []

def process_image_file(file_path: str) -> List[np.ndarray]:
    """
    Process image file and return as numpy array.
    
    Args:
        file_path: Path to image file
        
    Returns:
        List containing single image as numpy array
    """
    try:
        img = cv2.imread(file_path)
        if img is not None:
            return [img]
        else:
            logger.error(f"Failed to read image: {file_path}")
            return []
    except Exception as e:
        logger.error(f"Failed to process image: {e}")
        return []

def parse_invoice_data(extracted_text: str) -> Dict[str, Any]:
    """
    Parse invoice data from extracted text.
    
    Args:
        extracted_text: Raw OCR text
        
    Returns:
        Dictionary with parsed invoice data
    """
    invoice_data = {
        'invoice_number': None,
        'invoice_date': None,
        'supplier': None,
        'total_amount': None,
        'vat_rate': 0.2,
        'line_items': []
    }
    
    lines = extracted_text.split('\n')
    
    # Extract invoice number
    for line in lines:
        if re.search(r'invoice\s*#?\s*:?\s*([A-Z0-9\-]+)', line, re.IGNORECASE):
            match = re.search(r'invoice\s*#?\s*:?\s*([A-Z0-9\-]+)', line, re.IGNORECASE)
            if match:
                invoice_data['invoice_number'] = match.group(1)
                break
    
    # Extract date
    for line in lines:
        if re.search(r'(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})', line):
            match = re.search(r'(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})', line)
            if match:
                invoice_data['invoice_date'] = match.group(1)
                break
    
    # Extract supplier (usually in first few lines)
    for i, line in enumerate(lines[:5]):
        if len(line.strip()) > 5 and not re.search(r'\d+\.\d{2}', line):
            invoice_data['supplier'] = line.strip()
            break
    
    # Extract total amount
    for line in lines:
        if re.search(r'total\s*:?\s*£?(\d+\.\d{2})', line, re.IGNORECASE):
            match = re.search(r'total\s*:?\s*£?(\d+\.\d{2})', line, re.IGNORECASE)
            if match:
                invoice_data['total_amount'] = float(match.group(1))
                break
    
    # Extract line items
    line_items = []
    for line in lines:
        # Look for patterns like: "Item Name    12    2.50    30.00"
        if re.search(r'(.+?)\s+(\d+)\s+(\d+\.\d{2})\s+(\d+\.\d{2})', line):
            match = re.search(r'(.+?)\s+(\d+)\s+(\d+\.\d{2})\s+(\d+\.\d{2})', line)
            if match:
                item_name = match.group(1).strip()
                qty = float(match.group(2))
                unit_price = float(match.group(3))
                total = float(match.group(4))
                
                line_items.append({
                    'item': item_name,
                    'qty': qty,
                    'unit_price': unit_price,
                    'total': total,
                    'unit_descriptor': None,
                    'normalized_units': 1
                })
    
    invoice_data['line_items'] = line_items
    
    return invoice_data

def split_multi_invoice_pdf(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Split a multi-invoice PDF into separate invoices.
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        List of invoice data dictionaries
    """
    invoices = []
    
    try:
        doc = fitz.open(pdf_path)
        current_invoice = None
        current_pages = []
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = page.get_text()
            
            # Check if this page starts a new invoice
            if re.search(r'invoice\s*#?\s*:?\s*([A-Z0-9\-]+)', text, re.IGNORECASE):
                # Save previous invoice if exists
                if current_invoice and current_pages:
                    current_invoice['pages'] = current_pages
                    invoices.append(current_invoice)
                
                # Start new invoice
                current_invoice = {
                    'invoice_number': None,
                    'pages': [],
                    'start_page': page_num
                }
                current_pages = [page_num]
                
                # Extract invoice number
                match = re.search(r'invoice\s*#?\s*:?\s*([A-Z0-9\-]+)', text, re.IGNORECASE)
                if match:
                    current_invoice['invoice_number'] = match.group(1)
            else:
                # Continue current invoice
                if current_invoice:
                    current_pages.append(page_num)
        
        # Save last invoice
        if current_invoice and current_pages:
            current_invoice['pages'] = current_pages
            invoices.append(current_invoice)
        
        doc.close()
        
        # If no invoices found, treat as single invoice
        if not invoices:
            invoices = [{
                'invoice_number': None,
                'pages': list(range(len(doc))),
                'start_page': 0
            }]
        
        logger.info(f"Split PDF into {len(invoices)} invoices")
        return invoices
        
    except Exception as e:
        logger.error(f"Failed to split multi-invoice PDF: {e}")
        return []

def process_single_invoice(file_id: str, file_path: str, invoice_data: Dict[str, Any], 
                          extracted_text: str, confidence: float) -> str:
    """
    Process a single invoice and save to database.
    
    Args:
        file_id: File ID
        file_path: Path to file
        invoice_data: Parsed invoice data
        extracted_text: Raw OCR text
        confidence: OCR confidence score
        
    Returns:
        Invoice ID
    """
    conn = sqlite3.connect("data/owlin.db", check_same_thread=False)
    cursor = conn.cursor()
    
    try:
        # Generate invoice ID
        invoice_id = f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}-{file_id[:8]}"
        
        # Convert amounts to pennies
        total_amount_pennies = int(invoice_data.get('total_amount', 0) * 100) if invoice_data.get('total_amount') else 0
        vat_rate = invoice_data.get('vat_rate', 0.2)
        net_amount_pennies = int(total_amount_pennies / (1 + vat_rate))
        vat_amount_pennies = total_amount_pennies - net_amount_pennies
        
        # Insert invoice record
        cursor.execute('''
            INSERT INTO invoices 
            (id, invoice_number, invoice_date, supplier, total_amount_pennies, 
             currency, status, file_id, extracted_text, confidence, 
             upload_timestamp, processing_status, vat_rate, net_amount_pennies, 
             vat_amount_pennies, gross_amount_pennies, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            invoice_id, invoice_data.get('invoice_number'), invoice_data.get('invoice_date'),
            invoice_data.get('supplier'), total_amount_pennies, 'GBP', 'pending',
            file_id, extracted_text, confidence, datetime.now().isoformat(),
            'completed', vat_rate, net_amount_pennies, vat_amount_pennies,
            total_amount_pennies, get_current_user_id()
        ))
        
        # Insert line items
        for item in invoice_data.get('line_items', []):
            unit_price_pennies = int(item.get('unit_price', 0) * 100)
            total_pennies = int(item.get('total', 0) * 100)
            normalized_units = normalize_units(item.get('unit_descriptor', ''))
            
            cursor.execute('''
                INSERT INTO invoice_line_items 
                (invoice_id, item, qty, unit_price_pennies, total_pennies, 
                 unit_descriptor, normalized_units, source, upload_timestamp, confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                invoice_id, item.get('item'), item.get('qty'), unit_price_pennies,
                total_pennies, item.get('unit_descriptor'), normalized_units,
                'invoice', datetime.now().isoformat(), confidence
            ))
        
        conn.commit()
        
        # Detect and create issues
        issues = detect_issues(
            {'total_amount_pennies': total_amount_pennies},
            [{'total_pennies': item.get('total', 0) * 100, 'qty': item.get('qty', 0), 
              'unit_price_pennies': item.get('unit_price', 0) * 100, 'id': None} 
             for item in invoice_data.get('line_items', [])]
        )
        
        for issue in issues:
            create_issue_record(issue, invoice_id)
        
        # Log audit event
        log_audit_event(
            user_id=get_current_user_id(),
            action='create_invoice',
            entity_type='invoice',
            entity_id=invoice_id,
            new_values=invoice_data
        )
        
        logger.info(f"Created invoice: {invoice_id}")
        return invoice_id
        
    except Exception as e:
        logger.error(f"Failed to create invoice: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def process_uploaded_file(file_id: str, file_type: str) -> Dict[str, Any]:
    """
    Process uploaded file with OCR and create invoice records.
    
    Args:
        file_id: File ID to process
        file_type: 'invoice' or 'delivery_note'
        
    Returns:
        Dictionary with processing results
    """
    try:
        # Get file path from database
        conn = sqlite3.connect("data/owlin.db", check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute('SELECT file_path FROM uploaded_files WHERE id = ?', (file_id,))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            raise ValueError(f"File not found in database: {file_id}")
        
        file_path = result[0]
        
        # Extract text using OCR
        recognizer = get_ocr_recognizer()
        file_extension = os.path.splitext(file_path)[1].lower()
        
        if file_extension == '.pdf':
            images = extract_images_from_pdf(file_path)
        elif file_extension in ['.jpg', '.jpeg', '.png']:
            images = process_image_file(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")
        
        if not images:
            raise ValueError("No images extracted from file")
        
        # Process each image with OCR
        all_text = []
        total_confidence = 0.0
        processed_images = 0
        
        for img in images:
            text, confidence = recognizer.recognize(img)
            if text.strip():
                all_text.append(text)
                total_confidence += confidence
                processed_images += 1
        
        # Calculate average confidence
        avg_confidence = total_confidence / processed_images if processed_images > 0 else 0.0
        extracted_text = '\n'.join(all_text)
        
        # Update file processing status
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE uploaded_files 
            SET processing_status = ?, extracted_text = ?, confidence = ?, 
                processed_images = ?, extraction_timestamp = ?
            WHERE id = ?
        ''', ('completed', extracted_text, avg_confidence, processed_images, 
              datetime.now().isoformat(), file_id))
        conn.commit()
        conn.close()
        
        # Process invoices
        invoice_ids = []
        
        if file_type == 'invoice':
            # Check if this is a multi-invoice PDF
            if file_extension == '.pdf':
                invoices = split_multi_invoice_pdf(file_path)
                for invoice_info in invoices:
                    # Extract text for this specific invoice
                    invoice_text = extracted_text  # Simplified - in real implementation, extract per page
                    invoice_data = parse_invoice_data(invoice_text)
                    invoice_data['invoice_number'] = invoice_info.get('invoice_number')
                    
                    invoice_id = process_single_invoice(
                        file_id, file_path, invoice_data, invoice_text, avg_confidence
                    )
                    invoice_ids.append(invoice_id)
            else:
                # Single invoice
                invoice_data = parse_invoice_data(extracted_text)
                invoice_id = process_single_invoice(
                    file_id, file_path, invoice_data, extracted_text, avg_confidence
                )
                invoice_ids.append(invoice_id)
        
        return {
            'success': True,
            'file_id': file_id,
            'invoice_ids': invoice_ids,
            'confidence': avg_confidence,
            'processed_images': processed_images,
            'extracted_text': extracted_text
        }
        
    except Exception as e:
        logger.error(f"Failed to process file {file_id}: {e}")
        
        # Update status to failed
        conn = sqlite3.connect("data/owlin.db", check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute('UPDATE uploaded_files SET processing_status = ? WHERE id = ?', 
                      ('failed', file_id))
        conn.commit()
        conn.close()
        
        return {
            'success': False,
            'file_id': file_id,
            'error': str(e)
        }

def retry_ocr_for_invoice(invoice_id: str) -> Dict[str, Any]:
    """
    Retry OCR processing for a specific invoice.
    
    Args:
        invoice_id: Invoice ID to retry
        
    Returns:
        Dictionary with retry results
    """
    try:
        # Get invoice data
        conn = sqlite3.connect("data/owlin.db", check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT i.*, uf.file_path 
            FROM invoices i 
            JOIN uploaded_files uf ON i.file_id = uf.id 
            WHERE i.id = ?
        ''', (invoice_id,))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            raise ValueError(f"Invoice not found: {invoice_id}")
        
        file_path = result[12]  # file_path column
        
        # Re-process with OCR
        recognizer = get_ocr_recognizer()
        file_extension = os.path.splitext(file_path)[1].lower()
        
        if file_extension == '.pdf':
            images = extract_images_from_pdf(file_path)
        elif file_extension in ['.jpg', '.jpeg', '.png']:
            images = process_image_file(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")
        
        if not images:
            raise ValueError("No images extracted from file")
        
        # Process with OCR
        all_text = []
        total_confidence = 0.0
        processed_images = 0
        
        for img in images:
            text, confidence = recognizer.recognize(img)
            if text.strip():
                all_text.append(text)
                total_confidence += confidence
                processed_images += 1
        
        avg_confidence = total_confidence / processed_images if processed_images > 0 else 0.0
        extracted_text = '\n'.join(all_text)
        
        # Update invoice with new data
        invoice_data = parse_invoice_data(extracted_text)
        
        # Update database
        conn = sqlite3.connect("data/owlin.db", check_same_thread=False)
        cursor = conn.cursor()
        
        # Update invoice
        cursor.execute('''
            UPDATE invoices 
            SET extracted_text = ?, confidence = ?, processing_status = ?
            WHERE id = ?
        ''', (extracted_text, avg_confidence, 'completed', invoice_id))
        
        # Update line items
        cursor.execute('DELETE FROM invoice_line_items WHERE invoice_id = ?', (invoice_id,))
        
        for item in invoice_data.get('line_items', []):
            unit_price_pennies = int(item.get('unit_price', 0) * 100)
            total_pennies = int(item.get('total', 0) * 100)
            normalized_units = normalize_units(item.get('unit_descriptor', ''))
            
            cursor.execute('''
                INSERT INTO invoice_line_items 
                (invoice_id, item, qty, unit_price_pennies, total_pennies, 
                 unit_descriptor, normalized_units, source, upload_timestamp, confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                invoice_id, item.get('item'), item.get('qty'), unit_price_pennies,
                total_pennies, item.get('unit_descriptor'), normalized_units,
                'invoice', datetime.now().isoformat(), avg_confidence
            ))
        
        conn.commit()
        conn.close()
        
        # Log audit event
        log_audit_event(
            user_id=get_current_user_id(),
            action='retry_ocr',
            entity_type='invoice',
            entity_id=invoice_id,
            new_values={'confidence': avg_confidence, 'extracted_text': extracted_text}
        )
        
        return {
            'success': True,
            'invoice_id': invoice_id,
            'confidence': avg_confidence,
            'processed_images': processed_images,
            'extracted_text': extracted_text
        }
        
    except Exception as e:
        logger.error(f"Failed to retry OCR for invoice {invoice_id}: {e}")
        return {
            'success': False,
            'invoice_id': invoice_id,
            'error': str(e)
        }

def get_db_connection():
    """Get database connection."""
    db_path = os.path.join("data", "owlin.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return sqlite3.connect(db_path, check_same_thread=False)

def save_file_metadata(file_id: str, original_filename: str, file_type: str, 
                      file_path: str, file_size: int) -> bool:
    """
    Save file metadata to database.
    
    Args:
        file_id: Unique file ID
        original_filename: Original uploaded filename
        file_type: 'invoice' or 'delivery_note'
        file_path: Path to saved file
        file_size: File size in bytes
        
    Returns:
        True if successful, False otherwise
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO uploaded_files 
            (id, original_filename, file_type, file_path, file_size, upload_timestamp, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (file_id, original_filename, file_type, file_path, file_size, 
              datetime.now().isoformat(), get_current_user_id()))
        
        conn.commit()
        conn.close()
        logger.info(f"File metadata saved: {file_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to save file metadata: {e}")
        return False

def get_uploaded_files(file_type: str = None, status: str = None) -> List[Dict]:
    """
    Get uploaded files from database.
    
    Args:
        file_type: Filter by file type ('invoice', 'delivery_note', or None for all)
        status: Filter by processing status ('pending', 'processing', 'completed', 'failed', or None for all)
        
    Returns:
        List of file dictionaries
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = 'SELECT * FROM uploaded_files WHERE 1=1'
        params = []
        
        if file_type:
            query += ' AND file_type = ?'
            params.append(file_type)
        
        if status:
            query += ' AND processing_status = ?'
            params.append(status)
        
        query += ' ORDER BY upload_timestamp DESC'
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        # Convert to list of dictionaries
        files = []
        for row in rows:
            files.append({
                'id': row[0],
                'original_filename': row[1],
                'file_type': row[2],
                'file_path': row[3],
                'file_size': row[4],
                'upload_timestamp': row[5],
                'processing_status': row[6],
                'extracted_text': row[7],
                'confidence': row[8],
                'processed_images': row[9],
                'extraction_timestamp': row[10],
                'user_id': row[11] if len(row) > 11 else None,
                'upload_session_id': row[12] if len(row) > 12 else None
            })
        
        return files
        
    except Exception as e:
        logger.error(f"Failed to get uploaded files: {e}")
        return []
