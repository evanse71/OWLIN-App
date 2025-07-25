import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io
import re
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import os

logger = logging.getLogger(__name__)

class SmartUploadProcessor:
    def __init__(self):
        self.invoice_keywords = [
            'invoice', 'tax', 'total', 'vat', 'subtotal', 'net', 'amount due',
            'invoice number', 'invoice date', 'supplier', 'payment'
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
        Process a PDF that may contain multiple invoices and intelligently split them.
        """
        try:
            # Open the PDF
            doc = fitz.open(filepath)
            pages_data = []
            
            # Process each page individually
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                page_data = self._process_single_page(page, page_num + 1)
                pages_data.append(page_data)
            
            doc.close()
            
            # Group pages into logical documents
            grouped_documents = self._group_pages_into_documents(pages_data)
            
            return {
                "suggested_documents": grouped_documents,
                "total_pages": len(pages_data),
                "processing_summary": {
                    "pages_processed": len(pages_data),
                    "documents_found": len(grouped_documents),
                    "skipped_pages": len([p for p in pages_data if p.get('skip_page', False)])
                }
            }
            
        except Exception as e:
            logger.error(f"Error processing multi-invoice PDF {filepath}: {str(e)}")
            raise

    def _process_single_page(self, page, page_number: int) -> Dict[str, Any]:
        """
        Process a single page and extract metadata.
        """
        try:
            # Get page image
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # Higher resolution for better OCR
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            
            # Run OCR
            ocr_text = pytesseract.image_to_string(img)
            
            # Calculate text density
            word_count = len(ocr_text.split())
            text_density = word_count / (pix.width * pix.height / 1000000)  # words per megapixel
            
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
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"Error processing page {page_number}: {str(e)}")
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

    def _group_pages_into_documents(self, pages_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Group pages into logical documents based on metadata similarity.
        """
        documents = []
        current_group = []
        
        for page_data in pages_data:
            if page_data.get('skip_page', False):
                continue
            
            # If this is the first page or metadata is similar to current group
            if not current_group or self._should_group_with_current(page_data, current_group):
                current_group.append(page_data)
            else:
                # Create document from current group
                if current_group:
                    doc = self._create_document_from_group(current_group)
                    documents.append(doc)
                
                # Start new group
                current_group = [page_data]
        
        # Don't forget the last group
        if current_group:
            doc = self._create_document_from_group(current_group)
            documents.append(doc)
        
        return documents

    def _should_group_with_current(self, page_data: Dict[str, Any], current_group: List[Dict[str, Any]]) -> bool:
        """
        Determine if a page should be grouped with the current document group.
        """
        if not current_group:
            return True
        
        # Get metadata from current group (use the most complete one)
        current_metadata = self._get_best_metadata_from_group(current_group)
        new_metadata = page_data.get('metadata', {})
        
        # Check if supplier names match
        if (current_metadata.get('supplier_name') and 
            new_metadata.get('supplier_name') and
            current_metadata['supplier_name'].lower() != new_metadata['supplier_name'].lower()):
            return False
        
        # Check if invoice numbers match (for invoices)
        if (current_metadata.get('invoice_number') and 
            new_metadata.get('invoice_number') and
            current_metadata['invoice_number'] != new_metadata['invoice_number']):
            return False
        
        # Check if document types are compatible
        current_types = [p.get('document_type') for p in current_group]
        new_type = page_data.get('document_type')
        
        # If types are different, don't group (except for unknown types)
        if new_type != 'unknown' and 'unknown' not in current_types:
            if new_type not in current_types:
                return False
        
        return True

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

    def _create_document_from_group(self, group: List[Dict[str, Any]]) -> Dict[str, Any]:
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
        
        # Generate a unique ID
        import uuid
        doc_id = str(uuid.uuid4())
        
        return {
            "id": doc_id,
            "type": primary_type,
            "pages": page_numbers,
            "confidence": round(avg_confidence, 2),
            "supplier_name": metadata.get('supplier_name', 'Unknown'),
            "preview_urls": [],  # Would be populated with actual preview images
            "metadata": {
                "invoice_number": metadata.get('invoice_number'),
                "delivery_note_number": metadata.get('delivery_note_number'),
                "invoice_date": metadata.get('invoice_date'),
                "delivery_date": metadata.get('delivery_date'),
                "total_amount": metadata.get('total_amount')
            }
        } 