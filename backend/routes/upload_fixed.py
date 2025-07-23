#!/usr/bin/env python3
"""
Database setup script for Owlin invoice management system.
Creates necessary tables for the complete upload → scan → match flow.
"""

import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import random
import numpy as np
import uuid
import os
import traceback
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import shutil
import io
from PIL import Image
import fitz  # PyMuPDF for PDF processing
import re

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = "data/owlin.db"

def create_tables():
    """Create the necessary tables for the complete invoice management system."""
    logger.info("🚀 Starting database table creation...")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Create uploaded_files table (tracks all uploaded files)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS uploaded_files (
                id TEXT PRIMARY KEY,
                original_filename TEXT NOT NULL,
                file_type TEXT NOT NULL,  -- 'invoice', 'delivery_note', 'receipt'
                file_path TEXT NOT NULL,
                file_size INTEGER,
                upload_timestamp TEXT NOT NULL,
                processing_status TEXT DEFAULT 'pending',  -- 'pending', 'processing', 'completed', 'failed'
                extracted_text TEXT,
                confidence REAL,
                processed_images INTEGER,
                extraction_timestamp TEXT,
                error_message TEXT
            )
        """)
        
        # Create invoices table (processed invoice data)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS invoices (
                id TEXT PRIMARY KEY,
                file_id TEXT NOT NULL,
                invoice_number TEXT,
                invoice_date TEXT,
                supplier_name TEXT,
                total_amount REAL,
                currency TEXT DEFAULT 'GBP',
                status TEXT DEFAULT 'pending',  -- 'pending', 'scanned', 'matched', 'unmatched', 'error', 'utility', 'waiting'
                confidence REAL,
                upload_timestamp TEXT NOT NULL,
                processing_timestamp TEXT,
                delivery_note_id TEXT,  -- Foreign key to delivery_notes
                venue TEXT,
                delivery_note_required BOOLEAN DEFAULT TRUE,  -- New column for utility invoices
                ocr_text TEXT,  -- Store the full OCR text for each page
                parent_pdf_filename TEXT,  -- Original PDF filename for multi-page PDFs
                page_number INTEGER DEFAULT 1,  -- Page number within the PDF
                is_utility_invoice BOOLEAN DEFAULT FALSE,  -- Flag for utility/service invoices
                utility_keywords TEXT,  -- Keywords that triggered utility classification
                FOREIGN KEY (file_id) REFERENCES uploaded_files (id),
                FOREIGN KEY (delivery_note_id) REFERENCES delivery_notes (id)
            )
        """)
        
        # Create delivery_notes table (processed delivery note data)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS delivery_notes (
                id TEXT PRIMARY KEY,
                file_id TEXT NOT NULL,
                delivery_note_number TEXT,
                delivery_date TEXT,
                supplier_name TEXT,
                status TEXT DEFAULT 'pending',  -- 'pending', 'scanned', 'matched', 'unmatched', 'error'
                confidence REAL,
                upload_timestamp TEXT NOT NULL,
                processing_timestamp TEXT,
                invoice_id TEXT,  -- Foreign key to invoices
                FOREIGN KEY (file_id) REFERENCES uploaded_files (id),
                FOREIGN KEY (invoice_id) REFERENCES invoices (id)
            )
        """)
        
        # Create invoice_line_items table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS invoice_line_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id TEXT NOT NULL,
                item_description TEXT NOT NULL,
                quantity REAL NOT NULL,
                unit_price REAL NOT NULL,
                total_price REAL NOT NULL,
                source TEXT DEFAULT 'ocr',  -- 'ocr', 'manual', 'corrected'
                confidence REAL,
                flagged BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (invoice_id) REFERENCES invoices (id)
            )
        """)
        
        # Create delivery_line_items table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS delivery_line_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                delivery_note_id TEXT NOT NULL,
                item_description TEXT NOT NULL,
                quantity REAL NOT NULL,
                unit_price REAL NOT NULL,
                total_price REAL NOT NULL,
                source TEXT DEFAULT 'ocr',  -- 'ocr', 'manual', 'corrected'
                confidence REAL,
                flagged BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (delivery_note_id) REFERENCES delivery_notes (id)
            )
        """)
        
        # Create price_forecasting tables (existing - keep for compatibility)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS price_forecasting_invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_number TEXT NOT NULL,
                supplier_name TEXT NOT NULL,
                invoice_date DATE NOT NULL,
                total_amount REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS price_forecasting_line_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id INTEGER NOT NULL,
                item TEXT NOT NULL,
                quantity REAL NOT NULL,
                unit_price REAL NOT NULL,
                price REAL NOT NULL,
                FOREIGN KEY (invoice_id) REFERENCES price_forecasting_invoices (id)
            )
        """)
        
        # Create indexes for better performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_uploaded_files_type_status ON uploaded_files (file_type, processing_status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices (status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_delivery_notes_status ON delivery_notes (status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_invoices_supplier_date ON invoices (supplier_name, invoice_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_delivery_notes_supplier_date ON delivery_notes (supplier_name, delivery_date)")
        
        conn.commit()
        conn.close()
        logger.info("✅ Database tables created successfully")
    except Exception as e:
        logger.error(f"❌ Database table creation failed: {str(e)}")
        logger.error(f"❌ Full traceback: {traceback.format_exc()}")
        raise Exception(f"Failed to create database tables: {str(e)}")

