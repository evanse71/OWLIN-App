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

app = FastAPI(title="Owlin Advanced Simple API", version="2.0.0")

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

# Import simplified advanced OCR processor
try:
    from backend.advanced_ocr_processor_simple import AdvancedOCRProcessorSimple
    advanced_ocr_processor_simple = AdvancedOCRProcessorSimple()
    ADVANCED_OCR_AVAILABLE = True
    logger.info("✅ Simplified Advanced OCR processor loaded")
except ImportError as e:
    logger.warning(f"Advanced OCR not available: {e}")
    ADVANCED_OCR_AVAILABLE = False

@app.get("/")
async def root():
    return {"message": "Owlin Advanced Simple API is running"}

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
        results = await advanced_ocr_processor_simple.process_document_advanced(str(file_path))
        
        if not results:
            logger.warning("❌ No results from advanced OCR, falling back to basic processing")
            return await process_file_with_basic_ocr(file_path, original_filename)
        
        logger.info(f"📊 Advanced OCR processing completed: {len(results)} sections found")
        
        # If multiple sections found, create separate invoices
        if len(results) > 1:
            logger.info(f"📄 Multiple sections detected: {len(results)}")
            # For now, return the first section as the main result
            # TODO: Implement proper multi-invoice handling in the frontend
            main_result = results[0]
            main_result['multi_section'] = True
            main_result['section_count'] = len(results)
            main_result['all_sections'] = results
            return format_single_result(main_result, original_filename)
        else:
            # Single section - format the result
            result = results[0]
            return format_single_result(result, original_filename)
            
    except Exception as e:
        logger.error(f"❌ Advanced OCR processing failed: {e}")
        return await process_file_with_basic_ocr(file_path, original_filename)

def combine_multiple_sections(sections: List[Dict[str, Any]], original_filename: str) -> Dict[str, Any]:
    """Combine multiple sections into a single result with intelligent merging"""
    try:
        if not sections:
            logger.warning("⚠️ No sections to combine")
            return format_single_result({
                "confidence": 0.3,
                "supplier_name": "Unknown Supplier",
                "invoice_number": "Unknown",
                "total_amount": 0.0,
                "invoice_date": datetime.now().strftime("%Y-%m-%d"),
                "line_items": [],
                "document_type": "unknown"
            }, original_filename)
        
        # Analyze section relationships
        relationships = analyze_section_relationships(sections)
        
        # Group related sections
        grouped_sections = group_related_sections(sections, relationships)
        
        # Merge sections intelligently
        merged_sections = []
        for group in grouped_sections:
            merged = merge_related_sections(group)
            merged_sections.append(merged)
        
        # Resolve conflicts between merged sections
        resolved_sections = resolve_section_conflicts(merged_sections)
        
        # Combine final results
        return combine_final_sections(resolved_sections, original_filename)
        
    except Exception as e:
        logger.error(f"❌ Section combination failed: {e}")
        # Return the best section as fallback
        best_section = max(sections, key=lambda x: x.get('confidence', 0)) if sections else {
            "confidence": 0.3,
            "supplier_name": "Unknown Supplier",
            "invoice_number": "Unknown",
            "total_amount": 0.0,
            "invoice_date": datetime.now().strftime("%Y-%m-%d"),
            "line_items": [],
            "document_type": "unknown"
        }
        return format_single_result(best_section, original_filename)

