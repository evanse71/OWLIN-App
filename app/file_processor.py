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
from typing import List, Dict, Optional, Tuple
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

def extract_text_from_file(file_path: str, file_type: str) -> Dict[str, any]:
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
            file_size INTEGER,
            upload_timestamp TEXT NOT NULL,
            processing_status TEXT DEFAULT 'pending',
            extracted_text TEXT,
            confidence REAL,
            processed_images INTEGER,
            extraction_timestamp TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

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
                                extracted_text: str = None, 
                                confidence: float = None,
                                processed_images: int = None) -> bool:
    """
    Update file processing status in database.
    
    Args:
        file_id: File ID to update
        status: Processing status ('pending', 'processing', 'completed', 'failed')
        extracted_text: Extracted text from OCR
        confidence: OCR confidence score
        processed_images: Number of processed images
        
    Returns:
        True if successful, False otherwise
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if extracted_text is not None:
            cursor.execute('''
                UPDATE uploaded_files 
                SET processing_status = ?, extracted_text = ?, confidence = ?, 
                    processed_images = ?, extraction_timestamp = ?
                WHERE id = ?
            ''', (status, extracted_text, confidence, processed_images, 
                  datetime.now().isoformat(), file_id))
        else:
            cursor.execute('''
                UPDATE uploaded_files 
                SET processing_status = ?
                WHERE id = ?
            ''', (status, file_id))
        
        conn.commit()
        conn.close()
        logger.info(f"File status updated: {file_id} -> {status}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to update file status: {e}")
        return False

def process_uploaded_files(file_ids: List[str], file_type: str) -> Dict[str, any]:
    """
    Process uploaded files with OCR and save results.
    
    Args:
        file_ids: List of file IDs to process
        file_type: 'invoice' or 'delivery_note'
        
    Returns:
        Dictionary with processing results
    """
    results = {
        'successful': [],
        'failed': [],
        'total_processed': 0
    }
    
    for file_id in file_ids:
        try:
            # Update status to processing
            update_file_processing_status(file_id, 'processing')
            
            # Get file path from database
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT file_path FROM uploaded_files WHERE id = ?', (file_id,))
            result = cursor.fetchone()
            conn.close()
            
            if not result:
                logger.error(f"File not found in database: {file_id}")
                update_file_processing_status(file_id, 'failed')
                results['failed'].append(file_id)
                continue
            
            file_path = result[0]
            
            # Extract text using OCR
            extraction_result = extract_text_from_file(file_path, file_type)
            
            if extraction_result:
                # Update database with results
                update_file_processing_status(
                    file_id, 'completed',
                    extraction_result['extracted_text'],
                    extraction_result['confidence'],
                    extraction_result['processed_images']
                )
                results['successful'].append(file_id)
            else:
                update_file_processing_status(file_id, 'failed')
                results['failed'].append(file_id)
            
            results['total_processed'] += 1
            
        except Exception as e:
            logger.error(f"Failed to process file {file_id}: {e}")
            update_file_processing_status(file_id, 'failed')
            results['failed'].append(file_id)
            results['total_processed'] += 1
    
    logger.info(f"File processing completed: {results['total_processed']} files, "
                f"{len(results['successful'])} successful, {len(results['failed'])} failed")
    return results

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
                'extraction_timestamp': row[10]
            })
        
        return files
        
    except Exception as e:
        logger.error(f"Failed to get uploaded files: {e}")
        return []

# Initialize database tables
create_uploaded_files_table() 