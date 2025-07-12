#!/usr/bin/env python3
"""
Test script to verify file upload functionality
"""
import requests
import os
from pathlib import Path

# Test file creation
def create_test_pdf(filename: str, content: str = "Test content"):
    """Create a simple test PDF file"""
    # Create a minimal PDF content
    pdf_content = f"""%PDF-1.4
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
/Length 44
>>
stream
BT
/F1 12 Tf
72 720 Td
({content}) Tj
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
297
%%EOF"""
    
    with open(filename, 'w') as f:
        f.write(pdf_content)
    return filename

def test_upload():
    """Test the upload endpoints"""
    base_url = "http://localhost:8000/api"
    
    # Create test files with valid extensions
    test_invoice = create_test_pdf("test_invoice.pdf", "This is a test invoice")
    test_delivery = create_test_pdf("test_delivery.pdf", "This is a test delivery note")
    
    try:
        # Test invoice upload
        print("Testing invoice upload...")
        with open(test_invoice, 'rb') as f:
            files = {'file': f}
            response = requests.post(f"{base_url}/upload/invoice", files=files)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Invoice upload successful: {result}")
        else:
            print(f"❌ Invoice upload failed: {response.status_code} - {response.text}")
        
        # Test delivery upload
        print("\nTesting delivery upload...")
        with open(test_delivery, 'rb') as f:
            files = {'file': f}
            response = requests.post(f"{base_url}/upload/delivery", files=files)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Delivery upload successful: {result}")
        else:
            print(f"❌ Delivery upload failed: {response.status_code} - {response.text}")
        
        # List uploaded files
        print("\nListing uploaded files...")
        response = requests.get(f"{base_url}/files/invoices")
        if response.status_code == 200:
            print(f"📄 Invoices: {response.json()}")
        
        response = requests.get(f"{base_url}/files/delivery")
        if response.status_code == 200:
            print(f"📋 Delivery notes: {response.json()}")
            
    finally:
        # Clean up test files
        for file in [test_invoice, test_delivery]:
            if os.path.exists(file):
                os.remove(file)
                print(f"🧹 Cleaned up {file}")

if __name__ == "__main__":
    test_upload() 