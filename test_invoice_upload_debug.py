#!/usr/bin/env python3
"""
Test script to debug invoice upload and display issues
"""

import requests
import tempfile
import os
import json
from pathlib import Path

def create_test_invoice_pdf():
    """Create a test PDF for invoice upload"""
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
(INVOICE) Tj
0 -20 Td
(Invoice Number: INV-TEST-001) Tj
0 -20 Td
(Date: 2024-01-15) Tj
0 -20 Td
(Supplier: Test Company Ltd) Tj
0 -20 Td
(Total Amount: 1250.00) Tj
0 -20 Td
(Currency: GBP) Tj
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

def test_invoice_upload_and_display():
    """Test the full invoice upload and display flow"""
    base_url = "http://localhost:8000/api"
    
    print("🧪 Testing Invoice Upload and Display Flow")
    print("=" * 60)
    
    # Step 1: Upload test invoice
    print("\n1️⃣ Uploading test invoice...")
    test_pdf = create_test_invoice_pdf()
    
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
        f.write(test_pdf)
        temp_file = f.name
    
    try:
        with open(temp_file, 'rb') as f:
            files = {'file': f}
            response = requests.post(f"{base_url}/upload/invoice", files=files)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Invoice upload successful")
            print(f"📄 File ID: {result.get('file_id')}")
            print(f"📋 Invoice IDs: {result.get('invoice_ids', [])}")
            print(f"🔌 Is utility invoice: {result.get('is_utility_invoice', False)}")
            print(f"📋 Multiple invoices: {result.get('multiple_invoices', False)}")
        else:
            print(f"❌ Invoice upload failed: {response.status_code} - {response.text}")
            return
    
    finally:
        os.unlink(temp_file)
    
    # Step 2: Check database directly
    print("\n2️⃣ Checking database contents...")
    try:
        response = requests.get(f"{base_url}/documents/invoices")
        if response.status_code == 200:
            data = response.json()
            invoices = data.get('invoices', [])
            print(f"✅ Found {len(invoices)} invoices in database")
            
            for i, invoice in enumerate(invoices):
                print(f"   Invoice {i+1}:")
                print(f"     ID: {invoice['id']}")
                print(f"     Number: {invoice['invoice_number']}")
                print(f"     Supplier: {invoice['supplier_name']}")
                print(f"     Amount: £{invoice['total_amount']}")
                print(f"     Status: {invoice['status']}")
                print(f"     Utility: {invoice.get('is_utility_invoice', False)}")
                print(f"     Delivery note required: {invoice.get('delivery_note_required', True)}")
                print()
        else:
            print(f"❌ Failed to fetch invoices: {response.status_code}")
    
    except Exception as e:
        print(f"❌ Error checking database: {e}")
    
    # Step 3: Test frontend API endpoint
    print("\n3️⃣ Testing frontend API endpoint...")
    try:
        response = requests.get("http://localhost:3000/api/analytics/dashboard")
        if response.status_code == 200:
            print("✅ Frontend API endpoint responding")
        else:
            print(f"❌ Frontend API endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Frontend API test failed: {e}")
    
    # Step 4: Check if invoices are in the right category
    print("\n4️⃣ Checking invoice categorization...")
    try:
        response = requests.get(f"{base_url}/documents/invoices")
        if response.status_code == 200:
            data = response.json()
            invoices = data.get('invoices', [])
            
            waiting_invoices = [inv for inv in invoices if inv['status'] == 'waiting']
            utility_invoices = [inv for inv in invoices if inv['status'] == 'utility']
            scanned_invoices = [inv for inv in invoices if inv['status'] == 'scanned']
            
            print(f"📊 Invoice status breakdown:")
            print(f"   Waiting: {len(waiting_invoices)}")
            print(f"   Utility: {len(utility_invoices)}")
            print(f"   Scanned: {len(scanned_invoices)}")
            print(f"   Total: {len(invoices)}")
            
            # Show recent invoices
            recent_invoices = invoices[:3]
            print(f"\n📋 Recent invoices:")
            for inv in recent_invoices:
                print(f"   - {inv['invoice_number']} ({inv['supplier_name']}) - {inv['status']}")
    
    except Exception as e:
        print(f"❌ Error checking categorization: {e}")
    
    print("\n✅ Invoice upload and display test completed!")

if __name__ == "__main__":
    test_invoice_upload_and_display() 