def generate_sample_data():
    """Generate realistic sample data for the complete invoice management system."""
    logger.info("🚀 Starting sample data generation...")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Sample products with realistic price ranges and trends
        products = {
            'Milk': {'base_price': 1.20, 'volatility': 0.15, 'trend': 0.02},
            'Carrots': {'base_price': 0.80, 'volatility': 0.25, 'trend': 0.05},
            'Pork Shoulder': {'base_price': 3.50, 'volatility': 0.30, 'trend': -0.01},
            'Chicken Breast': {'base_price': 2.80, 'volatility': 0.20, 'trend': 0.03},
            'Tomatoes': {'base_price': 1.50, 'volatility': 0.40, 'trend': 0.08},
            'Potatoes': {'base_price': 0.60, 'volatility': 0.10, 'trend': 0.01},
            'Onions': {'base_price': 0.70, 'volatility': 0.20, 'trend': 0.02},
            'Bread': {'base_price': 1.10, 'volatility': 0.08, 'trend': 0.015},
        }
        
        suppliers = ['Fresh Foods Ltd', 'Quality Meats Co', 'Green Grocers Inc', 'Farm Fresh Supply']
        
        # Generate 18 months of data (from 2023-01 to 2024-06)
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2024, 6, 30)
        
        invoice_id = 1
        current_date = start_date
        
        while current_date <= end_date:
            # Generate 2-4 invoices per month
            invoices_per_month = random.randint(2, 4)
            
            for _ in range(invoices_per_month):
                supplier = random.choice(suppliers)
                invoice_date = current_date + timedelta(days=random.randint(0, 28))
                
                # Create uploaded file record
                file_id = f"FILE-{uuid.uuid4().hex[:8]}"
                cursor.execute("""
                    INSERT INTO uploaded_files 
                    (id, original_filename, file_type, file_path, file_size, upload_timestamp, processing_status, confidence)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    file_id,
                    f"INV-{invoice_id:04d}.pdf",
                    'invoice',
                    f"uploads/invoices/INV-{invoice_id:04d}.pdf",
                    1024 * 1024,  # 1MB
                    invoice_date.isoformat(),
                    'completed',
                    0.85 + random.random() * 0.15  # 85-100% confidence
                ))
                
                # Insert invoice
                cursor.execute("""
                    INSERT INTO price_forecasting_invoices (invoice_number, supplier_name, invoice_date, total_amount)
                    VALUES (?, ?, ?, ?)
                """, (f"INV-{invoice_id:04d}", supplier, invoice_date.strftime('%Y-%m-%d'), 0.0))
                
                # Generate line items for this invoice
                total_amount = 0.0
                items_in_invoice = random.sample(list(products.keys()), random.randint(2, 5))
                
                for item in items_in_invoice:
                    product_info = products[item]
                    
                    # Calculate price with trend and seasonal effects
                    months_since_start = (current_date.year - 2023) * 12 + current_date.month - 1
                    trend_factor = 1 + (product_info['trend'] * months_since_start)
                    
                    # Add seasonal variation (higher prices in winter for some items)
                    seasonal_factor = 1.0
                    if current_date.month in [12, 1, 2]:  # Winter months
                        if item in ['Milk', 'Bread']:
                            seasonal_factor = 1.1  # 10% higher in winter
                        elif item in ['Tomatoes', 'Carrots']:
                            seasonal_factor = 1.2  # 20% higher in winter
                    
                    # Add random volatility
                    volatility_factor = 1 + random.uniform(-product_info['volatility'], product_info['volatility'])
                    
                    # Calculate final price
                    unit_price = product_info['base_price'] * trend_factor * seasonal_factor * volatility_factor
                    unit_price = max(0.1, unit_price)  # Ensure positive price
                    
                    quantity = random.uniform(1, 10)
                    price = unit_price * quantity
                    total_amount += price
                    
                    # Insert line item
                    cursor.execute("""
                        INSERT INTO price_forecasting_line_items (invoice_id, item, quantity, unit_price, price)
                        VALUES (?, ?, ?, ?, ?)
                    """, (invoice_id, item, quantity, unit_price, price))
                
                # Update invoice total
                cursor.execute("""
                    UPDATE price_forecasting_invoices SET total_amount = ? WHERE id = ?
                """, (total_amount, invoice_id))
                
                invoice_id += 1
            
            # Move to next month
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1)
        
        conn.commit()
        conn.close()
        logger.info(f"✅ Generated {invoice_id - 1} invoices with realistic price data")
    except Exception as e:
        logger.error(f"❌ Sample data generation failed: {str(e)}")
        logger.error(f"❌ Full traceback: {traceback.format_exc()}")
        raise Exception(f"Failed to generate sample data: {str(e)}")

def verify_data():
    """Verify the generated data looks realistic."""
    logger.info("🚀 Starting data verification...")
    try:
        conn = sqlite3.connect(DB_PATH)
        
        # Check total records
        invoices_count = pd.read_sql("SELECT COUNT(*) as count FROM price_forecasting_invoices", conn).iloc[0]['count']
        line_items_count = pd.read_sql("SELECT COUNT(*) as count FROM price_forecasting_line_items", conn).iloc[0]['count']
        
        logger.info(f"📊 Database contains:")
        logger.info(f"   - {invoices_count} invoices")
        logger.info(f"   - {line_items_count} line items")
        
        # Show sample price trends
        sample_products = ['Milk', 'Carrots', 'Pork Shoulder']
        for product in sample_products:
            query = """
            SELECT 
                strftime('%Y-%m', i.invoice_date) as month,
                AVG(li.unit_price) as avg_price,
                COUNT(*) as transactions
            FROM price_forecasting_line_items li
            JOIN price_forecasting_invoices i ON li.invoice_id = i.id
            WHERE li.item = ?
            GROUP BY strftime('%Y-%m', i.invoice_date)
            ORDER BY month
            """
            df = pd.read_sql(query, conn, params=(product,))
            logger.info(f"\n📈 {product} price trends:")
            logger.info(df.to_string(index=False))
        
        conn.close()
        logger.info("✅ Data verification complete.")
    except Exception as e:
        logger.error(f"❌ Data verification failed: {str(e)}")
        logger.error(f"❌ Full traceback: {traceback.format_exc()}")
        raise Exception(f"Failed to verify data: {str(e)}")

if __name__ == "__main__":
    logger.info("🚀 Setting up Owlin invoice management database...")
    create_tables()
    generate_sample_data()
    verify_data()
    logger.info("\n✅ Database setup complete! Ready for invoice management.")

import os
import shutil
import uuid
import traceback
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import sqlite3
from backend.routes.ocr import parse_with_ocr, classify_document_type, extract_invoice_fields, classify_utility_invoice

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# Define upload directories
UPLOAD_BASE = Path("data/uploads")
INVOICE_DIR = UPLOAD_BASE / "invoices"
DELIVERY_DIR = UPLOAD_BASE / "delivery_notes"
RECEIPT_DIR = UPLOAD_BASE / "receipts"
DOCUMENTS_DIR = UPLOAD_BASE / "documents"  # General documents directory

# Create directories if they don't exist
INVOICE_DIR.mkdir(parents=True, exist_ok=True)
DELIVERY_DIR.mkdir(parents=True, exist_ok=True)
RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)

# Allowed file types
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}

# File size limits (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes

# Utility invoice keywords for detection
UTILITY_KEYWORDS = [
    "electricity", "edf", "octopus", "british gas", "utility", "water", "rates", 
    "gas", "tv license", "energy", "power", "electric", "british gas", "sse", 
    "npower", "eon", "scottish power", "thames water", "severn trent", "united utilities",
    "south west water", "wessex water", "anglia water", "yorkshire water", "northumbrian water",
    "tv licence", "council tax", "rates", "service charge", "maintenance", "insurance",
    "telephone", "internet", "broadband", "mobile", "phone", "telecom", "bt", "sky",
    "virgin media", "talktalk", "vodafone", "o2", "ee", "three", "giffgaff"
]

def is_pdf_file(filename: str) -> bool:
    """Check if file is a PDF"""
    return Path(filename).suffix.lower() == '.pdf'

def convert_pdf_to_images(file_bytes: bytes) -> List[Image.Image]:
    """Convert PDF bytes to list of PIL Images"""
    try:
        # Use PyMuPDF to convert PDF to images
        pdf_document = fitz.open(stream=file_bytes, filetype="pdf")
        images = []
        
        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            # Render page to image with higher resolution
            mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for better quality
            pix = page.get_pixmap(matrix=mat)
            
            # Convert to PIL Image
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            images.append(img)
        
        pdf_document.close()
        logger.info(f"✅ Converted PDF to {len(images)} images")
        return images
        
    except Exception as e:
        logger.error(f"❌ Failed to convert PDF to images: {str(e)}")
        raise Exception(f"PDF conversion failed: {str(e)}")

def detect_utility_invoice(text: str, supplier_name: str) -> tuple[bool, List[str]]:
    """Detect if an invoice is a utility/service invoice"""
    text_lower = text.lower()
    supplier_lower = supplier_name.lower()
    
    found_keywords = []
    
    # Check for utility keywords in text and supplier name
    for keyword in UTILITY_KEYWORDS:
        keyword_lower = keyword.lower()
        if keyword_lower in text_lower or keyword_lower in supplier_lower:
            found_keywords.append(keyword)
    
    # Additional checks for common patterns
    utility_patterns = [
        'british gas',
        'edf energy',
        'octopus energy',
        'sse energy',
        'npower',
        'eon energy',
        'scottish power',
        'thames water',
        'severn trent',
        'united utilities',
        'tv licence',
        'council tax',
        'service charge'
    ]
    
    for pattern in utility_patterns:
        if pattern in text_lower or pattern in supplier_lower:
            if pattern not in found_keywords:
                found_keywords.append(pattern)
    
    is_utility = len(found_keywords) > 0
    
    if is_utility:
        logger.info(f"🔌 Utility invoice detected with keywords: {found_keywords}")
        logger.info(f"🔌 Text sample: {text_lower[:100]}...")
        logger.info(f"🔌 Supplier: {supplier_lower}")
    else:
        logger.info(f"📄 Regular invoice detected")
        logger.info(f"📄 Text sample: {text_lower[:100]}...")
        logger.info(f"📄 Supplier: {supplier_lower}")
    
    return is_utility, found_keywords

async def process_single_page_ocr(image: Image.Image, page_number: int, filename: str) -> Dict[str, Any]:
    """Process OCR for a single page/image"""
    try:
        logger.info(f"🔄 Processing OCR for page {page_number}")
        
        # Convert PIL Image to bytes for OCR processing
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()
        
        # Create a mock UploadFile for OCR processing
        class MockUploadFile:
            def __init__(self, content: bytes, filename: str):
                self.file = io.BytesIO(content)
                self.filename = filename
                self.size = len(content)
            
            async def read(self):
                return self.file.read()
            
            def seek(self, pos):
                self.file.seek(pos)
        
        mock_file = MockUploadFile(img_byte_arr, f"{filename}_page_{page_number}.png")
        
        # Run OCR processing
        ocr_result = await parse_with_ocr(mock_file)
        
        # Extract text for utility detection
        ocr_text = ""
        if ocr_result.get('success', False):
            parsed_data = ocr_result.get('parsed_data', {})
            # Combine all text fields for utility detection
            text_fields = [
                parsed_data.get('supplier_name', ''),
                parsed_data.get('invoice_number', ''),
                parsed_data.get('invoice_date', ''),
                str(parsed_data.get('total_amount', '')),
                ocr_result.get('raw_text', '')
            ]
            ocr_text = ' '.join([str(field) for field in text_fields if field])
        
        # Detect utility invoice
        supplier_name = ocr_result.get('parsed_data', {}).get('supplier_name', 'Unknown Supplier')
        is_utility, utility_keywords = detect_utility_invoice(ocr_text, supplier_name)
        
        # Determine status and delivery note requirement
        if is_utility:
            status = 'utility'
            delivery_note_required = False
        else:
            status = 'waiting'
            delivery_note_required = True
        
        # Prepare result
        result = {
            'page_number': page_number,
            'success': ocr_result.get('success', False),
            'confidence_score': ocr_result.get('confidence_score', 0.0),
            'parsed_data': ocr_result.get('parsed_data', {}),
            'ocr_text': ocr_text,
            'is_utility_invoice': is_utility,
            'utility_keywords': utility_keywords,
            'status': status,
            'delivery_note_required': delivery_note_required,
            'error': ocr_result.get('error', None)
        }
        
        logger.info(f"✅ Page {page_number} processed. Status: {status}, Utility: {is_utility}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Failed to process page {page_number}: {str(e)}")
        return {
            'page_number': page_number,
            'success': False,
            'confidence_score': 0.0,
            'parsed_data': {},
            'ocr_text': '',
            'is_utility_invoice': False,
            'utility_keywords': [],
            'status': 'error',
            'delivery_note_required': True,
            'error': str(e)
        }

async def process_upload(file_bytes: bytes, filename: str) -> List[Dict[str, Any]]:
    """Process uploaded file and return list of invoice data for each page"""
    logger.info(f"🚀 Starting multi-page processing for: {filename}")
    
    try:
        results = []
        
        if is_pdf_file(filename):
            # Convert PDF to images
            logger.info("📄 Processing as multi-page PDF")
            images = convert_pdf_to_images(file_bytes)
            
            # Process each page
            for page_num, image in enumerate(images, 1):
                logger.info(f"🔄 Processing page {page_num}/{len(images)}")
                result = await process_single_page_ocr(image, page_num, filename)
                results.append(result)
                
        else:
            # Process as single image
            logger.info("🖼️ Processing as single image")
            image = Image.open(io.BytesIO(file_bytes))
            result = await process_single_page_ocr(image, 1, filename)
            results.append(result)
        
        logger.info(f"✅ Multi-page processing completed. Found {len(results)} pages/invoices")
        return results
        
    except Exception as e:
        logger.error(f"❌ Multi-page processing failed: {str(e)}")
        logger.error(f"❌ Full traceback: {traceback.format_exc()}")
        raise Exception(f"Multi-page processing failed: {str(e)}")

def get_db_connection():
    """Get database connection."""
    db_path = os.path.join("data", "owlin.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return sqlite3.connect(db_path)

def is_valid_file(filename: str) -> bool:
    """Check if file has allowed extension"""
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS

def validate_file_size(file_size: int) -> bool:
    """Check if file size is within limits"""
    return file_size <= MAX_FILE_SIZE

def validate_file(file: UploadFile) -> None:
    """Validate file type and size"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    if not is_valid_file(file.filename):
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    if file.size is None:
        raise HTTPException(status_code=400, detail="Unable to determine file size")
    
    if not validate_file_size(file.size):
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB"
        )

