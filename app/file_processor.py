"""
File Processor for Owlin App
Handles file upload, persistence, OCR processing, and database storage.

Usage:
    from app.file_processor import process_uploaded_files, save_file_to_disk
    file_id = save_file_to_disk(uploaded_file, file_type)
    process_uploaded_files(file_ids, file_type)
"""
import streamlit as st
import os
import uuid
import sqlite3
import logging
import cv2
import numpy as np
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any
from io import BytesIO
import fitz  # PyMuPDF for PDF processing
from app.ocr_factory import get_ocr_recognizer

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

def extract_text_from_file(file_path: str, file_type: str) -> Dict[str, Any]:
    """
    Extract text from file using OCR.
    
    Args:
        file_path: Path to file
        file_type: 'invoice' or 'delivery_note'
        
    Returns:
        Dictionary with extracted text and metadata
    """
    try:
        # Get OCR recognizer
        recognizer = get_ocr_recognizer()
        
        # Extract images based on file type
        file_extension = os.path.splitext(file_path)[1].lower()
        
        if file_extension == '.pdf':
            images = extract_images_from_pdf(file_path)
        elif file_extension in ['.jpg', '.jpeg', '.png']:
            images = process_image_file(file_path)
        else:
            logger.error(f"Unsupported file type: {file_extension}")
            return {}
        
        if not images:
            logger.error("No images extracted from file")
            return {}
        
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
        
        result = {
            'extracted_text': '\n'.join(all_text),
            'confidence': avg_confidence,
            'processed_images': processed_images,
            'file_type': file_type,
            'file_path': file_path,
            'extraction_timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"Text extraction completed: {len(result['extracted_text'])} chars, {avg_confidence:.2f} confidence")
        return result
        
    except Exception as e:
        logger.error(f"Failed to extract text from file: {e}")
        return {}

def get_db_connection():
    """Get database connection."""
    db_path = os.path.join("data", "owlin.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return sqlite3.connect(db_path, check_same_thread=False)

def create_uploaded_files_table():
    """Create uploaded_files table if it doesn't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS uploaded_files (
            id TEXT PRIMARY KEY,
            original_filename TEXT NOT NULL,
            file_type TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_size INTEGER NOT NULL,
            upload_timestamp TEXT NOT NULL,
            processing_status TEXT DEFAULT 'pending',
            extracted_text TEXT,
            confidence REAL,
            processed_images INTEGER,
            processing_timestamp TEXT
        )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("Uploaded files table created/verified")

def save_file_metadata(file_id: str, original_filename: str, file_type: str, 
                      file_path: str, file_size: int) -> bool:
    """
    Save file metadata to database.
    
    Args:
        file_id: Unique file ID
        original_filename: Original filename
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
            (id, original_filename, file_type, file_path, file_size, upload_timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (file_id, original_filename, file_type, file_path, file_size, 
              datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        logger.info(f"File metadata saved: {file_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to save file metadata: {e}")
        return False

def update_file_processing_status(file_id: str, status: str, 
                                extracted_text: Optional[str] = None, 
                                confidence: Optional[float] = None,
                                processed_images: Optional[int] = None) -> bool:
    """
    Update file processing status in database.
    
    Args:
        file_id: File ID
        status: Processing status
        extracted_text: Extracted text (optional)
        confidence: OCR confidence (optional)
        processed_images: Number of processed images (optional)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE uploaded_files 
            SET processing_status = ?, 
                extracted_text = ?, 
                confidence = ?, 
                processed_images = ?,
                processing_timestamp = ?
            WHERE id = ?
        ''', (status, extracted_text, confidence, processed_images, 
              datetime.now().isoformat(), file_id))
        
        conn.commit()
        conn.close()
        logger.info(f"File status updated: {file_id} -> {status}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to update file status: {e}")
        return False

def process_uploaded_files(file_ids: List[str], file_type: str) -> Dict[str, Any]:
    """
    Process uploaded files with OCR.
    
    Args:
        file_ids: List of file IDs to process
        file_type: 'invoice' or 'delivery_note'
        
    Returns:
        Dictionary with processing results
    """
    results = {
        'processed': 0,
        'failed': 0,
        'total_files': len(file_ids),
        'details': []
    }
    
    for file_id in file_ids:
        try:
            # Get file path from database
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT file_path FROM uploaded_files WHERE id = ?', (file_id,))
            result = cursor.fetchone()
            conn.close()
            
            if not result:
                logger.error(f"File not found in database: {file_id}")
                results['failed'] += 1
                continue
            
            file_path = result[0]
            
            # Update status to processing
            update_file_processing_status(file_id, 'processing')
            
            # Extract text using OCR
            extraction_result = extract_text_from_file(file_path, file_type)
            
            if extraction_result:
                # Update with successful results
                update_file_processing_status(
                    file_id, 'completed',
                    extraction_result['extracted_text'],
                    extraction_result['confidence'],
                    extraction_result['processed_images']
                )
                results['processed'] += 1
                results['details'].append({
                    'file_id': file_id,
                    'status': 'completed',
                    'confidence': extraction_result['confidence']
                })
            else:
                # Update with failed status
                update_file_processing_status(file_id, 'failed')
                results['failed'] += 1
                results['details'].append({
                    'file_id': file_id,
                    'status': 'failed'
                })
                
        except Exception as e:
            logger.error(f"Failed to process file {file_id}: {e}")
            update_file_processing_status(file_id, 'failed')
            results['failed'] += 1
            results['details'].append({
                'file_id': file_id,
                'status': 'failed',
                'error': str(e)
            })
    
    logger.info(f"Processing completed: {results['processed']} successful, {results['failed']} failed")
    return results

def get_uploaded_files(file_type: str = None, status: str = None) -> List[Dict]:
    """
    Get uploaded files from database.
    
    Args:
        file_type: Filter by file type (optional)
        status: Filter by processing status (optional)
        
    Returns:
        List of file dictionaries
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = 'SELECT * FROM uploaded_files'
        params = []
        
        if file_type or status:
            query += ' WHERE'
            conditions = []
            
            if file_type:
                conditions.append('file_type = ?')
                params.append(file_type)
            
            if status:
                conditions.append('processing_status = ?')
                params.append(status)
            
            query += ' AND '.join(conditions)
        
        query += ' ORDER BY upload_timestamp DESC'
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        # Convert to list of dictionaries
        files = []
        for row in rows:
            files.append({
                'id': str(row[0]) if row[0] is not None else '',
                'original_filename': str(row[1]) if row[1] is not None else '',
                'file_type': str(row[2]) if row[2] is not None else '',
                'file_path': str(row[3]) if row[3] is not None else '',
                'file_size': int(row[4]) if row[4] is not None else 0,
                'upload_timestamp': str(row[5]) if row[5] is not None else '',
                'processing_status': str(row[6]) if row[6] is not None else '',
                'extracted_text': row[7],
                'confidence': row[8],
                'processed_images': row[9],
                'processing_timestamp': row[10]
            })
        
        return files
        
    except Exception as e:
        logger.error(f"Failed to get uploaded files: {e}")
        return []

def process_invoice(uploaded_pdf) -> Dict[str, Any]:
    """
    Process an uploaded invoice PDF and extract line items.
    
    Args:
        uploaded_pdf: Streamlit uploaded file object
        
    Returns:
        Dictionary with line items and flagged issues
    """
    try:
        # Load and extract text from PDF
        doc = fitz.open(stream=uploaded_pdf.read(), filetype="pdf")
        text = "\n".join(page.get_text() for page in doc)
        doc.close()
        
        # Run OCR if needed (placeholder logic)
        ocr = get_ocr_recognizer()
        
        # This is a placeholder: replace with your real extraction logic
        line_items = [
            {"Item": "Beef", "Invoice Qty": 5, "Delivered Qty": 3, "Unit Price": 4.0, "Total": 20.0, "Match?": "⚠️"},
            {"Item": "Lettuce", "Invoice Qty": 20, "Delivered Qty": 20, "Unit Price": 1.0, "Total": 20.0, "Match?": "✅"},
        ]
        flagged_issues = ["Beef: expected 5, received 3"]
        
        return {
            "line_items": line_items,
            "flagged_issues": flagged_issues,
            "extracted_text": text
        }
        
    except Exception as e:
        logger.error(f"Failed to process invoice: {e}")
        return {
            "line_items": [],
            "flagged_issues": [f"Processing error: {str(e)}"],
            "extracted_text": ""
        }

# Initialize database tables
create_uploaded_files_table() 