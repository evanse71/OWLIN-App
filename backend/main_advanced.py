from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import uuid
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

# Add backend to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Owlin Advanced API", version="2.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create upload directory
upload_dir = Path("data/uploads")
upload_dir.mkdir(parents=True, exist_ok=True)

# Import advanced OCR processor
try:
    from advanced_ocr_processor import advanced_ocr_processor
    ADVANCED_OCR_AVAILABLE = True
    logger.info("✅ Advanced OCR processor loaded")
except ImportError as e:
    logger.warning(f"Advanced OCR not available: {e}")
    ADVANCED_OCR_AVAILABLE = False

@app.get("/")
async def root():
    return {"message": "Owlin Advanced API is running"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/api/health")
def api_health_check():
    return {"status": "ok"}

# Advanced OCR processing function
async def process_file_with_advanced_ocr(file_path: Path, original_filename: str) -> Dict[str, Any]:
    """Process file with advanced OCR and extract invoice data"""
    try:
        logger.info(f"🔍 Starting advanced OCR processing for: {file_path}")
        
        if not ADVANCED_OCR_AVAILABLE:
            logger.warning("❌ Advanced OCR not available, falling back to basic processing")
            return await process_file_with_basic_ocr(file_path, original_filename)
        
        # Process document with advanced OCR
        results = await advanced_ocr_processor.process_document_advanced(str(file_path))
        
        if not results:
            logger.warning("❌ No results from advanced OCR, falling back to basic processing")
            return await process_file_with_basic_ocr(file_path, original_filename)
        
        logger.info(f"📊 Advanced OCR processing completed: {len(results)} sections found")
        
        # If multiple sections found, combine them intelligently
        if len(results) > 1:
            logger.info(f"📄 Multiple sections detected: {len(results)}")
            return combine_multiple_sections(results, original_filename)
        else:
            # Single section - format the result
            result = results[0]
            return format_single_result(result, original_filename)
            
    except Exception as e:
        logger.error(f"❌ Advanced OCR processing failed: {e}")
        return await process_file_with_basic_ocr(file_path, original_filename)

def combine_multiple_sections(sections: List[Dict[str, Any]], original_filename: str) -> Dict[str, Any]:
    """Combine multiple sections into a single result"""
    try:
        # Find the best section (highest confidence)
        best_section = max(sections, key=lambda x: x.get('confidence', 0))
        
        # Combine line items from all sections
        all_line_items = []
        for section in sections:
            if 'line_items' in section and section['line_items']:
                all_line_items.extend(section['line_items'])
        
        # Create combined result
        combined_result = {
            "confidence": best_section.get('confidence', 0.5),
            "supplier_name": best_section.get('supplier_name', 'Unknown Supplier'),
            "invoice_number": best_section.get('invoice_number', 'Unknown'),
            "total_amount": best_section.get('total_amount', 0.0),
            "invoice_date": best_section.get('invoice_date', datetime.now().strftime("%Y-%m-%d")),
            "line_items": all_line_items,
            "document_type": best_section.get('document_type', 'unknown'),
            "multi_section": True,
            "section_count": len(sections),
            "sections": sections
        }
        
        return format_single_result(combined_result, original_filename)
        
    except Exception as e:
        logger.error(f"❌ Section combination failed: {e}")
        # Return the first section as fallback
        return format_single_result(sections[0], original_filename)

def format_single_result(result: Dict[str, Any], original_filename: str) -> Dict[str, Any]:
    """Format a single OCR result for the API response"""
    try:
        # Calculate word count from line items
        word_count = 0
        if 'line_items' in result and result['line_items']:
            for item in result['line_items']:
                if 'description' in item:
                    word_count += len(item['description'].split())
        
        # Create response structure
        response = {
            "confidence": result.get('confidence', 0.5),
            "supplier_name": result.get('supplier_name', 'Unknown Supplier'),
            "invoice_number": result.get('invoice_number', 'Unknown'),
            "total_amount": result.get('total_amount', 0.0),
            "invoice_date": result.get('invoice_date', datetime.now().strftime("%Y-%m-%d")),
            "line_items": result.get('line_items', []),
            "document_type": result.get('document_type', 'unknown'),
            "word_count": word_count,
            "raw_ocr_text": f"Processed with advanced OCR - {len(result.get('line_items', []))} line items found",
            "file_id": str(uuid.uuid4()),
            "parsed_data": {
                "confidence": result.get('confidence', 0.5),
                "supplier_name": result.get('supplier_name', 'Unknown Supplier'),
                "invoice_number": result.get('invoice_number', 'Unknown'),
                "total_amount": result.get('total_amount', 0.0),
                "invoice_date": result.get('invoice_date', datetime.now().strftime("%Y-%m-%d"))
            }
        }
        
        # Add multi-section info if available
        if 'multi_section' in result:
            response['multi_section'] = result['multi_section']
            response['section_count'] = result['section_count']
        
        return response
        
    except Exception as e:
        logger.error(f"❌ Result formatting failed: {e}")
        return {
            "confidence": 0.3,
            "supplier_name": "Processing Error",
            "invoice_number": "Unknown",
            "total_amount": 0.0,
            "invoice_date": datetime.now().strftime("%Y-%m-%d"),
            "line_items": [],
            "document_type": "unknown",
            "word_count": 0,
            "raw_ocr_text": f"Error formatting result: {str(e)}",
            "file_id": str(uuid.uuid4()),
            "parsed_data": {
                "confidence": 0.3,
                "supplier_name": "Processing Error",
                "invoice_number": "Unknown",
                "total_amount": 0.0,
                "invoice_date": datetime.now().strftime("%Y-%m-%d")
            }
        }

# Basic OCR fallback function (simplified version of the existing one)
async def process_file_with_basic_ocr(file_path: Path, original_filename: str) -> Dict[str, Any]:
    """Basic OCR processing as fallback"""
    try:
        logger.info(f"🔄 Using basic OCR processing for: {file_path}")
        
        file_extension = file_path.suffix.lower()
        
        # Handle text files
        if file_extension in {'.txt', '.md'}:
            logger.info("📝 Processing as text file")
            with open(file_path, 'r', encoding='utf-8') as f:
                text_content = f.read()
            
            return {
                "confidence": 0.85,
                "supplier_name": "Text File",
                "invoice_number": "Unknown",
                "total_amount": 0.0,
                "invoice_date": datetime.now().strftime("%Y-%m-%d"),
                "raw_text": text_content[:1000] + "..." if len(text_content) > 1000 else text_content,
                "word_count": len(text_content.split()),
                "line_items": [],
                "document_type": "unknown",
                "file_id": str(uuid.uuid4()),
                "parsed_data": {
                    "confidence": 0.85,
                    "supplier_name": "Text File",
                    "invoice_number": "Unknown",
                    "total_amount": 0.0,
                    "invoice_date": datetime.now().strftime("%Y-%m-%d")
                }
            }
        
        # Handle image files with basic Tesseract
        elif file_extension in {'.jpg', '.jpeg', '.png', '.tiff', '.tif'}:
            try:
                import pytesseract
                from PIL import Image
                
                image = Image.open(file_path)
                text_content = pytesseract.image_to_string(image)
                
                return {
                    "confidence": 0.75,
                    "supplier_name": "Image Processing",
                    "invoice_number": "Unknown",
                    "total_amount": 0.0,
                    "invoice_date": datetime.now().strftime("%Y-%m-%d"),
                    "raw_text": text_content[:1000] + "..." if len(text_content) > 1000 else text_content,
                    "word_count": len(text_content.split()),
                    "line_items": [],
                    "document_type": "unknown",
                    "file_id": str(uuid.uuid4()),
                    "parsed_data": {
                        "confidence": 0.75,
                        "supplier_name": "Image Processing",
                        "invoice_number": "Unknown",
                        "total_amount": 0.0,
                        "invoice_date": datetime.now().strftime("%Y-%m-%d")
                    }
                }
            except Exception as img_ocr_error:
                logger.error(f"❌ Basic image OCR failed: {img_ocr_error}")
                return {
                    "confidence": 0.3,
                    "supplier_name": "Image processing failed",
                    "invoice_number": "Unknown",
                    "total_amount": 0.0,
                    "invoice_date": datetime.now().strftime("%Y-%m-%d"),
                    "raw_text": f"Image processing error: {str(img_ocr_error)}",
                    "word_count": 0,
                    "line_items": [],
                    "document_type": "unknown",
                    "file_id": str(uuid.uuid4()),
                    "parsed_data": {
                        "confidence": 0.3,
                        "supplier_name": "Image processing failed",
                        "invoice_number": "Unknown",
                        "total_amount": 0.0,
                        "invoice_date": datetime.now().strftime("%Y-%m-%d")
                    }
                }
        
        # Handle PDF files
        elif file_extension == '.pdf':
            try:
                import fitz  # PyMuPDF
                
                doc = fitz.open(file_path)
                text_content = ""
                
                for page_num in range(len(doc)):
                    page = doc.load_page(page_num)
                    text_content += page.get_text()
                
                doc.close()
                
                return {
                    "confidence": 0.8,
                    "supplier_name": "PDF Processing",
                    "invoice_number": "Unknown",
                    "total_amount": 0.0,
                    "invoice_date": datetime.now().strftime("%Y-%m-%d"),
                    "raw_text": text_content[:1000] + "..." if len(text_content) > 1000 else text_content,
                    "word_count": len(text_content.split()),
                    "line_items": [],
                    "document_type": "unknown",
                    "file_id": str(uuid.uuid4()),
                    "parsed_data": {
                        "confidence": 0.8,
                        "supplier_name": "PDF Processing",
                        "invoice_number": "Unknown",
                        "total_amount": 0.0,
                        "invoice_date": datetime.now().strftime("%Y-%m-%d")
                    }
                }
                
            except Exception as pdf_error:
                logger.error(f"❌ Basic PDF processing failed: {pdf_error}")
                return {
                    "confidence": 0.3,
                    "supplier_name": "PDF processing failed",
                    "invoice_number": "Unknown",
                    "total_amount": 0.0,
                    "invoice_date": datetime.now().strftime("%Y-%m-%d"),
                    "raw_text": f"PDF processing error: {str(pdf_error)}",
                    "word_count": 0,
                    "line_items": [],
                    "document_type": "unknown",
                    "file_id": str(uuid.uuid4()),
                    "parsed_data": {
                        "confidence": 0.3,
                        "supplier_name": "PDF processing failed",
                        "invoice_number": "Unknown",
                        "total_amount": 0.0,
                        "invoice_date": datetime.now().strftime("%Y-%m-%d")
                    }
                }
        
        # Unknown file type
        else:
            return {
                "confidence": 0.3,
                "supplier_name": "Unsupported file type",
                "invoice_number": "Unknown",
                "total_amount": 0.0,
                "invoice_date": datetime.now().strftime("%Y-%m-%d"),
                "raw_text": f"Unsupported file type: {file_extension}",
                "word_count": 0,
                "line_items": [],
                "document_type": "unknown",
                "file_id": str(uuid.uuid4()),
                "parsed_data": {
                    "confidence": 0.3,
                    "supplier_name": "Unsupported file type",
                    "invoice_number": "Unknown",
                    "total_amount": 0.0,
                    "invoice_date": datetime.now().strftime("%Y-%m-%d")
                }
            }
    except Exception as e:
        logger.error(f"❌ Basic OCR processing failed: {e}")
        return {
            "confidence": 0.3,
            "supplier_name": "Basic OCR processing failed",
            "invoice_number": "Unknown",
            "total_amount": 0.0,
            "invoice_date": datetime.now().strftime("%Y-%m-%d"),
            "raw_text": f"Basic OCR processing error: {str(e)}",
            "word_count": 0,
            "line_items": [],
            "document_type": "unknown",
            "file_id": str(uuid.uuid4()),
            "parsed_data": {
                "confidence": 0.3,
                "supplier_name": "Basic OCR processing failed",
                "invoice_number": "Unknown",
                "total_amount": 0.0,
                "invoice_date": datetime.now().strftime("%Y-%m-%d")
            }
        }

# File upload endpoint
@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload and process a file with advanced OCR"""
    try:
        logger.info(f"📤 File upload started: {file.filename}")
        
        # Validate file type
        allowed_extensions = {'.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.tif', '.txt', '.md'}
        file_extension = Path(file.filename).suffix.lower()
        
        if file_extension not in allowed_extensions:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_extension}")
        
        # Save uploaded file
        file_id = str(uuid.uuid4())
        file_path = upload_dir / f"{file_id}_{file.filename}"
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        logger.info(f"💾 File saved: {file_path}")
        
        # Process file with advanced OCR
        result = await process_file_with_advanced_ocr(file_path, file.filename)
        
        # Save to database
        try:
            from db_manager import save_invoice_to_db, save_uploaded_file_to_db
            
            # Save uploaded file metadata
            save_uploaded_file_to_db(
                file_id=file_id,
                filename=file.filename,
                file_path=str(file_path),
                file_size=len(content),
                upload_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                processing_status="completed"
            )
            
            # Save invoice data
            save_invoice_to_db(
                invoice_id=file_id,
                supplier_name=result["supplier_name"],
                invoice_number=result["invoice_number"],
                invoice_date=result["invoice_date"],
                total_amount=result["total_amount"],
                confidence=result["confidence"],
                ocr_text=result.get("raw_ocr_text", ""),
                line_items=result.get("line_items", []),
                db_path="data/owlin.db"
            )
            
            logger.info(f"✅ Data saved to database: {file_id}")
            
        except Exception as db_error:
            logger.error(f"❌ Database save failed: {db_error}")
            # Continue without database save
        
        # Clean up uploaded file
        try:
            os.remove(file_path)
            logger.info(f"🗑️ Cleaned up uploaded file: {file_path}")
        except Exception as cleanup_error:
            logger.error(f"❌ File cleanup failed: {cleanup_error}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ File upload processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

# Database endpoints
@app.get("/api/invoices")
async def get_invoices():
    """Get all invoices from database"""
    try:
        from db_manager import get_all_invoices
        invoices = get_all_invoices()
        return {"invoices": invoices}
    except Exception as e:
        logger.error(f"❌ Failed to get invoices: {e}")
        return {"invoices": []}

@app.get("/api/delivery-notes")
async def get_delivery_notes():
    """Get all delivery notes from database"""
    try:
        from db_manager import get_all_delivery_notes
        delivery_notes = get_all_delivery_notes()
        return {"delivery_notes": delivery_notes}
    except Exception as e:
        logger.error(f"❌ Failed to get delivery notes: {e}")
        return {"delivery_notes": []}

@app.get("/api/files")
async def get_files():
    """Get all uploaded files from database"""
    try:
        from db_manager import get_all_uploaded_files
        files = get_all_uploaded_files()
        return {"files": files}
    except Exception as e:
        logger.error(f"❌ Failed to get files: {e}")
        return {"files": []}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 