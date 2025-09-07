# backend/services/document_classifier.py
"""
Document classification service for determining document types
"""

import re
import logging
from typing import Dict, Any, Optional
from db_manager_unified import get_db_manager

logger = logging.getLogger(__name__)

# Get unified database manager
db_manager = get_db_manager()

class DocumentClassifier:
    """Classifies documents as invoice, delivery note, or other"""
    
    # Keywords that indicate delivery notes
    DELIVERY_NOTE_KEYWORDS = [
        'delivery note', 'dn', 'goods delivered', 'signed for', 'received by',
        'delivery receipt', 'goods received', 'delivery confirmation',
        'delivered to', 'delivery date', 'delivery address'
    ]
    
    # Keywords that indicate invoices
    INVOICE_KEYWORDS = [
        'invoice', 'bill', 'statement', 'amount due', 'payment terms',
        'total amount', 'subtotal', 'tax', 'vat', 'balance due',
        'please pay', 'payment due', 'invoice number'
    ]
    
    @staticmethod
    def classify_document(ocr_text: str, filename: str = "") -> str:
        """
        Classify document based on OCR text and filename
        
        Returns: 'invoice', 'delivery_note', or 'other'
        """
        if not ocr_text:
            return 'other'
        
        # Normalize text for analysis
        text_lower = ocr_text.lower()
        
        # Count keyword matches
        delivery_score = 0
        invoice_score = 0
        
        # Check for delivery note keywords
        for keyword in DocumentClassifier.DELIVERY_NOTE_KEYWORDS:
            if keyword in text_lower:
                delivery_score += 1
        
        # Check for invoice keywords  
        for keyword in DocumentClassifier.INVOICE_KEYWORDS:
            if keyword in text_lower:
                invoice_score += 1
        
        # Additional heuristics
        if 'delivery note' in text_lower or 'dn' in text_lower:
            delivery_score += 2
        
        if 'invoice' in text_lower:
            invoice_score += 2
        
        # Check filename patterns
        if filename:
            filename_lower = filename.lower()
            if 'delivery' in filename_lower or 'dn' in filename_lower:
                delivery_score += 1
            if 'invoice' in filename_lower or 'inv' in filename_lower:
                invoice_score += 1
        
        # Decision logic
        if delivery_score >= 2 and delivery_score > invoice_score:
            return 'delivery_note'
        elif invoice_score >= 2 and invoice_score > delivery_score:
            return 'invoice'
        else:
            return 'other'
    
    @staticmethod
    def update_document_type(doc_id: str, doc_type: str, table: str = 'invoices') -> bool:
        """
        Update document type in database
        
        Args:
            doc_id: Document ID
            doc_type: 'invoice', 'delivery_note', or 'other'
            table: 'invoices' or 'delivery_notes'
        """
        try:
            with db_manager.get_connection() as conn:
                conn.execute(f"""
                    UPDATE {table} 
                    SET doc_type = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (doc_type, doc_id))
                conn.commit()
                
                logger.info(f"Updated {table} {doc_id} doc_type to {doc_type}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to update document type: {e}")
            return False
    
    @staticmethod
    def classify_and_update(doc_id: str, ocr_text: str, filename: str = "", table: str = 'invoices') -> str:
        """
        Classify document and update database
        
        Returns: The determined document type
        """
        doc_type = DocumentClassifier.classify_document(ocr_text, filename)
        DocumentClassifier.update_document_type(doc_id, doc_type, table)
        return doc_type 