def save_file_with_timestamp(file: UploadFile, directory: Path) -> str:
    """Save file with timestamp and return filename"""
    logger.info(f"🔄 Starting file save process for: {file.filename}")
    
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_id = str(uuid.uuid4())
        extension = Path(file.filename).suffix
        filename = f"{file_id}_{timestamp}{extension}"
        file_path = directory / filename
        
        logger.info(f"📁 Saving file to: {file_path}")
        logger.info(f"📊 File size: {file.size} bytes")
        logger.info(f"📄 File type: {extension}")
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Verify file was saved correctly
        if file_path.exists():
            actual_size = file_path.stat().st_size
            logger.info(f"✅ File saved successfully. Actual size: {actual_size} bytes")
            if actual_size != file.size:
                logger.warning(f"⚠️ Size mismatch: expected {file.size}, got {actual_size}")
        else:
            raise Exception("File was not created")
        
        return filename
        
    except Exception as e:
        logger.error(f"❌ File save failed for {file.filename}: {str(e)}")
        logger.error(f"❌ Full traceback: {traceback.format_exc()}")
        raise Exception(f"Failed to save file: {str(e)}")

def create_uploaded_file_record(file_id: str, original_filename: str, file_type: str, 
                               file_path: str, file_size: int) -> None:
    """Create a record in the uploaded_files table"""
    logger.info(f"🔄 Creating database record for file: {original_filename}")
    logger.info(f"📋 File ID: {file_id}")
    logger.info(f"📋 File type: {file_type}")
    logger.info(f"📋 File path: {file_path}")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO uploaded_files 
            (id, original_filename, file_type, file_path, file_size, upload_timestamp, processing_status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            file_id,
            original_filename,
            file_type,
            file_path,
            file_size,
            datetime.now().isoformat(),
            'pending'
        ))
        
        conn.commit()
        conn.close()
        logger.info(f"✅ Database record created successfully for file: {original_filename}")
        
    except Exception as e:
        logger.error(f"❌ Database record creation failed for {original_filename}: {str(e)}")
        logger.error(f"❌ Full traceback: {traceback.format_exc()}")
        raise Exception(f"Failed to create database record: {str(e)}")

