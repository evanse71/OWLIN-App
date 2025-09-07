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
    import easyocr
    from fuzzywuzzy import fuzz
    from fuzzywuzzy import process
    OCR_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Some OCR dependencies not available: {e}")
    OCR_AVAILABLE = False

class AdvancedOCRProcessorSimple:
    """
    Simplified Advanced OCR processor using:
    - EasyOCR for general text extraction
    - PyMuPDF for PDF text extraction
    - Tesseract as fallback
    - Custom document segmentation for multi-invoice files
    """
    
    def __init__(self):
        self.easyocr_reader = None
        self.initialize_models()
    
    def initialize_models(self):
        """Initialize OCR models"""
        try:
            # Initialize EasyOCR for general text extraction
            self.easyocr_reader = easyocr.Reader(['en'], gpu=False)
            logger.info("✅ EasyOCR initialized")
        except Exception as e:
            logger.warning(f"EasyOCR not available: {e}")
            self.easyocr_reader = None
    
    def preprocess_image_advanced(self, image: np.ndarray) -> List[np.ndarray]:
        """Advanced image preprocessing with multiple strategies"""
        try:
            # Convert to grayscale if needed
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image
            
            # Strategy 1: Deskewing
            angle = self.detect_skew_angle(gray)
            rotated = self.rotate_image(gray, angle)
            
            # Strategy 2: Perspective correction
            corrected = self.perspective_correction(rotated)
            
            # Multiple preprocessing strategies
            results = []
            
            # Strategy 1: CLAHE
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
            enhanced1 = clahe.apply(corrected)
            denoised1 = cv2.fastNlMeansDenoising(enhanced1)
            binary1 = cv2.adaptiveThreshold(
                denoised1, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )
            results.append(binary1)
            
            # Strategy 2: Histogram equalization
            enhanced2 = cv2.equalizeHist(corrected)
            denoised2 = cv2.fastNlMeansDenoising(enhanced2)
            binary2 = cv2.adaptiveThreshold(
                denoised2, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 15, 3
            )
            results.append(binary2)
            
            # Strategy 3: Gaussian blur + Otsu threshold
            blurred = cv2.GaussianBlur(corrected, (5,5), 0)
            _, binary3 = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            results.append(binary3)
            
            # Strategy 4: Original with minimal processing
            results.append(corrected)
            
            return results
            
        except Exception as e:
            logger.error(f"Advanced image preprocessing failed: {e}")
            return [image]
    
    def detect_skew_angle(self, image: np.ndarray) -> float:
        """Detect skew angle of document"""
        try:
            # Edge detection
            edges = cv2.Canny(image, 50, 150, apertureSize=3)
            
            # Line detection
            lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=100)
            
            if lines is None:
                return 0.0
            
            angles = []
            for line in lines:
                rho, theta = line[0]
                angle = theta * 180 / np.pi
                if angle < 45 or angle > 135:
                    angles.append(angle - 90)
            
            if angles:
                return np.median(angles)
            return 0.0
            
        except Exception as e:
            logger.error(f"Skew detection failed: {e}")
            return 0.0
    
    def rotate_image(self, image: np.ndarray, angle: float) -> np.ndarray:
        """Rotate image by given angle"""
        try:
            if abs(angle) < 0.5:
                return image
            
            height, width = image.shape[:2]
            center = (width // 2, height // 2)
            
            # Rotation matrix
            rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
            
            # Perform rotation
            rotated = cv2.warpAffine(image, rotation_matrix, (width, height), 
                                    flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, 
                                    borderValue=255)
            
            return rotated
            
        except Exception as e:
            logger.error(f"Image rotation failed: {e}")
            return image
    
    def perspective_correction(self, image: np.ndarray) -> np.ndarray:
        """Correct perspective distortion"""
        try:
            # Edge detection
            edges = cv2.Canny(image, 50, 150, apertureSize=3)
            
            # Find contours
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if not contours:
                return image
            
            # Find the largest contour (assumed to be the document)
            largest_contour = max(contours, key=cv2.contourArea)
            
            # Approximate contour to polygon
            epsilon = 0.02 * cv2.arcLength(largest_contour, True)
            approx = cv2.approxPolyDP(largest_contour, epsilon, True)
            
            # If we have 4 points, we can do perspective correction
            if len(approx) == 4:
                # Order points: top-left, top-right, bottom-right, bottom-left
                pts = approx.reshape(4, 2)
                rect = np.zeros((4, 2), dtype="float32")
                
                # Top-left point will have the smallest sum
                s = pts.sum(axis=1)
                rect[0] = pts[np.argmin(s)]
                rect[2] = pts[np.argmax(s)]
                
                # Top-right point will have the smallest difference
                diff = np.diff(pts, axis=1)
                rect[1] = pts[np.argmin(diff)]
                rect[3] = pts[np.argmax(diff)]
                
                # Calculate width and height
                widthA = np.sqrt(((rect[2][0] - rect[3][0]) ** 2) + ((rect[2][1] - rect[3][1]) ** 2))
                widthB = np.sqrt(((rect[1][0] - rect[0][0]) ** 2) + ((rect[1][1] - rect[0][1]) ** 2))
                maxWidth = max(int(widthA), int(widthB))
                
                heightA = np.sqrt(((rect[1][0] - rect[2][0]) ** 2) + ((rect[1][1] - rect[2][1]) ** 2))
                heightB = np.sqrt(((rect[0][0] - rect[3][0]) ** 2) + ((rect[0][1] - rect[3][1]) ** 2))
                maxHeight = max(int(heightA), int(heightB))
                
                # Destination points
                dst = np.array([
                    [0, 0],
                    [maxWidth - 1, 0],
                    [maxWidth - 1, maxHeight - 1],
                    [0, maxHeight - 1]
                ], dtype="float32")
                
                # Calculate perspective transform matrix
                M = cv2.getPerspectiveTransform(rect, dst)
                
                # Apply perspective transform
                corrected = cv2.warpPerspective(image, M, (maxWidth, maxHeight))
                
                return corrected
            
            return image
            
        except Exception as e:
            logger.error(f"Perspective correction failed: {e}")
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
            
            # First, try to detect multiple invoices by looking for invoice indicators
            combined_text = " ".join([t['text'] for t in all_texts])
            
            # Check if this might be multiple invoices
            invoice_indicators = [
                'invoice', 'inv#', 'invoice no', 'invoice number',
                'delivery note', 'advice note', 'receipt',
                'total', 'amount due', 'balance due'
            ]
            
            # Count invoice indicators
            indicator_count = sum(1 for indicator in invoice_indicators if indicator.lower() in combined_text.lower())
            
            # If we have multiple strong indicators, try to split
            if indicator_count > 2:
                logger.info(f"📄 Multiple invoice indicators detected ({indicator_count}), attempting segmentation")
                return self.segment_multiple_invoices(all_texts)
            
            # Single invoice processing
            for text_item in sorted_texts:
                text = text_item['text'].lower()
                
                # Check for invoice indicators
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
    
    def segment_multiple_invoices(self, all_texts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Segment document into multiple invoices"""
        try:
            sections = []
            current_section = []
            
            # Sort by vertical position
            sorted_texts = sorted(all_texts, key=lambda x: x['bbox'][1] if x['bbox'] else 0)
            
            # Look for clear invoice boundaries
            invoice_start_patterns = [
                r'\b(?:invoice|inv|bill)\s*#?\s*\d+',
                r'\b(?:invoice|inv|bill)\s*(?:number|no)\s*:?\s*\d+',
                r'\b(?:date|issued)\s*:?\s*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',
                r'\b(?:total|amount|balance)\s*(?:due|payable)\s*:?\s*[£$€]?\d+',
            ]
            
            # Also look for supplier names that might indicate new invoice
            supplier_indicators = ['limited', 'ltd', 'company', 'brewing', 'dispense', 'hospitality']
            
            for text_item in sorted_texts:
                text = text_item['text']
                
                # Check if this looks like the start of a new invoice
                is_new_invoice = False
                
                # Check for invoice patterns
                for pattern in invoice_start_patterns:
                    if re.search(pattern, text, re.IGNORECASE):
                        is_new_invoice = True
                        break
                
                # Check for supplier names that might indicate new invoice
                if any(indicator in text.lower() for indicator in supplier_indicators) and len(text.strip()) > 10:
                    # Check if this is likely a supplier name (not in a table)
                    if not any(table_word in text.lower() for table_word in ['qty', 'code', 'item', 'price', 'total']):
                        # Additional check: look for company name patterns
                        if re.search(r'\b[A-Z][A-Za-z\s&]+(?:LIMITED|LTD|CO|COMPANY|BREWING|BREWERY|DISPENSE|HOSPITALITY)\b', text):
                            is_new_invoice = True
                
                # Check for clear separators (but be more specific)
                if '=' in text and len(text.strip()) > 20:  # More specific separator check
                    is_new_invoice = True
                
                # Check for "INVOICE X" pattern
                if re.search(r'INVOICE\s+\d+', text, re.IGNORECASE):
                    is_new_invoice = True
                
                if is_new_invoice and current_section:
                    # Start new section
                    if current_section:
                        sections.append({
                            "texts": current_section,
                            "confidence": np.mean([t['confidence'] for t in current_section]),
                            "type": self.classify_section_type(current_section)
                        })
                    current_section = [text_item]
                else:
                    current_section.append(text_item)
            
            # Add final section
            if current_section:
                sections.append({
                    "texts": current_section,
                    "confidence": np.mean([t['confidence'] for t in current_section]),
                    "type": self.classify_section_type(current_section)
                })
            
            # If we only found one section, try alternative segmentation
            if len(sections) <= 1:
                return self.segment_by_page_breaks(all_texts)
            
            # Filter out sections that are too small (likely not complete invoices)
            filtered_sections = []
            for section in sections:
                section_text = " ".join([t.get('text', '') for t in section.get('texts', [])])
                if len(section_text) > 200:  # Increased minimum size for complete invoice
                    filtered_sections.append(section)
            
            # If we filtered out too many sections, try to merge small sections
            if len(filtered_sections) < 2 and len(sections) >= 2:
                logger.info("📄 Merging small sections to create complete invoices")
                # Try to merge sections that are too small
                merged_sections = []
                current_merged = []
                
                for section in sections:
                    section_text = " ".join([t.get('text', '') for t in section.get('texts', [])])
                    if len(section_text) < 200:
                        # Add to current merge
                        current_merged.extend(section.get('texts', []))
                    else:
                        # If we have accumulated text, create a merged section
                        if current_merged:
                            merged_sections.append({
                                "texts": current_merged,
                                "confidence": np.mean([t['confidence'] for t in current_merged]),
                                "type": "invoice"
                            })
                            current_merged = []
                        # Add the large section
                        merged_sections.append(section)
                
                # Add any remaining merged section
                if current_merged:
                    merged_sections.append({
                        "texts": current_merged,
                        "confidence": np.mean([t['confidence'] for t in current_merged]),
                        "type": "invoice"
                    })
                
                if merged_sections:
                    logger.info(f"📄 Successfully created {len(merged_sections)} merged invoices")
                    return merged_sections
            
            if filtered_sections:
                logger.info(f"📄 Successfully segmented into {len(filtered_sections)} invoices")
                return filtered_sections
            else:
                logger.info("📄 No valid sections found, returning original")
                return sections
            
        except Exception as e:
            logger.error(f"Multiple invoice segmentation failed: {e}")
            return [{"texts": all_texts, "confidence": 0.5, "type": "unknown"}]
    
    def segment_by_page_breaks(self, all_texts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Segment by looking for page breaks or large vertical gaps"""
        try:
            sections = []
            current_section = []
            last_y = None
            
            # Sort by vertical position
            sorted_texts = sorted(all_texts, key=lambda x: x['bbox'][1] if x['bbox'] else 0)
            
            for text_item in sorted_texts:
                if not text_item['bbox']:
                    current_section.append(text_item)
                    continue
                
                current_y = text_item['bbox'][1]
                
                # If there's a large gap, it might be a page break
                if last_y is not None and (current_y - last_y) > 100:  # 100px gap
                    if current_section:
                        sections.append({
                            "texts": current_section,
                            "confidence": np.mean([t['confidence'] for t in current_section]),
                            "type": self.classify_section_type(current_section)
                        })
                    current_section = [text_item]
                else:
                    current_section.append(text_item)
                
                last_y = current_y
            
            # Add final section
            if current_section:
                sections.append({
                    "texts": current_section,
                    "confidence": np.mean([t['confidence'] for t in current_section]),
                    "type": self.classify_section_type(current_section)
                })
            
            return sections
            
        except Exception as e:
            logger.error(f"Page break segmentation failed: {e}")
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
        """Advanced invoice data extraction with confidence scoring"""
        try:
            combined_text = " ".join([t['text'] for t in texts])
            
            # Initialize results
            extracted_data = {
                "supplier_name": "Unknown Supplier",
                "invoice_number": "Unknown",
                "total_amount": 0.0,
                "invoice_date": datetime.now().strftime("%Y-%m-%d"),
                "line_items": [],
                "confidence": 0.0,
                "document_type": "unknown",
                "extraction_details": {}
            }
            
            # Extract supplier name using multiple strategies
            supplier_name = self.extract_supplier_name_advanced(combined_text, texts)
            if supplier_name and supplier_name != "Unknown Supplier":
                extracted_data["supplier_name"] = supplier_name
                extracted_data["extraction_details"]["supplier_confidence"] = 0.8
            
            # Extract invoice number
            invoice_number = self.extract_invoice_number_advanced(combined_text)
            if invoice_number and invoice_number != "Unknown":
                extracted_data["invoice_number"] = invoice_number
                extracted_data["extraction_details"]["invoice_number_confidence"] = 0.7
            
            # Extract total amount
            total_amount = self.extract_total_amount_advanced(combined_text)
            if total_amount > 0:
                extracted_data["total_amount"] = total_amount
                extracted_data["extraction_details"]["total_amount_confidence"] = 0.9
            
            # Extract invoice date
            invoice_date = self.extract_invoice_date_advanced(combined_text)
            if invoice_date and invoice_date != datetime.now().strftime("%Y-%m-%d"):
                extracted_data["invoice_date"] = invoice_date
                extracted_data["extraction_details"]["date_confidence"] = 0.8
            
            # Extract line items
            line_items = self.extract_line_items_advanced(texts)
            if line_items:
                extracted_data["line_items"] = line_items
                extracted_data["extraction_details"]["line_items_confidence"] = 0.7
                extracted_data["extraction_details"]["line_items_count"] = len(line_items)
            
            # Calculate overall confidence
            overall_confidence = self.calculate_overall_confidence(extracted_data, texts)
            extracted_data["confidence"] = overall_confidence
            
            # Determine document type
            document_type = self.classify_document_type(combined_text, extracted_data)
            extracted_data["document_type"] = document_type
            
            # Add validation results
            validation_results = self.validate_extracted_data(extracted_data)
            extracted_data["validation"] = validation_results
            
            return extracted_data
            
        except Exception as e:
            logger.error(f"Advanced invoice data extraction failed: {e}")
            return {
                "supplier_name": "Unknown Supplier",
                "invoice_number": "Unknown",
                "total_amount": 0.0,
                "invoice_date": datetime.now().strftime("%Y-%m-%d"),
                "line_items": [],
                "confidence": 0.3,
                "document_type": "unknown",
                "extraction_details": {"error": str(e)}
            }
    
    def calculate_overall_confidence(self, extracted_data: Dict[str, Any], texts: List[Dict[str, Any]]) -> float:
        """Calculate overall confidence score for extracted data"""
        try:
            # Base OCR confidence
            base_confidence = np.mean([t['confidence'] for t in texts]) if texts else 0.5
            
            # Data extraction confidence
            data_confidence = 0.0
            
            # Supplier confidence
            if extracted_data.get('supplier_name') != 'Unknown Supplier':
                data_confidence += 0.2
                supplier_confidence = extracted_data.get('extraction_details', {}).get('supplier_confidence', 0.0)
                data_confidence += supplier_confidence * 0.1
            
            # Invoice number confidence
            if extracted_data.get('invoice_number') != 'Unknown':
                data_confidence += 0.15
                invoice_confidence = extracted_data.get('extraction_details', {}).get('invoice_number_confidence', 0.0)
                data_confidence += invoice_confidence * 0.1
            
            # Total amount confidence
            if extracted_data.get('total_amount', 0) > 0:
                data_confidence += 0.25
                total_confidence = extracted_data.get('extraction_details', {}).get('total_amount_confidence', 0.0)
                data_confidence += total_confidence * 0.1
            
            # Date confidence
            if extracted_data.get('invoice_date') != datetime.now().strftime("%Y-%m-%d"):
                data_confidence += 0.1
                date_confidence = extracted_data.get('extraction_details', {}).get('date_confidence', 0.0)
                data_confidence += date_confidence * 0.1
            
            # Line items confidence
            line_items = extracted_data.get('line_items', [])
            if line_items:
                data_confidence += 0.3
                line_items_confidence = extracted_data.get('extraction_details', {}).get('line_items_confidence', 0.0)
                data_confidence += line_items_confidence * 0.1
                
                # Bonus for multiple line items
                if len(line_items) > 1:
                    data_confidence += 0.1
            
            # Consistency validation
            consistency_score = self.validate_data_consistency(extracted_data)
            data_confidence += consistency_score * 0.2
            
            # Final confidence calculation
            final_confidence = min(0.95, base_confidence + data_confidence)
            
            # Ensure minimum confidence
            return max(0.3, final_confidence)
            
        except Exception as e:
            logger.error(f"Confidence calculation failed: {e}")
            return 0.5
    
    def validate_data_consistency(self, extracted_data: Dict[str, Any]) -> float:
        """Validate consistency of extracted data"""
        try:
            consistency_score = 0.0
            line_items = extracted_data.get('line_items', [])
            total_amount = extracted_data.get('total_amount', 0)
            
            # Check if line items sum matches total
            if line_items and total_amount > 0:
                line_items_total = sum(item.get('total_price', 0) for item in line_items)
                if abs(line_items_total - total_amount) < 1.0:  # Within £1
                    consistency_score += 0.3
                elif abs(line_items_total - total_amount) < 5.0:  # Within £5
                    consistency_score += 0.1
            
            # Check if invoice date is reasonable
            try:
                invoice_date = datetime.strptime(extracted_data.get('invoice_date', ''), "%Y-%m-%d")
                current_date = datetime.now()
                if invoice_date <= current_date and invoice_date.year >= 2020:
                    consistency_score += 0.2
            except:
                pass
            
            # Check if supplier name looks reasonable
            supplier_name = extracted_data.get('supplier_name', '')
            if supplier_name != 'Unknown Supplier' and len(supplier_name) > 5:
                consistency_score += 0.2
            
            # Check if invoice number looks reasonable
            invoice_number = extracted_data.get('invoice_number', '')
            if invoice_number != 'Unknown' and len(invoice_number) > 3:
                consistency_score += 0.2
            
            return min(1.0, consistency_score)
            
        except Exception as e:
            logger.error(f"Data consistency validation failed: {e}")
            return 0.0
    
    def classify_document_type(self, text: str, extracted_data: Dict[str, Any]) -> str:
        """Classify document type based on content and extracted data"""
        try:
            text_upper = text.upper()
            
            # Check for specific document type indicators
            if any(indicator in text_upper for indicator in ['INVOICE', 'INV#', 'INVOICE NO']):
                return 'invoice'
            elif any(indicator in text_upper for indicator in ['DELIVERY NOTE', 'ADVICE NOTE', 'GOODS RECEIVED']):
                return 'delivery_note'
            elif any(indicator in text_upper for indicator in ['RECEIPT', 'SALE', 'PURCHASE']):
                return 'receipt'
            elif any(indicator in text_upper for indicator in ['UTILITY', 'ELECTRICITY', 'GAS', 'WATER', 'TELEPHONE']):
                return 'utility'
            elif extracted_data.get('line_items'):
                # If we have line items, it's likely an invoice
                return 'invoice'
            else:
                return 'unknown'
                
        except Exception as e:
            logger.error(f"Document classification failed: {e}")
            return 'unknown'
    
    def validate_extracted_data(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate extracted data for business rules"""
        try:
            validation_results = {
                "is_valid": True,
                "warnings": [],
                "errors": []
            }
            
            # Validate total amount
            total_amount = extracted_data.get('total_amount', 0)
            if total_amount <= 0:
                validation_results["warnings"].append("Total amount is zero or negative")
            
            # Validate line items
            line_items = extracted_data.get('line_items', [])
            if not line_items:
                validation_results["warnings"].append("No line items found")
            else:
                # Check for line items with zero prices
                zero_price_items = [item for item in line_items if item.get('unit_price', 0) <= 0]
                if zero_price_items:
                    validation_results["warnings"].append(f"{len(zero_price_items)} line items have zero or missing prices")
            
            # Validate supplier name
            supplier_name = extracted_data.get('supplier_name', '')
            if supplier_name == 'Unknown Supplier':
                validation_results["warnings"].append("Supplier name not found")
            
            # Validate invoice date
            try:
                invoice_date = datetime.strptime(extracted_data.get('invoice_date', ''), "%Y-%m-%d")
                current_date = datetime.now()
                if invoice_date > current_date:
                    validation_results["warnings"].append("Invoice date is in the future")
            except:
                validation_results["warnings"].append("Invalid invoice date format")
            
            # Check for critical errors
            if validation_results["errors"]:
                validation_results["is_valid"] = False
            
            return validation_results
            
        except Exception as e:
            logger.error(f"Data validation failed: {e}")
            return {
                "is_valid": False,
                "warnings": [],
                "errors": [f"Validation error: {str(e)}"]
            }
    
    def extract_supplier_name_advanced(self, text: str, texts: List[Dict[str, Any]]) -> str:
        """Advanced supplier name extraction with multiple strategies"""
        try:
            candidates = []
            
            # Strategy 1: Header analysis
            header_candidates = self.extract_header_candidates(text, texts)
            candidates.extend(header_candidates)
            
            # Strategy 2: Layout-based extraction
            layout_candidates = self.extract_by_layout_position(texts)
            candidates.extend(layout_candidates)
            
            # Strategy 3: Pattern-based extraction
            pattern_candidates = self.extract_by_patterns(text)
            candidates.extend(pattern_candidates)
            
            # Strategy 4: Fuzzy matching with known suppliers
            fuzzy_candidates = self.fuzzy_match_suppliers(text)
            candidates.extend(fuzzy_candidates)
            
            # Strategy 5: Context analysis
            context_candidates = self.extract_by_context(text, texts)
            candidates.extend(context_candidates)
            
            # Score and select the best candidate
            scored_candidates = self.score_supplier_candidates(candidates)
            best_supplier = self.select_best_supplier(scored_candidates)
            
            # Additional validation: make sure it's not a table header or line item
            if best_supplier and self.is_valid_supplier_name(best_supplier):
                return best_supplier
            
            return "Unknown Supplier"
            
        except Exception as e:
            logger.error(f"Advanced supplier extraction failed: {e}")
            return "Unknown Supplier"
    
    def is_valid_supplier_name(self, supplier_name: str) -> bool:
        """Validate that a supplier name is not a table header or line item"""
        try:
            # Skip if it's too short
            if len(supplier_name.strip()) < 5:
                return False
            
            # Skip if it contains table header keywords (but be more specific)
            table_keywords = ['qty', 'quantity', 'code', 'item', 'description', 'unit', 'price', 'amount', 'total', 'subtotal', 'vat', 'balance']
            supplier_lower = supplier_name.lower()
            
            # Reject if it contains table keywords
            if any(keyword in supplier_lower for keyword in table_keywords):
                return False
            
            # Skip if it looks like a line item code (all caps with numbers, short)
            if re.match(r'^[A-Z0-9\-]{2,8}$', supplier_name.strip()):
                return False
            
            # Skip if it's just a number or date
            if re.match(r'^\d+$', supplier_name.strip()):
                return False
            
            # Skip if it contains currency symbols
            if any(symbol in supplier_name for symbol in ['£', '$', '€']):
                return False
            
            # Must contain at least one letter
            if not re.search(r'[A-Za-z]', supplier_name):
                return False
            
            # Skip if it's too generic
            generic_names = ['unknown', 'test', 'sample', 'example']
            if supplier_lower.strip() in generic_names:
                return False
            
            # Skip if it looks like a table header (short, all caps)
            if len(supplier_name.strip()) <= 10 and supplier_name.isupper():
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Supplier name validation failed: {e}")
            return False
    
    def extract_header_candidates(self, text: str, texts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract supplier candidates from header area"""
        candidates = []
        lines = text.split('\n')
        header_lines = lines[:15]  # Check first 15 lines
        
        for i, line in enumerate(header_lines):
            line_upper = line.upper()
            line_stripped = line.strip()
            
            # Skip common invoice labels
            if any(skip in line_upper for skip in ['INVOICE', 'BILL TO:', 'DELIVER TO:', 'DATE:', 'TOTAL:', 'QTY', 'CODE', 'ITEM', 'AMOUNT', 'BALANCE']):
                continue
            
            # Look for company patterns
            company_patterns = ['LIMITED', 'LTD', 'CO', 'COMPANY', 'BREWING', 'BREWERY', 'DISPENSE', 'HYGIENE', 'SERVICES', 'SOLUTIONS']
            if any(pattern in line_upper for pattern in company_patterns):
                if len(line_stripped) > 5:
                    candidates.append({
                        'name': line_stripped,
                        'confidence': 0.8,
                        'strategy': 'header_pattern',
                        'position': i
                    })
            
            # Look for lines that look like company names (length, capitalization)
            if len(line_stripped) > 8 and len(line_stripped) < 50:
                if line_stripped[0].isupper() and any(word.isupper() for word in line_stripped.split()):
                    candidates.append({
                        'name': line_stripped,
                        'confidence': 0.6,
                        'strategy': 'header_format',
                        'position': i
                    })
        
        return candidates
    
    def extract_by_layout_position(self, texts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract supplier candidates based on layout position"""
        candidates = []
        
        # Sort by vertical position (top to bottom)
        sorted_texts = sorted(texts, key=lambda x: x['bbox'][1] if x['bbox'] else 0)
        
        # Check first 20% of texts (header area)
        header_count = max(1, len(sorted_texts) // 5)
        header_texts = sorted_texts[:header_count]
        
        for text_item in header_texts:
            text_line = text_item['text'].strip()
            if len(text_line) > 10 and not any(skip in text_line.upper() for skip in ['INVOICE', 'BILL TO:', 'DELIVER TO:', 'DATE:', 'TOTAL:']):
                # Check if it looks like a company name
                if any(pattern in text_line.upper() for pattern in ['LIMITED', 'LTD', 'CO', 'COMPANY']):
                    candidates.append({
                        'name': text_line,
                        'confidence': 0.7,
                        'strategy': 'layout_position',
                        'bbox': text_item['bbox']
                    })
        
        return candidates
    
    def extract_by_patterns(self, text: str) -> List[Dict[str, Any]]:
        """Extract supplier candidates using regex patterns"""
        candidates = []
        
        # Pattern 1: "From:" or "Supplier:" followed by company name
        patterns = [
            r'(?:from|supplier|vendor)\s*:?\s*([^\n]+)',
            r'([A-Z][A-Za-z\s&]+(?:LIMITED|LTD|CO|COMPANY))',
            r'([A-Z][A-Za-z\s&]+(?:BREWING|BREWERY|DISPENSE|HYGIENE))',
            # Specific patterns for your suppliers
            r'(RED\s+DRAGON\s+DISPENSE\s+LIMITED)',
            r'(WILD\s+HORSE\s+BREWING)',
            r'(SNOWDONIA\s+HOSPITALITY)',
            # General company name patterns
            r'([A-Z][A-Za-z\s&]+(?:SERVICES|SOLUTIONS))',
            r'([A-Z][A-Za-z\s&]+(?:BREWING|BREWERY))',
            r'([A-Z][A-Za-z\s&]+(?:DISPENSE|HYGIENE))',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if len(match.strip()) > 5:
                    candidates.append({
                        'name': match.strip(),
                        'confidence': 0.75,
                        'strategy': 'regex_pattern',
                        'pattern': pattern
                    })
        
        return candidates
    
    def fuzzy_match_suppliers(self, text: str) -> List[Dict[str, Any]]:
        """Fuzzy match with known supplier names"""
        candidates = []
        
        # Known supplier patterns (from your documents)
        known_suppliers = [
            'Red Dragon Dispense Limited',
            'Wild Horse Brewery',
            'Snowdonia Hospitality',
            'Dispense Solutions',
            'Brewery Services',
            'Red Dragon Dispense',
            'Wild Horse Brewing',
            'Snowdonia Hospitality Limited'
        ]
        
        try:
            from fuzzywuzzy import fuzz
            
            lines = text.split('\n')
            for line in lines:
                line_stripped = line.strip()
                if len(line_stripped) > 5:
                    for known_supplier in known_suppliers:
                        # Use more lenient matching for OCR errors
                        ratio = fuzz.ratio(line_stripped.upper(), known_supplier.upper())
                        partial_ratio = fuzz.partial_ratio(line_stripped.upper(), known_supplier.upper())
                        token_sort_ratio = fuzz.token_sort_ratio(line_stripped.upper(), known_supplier.upper())
                        
                        # Use the best ratio
                        best_ratio = max(ratio, partial_ratio, token_sort_ratio)
                        
                        if best_ratio > 60:  # Lowered threshold for better matching
                            candidates.append({
                                'name': line_stripped,
                                'confidence': best_ratio / 100.0,
                                'strategy': 'fuzzy_match',
                                'matched_to': known_supplier,
                                'ratio': best_ratio
                            })
        except ImportError:
            logger.warning("fuzzywuzzy not available - skipping fuzzy matching")
        
        return candidates
    
    def extract_by_context(self, text: str, texts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract supplier candidates using context analysis"""
        candidates = []
        
        # Look for lines that appear before invoice details
        lines = text.split('\n')
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            # Check if this line is followed by invoice-related content
            if i + 1 < len(lines):
                next_line = lines[i + 1].upper()
                if any(indicator in next_line for indicator in ['INVOICE', 'DATE:', 'TOTAL:', 'AMOUNT:']):
                    if len(line_stripped) > 8 and line_stripped[0].isupper():
                        candidates.append({
                            'name': line_stripped,
                            'confidence': 0.65,
                            'strategy': 'context_analysis',
                            'context': 'before_invoice_details'
                        })
        
        return candidates
    
    def score_supplier_candidates(self, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Score and rank supplier candidates"""
        for candidate in candidates:
            score = candidate['confidence']
            
            # Boost score for certain strategies
            if candidate['strategy'] == 'fuzzy_match':
                score *= 1.2
            elif candidate['strategy'] == 'header_pattern':
                score *= 1.1
            
            # Penalize very short or very long names
            name_length = len(candidate['name'])
            if name_length < 5:
                score *= 0.5
            elif name_length > 100:
                score *= 0.7
            
            # Boost for common company suffixes
            if any(suffix in candidate['name'].upper() for suffix in ['LIMITED', 'LTD', 'CO', 'COMPANY']):
                score *= 1.1
            
            candidate['final_score'] = min(1.0, score)
        
        # Sort by final score
        return sorted(candidates, key=lambda x: x['final_score'], reverse=True)
    
    def select_best_supplier(self, scored_candidates: List[Dict[str, Any]]) -> str:
        """Select the best supplier candidate"""
        if not scored_candidates:
            return "Unknown Supplier"
        
        best_candidate = scored_candidates[0]
        
        # Only return if confidence is high enough
        if best_candidate['final_score'] > 0.5:
            return best_candidate['name']
        
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
        """Advanced total amount extraction with priority for correct totals"""
        try:
            # PATTERN 1: Look for explicit total fields first
            total_patterns = [
                r'(?:total|amount|balance)\s*(?:due|payable|inc\.?\s*vat)\s*:?\s*[£$€]?\s*(\d+\.?\d*)',
                r'(?:total|amount|balance)\s*\(inc\.?\s*vat\)\s*:?\s*[£$€]?\s*(\d+\.?\d*)',
                r'(?:total|amount|balance)\s*\(including\s*vat\)\s*:?\s*[£$€]?\s*(\d+\.?\d*)',
                r'(?:total|amount|balance)\s*:?\s*[£$€]?\s*(\d+\.?\d*)',
                r'[£$€]\s*(\d+\.?\d*)\s*(?:total|amount|balance)',
            ]
            
            # Try each pattern in order of priority
            for pattern in total_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    amount = float(match)
                    # Validate that this looks like a reasonable total (not a line item)
                    if amount > 10 and amount < 10000:  # Reasonable invoice total range
                        return amount
            
            # PATTERN 2: Look for currency amounts that appear to be totals
            currency_patterns = [
                r'[£$€]\s*(\d+\.?\d*)',
            ]
            
            all_amounts = []
            for pattern in currency_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    amount = float(match)
                    if amount > 10:  # Filter out small amounts that might be line items
                        all_amounts.append(amount)
            
            # If we found multiple amounts, try to identify the total
            if all_amounts:
                # Sort by amount (largest first)
                all_amounts.sort(reverse=True)
                
                # Look for amounts that appear near "total" keywords
                lines = text.split('\n')
                for line in lines:
                    line_lower = line.lower()
                    if any(keyword in line_lower for keyword in ['total', 'amount', 'balance', 'due', 'payable']):
                        # Extract amount from this line
                        amount_match = re.search(r'[£$€]\s*(\d+\.?\d*)', line)
                        if amount_match:
                            amount = float(amount_match.group(1))
                            if amount > 10:
                                return amount
                
                # If no clear total found, look for the largest amount that's not near line items
                for amount in all_amounts:
                    # Check if this amount appears near line item indicators
                    amount_str = f"£{amount}"
                    if amount_str in text:
                        # Find the context around this amount
                        lines = text.split('\n')
                        for line in lines:
                            if amount_str in line:
                                line_lower = line.lower()
                                # If this line contains line item indicators, skip it
                                if any(indicator in line_lower for indicator in ['qty', 'code', 'item', 'description', 'unit']):
                                    continue
                                # If this line contains total indicators, use it
                                if any(indicator in line_lower for indicator in ['total', 'amount', 'balance', 'due', 'payable']):
                                    return amount
                
                # If still no clear total, return the largest amount
                return all_amounts[0]
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Advanced total extraction failed: {e}")
            return 0.0
    
    def extract_invoice_date_advanced(self, text: str) -> str:
        """Advanced invoice date extraction with multiple formats"""
        try:
            # PATTERN 1: Explicit date fields
            date_patterns = [
                r'(?:invoice\s+date|date|issue\s+date)\s*:?\s*([^\n]+)',
                r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4})',
                r'((?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s*\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})',
                # Additional patterns for common date formats
                r'(\d{1,2}\.\d{1,2}\.\d{2,4})',  # DD.MM.YYYY
                r'(\d{4}-\d{1,2}-\d{1,2})',      # YYYY-MM-DD
                r'(\d{1,2}/\d{1,2}/\d{2,4})',    # MM/DD/YYYY or DD/MM/YYYY
                r'(\d{1,2}-\d{1,2}-\d{2,4})',    # MM-DD-YYYY or DD-MM-YYYY
            ]
            
            # First, try to find explicit date fields
            for pattern in date_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    try:
                        date_str = match.strip()
                        
                        # Handle "Friday, 4 July 2025" format
                        if ',' in date_str and any(day in date_str for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']):
                            parsed_date = datetime.strptime(date_str, "%A, %d %B %Y")
                            return parsed_date.strftime("%Y-%m-%d")
                        
                        # Handle DD/MM/YYYY format
                        elif '/' in date_str:
                            parts = date_str.split('/')
                            if len(parts) == 3:
                                if len(parts[2]) == 2:
                                    date_str = f"{parts[0]}/{parts[1]}/20{parts[2]}"
                                # Try DD/MM/YYYY first
                                try:
                                    parsed_date = datetime.strptime(date_str, "%d/%m/%Y")
                                    return parsed_date.strftime("%Y-%m-%d")
                                except:
                                    # Try MM/DD/YYYY
                                    try:
                                        parsed_date = datetime.strptime(date_str, "%m/%d/%Y")
                                        return parsed_date.strftime("%Y-%m-%d")
                                    except:
                                        continue
                        
                        # Handle DD-MM-YYYY format
                        elif '-' in date_str:
                            parts = date_str.split('-')
                            if len(parts) == 3:
                                if len(parts[2]) == 2:
                                    date_str = f"{parts[0]}-{parts[1]}-20{parts[2]}"
                                # Try DD-MM-YYYY first
                                try:
                                    parsed_date = datetime.strptime(date_str, "%d-%m-%Y")
                                    return parsed_date.strftime("%Y-%m-%d")
                                except:
                                    # Try MM-DD-YYYY
                                    try:
                                        parsed_date = datetime.strptime(date_str, "%m-%d-%Y")
                                        return parsed_date.strftime("%Y-%m-%d")
                                    except:
                                        continue
                        
                        # Handle DD.MM.YYYY format
                        elif '.' in date_str:
                            parts = date_str.split('.')
                            if len(parts) == 3:
                                if len(parts[2]) == 2:
                                    date_str = f"{parts[0]}.{parts[1]}.20{parts[2]}"
                                try:
                                    parsed_date = datetime.strptime(date_str, "%d.%m.%Y")
                                    return parsed_date.strftime("%Y-%m-%d")
                                except:
                                    continue
                        
                        # Handle "DD Month YYYY" format
                        else:
                            try:
                                parsed_date = datetime.strptime(date_str, "%d %b %Y")
                                return parsed_date.strftime("%Y-%m-%d")
                            except:
                                try:
                                    parsed_date = datetime.strptime(date_str, "%d %B %Y")
                                    return parsed_date.strftime("%Y-%m-%d")
                                except:
                                    continue
                    except:
                        continue
            
            # If no explicit date found, look for dates in context
            lines = text.split('\n')
            for line in lines:
                line_lower = line.lower()
                if any(keyword in line_lower for keyword in ['invoice date', 'date', 'issued', 'created']):
                    # Look for date patterns in this line
                    date_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', line)
                    if date_match:
                        try:
                            date_str = date_match.group(1)
                            if '/' in date_str:
                                parts = date_str.split('/')
                                if len(parts) == 3:
                                    if len(parts[2]) == 2:
                                        date_str = f"{parts[0]}/{parts[1]}/20{parts[2]}"
                                    try:
                                        parsed_date = datetime.strptime(date_str, "%d/%m/%Y")
                                        return parsed_date.strftime("%Y-%m-%d")
                                    except:
                                        try:
                                            parsed_date = datetime.strptime(date_str, "%m/%d/%Y")
                                            return parsed_date.strftime("%Y-%m-%d")
                                        except:
                                            continue
                        except:
                            continue
            
            # If still no date found, return a placeholder instead of today's date
            return "Unknown Date"
            
        except Exception as e:
            logger.error(f"Advanced date extraction failed: {e}")
            return "Unknown Date"
    
    def extract_line_items_advanced(self, texts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Advanced line item extraction using layout analysis"""
        try:
            # If no texts with bbox, try simple text-based extraction
            if not texts or not any('bbox' in text and text['bbox'] for text in texts):
                logger.info("📝 No bbox data available, using text-based line item extraction")
                return self.extract_line_items_from_text(texts)
            
            # 1. Detect table structure
            table_structure = self.detect_table_structure(texts)
            
            # 2. Align table columns
            aligned_columns = self.align_table_columns(texts, table_structure)
            
            # 3. Group rows with validation
            validated_rows = self.group_and_validate_rows(aligned_columns)
            
            # 4. Parse line items with confidence
            line_items = []
            for row in validated_rows:
                item = self.parse_line_item_with_confidence(row)
                if item and item['confidence'] > 0.6:
                    line_items.append(item)
            
            # 5. Calculate tax and VAT
            line_items = self.calculate_tax_and_vat(line_items)
            
            return line_items
            
        except Exception as e:
            logger.error(f"Advanced line item extraction failed: {e}")
            return []
    
    def extract_line_items_from_text(self, texts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract line items from text without bbox data"""
        try:
            line_items = []
            
            # Combine all text
            combined_text = " ".join([t.get('text', '') for t in texts])
            
            # Split into lines
            lines = combined_text.split('\n')
            
            # Look for line item patterns
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Skip headers and totals
                if any(skip in line.upper() for skip in ['QTY', 'QUANTITY', 'CODE', 'ITEM', 'DESCRIPTION', 'UNIT', 'PRICE', 'AMOUNT', 'TOTAL', 'SUBTOTAL', 'VAT', 'BALANCE']):
                    continue
                
                # Try to parse line item
                item = self.parse_simple_line_item(line)
                if item:
                    line_items.append(item)
            
            return line_items
            
        except Exception as e:
            logger.error(f"Text-based line item extraction failed: {e}")
            return []
    
    def parse_simple_line_item(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse a simple line item from text"""
        try:
            # Look for quantity and code pattern
            qty_code_match = re.search(r'(\d+)\s+([A-Z0-9\-]+)', line)
            if qty_code_match:
                quantity = int(qty_code_match.group(1))
                code = qty_code_match.group(2)
                
                # Extract description (everything between code and price)
                remaining_text = line[qty_code_match.end():].strip()
                
                # Look for price patterns
                price_match = re.search(r'[£$€](\d+\.?\d*)', remaining_text)
                if price_match:
                    unit_price = float(price_match.group(1))
                    
                    # Description is everything before the price
                    description = remaining_text[:price_match.start()].strip()
                    if not description:
                        description = f"Item {code}"
                    
                    return {
                        "quantity": quantity,
                        "code": code,
                        "description": description,
                        "unit_price": unit_price,
                        "total_price": quantity * unit_price,
                        "confidence": 0.7
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Simple line item parsing failed: {e}")
            return None
    
    def detect_table_structure(self, texts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Detect table structure and column positions"""
        try:
            # Sort by vertical position
            sorted_texts = sorted(texts, key=lambda x: x['bbox'][1] if x['bbox'] else 0)
            
            # Find potential table headers
            headers = []
            for text_item in sorted_texts:
                text = text_item['text'].upper()
                if any(header in text for header in ['QTY', 'QUANTITY', 'CODE', 'ITEM', 'DESCRIPTION', 'UNIT', 'PRICE', 'AMOUNT', 'TOTAL']):
                    headers.append(text_item)
            
            # Analyze column positions
            if headers:
                x_positions = [h['bbox'][0] for h in headers if h['bbox']]
                if x_positions:
                    # Group nearby x-positions to identify columns
                    x_positions.sort()
                    columns = []
                    current_group = [x_positions[0]]
                    
                    for x in x_positions[1:]:
                        if x - current_group[-1] < 50:  # 50px threshold
                            current_group.append(x)
                        else:
                            columns.append(sum(current_group) / len(current_group))
                            current_group = [x]
                    
                    if current_group:
                        columns.append(sum(current_group) / len(current_group))
                    
                    return {
                        'columns': columns,
                        'has_headers': True,
                        'header_texts': [h['text'] for h in headers]
                    }
            
            # Fallback: estimate columns based on text distribution
            x_positions = [t['bbox'][0] for t in sorted_texts if t['bbox']]
            if x_positions:
                x_positions.sort()
                # Simple clustering
                columns = []
                for i in range(0, len(x_positions), max(1, len(x_positions) // 4)):
                    columns.append(x_positions[i])
                
                return {
                    'columns': columns,
                    'has_headers': False,
                    'header_texts': []
                }
            
            return {'columns': [], 'has_headers': False, 'header_texts': []}
            
        except Exception as e:
            logger.error(f"Table structure detection failed: {e}")
            return {'columns': [], 'has_headers': False, 'header_texts': []}
    
    def align_table_columns(self, texts: List[Dict[str, Any]], table_structure: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Align texts to table columns"""
        try:
            columns = table_structure.get('columns', [])
            if not columns:
                return texts
            
            aligned_texts = []
            for text_item in texts:
                if not text_item['bbox']:
                    continue
                
                x_pos = text_item['bbox'][0]
                
                # Find closest column
                closest_column = min(columns, key=lambda col: abs(col - x_pos))
                column_index = columns.index(closest_column)
                
                aligned_texts.append({
                    **text_item,
                    'column_index': column_index,
                    'column_x': closest_column
                })
            
            return aligned_texts
            
        except Exception as e:
            logger.error(f"Column alignment failed: {e}")
            return texts
    
    def group_and_validate_rows(self, aligned_texts: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """Group texts into rows and validate"""
        try:
            # Sort by vertical position
            sorted_texts = sorted(aligned_texts, key=lambda x: x['bbox'][1] if x['bbox'] else 0)
            
            rows = []
            current_row = []
            last_y = None
            
            for text_item in sorted_texts:
                if not text_item['bbox']:
                    continue
                
                current_y = text_item['bbox'][1]
                
                # If y-position changes significantly, start new row
                if last_y is None or abs(current_y - last_y) > 25:  # Increased threshold
                    if current_row:
                        # Validate row has meaningful content
                        if self.validate_row_content(current_row):
                            rows.append(current_row)
                    current_row = [text_item]
                else:
                    current_row.append(text_item)
                
                last_y = current_y
            
            # Process final row
            if current_row and self.validate_row_content(current_row):
                rows.append(current_row)
            
            return rows
            
        except Exception as e:
            logger.error(f"Row grouping failed: {e}")
            return []
    
    def validate_row_content(self, row: List[Dict[str, Any]]) -> bool:
        """Validate that a row contains meaningful line item data"""
        try:
            row_text = " ".join([t['text'] for t in row])
            
            # Skip header rows
            if any(header in row_text.upper() for header in ['QTY', 'QUANTITY', 'CODE', 'ITEM', 'DESCRIPTION', 'UNIT', 'PRICE', 'AMOUNT', 'TOTAL']):
                return False
            
            # Skip total rows
            if any(total in row_text.upper() for total in ['TOTAL', 'SUBTOTAL', 'VAT', 'BALANCE']):
                return False
            
            # Must have some text content
            if len(row_text.strip()) < 3:
                return False
            
            # Must have at least 2 columns for a line item
            if len(row) < 2:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Row validation failed: {e}")
            return False
    
    def parse_line_item_with_confidence(self, row: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Parse a row into a line item with confidence scoring"""
        try:
            # Sort by column position
            sorted_row = sorted(row, key=lambda x: x.get('column_x', 0))
            
            row_text = " ".join([t['text'] for t in sorted_row])
            
            # Extract quantity
            quantity = self.extract_quantity(row_text)
            
            # Extract product code
            code = self.extract_product_code(row_text)
            
            # Extract description
            description = self.extract_description(row_text)
            
            # Extract unit price
            unit_price = self.extract_unit_price(row_text)
            
            # Extract total price
            total_price = self.extract_total_price(row_text)
            
            # Calculate confidence
            confidence = self.calculate_line_item_confidence(quantity, code, description, unit_price, total_price)
            
            if confidence > 0.3:  # Minimum confidence threshold
                return {
                    "quantity": quantity,
                    "code": code,
                    "description": description,
                    "unit_price": unit_price,
                    "total_price": total_price,
                    "confidence": confidence
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Line item parsing failed: {e}")
            return None
    
    def extract_quantity(self, text: str) -> int:
        """Extract quantity from text"""
        try:
            # Look for quantity patterns
            patterns = [
                r'(\d+)\s+[A-Z0-9\-]+',  # "2 ABC123"
                r'QTY\s*:?\s*(\d+)',     # "QTY: 2"
                r'(\d+)\s*[xX]\s*',      # "2 x"
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    return int(match.group(1))
            
            return 1  # Default quantity
            
        except Exception as e:
            logger.error(f"Quantity extraction failed: {e}")
            return 1
    
    def extract_product_code(self, text: str) -> str:
        """Extract product code from text"""
        try:
            # Look for product code patterns
            patterns = [
                r'(\d+)\s+([A-Z0-9\-]+)',  # "2 ABC123"
                r'([A-Z0-9]{3,})',         # Any 3+ alphanumeric
                r'CODE\s*:?\s*([A-Z0-9\-]+)',  # "CODE: ABC123"
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    return match.group(1) if len(match.groups()) == 1 else match.group(2)
            
            return "UNKNOWN"
            
        except Exception as e:
            logger.error(f"Product code extraction failed: {e}")
            return "UNKNOWN"
    
    def extract_description(self, text: str) -> str:
        """Extract product description from text"""
        try:
            # Remove quantity and code
            cleaned_text = re.sub(r'\d+\s+[A-Z0-9\-]+', '', text)
            cleaned_text = re.sub(r'[A-Z0-9]{3,}', '', cleaned_text)
            
            # Remove price patterns
            cleaned_text = re.sub(r'[£$€]\s*\d+\.?\d*', '', cleaned_text)
            
            # Clean up
            description = re.sub(r'\s+', ' ', cleaned_text).strip()
            
            if description and len(description) > 2:
                return description
            
            return "Unknown Item"
            
        except Exception as e:
            logger.error(f"Description extraction failed: {e}")
            return "Unknown Item"
    
    def extract_unit_price(self, text: str) -> float:
        """Extract unit price from text"""
        try:
            # Look for unit price patterns
            patterns = [
                r'[£$€]\s*(\d+\.?\d*)\s*@',  # "£10.50 @"
                r'@\s*[£$€]\s*(\d+\.?\d*)',  # "@ £10.50"
                r'UNIT\s*:?\s*[£$€]\s*(\d+\.?\d*)',  # "UNIT: £10.50"
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    return float(match.group(1))
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Unit price extraction failed: {e}")
            return 0.0
    
    def extract_total_price(self, text: str) -> float:
        """Extract total price from text"""
        try:
            # Look for total price patterns
            patterns = [
                r'[£$€]\s*(\d+\.?\d*)\s*$',  # "£21.00" at end
                r'TOTAL\s*:?\s*[£$€]\s*(\d+\.?\d*)',  # "TOTAL: £21.00"
                r'[£$€]\s*(\d+\.?\d*)',  # Any currency amount
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    return float(match.group(1))
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Total price extraction failed: {e}")
            return 0.0
    
    def calculate_line_item_confidence(self, quantity: int, code: str, description: str, unit_price: float, total_price: float) -> float:
        """Calculate confidence score for a line item"""
        try:
            confidence = 0.0
            
            # Quantity confidence
            if quantity > 0:
                confidence += 0.2
            
            # Code confidence
            if code != "UNKNOWN":
                confidence += 0.2
            
            # Description confidence
            if description != "Unknown Item" and len(description) > 3:
                confidence += 0.2
            
            # Price confidence
            if unit_price > 0:
                confidence += 0.2
            if total_price > 0:
                confidence += 0.2
            
            # Validation confidence
            if unit_price > 0 and quantity > 0:
                expected_total = unit_price * quantity
                if abs(expected_total - total_price) < 0.01:  # Within 1p
                    confidence += 0.1
            
            return min(1.0, confidence)
            
        except Exception as e:
            logger.error(f"Confidence calculation failed: {e}")
            return 0.0
    
    def calculate_tax_and_vat(self, line_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Calculate tax and VAT for line items"""
        try:
            for item in line_items:
                # Add VAT calculation if unit price is available
                if item.get('unit_price', 0) > 0:
                    # Assume 20% VAT (UK standard)
                    vat_rate = 0.20
                    item['vat_amount'] = item['unit_price'] * vat_rate
                    item['price_with_vat'] = item['unit_price'] * (1 + vat_rate)
                
                # Add total with VAT if total price is available
                if item.get('total_price', 0) > 0:
                    vat_rate = 0.20
                    item['total_vat'] = item['total_price'] * vat_rate
                    item['total_with_vat'] = item['total_price'] * (1 + vat_rate)
            
            return line_items
            
        except Exception as e:
            logger.error(f"Tax calculation failed: {e}")
            return line_items
    
    async def process_document_advanced(self, file_path: str) -> List[Dict[str, Any]]:
        """Main method to process a document with advanced OCR"""
        try:
            logger.info(f"🔍 Starting advanced OCR processing for: {file_path}")
            
            # Check if OCR engines are properly initialized
            if not hasattr(self, 'easyocr_reader') or self.easyocr_reader is None:
                logger.error("❌ EasyOCR not initialized")
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
            elif file_path.suffix.lower() in ['.txt', '.md']:
                # Handle text files with advanced processing
                logger.info("📝 Processing text file with advanced extraction")
                with open(file_path, 'r', encoding='utf-8') as f:
                    text_content = f.read()
                return await self.process_text_content(text_content, "text_file")
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
            
            # ADDED: PDF image processing fallback
            try:
                from pdf2image import convert_from_path
                logger.info("🔄 Attempting PDF image processing...")
                
                # Convert PDF pages to images
                images = convert_from_path(str(file_path), dpi=300)
                logger.info(f"✅ Converted PDF to {len(images)} images")
                
                all_results = []
                for page_num, image in enumerate(images, 1):
                    logger.info(f"📄 Processing page {page_num}/{len(images)}")
                    
                    # Convert PIL image to numpy array
                    img_array = np.array(image)
                    
                    # Process with image OCR
                    page_results = await self.process_image_advanced(img_array)
                    all_results.extend(page_results)
                
                logger.info(f"✅ PDF image processing completed with {len(all_results)} results")
                return all_results
                
            except ImportError:
                logger.error("❌ pdf2image not available - PDF image processing disabled")
                return []
            except Exception as e:
                logger.error(f"❌ PDF image processing failed: {e}")
                return []
                
        except Exception as e:
            logger.error(f"PDF processing failed: {e}")
            return []
    
    async def process_image_advanced(self, file_path_or_array) -> List[Dict[str, Any]]:
        """Process image with advanced OCR - handles both file paths and numpy arrays"""
        try:
            # Check if input is a numpy array or file path
            if isinstance(file_path_or_array, np.ndarray):
                # Direct numpy array input
                image = file_path_or_array
                logger.info("🖼️ Processing numpy array image")
            else:
                # File path input
                file_path = Path(file_path_or_array)
                logger.info(f"🖼️ Processing image file: {file_path}")
                
                # Load image
                image = cv2.imread(str(file_path))
                if image is None:
                    logger.error(f"❌ Failed to load image: {file_path}")
                    return []
            
            # Use advanced preprocessing with multiple strategies
            processed_images = self.preprocess_image_advanced(image)
            
            all_results = []
            
            # Process each preprocessed version
            for i, processed_image in enumerate(processed_images):
                logger.info(f"🔄 Processing strategy {i+1}/{len(processed_images)}")
                
                # Extract text with multiple OCR engines
                easyocr_results = self.extract_text_with_easyocr(processed_image)
                tesseract_results = self.extract_text_with_tesseract(processed_image)
                
                # Combine results
                combined_results = easyocr_results + tesseract_results
                
                if combined_results:
                    # Segment document into sections
                    sections = self.segment_document(combined_results)
                    
                    for section in sections:
                        # Extract invoice data for each section
                        invoice_data = self.extract_invoice_data_advanced(section['texts'])
                        invoice_data['section_confidence'] = section['confidence']
                        invoice_data['section_type'] = section['type']
                        invoice_data['preprocessing_strategy'] = i + 1
                        
                        all_results.append(invoice_data)
            
            # If no results from any strategy, try original image
            if not all_results:
                logger.info("🔄 Trying original image as fallback")
                easyocr_results = self.extract_text_with_easyocr(image)
                tesseract_results = self.extract_text_with_tesseract(image)
                combined_results = easyocr_results + tesseract_results
                
                if combined_results:
                    sections = self.segment_document(combined_results)
                    for section in sections:
                        invoice_data = self.extract_invoice_data_advanced(section['texts'])
                        invoice_data['section_confidence'] = section['confidence']
                        invoice_data['section_type'] = section['type']
                        invoice_data['preprocessing_strategy'] = 'original'
                        all_results.append(invoice_data)
            
            return all_results
            
        except Exception as e:
            logger.error(f"Image processing failed: {e}")
            return []
    
    async def process_text_content(self, text: str, source: str) -> List[Dict[str, Any]]:
        """Process text content directly"""
        try:
            logger.info(f"📝 Processing text content from {source}")
            
            # Split text into lines and create text items
            lines = text.split('\n')
            text_items = []
            
            for i, line in enumerate(lines):
                if line.strip():  # Skip empty lines
                    text_item = {
                        "text": line.strip(),
                        "confidence": 0.9,
                        "bbox": [0, i * 20, 100, (i + 1) * 20],  # Simulate vertical positioning
                        "type": source
                    }
                    text_items.append(text_item)
            
            # Segment document
            sections = self.segment_document(text_items)
            
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
advanced_ocr_processor_simple = AdvancedOCRProcessorSimple() 