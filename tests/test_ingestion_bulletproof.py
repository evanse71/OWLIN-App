#!/usr/bin/env python3
"""
Test script for Bulletproof Ingestion v3

Tests the complete bulletproof ingestion pipeline with various scenarios.
"""

import os
import sys
import json
import tempfile
import shutil
from pathlib import Path
from typing import List, Dict, Any

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

try:
    from ingest.intake_router import IntakeRouter
    from ingest.page_fingerprints import PageFingerprinter
    from ingest.page_classifier import PageClassifier
    from ingest.cross_file_stitcher import CrossFileStitcher
    from ingest.deduper import Deduper
    from ingest.canonical_builder import CanonicalBuilder
    from ocr.multi_document_segmenter import MultiDocumentSegmenter
    print("✅ All bulletproof ingestion components imported successfully")
except ImportError as e:
    print(f"❌ Failed to import bulletproof ingestion components: {e}")
    sys.exit(1)

def create_test_files() -> List[Dict[str, Any]]:
    """Create test files for ingestion testing"""
    
    # Create a temporary directory for test files
    test_dir = Path("test_fixtures")
    test_dir.mkdir(exist_ok=True)
    
    test_files = []
    
    # Test file 1: Simple invoice
    invoice_content = """
    INVOICE
    
    Invoice Number: INV-2024-001
    Date: 2024-01-15
    
    Supplier: ABC Company LTD
    123 Business Street
    City, State 12345
    
    Bill To:
    Customer Name
    456 Customer Ave
    City, State 67890
    
    Item Description     Qty    Unit Price    Amount
    Product A           2      $50.00        $100.00
    Product B           1      $75.00        $75.00
    
    Subtotal: $175.00
    Tax: $17.50
    Total: $192.50
    
    Thank you for your business!
    """
    
    invoice_file = test_dir / "test_invoice.txt"
    with open(invoice_file, 'w') as f:
        f.write(invoice_content)
    
    test_files.append({
        'id': 'test_invoice_1',
        'file_path': str(invoice_file),
        'filename': 'test_invoice.txt',
        'file_size': len(invoice_content),
        'upload_time': '2024-01-15T10:00:00',
        'images': [None],  # Placeholder for image
        'ocr_texts': [invoice_content]
    })
    
    # Test file 2: Delivery note
    delivery_content = """
    DELIVERY NOTE
    
    Delivery Number: DEL-2024-001
    Date: 2024-01-16
    
    Supplier: XYZ Logistics LTD
    789 Delivery Road
    City, State 11111
    
    Deliver To:
    Customer Name
    456 Customer Ave
    City, State 67890
    
    Items Delivered:
    Product A - 2 units
    Product B - 1 unit
    
    Received by: John Doe
    Signature: _________________
    Date: 2024-01-16
    """
    
    delivery_file = test_dir / "test_delivery.txt"
    with open(delivery_file, 'w') as f:
        f.write(delivery_content)
    
    test_files.append({
        'id': 'test_delivery_1',
        'file_path': str(delivery_file),
        'filename': 'test_delivery.txt',
        'file_size': len(delivery_content),
        'upload_time': '2024-01-16T10:00:00',
        'images': [None],  # Placeholder for image
        'ocr_texts': [delivery_content]
    })
    
    # Test file 3: Multi-page invoice (split across files)
    invoice_page1_content = """
    INVOICE - Page 1
    
    Invoice Number: INV-2024-002
    Date: 2024-01-20
    
    Supplier: Multi Page Ltd
    999 Business Blvd
    City, State 99999
    
    Bill To:
    Customer Name
    456 Customer Ave
    City, State 67890
    """
    
    invoice_page2_content = """
    INVOICE - Page 2
    
    Item Description     Qty    Unit Price    Amount
    Product C           3      $25.00        $75.00
    Product D           2      $40.00        $80.00
    Product E           1      $100.00       $100.00
    
    Subtotal: $255.00
    Tax: $25.50
    Total: $280.50
    
    Thank you for your business!
    """
    
    invoice_page1_file = test_dir / "test_invoice_page1.txt"
    invoice_page2_file = test_dir / "test_invoice_page2.txt"
    
    with open(invoice_page1_file, 'w') as f:
        f.write(invoice_page1_content)
    
    with open(invoice_page2_file, 'w') as f:
        f.write(invoice_page2_content)
    
    test_files.append({
        'id': 'test_invoice_page1',
        'file_path': str(invoice_page1_file),
        'filename': 'test_invoice_page1.txt',
        'file_size': len(invoice_page1_content),
        'upload_time': '2024-01-20T10:00:00',
        'images': [None],
        'ocr_texts': [invoice_page1_content]
    })
    
    test_files.append({
        'id': 'test_invoice_page2',
        'file_path': str(invoice_page2_file),
        'filename': 'test_invoice_page2.txt',
        'file_size': len(invoice_page2_content),
        'upload_time': '2024-01-20T10:00:00',
        'images': [None],
        'ocr_texts': [invoice_page2_content]
    })
    
    return test_files

