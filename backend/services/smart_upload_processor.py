import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)

# Classification keywords
DOCUMENT_KEYWORDS = {
    'invoice': [
        'invoice', 'tax total', 'vat', 'subtotal', 'net', 'invoice number', 
        'invoice date', 'total amount', 'amount due', 'payment terms'
    ],
    'delivery_note': [
        'delivery note', 'goods received', 'pod', 'driver', 'delivery date',
        'delivery number', 'packing list', 'shipping note'
    ],
    'utility': [
        'energy', 'kwh', 'standing charge', 'edf', 'gas', 'electricity',
        'utility bill', 'energy bill', 'meter reading', 'consumption'
    ],
    'receipt': [
        'thank you', 'receipt', 'cash tendered', 'pos', 'transaction',
        'payment received', 'sale receipt'
    ]
}

class SmartUploadProcessor:
    def __init__(self, temp_dir: str = "temp", previews_dir: str = "data/previews"):
        self.temp_dir = Path(temp_dir)
        self.previews_dir = Path(previews_dir)
        self.temp_dir.mkdir(exist_ok=True)
        self.previews_dir.mkdir(parents=True, exist_ok=True)
    
    def process_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        Main processing function that orchestrates the entire pipeline
        """
        try:
            # Step 1: Split PDF into pages
            pages = self._split_pdf(pdf_path)
            
            # Step 2: Process each page
            processed_pages = []
            for page_num, page_data in enumerate(pages, 1):
                processed_page = self._process_page(page_data, page_num)
                processed_pages.append(processed_page)
            
            # Step 3: Group pages into documents
            suggested_documents = self._group_pages_into_documents(processed_pages)
            
            return {
                "suggested_documents": suggested_documents
            }
            
        except Exception as e:
            logger.error(f"Error processing PDF {pdf_path}: {str(e)}")
            raise
    
    def _split_pdf(self, pdf_path: str) -> List[Tuple[int, bytes]]:
        """
        Split PDF into individual pages and return as bytes
        """
        pages = []
        try:
            doc = fitz.open(pdf_path)
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                # Convert page to image
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better quality
                img_data = pix.tobytes("png")
                pages.append((page_num + 1, img_data))
            doc.close()
            return pages
        except Exception as e:
            logger.error(f"Error splitting PDF: {str(e)}")
            raise
    
    def _process_page(self, page_data: Tuple[int, bytes], page_num: int) -> Dict[str, Any]:
        """
        Process a single page: OCR, classification, metadata extraction
        """
        page_num, img_data = page_data
        
        try:
            # Convert bytes to PIL Image
            img = Image.open(io.BytesIO(img_data))
            
            # Run OCR
            ocr_text = self._run_ocr(img)
            
            # Classify document type
            doc_type, confidence = self._classify_document(ocr_text)
            
            # Extract metadata
            metadata = self._extract_metadata(ocr_text, doc_type)
            
            # Generate preview image
            preview_url = self._save_preview_image(img, page_num)
            
            return {
                "page_num": page_num,
                "ocr_text": ocr_text,
                "doc_type": doc_type,
                "confidence": confidence,
                "metadata": metadata,
                "preview_url": preview_url
            }
            
        except Exception as e:
            logger.error(f"Error processing page {page_num}: {str(e)}")
            return {
                "page_num": page_num,
                "ocr_text": "",
                "doc_type": "unknown",
                "confidence": 0,
                "metadata": {},
                "preview_url": ""
            }
    
    def _run_ocr(self, img: Image.Image) -> str:
        """
        Run Tesseract OCR on the image
        """
        try:
            # Configure Tesseract for better accuracy
            custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,£$€@#%&*()_+-=[]{}|;:"\'<>?/ '
            text = pytesseract.image_to_string(img, config=custom_config)
            return text.lower()
        except Exception as e:
            logger.error(f"OCR error: {str(e)}")
            return ""
    
    def _classify_document(self, text: str) -> Tuple[str, int]:
        """
        Classify document type based on keywords and return confidence score
        """
        scores = {}
        
        for doc_type, keywords in DOCUMENT_KEYWORDS.items():
            score = 0
            for keyword in keywords:
                if keyword in text:
                    score += 1
            
            # Normalize score based on number of keywords found
            if score > 0:
                scores[doc_type] = min(100, (score / len(keywords)) * 100)
            else:
                scores[doc_type] = 0
        
        if not scores or max(scores.values()) < 30:
            return "unknown", 0
        
        best_type = max(scores, key=scores.get)
        confidence = int(scores[best_type])
        
        return best_type, confidence
    
    def _extract_metadata(self, text: str, doc_type: str) -> Dict[str, Any]:
        """
        Extract metadata based on document type
        """
        metadata = {}
        
        try:
            # Extract supplier name (look for common patterns)
            supplier_patterns = [
                r'from:\s*([A-Za-z\s&]+)',
                r'supplier:\s*([A-Za-z\s&]+)',
                r'company:\s*([A-Za-z\s&]+)',
                r'([A-Z][A-Za-z\s&]{3,20})\s*invoice',
                r'([A-Z][A-Za-z\s&]{3,20})\s*delivery'
            ]
            
            for pattern in supplier_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    supplier = match.group(1).strip()
                    if len(supplier) > 2:  # Filter out very short matches
                        metadata['supplier_name'] = supplier
                        break
            
            # Extract dates
            date_patterns = [
                r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                r'(\d{4}-\d{2}-\d{2})',
                r'(\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{2,4})'
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    metadata['invoice_date'] = match.group(1)
                    break
            
            # Extract amounts
            amount_patterns = [
                r'total[:\s]*£?([\d,]+\.?\d*)',
                r'amount[:\s]*£?([\d,]+\.?\d*)',
                r'£([\d,]+\.?\d*)',
                r'([\d,]+\.?\d*)\s*gbp'
            ]
            
            for pattern in amount_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    amount_str = match.group(1).replace(',', '')
                    try:
                        amount = float(amount_str)
                        metadata['total_amount'] = amount
                        break
                    except ValueError:
                        continue
            
            # Extract invoice/delivery note numbers
            if doc_type == 'invoice':
                invoice_patterns = [
                    r'invoice[:\s]*#?\s*([A-Z0-9-]+)',
                    r'inv[:\s]*#?\s*([A-Z0-9-]+)',
                    r'([A-Z]{2,4}-\d{6,})'
                ]
                
                for pattern in invoice_patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        metadata['invoice_number'] = match.group(1).strip()
                        break
            
            elif doc_type == 'delivery_note':
                dn_patterns = [
                    r'delivery[:\s]*#?\s*([A-Z0-9-]+)',
                    r'dn[:\s]*#?\s*([A-Z0-9-]+)',
                    r'([A-Z]{2,4}-\d{6,})'
                ]
                
                for pattern in dn_patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        metadata['delivery_note_number'] = match.group(1).strip()
                        break
            
        except Exception as e:
            logger.error(f"Error extracting metadata: {str(e)}")
        
        return metadata
    
    def _save_preview_image(self, img: Image.Image, page_num: int) -> str:
        """
        Save preview image and return URL
        """
        try:
            # Generate unique filename
            doc_id = str(uuid.uuid4())[:8]
            filename = f"doc_{doc_id}_page{page_num}.jpg"
            filepath = self.previews_dir / filename
            
            # Resize image for preview (max 800px width)
            img.thumbnail((800, 1000), Image.Resampling.LANCZOS)
            
            # Save as JPEG
            img.save(filepath, "JPEG", quality=85)
            
            # Return relative URL
            return f"/previews/{filename}"
            
        except Exception as e:
            logger.error(f"Error saving preview image: {str(e)}")
            return ""
    
    def _group_pages_into_documents(self, processed_pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Group consecutive pages with same type and supplier into logical documents
        """
        documents = []
        current_doc = None
        
        for page in processed_pages:
            # Skip pages with very low confidence
            if page['confidence'] < 20:
                continue
            
            # If no current document, start a new one
            if current_doc is None:
                current_doc = {
                    "id": f"doc_{str(uuid.uuid4())[:8]}",
                    "type": page['doc_type'],
                    "confidence": page['confidence'],
                    "supplier_name": page['metadata'].get('supplier_name', 'Unknown Supplier'),
                    "pages": [page['page_num']],
                    "preview_urls": [page['preview_url']],
                    "metadata": page['metadata']
                }
            else:
                # Check if this page belongs to the same document
                same_type = page['doc_type'] == current_doc['type']
                same_supplier = (
                    page['metadata'].get('supplier_name', '') == current_doc['supplier_name'] or
                    page['metadata'].get('supplier_name', '') == 'Unknown Supplier' or
                    current_doc['supplier_name'] == 'Unknown Supplier'
                )
                consecutive_page = page['page_num'] == current_doc['pages'][-1] + 1
                
                # Group if same type and supplier, and pages are consecutive
                if same_type and (same_supplier or consecutive_page):
                    current_doc['pages'].append(page['page_num'])
                    current_doc['preview_urls'].append(page['preview_url'])
                    
                    # Update confidence (average)
                    current_doc['confidence'] = int(
                        (current_doc['confidence'] + page['confidence']) / 2
                    )
                    
                    # Merge metadata (prefer non-empty values)
                    for key, value in page['metadata'].items():
                        if value and not current_doc['metadata'].get(key):
                            current_doc['metadata'][key] = value
                else:
                    # Save current document and start a new one
                    documents.append(current_doc)
                    current_doc = {
                        "id": f"doc_{str(uuid.uuid4())[:8]}",
                        "type": page['doc_type'],
                        "confidence": page['confidence'],
                        "supplier_name": page['metadata'].get('supplier_name', 'Unknown Supplier'),
                        "pages": [page['page_num']],
                        "preview_urls": [page['preview_url']],
                        "metadata": page['metadata']
                    }
        
        # Add the last document if exists
        if current_doc:
            documents.append(current_doc)
        
        return documents 