def analyze_section_relationships(sections: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze relationships between sections"""
    try:
        relationships = {
            "related_groups": [],
            "conflicts": [],
            "supplier_matches": [],
            "date_matches": []
        }
        
        # Group sections by supplier
        supplier_groups = {}
        for i, section in enumerate(sections):
            supplier = section.get('supplier_name', 'Unknown')
            if supplier not in supplier_groups:
                supplier_groups[supplier] = []
            supplier_groups[supplier].append(i)
        
        # Find related sections
        for supplier, indices in supplier_groups.items():
            if len(indices) > 1:
                relationships["related_groups"].append({
                    "type": "supplier_match",
                    "supplier": supplier,
                    "section_indices": indices
                })
        
        # Find date matches
        date_groups = {}
        for i, section in enumerate(sections):
            date = section.get('invoice_date', '')
            if date and date != datetime.now().strftime("%Y-%m-%d"):
                if date not in date_groups:
                    date_groups[date] = []
                date_groups[date].append(i)
        
        for date, indices in date_groups.items():
            if len(indices) > 1:
                relationships["date_matches"].append({
                    "date": date,
                    "section_indices": indices
                })
        
        return relationships
        
    except Exception as e:
        logger.error(f"Section relationship analysis failed: {e}")
        return {"related_groups": [], "conflicts": [], "supplier_matches": [], "date_matches": []}

def group_related_sections(sections: List[Dict[str, Any]], relationships: Dict[str, Any]) -> List[List[Dict[str, Any]]]:
    """Group sections that are related"""
    try:
        groups = []
        used_indices = set()
        
        # Group by supplier matches
        for group_info in relationships.get("related_groups", []):
            indices = group_info["section_indices"]
            if not any(idx in used_indices for idx in indices):
                group = [sections[idx] for idx in indices]
                groups.append(group)
                used_indices.update(indices)
        
        # Add remaining sections as individual groups
        for i, section in enumerate(sections):
            if i not in used_indices:
                groups.append([section])
        
        return groups
        
    except Exception as e:
        logger.error(f"Section grouping failed: {e}")
        return [[section] for section in sections]

def merge_related_sections(group: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Merge related sections into a single result"""
    try:
        if not group:
            return {}
        
        if len(group) == 1:
            return group[0]
        
        # Find the best section as base
        best_section = max(group, key=lambda x: x.get('confidence', 0))
        
        # Combine line items from all sections
        all_line_items = []
        for section in group:
            if 'line_items' in section and section['line_items']:
                all_line_items.extend(section['line_items'])
        
        # Remove duplicate line items
        unique_line_items = remove_duplicate_line_items(all_line_items)
        
        # Calculate combined total
        combined_total = sum(item.get('total_price', 0) for item in unique_line_items)
        
        # Create merged result
        merged = {
            "confidence": best_section.get('confidence', 0.5),
            "supplier_name": best_section.get('supplier_name', 'Unknown Supplier'),
            "invoice_number": best_section.get('invoice_number', 'Unknown'),
            "total_amount": combined_total if combined_total > 0 else best_section.get('total_amount', 0.0),
            "invoice_date": best_section.get('invoice_date', datetime.now().strftime("%Y-%m-%d")),
            "line_items": unique_line_items,
            "document_type": best_section.get('document_type', 'unknown'),
            "merged_from_count": len(group),
            "original_sections": group
        }
        
        return merged
        
    except Exception as e:
        logger.error(f"Section merging failed: {e}")
        return group[0] if group else {}

def remove_duplicate_line_items(line_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicate line items based on description and code"""
    try:
        unique_items = []
        seen_items = set()
        
        for item in line_items:
            # Create a key for comparison
            description = item.get('description', '').lower().strip()
            code = item.get('code', '').lower().strip()
            key = f"{description}_{code}"
            
            if key not in seen_items:
                unique_items.append(item)
                seen_items.add(key)
            else:
                # Merge quantities if same item
                for existing_item in unique_items:
                    existing_desc = existing_item.get('description', '').lower().strip()
                    existing_code = existing_item.get('code', '').lower().strip()
                    existing_key = f"{existing_desc}_{existing_code}"
                    
                    if existing_key == key:
                        existing_item['quantity'] = existing_item.get('quantity', 0) + item.get('quantity', 0)
                        existing_item['total_price'] = existing_item.get('total_price', 0) + item.get('total_price', 0)
                        break
        
        return unique_items
        
    except Exception as e:
        logger.error(f"Duplicate removal failed: {e}")
        return line_items

def resolve_section_conflicts(merged_sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Resolve conflicts between merged sections"""
    try:
        resolved = []
        
        for section in merged_sections:
            # Validate the merged section
            if section.get('supplier_name') != 'Unknown Supplier' and section.get('total_amount', 0) > 0:
                resolved.append(section)
            elif section.get('line_items'):
                # Keep sections with line items even if other data is missing
                resolved.append(section)
        
        return resolved
        
    except Exception as e:
        logger.error(f"Conflict resolution failed: {e}")
        return merged_sections

def combine_final_sections(resolved_sections: List[Dict[str, Any]], original_filename: str) -> Dict[str, Any]:
    """Combine final sections into a single result"""
    try:
        if not resolved_sections:
            return format_single_result({
                "confidence": 0.3,
                "supplier_name": "Unknown Supplier",
                "invoice_number": "Unknown",
                "total_amount": 0.0,
                "invoice_date": datetime.now().strftime("%Y-%m-%d"),
                "line_items": [],
                "document_type": "unknown"
            }, original_filename)
        
        if len(resolved_sections) == 1:
            return format_single_result(resolved_sections[0], original_filename)
        
        # Multiple sections - combine intelligently
        best_section = max(resolved_sections, key=lambda x: x.get('confidence', 0))
        
        # Combine all line items
        all_line_items = []
        for section in resolved_sections:
            if 'line_items' in section and section['line_items']:
                all_line_items.extend(section['line_items'])
        
        # Remove duplicates
        unique_line_items = remove_duplicate_line_items(all_line_items)
        
        # Calculate total
        total_amount = sum(item.get('total_price', 0) for item in unique_line_items)
        
        # Create final combined result
        combined_result = {
            "confidence": best_section.get('confidence', 0.5),
            "supplier_name": best_section.get('supplier_name', 'Unknown Supplier'),
            "invoice_number": best_section.get('invoice_number', 'Unknown'),
            "total_amount": total_amount if total_amount > 0 else best_section.get('total_amount', 0.0),
            "invoice_date": best_section.get('invoice_date', datetime.now().strftime("%Y-%m-%d")),
            "line_items": unique_line_items,
            "document_type": best_section.get('document_type', 'unknown'),
            "multi_section": True,
            "section_count": len(resolved_sections),
            "sections": resolved_sections
        }
        
        return format_single_result(combined_result, original_filename)
        
    except Exception as e:
        logger.error(f"Final section combination failed: {e}")
        return format_single_result(resolved_sections[0] if resolved_sections else {
            "confidence": 0.3,
            "supplier_name": "Unknown Supplier",
            "invoice_number": "Unknown",
            "total_amount": 0.0,
            "invoice_date": datetime.now().strftime("%Y-%m-%d"),
            "line_items": [],
            "document_type": "unknown"
        }, original_filename)

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

# Basic OCR fallback function
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
            
            # Use advanced text processing instead of basic response
            try:
                results = await advanced_ocr_processor_simple.process_text_content(text_content, "text_file")
                if results:
                    logger.info("✅ Advanced text processing successful")
                    return format_single_result(results[0], original_filename)
                else:
                    logger.warning("⚠️ Advanced text processing returned no results, using fallback")
            except Exception as e:
                logger.error(f"❌ Advanced text processing failed: {e}")
            
            # Fallback to basic response
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
        
        # Handle image files with advanced OCR
        elif file_extension in {'.jpg', '.jpeg', '.png', '.tiff', '.tif'}:
            try:
                logger.info("🖼️ Processing image with advanced OCR")
                
                # Use advanced image processing
                results = await advanced_ocr_processor_simple.process_image_advanced(file_path)
                if results:
                    logger.info("✅ Advanced image processing successful")
                    return format_single_result(results[0], original_filename)
                else:
                    logger.warning("⚠️ Advanced image processing returned no results, using basic fallback")
            except Exception as e:
                logger.error(f"❌ Advanced image processing failed: {e}")
            
            # Fallback to basic Tesseract
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
            
            # Handle multiple invoices
            if result.get('multi_section') and result.get('all_sections'):
                logger.info(f"📄 Processing {len(result['all_sections'])} separate invoices")
                
                # Create separate database entries for each invoice
                for i, section in enumerate(result['all_sections']):
                    section_id = f"{file_id}_section_{i}"
                    
                    # Extract data from this section
                    section_text = " ".join([t.get('text', '') for t in section.get('texts', [])])
                    
                    # Extract invoice data for this section
                    from backend.advanced_ocr_processor_simple import AdvancedOCRProcessorSimple
                    processor = AdvancedOCRProcessorSimple()
                    
                    supplier_name = processor.extract_supplier_name_advanced(section_text, section.get('texts', []))
                    invoice_date = processor.extract_invoice_date_advanced(section_text)
                    total_amount = processor.extract_total_amount_advanced(section_text)
                    invoice_number = processor.extract_invoice_number_advanced(section_text)
                    line_items = processor.extract_line_items_advanced(section.get('texts', []))
                    
                    # Save this section as a separate invoice
                    save_invoice_to_db(
                        invoice_id=section_id,
                        supplier_name=supplier_name,
                        invoice_number=invoice_number,
                        invoice_date=invoice_date,
                        total_amount=total_amount,
                        confidence=section.get('confidence', 0.8),
                        ocr_text=f"Section {i+1} of multi-invoice file",
                        line_items=line_items,
                        db_path="data/owlin.db"
                    )
                
                # Return the first section as the main result
                result = format_single_result(result['all_sections'][0], file.filename)
                result['multi_section'] = True
                result['section_count'] = len(result['all_sections'])
                
            else:
                # Single invoice - save normally
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