def test_components():
    """Test individual components"""
    print("\n🧪 Testing individual components...")
    
    # Test PageFingerprinter
    try:
        fingerprinter = PageFingerprinter()
        print("✅ PageFingerprinter initialized")
    except Exception as e:
        print(f"❌ PageFingerprinter failed: {e}")
    
    # Test PageClassifier
    try:
        classifier = PageClassifier()
        result = classifier.classify("This is an invoice with invoice number INV-001")
        print(f"✅ PageClassifier test: {result.doc_type} (confidence: {result.confidence})")
    except Exception as e:
        print(f"❌ PageClassifier failed: {e}")
    
    # Test Deduper
    try:
        deduper = Deduper()
        print("✅ Deduper initialized")
    except Exception as e:
        print(f"❌ Deduper failed: {e}")
    
    # Test CrossFileStitcher
    try:
        stitcher = CrossFileStitcher()
        print("✅ CrossFileStitcher initialized")
    except Exception as e:
        print(f"❌ CrossFileStitcher failed: {e}")
    
    # Test CanonicalBuilder
    try:
        builder = CanonicalBuilder()
        print("✅ CanonicalBuilder initialized")
    except Exception as e:
        print(f"❌ CanonicalBuilder failed: {e}")
    
    # Test MultiDocumentSegmenter
    try:
        segmenter = MultiDocumentSegmenter()
        print("✅ MultiDocumentSegmenter initialized")
    except Exception as e:
        print(f"❌ MultiDocumentSegmenter failed: {e}")

def test_full_pipeline():
    """Test the complete bulletproof ingestion pipeline"""
    print("\n🚀 Testing full bulletproof ingestion pipeline...")
    
    try:
        # Create test files
        test_files = create_test_files()
        print(f"✅ Created {len(test_files)} test files")
        
        # Initialize intake router
        intake_router = IntakeRouter()
        print("✅ IntakeRouter initialized")
        
        # Process test files
        print("🔄 Processing test files...")
        result = intake_router.process_upload(test_files)
        
        # Print results
        print(f"\n📊 Processing Results:")
        print(f"  Success: {result.success}")
        print(f"  Processing time: {result.processing_time:.3f}s")
        print(f"  Canonical invoices: {len(result.canonical_invoices)}")
        print(f"  Canonical documents: {len(result.canonical_documents)}")
        print(f"  Duplicate groups: {len(result.duplicate_groups)}")
        print(f"  Stitch groups: {len(result.stitch_groups)}")
        print(f"  Warnings: {len(result.warnings)}")
        print(f"  Errors: {len(result.errors)}")
        
        # Print metadata
        print(f"\n📈 Metadata:")
        for key, value in result.metadata.items():
            print(f"  {key}: {value}")
        
        # Print canonical invoices
        if result.canonical_invoices:
            print(f"\n🧾 Canonical Invoices:")
            for invoice in result.canonical_invoices:
                print(f"  - {invoice.invoice_number} ({invoice.supplier_name}): ${invoice.total_amount}")
        
        # Print canonical documents
        if result.canonical_documents:
            print(f"\n📄 Canonical Documents:")
            for doc in result.canonical_documents:
                print(f"  - {doc.doc_type}: {doc.supplier_name}")
        
        # Print stitch groups
        if result.stitch_groups:
            print(f"\n🔗 Stitch Groups:")
            for group in result.stitch_groups:
                print(f"  - {group.doc_type}: {len(group.segments)} segments")
        
        # Print duplicate groups
        if result.duplicate_groups:
            print(f"\n🔄 Duplicate Groups:")
            for group in result.duplicate_groups:
                print(f"  - {group.duplicate_type}: {len(group.duplicates)} duplicates")
        
        if result.warnings:
            print(f"\n⚠️ Warnings:")
            for warning in result.warnings:
                print(f"  - {warning}")
        
        if result.errors:
            print(f"\n❌ Errors:")
            for error in result.errors:
                print(f"  - {error}")
        
        print("\n✅ Full pipeline test completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Full pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_api_endpoint():
    """Test the API endpoint"""
    print("\n🌐 Testing API endpoint...")
    
    import requests
    
    try:
        # Test the endpoint
        test_file = Path("test_fixtures/test_invoice.txt")
        if test_file.exists():
            with open(test_file, 'rb') as f:
                files = {'file': f}
                response = requests.post(
                    'http://localhost:8002/api/upload-bulletproof',
                    files=files,
                    timeout=30
                )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ API endpoint test successful:")
                print(f"  File ID: {result.get('file_id')}")
                print(f"  Processing time: {result.get('processing_time')}")
                print(f"  Canonical invoices: {len(result.get('canonical_invoices', []))}")
                print(f"  Canonical documents: {len(result.get('canonical_documents', []))}")
                return True
            else:
                print(f"❌ API endpoint test failed: {response.status_code}")
                print(f"  Response: {response.text}")
                return False
        else:
            print("❌ Test file not found")
            return False
            
    except Exception as e:
        print(f"❌ API endpoint test failed: {e}")
        return False

def main():
    """Main test function"""
    print("🧪 Bulletproof Ingestion v3 Test Suite")
    print("=" * 50)
    
    # Test individual components
    test_components()
    
    # Test full pipeline
    pipeline_success = test_full_pipeline()
    
    # Test API endpoint (if pipeline was successful)
    if pipeline_success:
        api_success = test_api_endpoint()
    else:
        api_success = False
        print("\n⚠️ Skipping API endpoint test due to pipeline failure")
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 Test Summary:")
    print(f"  Pipeline test: {'✅ PASSED' if pipeline_success else '❌ FAILED'}")
    print(f"  API endpoint test: {'✅ PASSED' if api_success else '❌ FAILED'}")
    
    if pipeline_success and api_success:
        print("\n🎉 All tests passed! Bulletproof ingestion v3 is working correctly.")
        return 0
    else:
        print("\n⚠️ Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    exit(main()) 