def update_file_processing_status(file_id: str, status: str, confidence: float = None, 
                                 extracted_text: str = None, error_message: str = None) -> None:
    """Update the processing status of an uploaded file"""
    logger.info(f"🔄 Updating processing status for file ID: {file_id}")
    logger.info(f"📋 New status: {status}")
    if confidence is not None:
        logger.info(f"📋 Confidence: {confidence}")
    if error_message:
        logger.warning(f"⚠️ Error message: {error_message}")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE uploaded_files 
            SET processing_status = ?, confidence = ?, extracted_text = ?, 
                extraction_timestamp = ?, error_message = ?
            WHERE id = ?
        """, (
            status,
            confidence,
            extracted_text,
            datetime.now().isoformat() if status in ['completed', 'failed'] else None,
            error_message,
            file_id
        ))
        
        conn.commit()
        conn.close()
        logger.info(f"✅ Processing status updated successfully for file ID: {file_id}")
        
    except Exception as e:
        logger.error(f"❌ Failed to update processing status for file ID {file_id}: {str(e)}")
        logger.error(f"❌ Full traceback: {traceback.format_exc()}")
        raise Exception(f"Failed to update processing status: {str(e)}")

def create_invoice_record(file_id: str, parsed_data: Dict, confidence: float, 
                         ocr_text: str = "", parent_pdf_filename: str = None, 
                         page_number: int = 1, is_utility_invoice: bool = False, 
                         utility_keywords: List[str] = None) -> str:
    """Create an invoice record in the database with enhanced fields"""
    logger.info(f"🔄 Creating invoice record for file ID: {file_id}")
    logger.info(f"📋 Parsed data keys: {list(parsed_data.keys())}")
    logger.info(f"📋 Confidence: {confidence}")
    logger.info(f"📋 Page number: {page_number}")
    logger.info(f"📋 Is utility: {is_utility_invoice}")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        invoice_id = str(uuid.uuid4())
        
        # Extract values with logging
        invoice_number = parsed_data.get('invoice_number')
        invoice_date = parsed_data.get('invoice_date')
        supplier_name = parsed_data.get('supplier_name')
        total_amount = float(parsed_data.get('total_amount', 0))
        delivery_note_required = not is_utility_invoice  # Utility invoices don't need delivery notes
        
        # Determine status
        if is_utility_invoice:
            status = 'utility'
        else:
            status = 'waiting'
        
        # Convert utility keywords list to string
        utility_keywords_str = ', '.join(utility_keywords) if utility_keywords else None
        
        logger.info(f"📋 Invoice number: {invoice_number}")
        logger.info(f"📋 Invoice date: {invoice_date}")
        logger.info(f"📋 Supplier: {supplier_name}")
        logger.info(f"📋 Total amount: {total_amount}")
        logger.info(f"📋 Delivery note required: {delivery_note_required}")
        logger.info(f"📋 Status: {status}")
        logger.info(f"📋 Utility keywords: {utility_keywords_str}")
        
        cursor.execute("""
            INSERT INTO invoices 
            (id, file_id, invoice_number, invoice_date, supplier_name, total_amount, 
             confidence, upload_timestamp, status, delivery_note_required, ocr_text,
             parent_pdf_filename, page_number, is_utility_invoice, utility_keywords)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            invoice_id,
            file_id,
            invoice_number,
            invoice_date,
            supplier_name,
            total_amount,
            confidence,
            datetime.now().isoformat(),
            status,
            delivery_note_required,
            ocr_text,
            parent_pdf_filename,
            page_number,
            is_utility_invoice,
            utility_keywords_str
        ))
        
        conn.commit()
        conn.close()
        logger.info(f"✅ Invoice record created successfully. Invoice ID: {invoice_id}")
        return invoice_id
        
    except Exception as e:
        logger.error(f"❌ Failed to create invoice record for file ID {file_id}: {str(e)}")
        logger.error(f"❌ Full traceback: {traceback.format_exc()}")
        raise Exception(f"Failed to create invoice record: {str(e)}")

