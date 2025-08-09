import os
import sys
import logging
import re
import json
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import asyncio

# Add backend to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    import fitz  # PyMuPDF
    import pytesseract
    from PIL import Image, ImageEnhance, ImageFilter
    import cv2
    import numpy as np
    from pdf2image import convert_from_path
    import easyocr
    from transformers import LayoutLMv3Processor, LayoutLMv3ForSequenceClassification
    import torch
    from sentence_transformers import SentenceTransformer
    import spacy
    from fuzzywuzzy import fuzz
    from fuzzywuzzy import process
    OCR_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Some OCR dependencies not available: {e}")
    OCR_AVAILABLE = False

class AdvancedOCRProcessor:
    """
    Advanced OCR processor using multiple state-of-the-art open-source tools:
    - EasyOCR for general text extraction
    - LayoutLMv3 for document understanding
    - PyMuPDF for PDF text extraction
    - Tesseract as fallback
    - Custom document segmentation for multi-invoice files
    """
    
    def __init__(self):
        self.easyocr_reader = None
        self.layout_processor = None
        self.layout_model = None
        self.sentence_transformer = None
        self.nlp = None
        self.initialize_models()
    
    def initialize_models(self):
        """Initialize all OCR and NLP models"""
        try:
            # Initialize EasyOCR for general text extraction
            self.easyocr_reader = easyocr.Reader(['en'], gpu=False)
            logger.info("✅ EasyOCR initialized")
        except Exception as e:
            logger.warning(f"EasyOCR not available: {e}")
            self.easyocr_reader = None
        
        try:
            # Initialize LayoutLMv3 for document understanding
            self.layout_processor = LayoutLMv3Processor.from_pretrained("microsoft/layoutlmv3-base")
            self.layout_model = LayoutLMv3ForSequenceClassification.from_pretrained("microsoft/layoutlmv3-base")
            logger.info("✅ LayoutLMv3 initialized")
        except Exception as e:
            logger.warning(f"LayoutLMv3 not available: {e}")
            self.layout_processor = None
            self.layout_model = None
        
        try:
            # Initialize sentence transformer for semantic similarity
            self.sentence_transformer = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("✅ Sentence Transformer initialized")
        except Exception as e:
            logger.warning(f"Sentence Transformer not available: {e}")
            self.sentence_transformer = None
        
        try:
            # Initialize spaCy for NLP
            self.nlp = spacy.load("en_core_web_sm")
            logger.info("✅ spaCy initialized")
        except Exception as e:
            logger.warning(f"spaCy not available: {e}")
            self.nlp = None
    
    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """Advanced image preprocessing for better OCR"""
        try:
            # Convert to grayscale
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image
            
            # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            enhanced = clahe.apply(gray)
            
            # Denoise
            denoised = cv2.fastNlMeansDenoising(enhanced)
            
            # Adaptive thresholding
            binary = cv2.adaptiveThreshold(
                denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )
            
            # Deskew if needed
            coords = np.column_stack(np.where(binary > 0))
            angle = cv2.minAreaRect(coords)[-1]
            if angle < -45:
                angle = -(90 + angle)
            else:
                angle = -angle
            
            if abs(angle) > 0.5:
                (h, w) = binary.shape[:2]
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, angle, 1.0)
                rotated = cv2.warpAffine(binary, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
                return rotated
            
            return binary
            
        except Exception as e:
            logger.error(f"Image preprocessing failed: {e}")
            return image
    
    def extract_text_with_easyocr(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """Extract text using EasyOCR with confidence scores"""
        if not self.easyocr_reader:
            return []
        
        try:
            # Preprocess image
            processed_image = self.preprocess_image(image)
            
            # Run EasyOCR
            results = self.easyocr_reader.readtext(processed_image)
            
            extracted_texts = []
            for (bbox, text, confidence) in results:
                if confidence > 0.3 and len(text.strip()) > 1:  # Filter low confidence and empty text
                    extracted_texts.append({
                        "text": text.strip(),
                        "confidence": confidence,
                        "bbox": bbox,
                        "type": "easyocr"
                    })
            
            return extracted_texts
            
        except Exception as e:
            logger.error(f"EasyOCR extraction failed: {e}")
            return []
    
    def extract_text_with_tesseract(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """Extract text using Tesseract as fallback"""
        try:
            # Convert numpy array to PIL Image
            pil_image = Image.fromarray(image)
            
            # Configure Tesseract for better accuracy
            custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,£$€@#%&*()_+-=[]{}|;:"\'<>?/ '
            
            # Get detailed OCR data
            data = pytesseract.image_to_data(pil_image, config=custom_config, output_type=pytesseract.Output.DICT)
            
            extracted_texts = []
            for i in range(len(data['text'])):
                text = data['text'][i].strip()
                confidence = float(data['conf'][i]) / 100.0
                
                if confidence > 0.3 and len(text) > 1:
                    bbox = (
                        data['left'][i],
                        data['top'][i],
                        data['left'][i] + data['width'][i],
                        data['top'][i] + data['height'][i]
                    )
                    extracted_texts.append({
                        "text": text,
                        "confidence": confidence,
                        "bbox": bbox,
                        "type": "tesseract"
                    })
            
            return extracted_texts
            
        except Exception as e:
            logger.error(f"Tesseract extraction failed: {e}")
            return []
    
    def segment_document(self, all_texts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Segment document into potential invoice sections"""
        try:
            # Group texts by vertical position (y-coordinate)
            sorted_texts = sorted(all_texts, key=lambda x: x['bbox'][1] if x['bbox'] else 0)
            
            # Find potential invoice boundaries
            invoice_sections = []
            current_section = []
            
            for text_item in sorted_texts:
                text = text_item['text'].lower()
                
                # Check for invoice indicators
                invoice_indicators = [
                    'invoice', 'inv#', 'invoice no', 'invoice number',
                    'delivery note', 'advice note', 'receipt',
                    'total', 'amount due', 'balance due'
                ]
                
                is_invoice_start = any(indicator in text for indicator in invoice_indicators)
                
                if is_invoice_start and current_section:
                    # Start new section
                    if current_section:
                        invoice_sections.append({
                            "texts": current_section,
                            "confidence": np.mean([t['confidence'] for t in current_section]),
                            "type": self.classify_section_type(current_section)
                        })
                    current_section = [text_item]
                else:
                    current_section.append(text_item)
            
            # Add final section
            if current_section:
                invoice_sections.append({
                    "texts": current_section,
                    "confidence": np.mean([t['confidence'] for t in current_section]),
                    "type": self.classify_section_type(current_section)
                })
            
            return invoice_sections
            
        except Exception as e:
            logger.error(f"Document segmentation failed: {e}")
            return [{"texts": all_texts, "confidence": 0.5, "type": "unknown"}]
    
    def classify_section_type(self, texts: List[Dict[str, Any]]) -> str:
        """Classify document section type"""
        try:
            combined_text = " ".join([t['text'].lower() for t in texts])
            
            # Define keywords for different document types
            invoice_keywords = ['invoice', 'inv#', 'invoice no', 'total', 'amount due', 'balance due']
            delivery_keywords = ['delivery note', 'advice note', 'goods received', 'delivery address']
            receipt_keywords = ['receipt', 'sale', 'purchase', 'payment received']
            utility_keywords = ['utility', 'electricity', 'gas', 'water', 'telephone', 'internet']
            
            scores = {
                'invoice': sum(1 for keyword in invoice_keywords if keyword in combined_text),
                'delivery_note': sum(1 for keyword in delivery_keywords if keyword in combined_text),
                'receipt': sum(1 for keyword in receipt_keywords if keyword in combined_text),
                'utility': sum(1 for keyword in utility_keywords if keyword in combined_text)
            }
            
            if scores['invoice'] > 0:
                return 'invoice'
            elif scores['delivery_note'] > 0:
                return 'delivery_note'
            elif scores['receipt'] > 0:
                return 'receipt'
            elif scores['utility'] > 0:
                return 'utility'
            else:
                return 'unknown'
                
        except Exception as e:
            logger.error(f"Section classification failed: {e}")
            return 'unknown'
    
    def extract_invoice_data_advanced(self, texts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Advanced invoice data extraction using NLP and semantic similarity"""
        try:
            combined_text = " ".join([t['text'] for t in texts])
            
            # Initialize results
            extracted_data = {
                "supplier_name": "Unknown Supplier",
                "invoice_number": "Unknown",
                "total_amount": 0.0,
                "invoice_date": datetime.now().strftime("%Y-%m-%d"),
                "line_items": [],
                "confidence": np.mean([t['confidence'] for t in texts]),
                "document_type": "unknown"
            }
            
            # Extract supplier name using multiple strategies
            supplier_name = self.extract_supplier_name_advanced(combined_text, texts)
            if supplier_name:
                extracted_data["supplier_name"] = supplier_name
            
            # Extract invoice number
            invoice_number = self.extract_invoice_number_advanced(combined_text)
            if invoice_number:
                extracted_data["invoice_number"] = invoice_number
            
            # Extract total amount
            total_amount = self.extract_total_amount_advanced(combined_text)
            if total_amount > 0:
                extracted_data["total_amount"] = total_amount
            
            # Extract invoice date
            invoice_date = self.extract_invoice_date_advanced(combined_text)
            if invoice_date:
                extracted_data["invoice_date"] = invoice_date
            
            # Extract line items
            line_items = self.extract_line_items_advanced(texts)
            if line_items:
                extracted_data["line_items"] = line_items
            
            # Classify document type
            document_type = self.classify_section_type(texts)
            extracted_data["document_type"] = document_type
            
            return extracted_data
            
        except Exception as e:
            logger.error(f"Advanced data extraction failed: {e}")
            return {
                "supplier_name": "Unknown Supplier",
                "invoice_number": "Unknown",
                "total_amount": 0.0,
                "invoice_date": datetime.now().strftime("%Y-%m-%d"),
                "line_items": [],
                "confidence": 0.3,
                "document_type": "unknown"
            }
    
    def extract_supplier_name_advanced(self, text: str, texts: List[Dict[str, Any]]) -> str:
        """Advanced supplier name extraction using NLP and layout analysis"""
        try:
            # Strategy 1: Look for company patterns in header area
            lines = text.split('\n')
            header_lines = lines[:10]  # Check first 10 lines
            
            for line in header_lines:
                line_upper = line.upper()
                # Skip common invoice labels
                if any(skip in line_upper for skip in ['INVOICE', 'BILL TO:', 'DELIVER TO:', 'DATE:', 'TOTAL:', 'QTY', 'CODE', 'ITEM']):
                    continue
                
                # Look for company patterns
                if any(pattern in line_upper for pattern in ['LIMITED', 'LTD', 'CO', 'COMPANY', 'BREWING', 'BREWERY', 'DISPENSE', 'HYGIENE']):
                    if len(line.strip()) > 5:
                        return line.strip()
            
            # Strategy 2: Use spaCy for named entity recognition
            if self.nlp:
                doc = self.nlp(text)
                for ent in doc.ents:
                    if ent.label_ in ['ORG', 'PERSON'] and len(ent.text) > 5:
                        return ent.text.strip()
            
            # Strategy 3: Look for patterns in text layout
            for text_item in texts:
                text_line = text_item['text']
                if len(text_line) > 10 and not any(skip in text_line.upper() for skip in ['INVOICE', 'BILL TO:', 'DELIVER TO:', 'DATE:', 'TOTAL:']):
                    # Check if it looks like a company name
                    if any(pattern in text_line.upper() for pattern in ['LIMITED', 'LTD', 'CO', 'COMPANY']):
                        return text_line.strip()
            
            return "Unknown Supplier"
            
        except Exception as e:
            logger.error(f"Advanced supplier extraction failed: {e}")
            return "Unknown Supplier"
    
    def extract_invoice_number_advanced(self, text: str) -> str:
        """Advanced invoice number extraction"""
        try:
            # Multiple patterns for invoice numbers
            patterns = [
                r'invoice\s*#?\s*:?\s*([^\n\s]+)',
                r'invoice\s*no\.?\s*:?\s*([^\n\s]+)',
                r'inv\.?\s*#?\s*:?\s*([^\n\s]+)',
                r'#\s*(\d{4,})',
                r'invoice\s*(\d{4,})',
                r'(\d{5,})',  # Look for 5+ digit numbers
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    if match and len(match) >= 4:
                        return match.strip()
            
            return "Unknown"
            
        except Exception as e:
            logger.error(f"Advanced invoice number extraction failed: {e}")
            return "Unknown"
    
    def extract_total_amount_advanced(self, text: str) -> float:
        """Advanced total amount extraction"""
        try:
            # Look for total patterns with VAT included
            total_patterns = [
                r'total\s*(?:inc\.?\s*vat|including\s*vat)\s*:?\s*[£$€]?([\d,]+\.?\d*)',
                r'total\s*due\s*:?\s*[£$€]?([\d,]+\.?\d*)',
                r'amount\s*due\s*:?\s*[£$€]?([\d,]+\.?\d*)',
                r'balance\s*due\s*:?\s*[£$€]?([\d,]+\.?\d*)',
                r'total\s*:?\s*[£$€]?([\d,]+\.?\d*)',
            ]
            
            for pattern in total_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    try:
                        amount = float(match.replace(',', ''))
                        if amount > 10:  # Reasonable minimum
                            return amount
                    except:
                        continue
            
            # Fallback: find largest amount that looks like a total
            amount_pattern = r'[£$€]?\s*([\d,]+\.?\d*)'
            amounts = re.findall(amount_pattern, text)
            
            valid_amounts = []
            for amount_str in amounts:
                try:
                    amount = float(amount_str.replace(',', ''))
                    if amount > 50 and amount < 100000:  # Reasonable range
                        valid_amounts.append(amount)
                except:
                    continue
            
            if valid_amounts:
                return max(valid_amounts)
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Advanced total amount extraction failed: {e}")
            return 0.0
    
    def extract_invoice_date_advanced(self, text: str) -> str:
        """Advanced invoice date extraction"""
        try:
            # Multiple date patterns
            date_patterns = [
                r'(?:invoice\s+date|date|issue\s+date)\s*:?\s*([^\n]+)',
                r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4})',
                r'((?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s*\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})',
            ]
            
            for pattern in date_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    try:
                        date_str = match.strip()
                        if ',' in date_str and any(day in date_str for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']):
                            # Handle "Friday, 4 July 2025" format
                            parsed_date = datetime.strptime(date_str, "%A, %d %B %Y")
                            return parsed_date.strftime("%Y-%m-%d")
                        elif '/' in date_str:
                            # Handle DD/MM/YYYY format
                            parts = date_str.split('/')
                            if len(parts) == 3:
                                if len(parts[2]) == 2:
                                    date_str = f"{parts[0]}/{parts[1]}/20{parts[2]}"
                                parsed_date = datetime.strptime(date_str, "%d/%m/%Y")
                                return parsed_date.strftime("%Y-%m-%d")
                        elif '-' in date_str:
                            # Handle DD-MM-YYYY format
                            parts = date_str.split('-')
                            if len(parts) == 3:
                                if len(parts[2]) == 2:
                                    date_str = f"{parts[0]}-{parts[1]}-20{parts[2]}"
                                parsed_date = datetime.strptime(date_str, "%d-%m-%Y")
                                return parsed_date.strftime("%Y-%m-%d")
                        else:
                            # Handle "DD Month YYYY" format
                            parsed_date = datetime.strptime(date_str, "%d %b %Y")
                            return parsed_date.strftime("%Y-%m-%d")
                    except:
                        continue
            
            return datetime.now().strftime("%Y-%m-%d")
            
        except Exception as e:
            logger.error(f"Advanced date extraction failed: {e}")
            return datetime.now().strftime("%Y-%m-%d")
    
    def extract_line_items_advanced(self, texts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Advanced line item extraction using layout analysis"""
        try:
            line_items = []
            
            # Group texts by horizontal position to identify table rows
            sorted_texts = sorted(texts, key=lambda x: x['bbox'][1] if x['bbox'] else 0)
            
            current_row = []
            last_y = None
            
            for text_item in sorted_texts:
                if not text_item['bbox']:
                    continue
                
                current_y = text_item['bbox'][1]
                
                # If y-position changes significantly, start new row
                if last_y is None or abs(current_y - last_y) > 20:
                    if current_row:
                        # Process completed row
                        line_item = self.parse_line_item_row(current_row)
                        if line_item:
                            line_items.append(line_item)
                    current_row = [text_item]
                else:
                    current_row.append(text_item)
                
                last_y = current_y
            
            # Process final row
            if current_row:
                line_item = self.parse_line_item_row(current_row)
                if line_item:
                    line_items.append(line_item)
            
            return line_items
            
        except Exception as e:
            logger.error(f"Advanced line item extraction failed: {e}")
            return []
    
    def parse_line_item_row(self, row_texts: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Parse a single row of text into a line item"""
        try:
            # Sort by x-position to get columns
            sorted_row = sorted(row_texts, key=lambda x: x['bbox'][0] if x['bbox'] else 0)
            
            row_text = " ".join([t['text'] for t in sorted_row])
            
            # Look for quantity patterns
            qty_match = re.search(r'(\d+)\s+([A-Z0-9\-]+)', row_text)
            if qty_match:
                quantity = int(qty_match.group(1))
                code = qty_match.group(2)
                
                # Extract description and price
                remaining_text = row_text[qty_match.end():].strip()
                
                # Look for price pattern
                price_match = re.search(r'[£$€](\d+\.?\d*)', remaining_text)
                if price_match:
                    unit_price = float(price_match.group(1))
                    
                    # Description is everything between code and price
                    description = remaining_text[:price_match.start()].strip()
                    if not description:
                        description = f"Item {code}"
                    
                    return {
                        "quantity": quantity,
                        "code": code,
                        "description": description,
                        "unit_price": unit_price,
                        "total_price": quantity * unit_price
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Line item row parsing failed: {e}")
            return None
    
    async def process_document_advanced(self, file_path: str) -> List[Dict[str, Any]]:
        """Main method to process a document with advanced OCR"""
        try:
            logger.info(f"🔍 Starting advanced OCR processing for: {file_path}")
            
            if not OCR_AVAILABLE:
                logger.error("❌ OCR dependencies not available")
                return []
            
            file_path = Path(file_path)
            if not file_path.exists():
                logger.error(f"❌ File not found: {file_path}")
                return []
            
            # Handle different file types
            if file_path.suffix.lower() == '.pdf':
                return await self.process_pdf_advanced(file_path)
            elif file_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.tiff', '.tif']:
                return await self.process_image_advanced(file_path)
            else:
                logger.error(f"❌ Unsupported file type: {file_path.suffix}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Advanced document processing failed: {e}")
            return []
    
    async def process_pdf_advanced(self, file_path: Path) -> List[Dict[str, Any]]:
        """Process PDF with advanced OCR"""
        try:
            logger.info(f"📄 Processing PDF: {file_path}")
            
            # Try text extraction first
            try:
                doc = fitz.open(file_path)
                all_text = ""
                for page in doc:
                    all_text += page.get_text()
                doc.close()
                
                if all_text.strip():
                    logger.info("✅ PDF text extraction successful")
                    # Process extracted text
                    return await self.process_text_content(all_text, "pdf_text")
            except Exception as e:
                logger.warning(f"PDF text extraction failed: {e}")
            
            # Fallback to image-based OCR
            try:
                images = convert_from_path(file_path)
                all_results = []
                
                for page_num, image in enumerate(images, 1):
                    logger.info(f"📄 Processing PDF page {page_num}")
                    
                    # Convert PIL image to numpy array
                    img_array = np.array(image)
                    
                    # Extract text with multiple OCR engines
                    easyocr_results = self.extract_text_with_easyocr(img_array)
                    tesseract_results = self.extract_text_with_tesseract(img_array)
                    
                    # Combine results, preferring EasyOCR
                    combined_results = easyocr_results + tesseract_results
                    
                    if combined_results:
                        # Segment document into sections
                        sections = self.segment_document(combined_results)
                        
                        for section in sections:
                            # Extract invoice data for each section
                            invoice_data = self.extract_invoice_data_advanced(section['texts'])
                            invoice_data['page_number'] = page_num
                            invoice_data['section_confidence'] = section['confidence']
                            invoice_data['section_type'] = section['type']
                            
                            all_results.append(invoice_data)
                
                return all_results
                
            except Exception as e:
                logger.error(f"PDF image processing failed: {e}")
                return []
                
        except Exception as e:
            logger.error(f"PDF processing failed: {e}")
            return []
    
    async def process_image_advanced(self, file_path: Path) -> List[Dict[str, Any]]:
        """Process image with advanced OCR"""
        try:
            logger.info(f"🖼️ Processing image: {file_path}")
            
            # Load image
            image = cv2.imread(str(file_path))
            if image is None:
                logger.error(f"❌ Failed to load image: {file_path}")
                return []
            
            # Extract text with multiple OCR engines
            easyocr_results = self.extract_text_with_easyocr(image)
            tesseract_results = self.extract_text_with_tesseract(image)
            
            # Combine results
            combined_results = easyocr_results + tesseract_results
            
            if not combined_results:
                logger.warning("❌ No text extracted from image")
                return []
            
            # Segment document into sections
            sections = self.segment_document(combined_results)
            
            all_results = []
            for section in sections:
                # Extract invoice data for each section
                invoice_data = self.extract_invoice_data_advanced(section['texts'])
                invoice_data['section_confidence'] = section['confidence']
                invoice_data['section_type'] = section['type']
                
                all_results.append(invoice_data)
            
            return all_results
            
        except Exception as e:
            logger.error(f"Image processing failed: {e}")
            return []
    
    async def process_text_content(self, text: str, source: str) -> List[Dict[str, Any]]:
        """Process text content directly"""
        try:
            logger.info(f"📝 Processing text content from {source}")
            
            # Create a mock text item for processing
            text_item = {
                "text": text,
                "confidence": 0.9,
                "bbox": [0, 0, 100, 100],
                "type": source
            }
            
            # Segment document
            sections = self.segment_document([text_item])
            
            all_results = []
            for section in sections:
                # Extract invoice data for each section
                invoice_data = self.extract_invoice_data_advanced(section['texts'])
                invoice_data['section_confidence'] = section['confidence']
                invoice_data['section_type'] = section['type']
                invoice_data['source'] = source
                
                all_results.append(invoice_data)
            
            return all_results
            
        except Exception as e:
            logger.error(f"Text content processing failed: {e}")
            return []

# Global instance
advanced_ocr_processor = AdvancedOCRProcessor() 