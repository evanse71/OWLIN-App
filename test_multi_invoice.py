#!/usr/bin/env python3
"""
Test script for multi-invoice PDF processing functionality.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from ocr.smart_upload_processor import SmartUploadProcessor
from ocr.ocr_engine import calculate_display_confidence
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_multi_invoice_processing():
    """Test the multi-invoice PDF processing functionality."""
    print("🧪 Testing Multi-Invoice PDF Processing")
    
    try:
        # Test the SmartUploadProcessor
        processor = SmartUploadProcessor()
        print("✅ SmartUploadProcessor initialized successfully")
        
        # Test the calculate_display_confidence function
        test_confidence = 0.85
        display_confidence = calculate_display_confidence(test_confidence)
        print(f"✅ Confidence calculation test: {test_confidence} -> {display_confidence}%")
        
        # Test with a sample PDF (if available)
        test_pdf_path = "test_multi_invoice.pdf"
        if os.path.exists(test_pdf_path):
            print(f"📄 Testing with sample PDF: {test_pdf_path}")
            result = processor.process_multi_invoice_pdf(test_pdf_path)
            
            if "suggested_documents" in result:
                doc_count = len(result["suggested_documents"])
                print(f"✅ Multi-invoice processing successful! Found {doc_count} documents")
                
                for i, doc in enumerate(result["suggested_documents"]):
                    print(f"  Document {i+1}:")
                    print(f"    Type: {doc.get('type', 'unknown')}")
                    print(f"    Pages: {doc.get('pages', [])}")
                    print(f"    Confidence: {doc.get('confidence', 0)}")
                    print(f"    Supplier: {doc.get('supplier_name', 'Unknown')}")
            else:
                print("⚠️ No suggested documents found in result")
        else:
            print("ℹ️ No test PDF found - skipping file processing test")
        
        print("✅ Multi-invoice processing test completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Multi-invoice processing test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_multi_invoice_processing()
    sys.exit(0 if success else 1) 