def create_delivery_note_record(file_id: str, parsed_data: Dict, confidence: float) -> str:
    """Create a delivery note record in the database"""
    logger.info(f"🔄 Creating delivery note record for file ID: {file_id}")
    logger.info(f"📋 Parsed data keys: {list(parsed_data.keys())}")
    logger.info(f"📋 Confidence: {confidence}")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        delivery_note_id = str(uuid.uuid4())
        
        # Extract values with logging
        delivery_note_number = parsed_data.get('delivery_note_number')
        delivery_date = parsed_data.get('delivery_date')
        supplier_name = parsed_data.get('supplier_name')
        
        logger.info(f"📋 Delivery note number: {delivery_note_number}")
        logger.info(f"📋 Delivery date: {delivery_date}")
        logger.info(f"📋 Supplier: {supplier_name}")
        
        cursor.execute("""
            INSERT INTO delivery_notes 
            (id, file_id, delivery_note_number, delivery_date, supplier_name, 
             confidence, upload_timestamp, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            delivery_note_id,
            file_id,
            delivery_note_number,
            delivery_date,
            supplier_name,
            confidence,
            datetime.now().isoformat(),
            'scanned'
        ))
        
        conn.commit()
        conn.close()
        logger.info(f"✅ Delivery note record created successfully. Delivery note ID: {delivery_note_id}")
        return delivery_note_id
        
    except Exception as e:
        logger.error(f"❌ Failed to create delivery note record for file ID {file_id}: {str(e)}")
        logger.error(f"❌ Full traceback: {traceback.format_exc()}")
        raise Exception(f"Failed to create delivery note record: {str(e)}")

def attempt_matching(document_type: str, document_id: str, parsed_data: Dict) -> Dict:
    """Attempt to match document with existing documents"""
    logger.info(f"🔄 Attempting matching for {document_type} ID: {document_id}")
    
    try:
        # This is a simplified matching attempt
        # In a real implementation, you would query the database for potential matches
        logger.info(f"📋 Matching logic would run here for {document_type}")
        logger.info(f"📋 Parsed data available for matching: {list(parsed_data.keys())}")
        
        # For now, return a simple unmatched result
        result = {
            'matched': False,
            'confidence': 0.0,
            'reason': 'No matching logic implemented yet'
        }
        
        logger.info(f"✅ Matching completed. Result: {result}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Matching failed for {document_type} ID {document_id}: {str(e)}")
        logger.error(f"❌ Full traceback: {traceback.format_exc()}")
        return {
            'matched': False,
            'confidence': 0.0,
            'reason': f'Matching error: {str(e)}'
        }

@router.post("/upload/invoice")
async def upload_invoice(file: UploadFile = File(...)):
    """Upload invoice file, parse, and try to match with delivery notes"""
    logger.info(f"🚀 Starting invoice upload process for: {file.filename}")
    logger.info(f"📊 File size: {file.size} bytes")
    logger.info(f"📄 File type: {Path(file.filename).suffix}")
    
    try:
        # Step 1: Validate file
        logger.info("🔄 Step 1: Validating file...")
        validate_file(file)
        logger.info("✅ File validation passed")
        
        # Step 2: Generate unique file ID
        logger.info("🔄 Step 2: Generating file ID...")
        file_id = str(uuid.uuid4())
        logger.info(f"✅ Generated file ID: {file_id}")
        
        # Step 3: Save file to disk
        logger.info("🔄 Step 3: Saving file to disk...")
        filename = save_file_with_timestamp(file, INVOICE_DIR)
        file_path = f"uploads/invoices/{filename}"
        logger.info(f"✅ File saved as: {filename}")
        
        # Step 4: Create uploaded file record
        logger.info("🔄 Step 4: Creating database record...")
        create_uploaded_file_record(file_id, file.filename, 'invoice', file_path, file.size)
        logger.info("✅ Database record created")
        
        # Step 5: Update status to processing
        logger.info("🔄 Step 5: Updating status to processing...")
        update_file_processing_status(file_id, 'processing')
        logger.info("✅ Status updated to processing")
        
        # Step 6: Read file bytes for multi-page processing
        logger.info("🔄 Step 6: Reading file bytes...")
        file.file.seek(0)
        file_bytes = await file.read()
        logger.info(f"✅ Read {len(file_bytes)} bytes")
        
        # Step 7: Process multi-page PDF/image
        logger.info("🔄 Step 7: Starting multi-page processing...")
        page_results = await process_upload(file_bytes, file.filename)
        logger.info(f"✅ Multi-page processing completed. Found {len(page_results)} pages")
        
        # Step 8: Create invoice records for each page
        logger.info("🔄 Step 8: Creating invoice records...")
        invoice_ids = []
        match_results = []
        
        for page_result in page_results:
            if page_result['success']:
                # Create invoice record for this page
                invoice_id = create_invoice_record(
                    file_id=file_id,
                    parsed_data=page_result['parsed_data'],
                    confidence=page_result['confidence_score'],
                    ocr_text=page_result['ocr_text'],
                    parent_pdf_filename=file.filename if is_pdf_file(file.filename) else None,
                    page_number=page_result['page_number'],
                    is_utility_invoice=page_result['is_utility_invoice'],
                    utility_keywords=page_result['utility_keywords']
                )
                invoice_ids.append(invoice_id)
                
                # Attempt matching (skip for utility invoices)
                if not page_result['is_utility_invoice']:
                    match_result = attempt_matching('invoice', invoice_id, page_result['parsed_data'])
                    match_results.append(match_result)
                    logger.info(f"✅ Matching completed for page {page_result['page_number']}: {match_result['matched']}")
                else:
                    match_results.append({'matched': False, 'reason': 'Utility invoice - no delivery note required'})
                    logger.info(f"✅ Skipped matching for utility invoice on page {page_result['page_number']}")
            else:
                logger.warning(f"⚠️ Page {page_result['page_number']} failed processing: {page_result.get('error', 'Unknown error')}")
                match_results.append({'matched': False, 'reason': f"Processing failed: {page_result.get('error', 'Unknown error')}"})
        
        # Step 9: Update file status to completed
        logger.info("🔄 Step 9: Updating file status to completed...")
        successful_pages = len([r for r in page_results if r['success']])
        total_pages = len(page_results)
        update_file_processing_status(
            file_id, 'completed', 
            confidence=sum(r['confidence_score'] for r in page_results if r['success']) / max(successful_pages, 1),
            extracted_text=f"Processed {successful_pages}/{total_pages} pages successfully"
        )
        logger.info("✅ File status updated to completed")
        
        # Step 10: Prepare response
        logger.info("🔄 Step 10: Preparing response...")
        
        if len(page_results) > 1:
            # Multiple pages/invoices
            response_data = {
                "success": True,
                "file_id": file_id,
                "filename": filename,
                "original_name": file.filename,
                "uploaded_at": datetime.now().isoformat(),
                "file_size": file.size,
                "status": 'completed',
                "page_count": len(page_results),
                "successful_pages": successful_pages,
                "invoice_ids": invoice_ids,
                "match_results": match_results,
                "multiple_invoices": True,
                "message": f"Successfully processed {successful_pages}/{total_pages} pages from PDF",
                "page_details": [
                    {
                        "page_number": r['page_number'],
                        "success": r['success'],
                        "status": r['status'],
                        "is_utility_invoice": r['is_utility_invoice'],
                        "supplier_name": r['parsed_data'].get('supplier_name', 'Unknown'),
                        "invoice_number": r['parsed_data'].get('invoice_number', 'Unknown'),
                        "total_amount": r['parsed_data'].get('total_amount', 0.0),
                        "confidence_score": r['confidence_score'],
                        "error": r.get('error')
                    } for r in page_results
                ]
            }
        else:
            # Single page/invoice
            page_result = page_results[0]
            response_data = {
                "success": page_result['success'],
                "file_id": file_id,
                "invoice_id": invoice_ids[0] if invoice_ids else None,
                "filename": filename,
                "original_name": file.filename,
                "uploaded_at": datetime.now().isoformat(),
                "file_size": file.size,
                "status": page_result['status'],
                "confidence_score": page_result['confidence_score'],
                "parsed_data": page_result['parsed_data'],
                "match_result": match_results[0] if match_results else None,
                "multiple_invoices": False,
                "is_utility_invoice": page_result['is_utility_invoice'],
                "delivery_note_required": page_result['delivery_note_required'],
                "utility_keywords": page_result['utility_keywords'],
                "error": page_result.get('error')
            }
        
        logger.info("✅ Invoice upload process completed successfully")
        return JSONResponse(response_data)
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        logger.error("❌ HTTP exception occurred during upload")
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error during invoice upload: {str(e)}")
        logger.error(f"❌ Full traceback: {traceback.format_exc()}")
        
        # Try to update file status to failed if we have a file_id
        try:
            if 'file_id' in locals():
                update_file_processing_status(
                    file_id, 'failed', None, None, f"Unexpected error: {str(e)}"
                )
                logger.info("✅ File status updated to failed due to unexpected error")
        except Exception as update_error:
            logger.error(f"❌ Failed to update file status after error: {str(update_error)}")
        
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.post("/upload/delivery")
async def upload_delivery(file: UploadFile = File(...)):
    """Upload delivery note file, parse, and try to match with invoices"""
    logger.info(f"🚀 Starting delivery note upload process for: {file.filename}")
    logger.info(f"📊 File size: {file.size} bytes")
    logger.info(f"📄 File type: {Path(file.filename).suffix}")
    
    try:
        # Step 1: Validate file
        logger.info("🔄 Step 1: Validating file...")
        validate_file(file)
        logger.info("✅ File validation passed")
        
        # Step 2: Generate unique file ID
        logger.info("🔄 Step 2: Generating file ID...")
        file_id = str(uuid.uuid4())
        logger.info(f"✅ Generated file ID: {file_id}")
        
        # Step 3: Save file to disk
        logger.info("🔄 Step 3: Saving file to disk...")
        filename = save_file_with_timestamp(file, DELIVERY_DIR)
        file_path = f"uploads/delivery_notes/{filename}"
        logger.info(f"✅ File saved as: {filename}")
        
        # Step 4: Create uploaded file record
        logger.info("🔄 Step 4: Creating database record...")
        create_uploaded_file_record(file_id, file.filename, 'delivery_note', file_path, file.size)
        logger.info("✅ Database record created")
        
        # Step 5: Update status to processing
        logger.info("🔄 Step 5: Updating status to processing...")
        update_file_processing_status(file_id, 'processing')
        logger.info("✅ Status updated to processing")
        
        # Step 6: Rewind file for parsing
        logger.info("🔄 Step 6: Preparing file for OCR...")
        file.file.seek(0)
        logger.info("✅ File prepared for OCR")
        
        # Step 7: Parse with OCR
        logger.info("🔄 Step 7: Starting OCR processing...")
        parsed = await parse_with_ocr(file)
        parsed_data = parsed.get('parsed_data', {})
        confidence_score = parsed.get('confidence_score', 0.0)
        logger.info(f"✅ OCR completed. Confidence: {confidence_score}")
        logger.info(f"📋 Parsed fields: {list(parsed_data.keys())}")
        
        if parsed.get('success', False):
            # Step 8: Create delivery note record
            logger.info("🔄 Step 8: Creating delivery note record...")
            delivery_note_id = create_delivery_note_record(file_id, parsed_data, confidence_score)
            logger.info(f"✅ Delivery note record created. Delivery note ID: {delivery_note_id}")
            
            # Step 9: Update file status to completed
            logger.info("🔄 Step 9: Updating file status to completed...")
            update_file_processing_status(
                file_id, 'completed', confidence_score, 
                str(parsed_data), None
            )
            logger.info("✅ File status updated to completed")
            
            # Step 10: Attempt matching
            logger.info("🔄 Step 10: Attempting document matching...")
            match_result = attempt_matching('delivery_note', delivery_note_id, parsed_data)
            logger.info(f"✅ Matching completed. Result: {match_result}")
            
            # Step 11: Return success response
            logger.info("🔄 Step 11: Preparing success response...")
            response_data = {
                "success": True,
                "file_id": file_id,
                "delivery_note_id": delivery_note_id,
                "filename": filename,
                "original_name": file.filename,
                "uploaded_at": datetime.now().isoformat(),
                "file_size": file.size,
                "status": 'matched' if match_result['matched'] else 'unmatched',
                "confidence_score": confidence_score,
                "parsed_data": parsed_data,
                "match_result": match_result
            }
            logger.info("✅ Delivery note upload process completed successfully")
            return JSONResponse(response_data)
            
        else:
            # Step 8b: Handle OCR failure
            logger.error("❌ Step 8b: OCR processing failed")
            error_msg = parsed.get('error', 'OCR processing failed')
            logger.error(f"❌ OCR error: {error_msg}")
            
            # Update file status to failed
            logger.info("🔄 Updating file status to failed...")
            update_file_processing_status(
                file_id, 'failed', None, None, error_msg
            )
            logger.info("✅ File status updated to failed")
            
            raise HTTPException(status_code=500, detail=f"OCR processing failed: {error_msg}")
            
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        logger.error("❌ HTTP exception occurred during upload")
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error during delivery note upload: {str(e)}")
        logger.error(f"❌ Full traceback: {traceback.format_exc()}")
        
        # Try to update file status to failed if we have a file_id
        try:
            if 'file_id' in locals():
                update_file_processing_status(
                    file_id, 'failed', None, None, f"Unexpected error: {str(e)}"
                )
                logger.info("✅ File status updated to failed due to unexpected error")
        except Exception as update_error:
            logger.error(f"❌ Failed to update file status after error: {str(update_error)}")
        
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.post("/upload/document")
async def upload_document(file: UploadFile = File(...)):
    """Upload any document file and automatically classify it as invoice or delivery note"""
    logger.info(f"🚀 Starting general document upload process for: {file.filename}")
    logger.info(f"📊 File size: {file.size} bytes")
    logger.info(f"📄 File type: {Path(file.filename).suffix}")
    
    try:
        # Step 1: Validate file
        logger.info("🔄 Step 1: Validating file...")
        validate_file(file)
        logger.info("✅ File validation passed")
        
        # Step 2: Generate unique file ID
        logger.info("🔄 Step 2: Generating file ID...")
        file_id = str(uuid.uuid4())
        logger.info(f"✅ Generated file ID: {file_id}")
        
        # Step 3: Save file to documents directory
        logger.info("🔄 Step 3: Saving file to documents directory...")
        filename = save_file_with_timestamp(file, DOCUMENTS_DIR)
        file_path = f"uploads/documents/{filename}"
        logger.info(f"✅ File saved as: {filename}")
        
        # Step 4: Create uploaded file record
        logger.info("🔄 Step 4: Creating database record...")
        create_uploaded_file_record(file_id, file.filename, 'document', file_path, file.size)
        logger.info("✅ Database record created")
        
        # Step 5: Update status to processing
        logger.info("🔄 Step 5: Updating status to processing...")
        update_file_processing_status(file_id, 'processing')
        logger.info("✅ Status updated to processing")
        
        # Step 6: Rewind file for parsing
        logger.info("🔄 Step 6: Preparing file for OCR...")
        file.file.seek(0)
        logger.info("✅ File prepared for OCR")
        
        # Step 7: Parse with OCR to determine document type
        logger.info("🔄 Step 7: Starting OCR processing for classification...")
        parsed = await parse_with_ocr(file)
        parsed_data = parsed.get('parsed_data', {})
        confidence_score = parsed.get('confidence_score', 0.0)
        document_type = parsed.get('document_type', 'unknown')
        
        logger.info(f"✅ OCR completed. Document type: {document_type}, Confidence: {confidence_score}")
        
        # Step 8: Handle based on document type
        if parsed.get('success', False) and document_type in ['invoice', 'delivery_note']:
            logger.info(f"🔄 Step 8: Processing as {document_type}...")
            
            if document_type == 'invoice':
                # Process as invoice
                invoice_id = create_invoice_record(file_id, parsed_data, confidence_score)
                logger.info(f"✅ Invoice record created with ID: {invoice_id}")
                
                # Attempt matching
                match_result = attempt_matching('invoice', invoice_id, parsed_data)
                logger.info(f"✅ Matching completed: {match_result['matched']}")
                
                response_data = {
                    "success": True,
                    "file_id": file_id,
                    "invoice_id": invoice_id,
                    "filename": filename,
                    "original_name": file.filename,
                    "uploaded_at": datetime.now().isoformat(),
                    "file_size": file.size,
                    "status": 'matched' if match_result['matched'] else 'unmatched',
                    "confidence_score": confidence_score,
                    "parsed_data": parsed_data,
                    "match_result": match_result,
                    "multiple_invoices": False,
                    "is_utility_invoice": parsed.get('is_utility_invoice', False),
                    "delivery_note_required": parsed_data.get('delivery_note_required', True)
                }
                
            else:  # delivery_note
                # Process as delivery note
                delivery_id = create_delivery_note_record(file_id, parsed_data, confidence_score)
                logger.info(f"✅ Delivery note record created with ID: {delivery_id}")
                
                # Attempt matching
                match_result = attempt_matching('delivery_note', delivery_id, parsed_data)
                logger.info(f"✅ Matching completed: {match_result['matched']}")
                
                response_data = {
                    "success": True,
                    "file_id": file_id,
                    "delivery_id": delivery_id,
                    "filename": filename,
                    "original_name": file.filename,
                    "uploaded_at": datetime.now().isoformat(),
                    "file_size": file.size,
                    "status": 'matched' if match_result['matched'] else 'unmatched',
                    "confidence_score": confidence_score,
                    "parsed_data": parsed_data,
                    "match_result": match_result
                }
            
            # Update file status to completed
            logger.info("🔄 Updating file status to completed...")
            update_file_processing_status(file_id, 'completed', confidence_score)
            logger.info("✅ File status updated to completed")
            
            logger.info("✅ Document upload process completed successfully")
            return JSONResponse(response_data)
            
        else:
            # Step 8b: Handle OCR failure or unknown document type
            logger.warning("⚠️ Step 8b: OCR processing failed or unknown document type")
            error_msg = parsed.get('error', 'OCR processing failed or unknown document type')
            logger.warning(f"⚠️ OCR result: {error_msg}")
            
            # Update file status to failed
            logger.info("🔄 Updating file status to failed...")
            update_file_processing_status(
                file_id, 'failed', None, None, error_msg
            )
            logger.info("✅ File status updated to failed")
            
            # Return response indicating the document needs manual review
            response_data = {
                "success": True,
                "file_id": file_id,
                "filename": filename,
                "original_name": file.filename,
                "uploaded_at": datetime.now().isoformat(),
                "file_size": file.size,
                "status": 'needs_review',
                "confidence_score": confidence_score,
                "parsed_data": {
                    "supplier_name": "Document requires manual review",
                    "invoice_number": "Unknown",
                    "invoice_date": "Unknown",
                    "total_amount": 0.0,
                    "currency": "GBP"
                },
                "error": error_msg,
                "document_type": "unknown"
            }
            
            logger.info("✅ Document uploaded but requires manual review")
            return JSONResponse(response_data)
            
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        logger.error("❌ HTTP exception occurred during upload")
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error during document upload: {str(e)}")
        logger.error(f"❌ Full traceback: {traceback.format_exc()}")
        
        # Try to update file status to failed if we have a file_id
        try:
            if 'file_id' in locals():
                update_file_processing_status(
                    file_id, 'failed', None, None, f"Unexpected error: {str(e)}"
                )
                logger.info("✅ File status updated to failed due to unexpected error")
        except Exception as update_error:
            logger.error(f"❌ Failed to update file status after error: {str(update_error)}")
        
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.get("/files/status")
async def get_files_status():
    """Get status of all uploaded files"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            uf.id,
            uf.original_filename,
            uf.file_type,
            uf.processing_status,
            uf.confidence,
            uf.upload_timestamp,
            uf.error_message,
            CASE 
                WHEN uf.file_type = 'invoice' THEN i.status
                WHEN uf.file_type = 'delivery_note' THEN dn.status
                ELSE NULL
            END as document_status
        FROM uploaded_files uf
        LEFT JOIN invoices i ON uf.id = i.file_id
        LEFT JOIN delivery_notes dn ON uf.id = dn.file_id
        ORDER BY uf.upload_timestamp DESC
    """)
    
    rows = cursor.fetchall()
    files = []
    
    for row in rows:
        files.append({
            "id": row[0],
            "original_filename": row[1],
            "file_type": row[2],
            "processing_status": row[3],
            "confidence": row[4],
            "upload_timestamp": row[5],
            "error_message": row[6],
            "document_status": row[7]
        })
    
    conn.close()
    return {"files": files}

@router.get("/documents/invoices")
async def get_invoices():
    """Get all invoices with their status"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            i.id,
            i.invoice_number,
            i.invoice_date,
            i.supplier_name,
            i.total_amount,
            i.status,
            i.confidence,
            i.upload_timestamp,
            i.delivery_note_required,
            i.ocr_text,
            i.parent_pdf_filename,
            i.page_number,
            i.is_utility_invoice,
            i.utility_keywords,
            dn.id as delivery_note_id,
            dn.delivery_note_number,
            dn.delivery_date
        FROM invoices i
        LEFT JOIN delivery_notes dn ON i.delivery_note_id = dn.id
        ORDER BY i.upload_timestamp DESC
    """)
    
    rows = cursor.fetchall()
    invoices = []
    
    for row in rows:
        invoices.append({
            "id": row[0],
            "invoice_number": row[1],
            "invoice_date": row[2],
            "supplier_name": row[3],
            "total_amount": float(row[4]) if row[4] else 0.0,
            "status": row[5],
            "confidence": row[6],
            "upload_timestamp": row[7],
            "delivery_note_required": bool(row[8]) if row[8] is not None else True,
            "ocr_text": row[9],
            "parent_pdf_filename": row[10],
            "page_number": row[11],
            "is_utility_invoice": bool(row[12]) if row[12] is not None else False,
            "utility_keywords": row[13].split(', ') if row[13] else [],
            "delivery_note": {
                "id": row[14],
                "delivery_note_number": row[15],
                "delivery_date": row[16]
            } if row[14] else None
        })
    
    conn.close()
    return {"invoices": invoices}

@router.get("/documents/delivery-notes")
async def get_delivery_notes():
    """Get all delivery notes with their status"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            dn.id,
            dn.delivery_note_number,
            dn.delivery_date,
            dn.supplier_name,
            dn.status,
            dn.confidence,
            dn.upload_timestamp,
            i.id as invoice_id,
            i.invoice_number,
            i.invoice_date
        FROM delivery_notes dn
        LEFT JOIN invoices i ON dn.invoice_id = i.id
        ORDER BY dn.upload_timestamp DESC
    """)
    
    rows = cursor.fetchall()
    delivery_notes = []
    
    for row in rows:
        delivery_notes.append({
            "id": row[0],
            "delivery_note_number": row[1],
            "delivery_date": row[2],
            "supplier_name": row[3],
            "status": row[4],
            "confidence": row[5],
            "upload_timestamp": row[6],
            "invoice": {
                "id": row[7],
                "invoice_number": row[8],
                "invoice_date": row[9]
            } if row[7] else None
        })
    
    conn.close()
    return {"delivery_notes": delivery_notes} 