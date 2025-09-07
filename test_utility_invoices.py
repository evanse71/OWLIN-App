#!/usr/bin/env python3
"""
Test script for utility invoice classification and multi-invoice PDF support
"""

import asyncio
import tempfile
import os
from pathlib import Path
from fastapi import UploadFile
import io
import json

async def test_utility_invoice_classification():
    """Test utility invoice classification"""
    
    print("🧪 Testing Utility Invoice Classification")
    print("=" * 50)
    
    try:
        # Import the classification function
        from backend.routes.ocr import classify_utility_invoice
        print("✅ Utility classification function imported successfully")
        
        # Test cases
        test_cases = [
            {
                "name": "British Gas Invoice",
                "supplier": "British Gas",
                "text": "British Gas Energy Bill\nInvoice Number: BG123456\nTotal Amount: £89.50\nService period: January 2024",
                "expected": True
            },
            {
                "name": "EDF Energy Invoice",
                "supplier": "EDF Energy",
                "text": "EDF Energy\nElectricity Bill\nInvoice Date: 15/01/2024\nAmount Due: £67.30",
                "expected": True
            },
            {
                "name": "Fresh Foods Ltd Invoice",
                "supplier": "Fresh Foods Ltd",
                "text": "Fresh Foods Ltd\nInvoice Number: FF789\nDelivery Date: 20/01/2024\nItems: Tomatoes, Bread, Milk\nTotal: £45.20",
                "expected": False
            },
            {
                "name": "BT Internet Bill",
                "supplier": "BT",
                "text": "BT Internet Services\nBroadband Bill\nMonthly subscription: £29.99\nTotal: £29.99",
                "expected": True
            },
            {
                "name": "Insurance Premium",
                "supplier": "Aviva Insurance",
                "text": "Aviva Insurance\nPolicy Premium\nInsurance coverage for business\nPremium amount: £150.00",
                "expected": True
            }
        ]
        
        for test_case in test_cases:
            print(f"\n🔍 Testing: {test_case['name']}")
            result = classify_utility_invoice(test_case['supplier'], test_case['text'])
            expected = test_case['expected']
            
            if result == expected:
                print(f"✅ PASS: Expected {expected}, Got {result}")
            else:
                print(f"❌ FAIL: Expected {expected}, Got {result}")
                
    except Exception as e:
        print(f"❌ Utility classification test failed: {str(e)}")
        import traceback
        print(f"❌ Full traceback: {traceback.format_exc()}")

async def test_multi_invoice_detection():
    """Test multi-invoice PDF detection"""
    
    print("\n🧪 Testing Multi-Invoice PDF Detection")
    print("=" * 50)
    
    try:
        # Import the detection function
        from backend.routes.ocr import detect_multiple_invoices
        print("✅ Multi-invoice detection function imported successfully")
        
        # Mock page results
        mock_page_results = [
            {
                'page': 1,
                'lines': [
                    'British Gas Energy',
                    'Invoice Number: BG001',
                    'Invoice Date: 15/01/2024',
                    'Total Amount: £89.50',
                    'Service period: January 2024'
                ],
                'confidence': 0.85
            },
            {
                'page': 2,
                'lines': [
                    'EDF Energy',
                    'Invoice Number: EDF002',
                    'Invoice Date: 20/01/2024',
                    'Total Amount: £67.30',
                    'Electricity Bill'
                ],
                'confidence': 0.82
            },
            {
                'page': 3,
                'lines': [
                    'Terms and Conditions',
                    'Please read carefully',
                    'Contact us for support',
                    'Customer service: 0800 123 456'
                ],
                'confidence': 0.90
            }
        ]
        
        print(f"🔍 Testing with {len(mock_page_results)} pages")
        result = detect_multiple_invoices(mock_page_results)
        
        print(f"✅ Detected {len(result)} separate invoices:")
        for invoice in result:
            print(f"   - Page {invoice['page_number']}: {invoice['indicators_found']} indicators")
            print(f"     Supplier found: {invoice['has_supplier']}")
            print(f"     Total found: {invoice['has_total']}")
            
    except Exception as e:
        print(f"❌ Multi-invoice detection test failed: {str(e)}")
        import traceback
        print(f"❌ Full traceback: {traceback.format_exc()}")

async def test_upload_with_utility_classification():
    """Test upload endpoint with utility invoice classification"""
    
    print("\n🧪 Testing Upload with Utility Classification")
    print("=" * 50)
    
    try:
        # Import the upload function
        from backend.routes.upload_fixed import upload_invoice
        print("✅ Upload function imported successfully")
        
        # Create a mock utility invoice file
        test_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Contents 4 0 R\n>>\nendobj\n4 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n/F1 12 Tf\n72 720 Td\n(British Gas Energy Bill) Tj\nET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000204 00000 n \ntrailer\n<<\n/Size 5\n/Root 1 0 R\n>>\nstartxref\n297\n%%EOF"
        
        # Create a mock UploadFile
        file_content = io.BytesIO(test_content)
        upload_file = UploadFile(
            filename="british_gas_bill.pdf",
            file=file_content,
            size=len(test_content)
        )
        
        print(f"📄 Created test utility invoice: {upload_file.filename}")
        print(f"📊 File size: {upload_file.size} bytes")
        
        # Note: This would require a running server to test the actual upload
        print("ℹ️  Upload test requires running server - skipping actual upload")
        print("✅ Test setup completed successfully")
            
    except Exception as e:
        print(f"❌ Upload test failed: {str(e)}")
        import traceback
        print(f"❌ Full traceback: {traceback.format_exc()}")

async def main():
    """Run all tests"""
    print("🚀 Starting Utility Invoice and Multi-Invoice PDF Tests")
    print("=" * 60)
    
    await test_utility_invoice_classification()
    await test_multi_invoice_detection()
    await test_upload_with_utility_classification()
    
    print("\n✅ All tests completed!")

if __name__ == "__main__":
    asyncio.run(main()) 