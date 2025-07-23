#!/usr/bin/env python3
"""
Test script for multi-page PDF processing and utility invoice detection
"""

import requests
import tempfile
import os
import json
from pathlib import Path

def create_test_pdf_with_multiple_pages():
    """Create a test PDF with multiple pages for testing"""
    # This is a minimal PDF content that should work for testing
    pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R 4 0 R]
/Count 2
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 5 0 R
>>
endobj
4 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 6 0 R
>>
endobj
5 0 obj
<<
/Length 200
>>
stream
BT
/F1 12 Tf
72 720 Td
(INVOICE PAGE 1) Tj
0 -20 Td
(Invoice Number: INV-2024-001) Tj
0 -20 Td
(Date: 2024-01-15) Tj
0 -20 Td
(Supplier: Test Company) Tj
0 -20 Td
(Total Amount: 1500.00) Tj
ET
endstream
endobj
6 0 obj
<<
/Length 200
>>
stream
BT
/F1 12 Tf
72 720 Td
(INVOICE PAGE 2) Tj
0 -20 Td
(Invoice Number: INV-2024-002) Tj
0 -20 Td
(Date: 2024-01-16) Tj
0 -20 Td
(Supplier: Another Company) Tj
0 -20 Td
(Total Amount: 2500.00) Tj
ET
endstream
endobj
xref
0 7
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000204 00000 n 
0000000293 00000 n 
0000000382 00000 n 
trailer
<<
/Size 7
/Root 1 0 R
>>
startxref
650
%%EOF"""
    
    return pdf_content

def create_utility_invoice_pdf():
    """Create a test PDF for utility invoice detection"""
    pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj
4 0 obj
<<
/Length 300
>>
stream
BT
/F1 12 Tf
72 720 Td
(BRITISH GAS INVOICE) Tj
0 -20 Td
(Invoice Number: BG-2024-001) Tj
0 -20 Td
(Date: 2024-01-15) Tj
0 -20 Td
(Supplier: British Gas Energy) Tj
0 -20 Td
(Electricity and Gas Supply) Tj
0 -20 Td
(Total Amount: 89.50) Tj
0 -20 Td
(Utility Service Invoice) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000204 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
450
%%EOF"""
    
    return pdf_content

def test_multi_page_processing():
    """Test multi-page PDF processing"""
    base_url = "http://localhost:8000/api"
    
    print("🧪 Testing Multi-Page PDF Processing")
    print("=" * 50)
    
    # Test 1: Multi-page PDF
    print("\n1️⃣ Testing multi-page PDF upload...")
    multi_page_pdf = create_test_pdf_with_multiple_pages()
    
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
        f.write(multi_page_pdf)
        temp_file = f.name
    
    try:
        with open(temp_file, 'rb') as f:
            files = {'file': f}
            response = requests.post(f"{base_url}/upload/invoice", files=files)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Multi-page PDF upload successful")
            print(f"📄 Page count: {result.get('page_count', 'N/A')}")
            print(f"✅ Successful pages: {result.get('successful_pages', 'N/A')}")
            print(f"🆔 Invoice IDs: {result.get('invoice_ids', [])}")
            print(f"📋 Multiple invoices: {result.get('multiple_invoices', False)}")
            
            if 'page_details' in result:
                print("\n📋 Page Details:")
                for page in result['page_details']:
                    print(f"   Page {page['page_number']}: {page['supplier_name']} - £{page['total_amount']} ({page['status']})")
        else:
            print(f"❌ Multi-page PDF upload failed: {response.status_code} - {response.text}")
    
    finally:
        os.unlink(temp_file)
    
    # Test 2: Utility invoice PDF
    print("\n2️⃣ Testing utility invoice detection...")
    utility_pdf = create_utility_invoice_pdf()
    
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
        f.write(utility_pdf)
        temp_file = f.name
    
    try:
        with open(temp_file, 'rb') as f:
            files = {'file': f}
            response = requests.post(f"{base_url}/upload/invoice", files=files)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Utility invoice upload successful")
            print(f"🔌 Is utility invoice: {result.get('is_utility_invoice', False)}")
            print(f"📋 Delivery note required: {result.get('delivery_note_required', True)}")
            print(f"🔑 Utility keywords: {result.get('utility_keywords', [])}")
            print(f"📄 Status: {result.get('status', 'Unknown')}")
            print(f"🏢 Supplier: {result.get('parsed_data', {}).get('supplier_name', 'Unknown')}")
        else:
            print(f"❌ Utility invoice upload failed: {response.status_code} - {response.text}")
    
    finally:
        os.unlink(temp_file)
    
    # Test 3: Check database records
    print("\n3️⃣ Checking database records...")
    try:
        response = requests.get(f"{base_url}/documents/invoices")
        if response.status_code == 200:
            invoices = response.json().get('invoices', [])
            print(f"✅ Found {len(invoices)} invoices in database")
            
            for invoice in invoices[:5]:  # Show first 5
                print(f"   📄 {invoice['invoice_number']} - {invoice['supplier_name']} - £{invoice['total_amount']}")
                print(f"      Status: {invoice['status']}, Utility: {invoice.get('is_utility_invoice', False)}")
                print(f"      Delivery note required: {invoice.get('delivery_note_required', True)}")
                if invoice.get('page_number'):
                    print(f"      Page: {invoice['page_number']}")
                print()
        else:
            print(f"❌ Failed to fetch invoices: {response.status_code}")
    
    except Exception as e:
        print(f"❌ Error checking database: {e}")
    
    print("\n✅ Multi-page processing test completed!")

if __name__ == "__main__":
    test_multi_page_processing() 