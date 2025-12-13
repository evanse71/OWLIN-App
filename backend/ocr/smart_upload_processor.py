import fitz  # PyMuPDF
from paddleocr import PaddleOCR
from PIL import Image
import io
import re
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import os
import uuid
import numpy as np

logger = logging.getLogger(__name__)

# Initialize PaddleOCR model
try:
    ocr_model = PaddleOCR(use_textline_orientation=True, lang='en')
    logger.info("✅ PaddleOCR model initialized for smart upload processor")
except Exception as e:
    logger.error(f"❌ Failed to initialize PaddleOCR: {e}")
    ocr_model = None

class SmartUploadProcessor:
    """
    Intelligent PDF processor that can detect and split multi-invoice PDFs.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.info("✅ SmartUploadProcessor initialized")
        # Enhanced invoice keywords for better detection
        self.invoice_keywords = [
            'invoice', 'tax', 'total', 'vat', 'subtotal', 'net', 'amount due',
            'invoice number', 'invoice date', 'supplier', 'payment', 'bill',
            'statement', 'account', 'balance', 'outstanding'
        ]
        
        # Invoice header patterns to detect new invoices
        self.invoice_header_patterns = [
            r'invoice\s*#?\s*[:.]?\s*([A-Za-z0-9\-_/]+)',
            r'invoice\s*number\s*[:.]?\s*([A-Za-z0-9\-_/]+)',
            r'inv\s*[:.]?\s*([A-Za-z0-9\-_/]+)',
            r'bill\s*#?\s*[:.]?\s*([A-Za-z0-9\-_/]+)',
            r'statement\s*#?\s*[:.]?\s*([A-Za-z0-9\-_/]+)',
            r'page\s+\d+\s+of\s+\d+',  # Page numbering often indicates new document
            r'continued\s+on\s+next\s+page',  # Continuation indicators
        ]
        
        # Keywords that indicate end of invoice
        self.invoice_end_patterns = [
            r'total\s+amount\s+due',
            r'grand\s+total',
            r'amount\s+due',
            r'payment\s+terms',
            r'thank\s+you',
            r'please\s+pay',
            r'terms\s+and\s+conditions'
        ]
        
        self.delivery_keywords = [
            'delivery note', 'goods received', 'pod', 'driver', 'delivery date',
            'received by', 'signature'
        ]
        
        self.utility_keywords = [
            'energy', 'kwh', 'standing charge', 'gas', 'electricity', 'utility',
            'meter reading', 'consumption'
        ]

    def process_multi_invoice_pdf(self, filepath: str) -> Dict[str, Any]:
        """
        Process a PDF that may contain multiple invoices and split them intelligently.
        
        Args:
            filepath: Path to the PDF file
            
        Returns:
            Dictionary with suggested documents and processing summary
        """
        try:
            self.logger.info(f"🔄 Processing multi-invoice PDF: {filepath}")
            
            # Open PDF
            doc = fitz.open(filepath)
            pages_data = []
            
            # Process each page
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                
                # Convert page to image
                pix = page.get_pixmap(dpi=300)
                img_data = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_data))
                
                # Run OCR
                ocr_text = self._run_ocr(img)
                
                # Analyze page content
                page_info = self._analyze_page_content(ocr_text, page_num + 1)
                pages_data.append(page_info)
                
                self.logger.debug(f"Page {page_num + 1}: {page_info.get('confidence', 0):.1f}% confidence, "
                                f"{page_info.get('word_count', 0)} words")
            
            doc.close()
            
            # Group pages into invoices
            processed_documents = self._group_pages_into_invoices(pages_data)
            
            result = {
                "suggested_documents": processed_documents,
                "total_pages": len(pages_data),
                "processing_summary": {
                    "pages_processed": len(pages_data),
                    "invoices_found": len(processed_documents),
                    "skipped_pages": len([p for p in pages_data if p.get('skip_page', False)])
                }
            }
            
            self.logger.info(f"✅ Multi-invoice processing complete: {len(processed_documents)} documents found")
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Multi-invoice processing failed: {str(e)}")
            raise
    
    def _run_ocr(self, img: Image.Image) -> str:
        """
        Run OCR on an image using PaddleOCR.
        
        Args:
            img: PIL Image to process
            
        Returns:
            Extracted text as string
        """
        try:
            if ocr_model is None:
                self.logger.error("❌ PaddleOCR model not initialized")
                return ""
            
            self.logger.info(f"🔄 Starting PaddleOCR OCR")
            self.logger.debug(f"📊 Input image shape: {img.size}")
            
            # Run PaddleOCR
            result = ocr_model.predict(np.array(img))
            
            # Extract text
            text = ""
            line_count = 0
            
            if result and len(result) > 0:
                self.logger.debug(f"📊 PaddleOCR returned {len(result)} result groups")
                
                # Handle PaddleOCR result structure (list containing OCRResult object)
                if isinstance(result, (list, tuple)) and len(result) > 0:
                    ocr_result = result[0]  # Get the first (and usually only) result
                    
                    # Handle PaddleOCR result structure (OCRResult object)
                    if hasattr(ocr_result, 'rec_texts'):
                        rec_texts = ocr_result.rec_texts
                        self.logger.debug(f"📊 Found {len(rec_texts)} text items")
                        
                        for i, text_item in enumerate(rec_texts):
                            extracted_text = str(text_item)
                            text += extracted_text + " "
                            line_count += 1
                            self.logger.debug(f"   → Extracted: '{extracted_text}'")
            
            text = text.strip()
            word_count = len([word for word in text.split() if len(word) > 1])
            
            self.logger.info(f"✅ PaddleOCR completed: {word_count} words, {line_count} lines")
            self.logger.debug(f"📝 Final text: '{text[:100]}{'...' if len(text) > 100 else ''}'")
            
            return text
            
        except Exception as e:
            self.logger.error(f"❌ OCR failed: {str(e)}")
            return ""

    def _analyze_page_content(self, ocr_text: str, page_number: int) -> Dict[str, Any]:
        """
        Analyze a single page's content and return relevant metadata.
        """
        try:
            # Calculate text density (simplified approach)
            word_count = len(ocr_text.split())
            # Use a reasonable default for text density calculation
            estimated_pixels = 2000000  # Assume 2MP image
            text_density = word_count / (estimated_pixels / 1000000)  # words per megapixel
            
            # Skip pages with very low text density (likely blank or terms pages)
            if word_count < 10 or text_density < 50:
                return {
                    "page_number": page_number,
                    "skip_page": True,
                    "reason": "Low text density",
                    "word_count": word_count,
                    "text_density": text_density
                }
            
            # Extract metadata
            metadata = self._extract_page_metadata(ocr_text)
            
            # Determine document type
            doc_type = self._classify_document_type(ocr_text)
            
            # Check for invoice headers
            invoice_headers = self._detect_invoice_headers(ocr_text)
            
            # Calculate confidence based on metadata completeness
            confidence = self._calculate_page_confidence(metadata, doc_type, word_count)
            
            return {
                "page_number": page_number,
                "ocr_text": ocr_text,
                "word_count": word_count,
                "text_density": text_density,
                "skip_page": False,
                "document_type": doc_type,
                "confidence": confidence,
                "metadata": metadata,
                "invoice_headers": invoice_headers,
                "is_invoice_start": len(invoice_headers) > 0
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error analyzing page {page_number}: {str(e)}")
            return {
                "page_number": page_number,
                "skip_page": True,
                "reason": f"Processing error: {str(e)}",
                "error": str(e)
            }

    def _extract_page_metadata(self, ocr_text: str) -> Dict[str, Any]:
        """
        Extract key metadata from OCR text.
        """
        metadata = {
            "supplier_name": None,
            "invoice_number": None,
            "delivery_note_number": None,
            "invoice_date": None,
            "delivery_date": None,
            "total_amount": None
        }
        
        # Extract supplier name (look for common patterns)
        supplier_patterns = [
            r'(?:supplier|from|company|business):\s*([A-Za-z\s&\.]+)',
            r'^([A-Za-z\s&\.]+)\s*(?:Ltd|Limited|Inc|Corp|Company)',
            r'(?:Invoice|Delivery Note) from\s*([A-Za-z\s&\.]+)'
        ]
        
        for pattern in supplier_patterns:
            match = re.search(pattern, ocr_text, re.IGNORECASE)
            if match:
                supplier = match.group(1).strip()
                if len(supplier) > 2:  # Avoid very short matches
                    metadata["supplier_name"] = supplier
                    break
        
        # Extract invoice number
        invoice_patterns = [
            r'(?:invoice|inv)\.?\s*(?:no|number|#)?\.?\s*:?\s*([A-Za-z0-9\-_]+)',
            r'(?:invoice|inv)\.?\s*(?:no|number|#)?\.?\s*([A-Za-z0-9\-_]+)',
            r'([A-Za-z]{2,4}[-_]\d{6,8})',  # Common patterns like INV-123456
        ]
        
        for pattern in invoice_patterns:
            match = re.search(pattern, ocr_text, re.IGNORECASE)
            if match:
                metadata["invoice_number"] = match.group(1).strip()
                break
        
        # Extract delivery note number
        delivery_patterns = [
            r'(?:delivery note|dn)\.?\s*(?:no|number|#)?\.?\s*:?\s*([A-Za-z0-9\-_]+)',
            r'(?:delivery note|dn)\.?\s*(?:no|number|#)?\.?\s*([A-Za-z0-9\-_]+)',
        ]
        
        for pattern in delivery_patterns:
            match = re.search(pattern, ocr_text, re.IGNORECASE)
            if match:
                metadata["delivery_note_number"] = match.group(1).strip()
                break
        
        # Extract dates
        date_patterns = [
            r'(?:date|dated):\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(\d{4}-\d{2}-\d{2})',  # ISO format
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, ocr_text, re.IGNORECASE)
            if match:
                date_str = match.group(1)
                try:
                    # Try to parse and standardize the date
                    if '/' in date_str or '-' in date_str:
                        if len(date_str.split('/')[0]) == 4:  # YYYY/MM/DD
                            date_obj = datetime.strptime(date_str, '%Y/%m/%d')
                        elif len(date_str.split('/')[-1]) == 4:  # DD/MM/YYYY
                            date_obj = datetime.strptime(date_str, '%d/%m/%Y')
                        else:  # MM/DD/YYYY
                            date_obj = datetime.strptime(date_str, '%m/%d/%Y')
                    else:
                        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                    
                    metadata["invoice_date"] = date_obj.strftime('%Y-%m-%d')
                    break
                except ValueError:
                    continue
        
        # Extract total amount
        amount_patterns = [
            r'(?:total|amount|sum|due):\s*[£$€]?\s*([\d,]+\.?\d*)',
            r'[£$€]\s*([\d,]+\.?\d*)\s*(?:total|amount)',
            r'(?:grand total|final total):\s*[£$€]?\s*([\d,]+\.?\d*)',
        ]
        
        for pattern in amount_patterns:
            match = re.search(pattern, ocr_text, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(',', '')
                try:
                    metadata["total_amount"] = float(amount_str)
                    break
                except ValueError:
                    continue
        
        return metadata

    def _classify_document_type(self, ocr_text: str) -> str:
        """
        Classify the document type based on keywords.
        """
        text_lower = ocr_text.lower()
        
        # Count keyword matches
        invoice_score = sum(1 for keyword in self.invoice_keywords if keyword in text_lower)
        delivery_score = sum(1 for keyword in self.delivery_keywords if keyword in text_lower)
        utility_score = sum(1 for keyword in self.utility_keywords if keyword in text_lower)
        
        # Determine type based on highest score
        if utility_score > invoice_score and utility_score > delivery_score:
            return 'utility'
        elif delivery_score > invoice_score:
            return 'delivery_note'
        elif invoice_score > 0:
            return 'invoice'
        else:
            return 'unknown'

    def _detect_invoice_headers(self, ocr_text: str) -> List[str]:
        """
        Detect invoice headers that indicate the start of a new invoice.
        """
        headers = []
        text_lower = ocr_text.lower()
        
        for pattern in self.invoice_header_patterns:
            matches = re.finditer(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                headers.append(match.group(0))
        
        return headers

    def _calculate_page_confidence(self, metadata: Dict[str, Any], doc_type: str, word_count: int) -> float:
        """
        Calculate confidence score based on metadata completeness and document type.
        """
        base_confidence = 0.2
        
        # Boost confidence for good word count
        if word_count > 100:
            base_confidence += 0.3
        elif word_count > 50:
            base_confidence += 0.2
        elif word_count > 20:
            base_confidence += 0.1
        
        # Boost confidence for complete metadata
        metadata_fields = [metadata.get('supplier_name'), metadata.get('invoice_number'), 
                          metadata.get('invoice_date'), metadata.get('total_amount')]
        completed_fields = sum(1 for field in metadata_fields if field is not None)
        
        if completed_fields >= 3:
            base_confidence += 0.3
        elif completed_fields >= 2:
            base_confidence += 0.2
        elif completed_fields >= 1:
            base_confidence += 0.1
        
        # Boost confidence for clear document type
        if doc_type in ['invoice', 'delivery_note', 'utility']:
            base_confidence += 0.2
        
        return min(base_confidence, 1.0)

    def _group_pages_into_invoices(self, pages_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Group pages into logical invoice documents based on invoice headers and content.
        """
        documents = []
        current_group = []
        current_invoice_start = None
        
        for page_data in pages_data:
            if page_data.get('skip_page', False):
                continue
            
            # Check if this page starts a new invoice
            if page_data.get('is_invoice_start', False) and current_group:
                # Save current group as a document
                if current_group:
                    doc = self._create_document_from_group(current_group, current_invoice_start)
                    documents.append(doc)
                
                # Start new group
                current_group = [page_data]
                current_invoice_start = page_data.get('page_number')
            else:
                # Add to current group
                if not current_group:
                    current_invoice_start = page_data.get('page_number')
                current_group.append(page_data)
        
        # Don't forget the last group
        if current_group:
            doc = self._create_document_from_group(current_group, current_invoice_start)
            documents.append(doc)
        
        return documents

    def _process_invoice_group(self, group: Dict[str, Any], pages_data: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Process a group of pages as a single invoice and extract full metadata.
        """
        try:
            page_numbers = group.get('pages', [])
            if not page_numbers:
                return None
            
            # Combine OCR text from all pages in the group
            combined_ocr = ""
            for page_num in page_numbers:
                page_data = next((p for p in pages_data if p.get('page_number') == page_num), None)
                if page_data and not page_data.get('skip_page', False):
                    combined_ocr += page_data.get('ocr_text', '') + "\n"
            
            if not combined_ocr.strip():
                return None
            
            # Extract full invoice metadata
            from ocr.parse_invoice import parse_invoice_text
            parsed_data = parse_invoice_text(combined_ocr)
            
            # Validate that this is actually an invoice
            if not self._is_valid_invoice(parsed_data, combined_ocr):
                return None
            
            # Create the invoice document
            invoice_doc = {
                "id": str(uuid.uuid4()),
                "type": "invoice",
                "pages": page_numbers,
                "confidence": group.get('confidence', 0.5),
                "supplier_name": parsed_data.get('supplier_name', 'Unknown'),
                "metadata": {
                    "invoice_number": parsed_data.get('invoice_number'),
                    "invoice_date": parsed_data.get('invoice_date'),
                    "total_amount": parsed_data.get('total_amount'),
                    "subtotal": parsed_data.get('subtotal'),
                    "vat": parsed_data.get('vat'),
                    "vat_rate": parsed_data.get('vat_rate'),
                    "total_incl_vat": parsed_data.get('total_incl_vat')
                },
                "line_items": parsed_data.get('line_items', []),
                "ocr_text": combined_ocr,
                "word_count": len(combined_ocr.split()),
                "preview_urls": []  # Would be populated with actual preview images
            }
            
            return invoice_doc
            
        except Exception as e:
            self.logger.error(f"❌ Error processing invoice group: {str(e)}")
            return None

    def _is_valid_invoice(self, parsed_data: Dict[str, Any], ocr_text: str) -> bool:
        """
        Validate that the parsed data represents a valid invoice.
        """
        # Check for minimum required fields
        has_invoice_number = parsed_data.get('invoice_number') and parsed_data.get('invoice_number') != 'Unknown'
        has_supplier = parsed_data.get('supplier_name') and parsed_data.get('supplier_name') != 'Unknown'
        has_total = parsed_data.get('total_amount') and parsed_data.get('total_amount') > 0
        
        # Check for minimum word count (filter out irrelevant pages)
        word_count = len(ocr_text.split())
        has_sufficient_content = word_count >= 30
        
        # Check for invoice keywords
        text_lower = ocr_text.lower()
        has_invoice_keywords = any(keyword in text_lower for keyword in self.invoice_keywords)
        
        # Must have at least 2 out of 3 required fields and sufficient content
        required_fields = sum([has_invoice_number, has_supplier, has_total])
        return required_fields >= 2 and has_sufficient_content and has_invoice_keywords

    def _create_document_from_group(self, group: List[Dict[str, Any]], invoice_start: Optional[int]) -> Dict[str, Any]:
        """
        Create a document object from a group of pages.
        """
        if not group:
            return {}
        
        # Get the best metadata from the group
        metadata = self._get_best_metadata_from_group(group)
        
        # Determine the primary document type
        doc_types = [p.get('document_type') for p in group]
        primary_type = max(set(doc_types), key=doc_types.count) if doc_types else 'unknown'
        
        # Calculate average confidence
        confidences = [p.get('confidence', 0) for p in group]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        # Get page numbers
        page_numbers = [p.get('page_number') for p in group]
        
        return {
            "type": primary_type,
            "pages": page_numbers,
            "confidence": round(avg_confidence, 2),
            "supplier_name": metadata.get('supplier_name', 'Unknown'),
            "invoice_start": invoice_start
        }

    def _get_best_metadata_from_group(self, group: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get the most complete metadata from a group of pages.
        """
        best_metadata = {}
        best_score = 0
        
        for page in group:
            metadata = page.get('metadata', {})
            score = sum(1 for v in metadata.values() if v is not None)
            
            if score > best_score:
                best_score = score
                best_metadata = metadata
        
        return best_metadata 