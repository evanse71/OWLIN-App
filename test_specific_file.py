#!/usr/bin/env python3
"""
Test script for specific file upload issues
"""

import requests
import tempfile
import os

def test_specific_file():
    """Test upload of the specific problematic file"""
    base_url = "http://localhost:8000/api"
    
    print("🧪 Testing Specific File Upload")
    print("=" * 50)
    
    # Create a test PDF file similar to what might be uploaded
    print("📄 Creating test PDF file...")
    
    # This is a minimal PDF content that should work
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
/Length 200
>>
stream
BT
/F1 12 Tf
72 720 Td
(INVOICE) Tj
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
    
    try:
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            f.write(pdf_content)
            temp_file_path = f.name
        
        print(f"✅ Created test PDF: {temp_file_path}")
        print(f"📊 File size: {len(pdf_content)} bytes")
        
        # Test the upload
        print("🔄 Testing upload...")
        with open(temp_file_path, 'rb') as file:
            response = requests.post(f"{base_url}/upload/invoice", files={"file": file})
        
        print(f"📋 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Upload successful!")
            print(f"📋 File ID: {result.get('file_id')}")
            print(f"📋 Invoice ID: {result.get('invoice_id')}")
            print(f"📋 Confidence: {result.get('confidence_score')}%")
            print(f"📋 Parsed Data: {result.get('parsed_data')}")
        else:
            print(f"❌ Upload failed: {response.text}")
        
        # Clean up
        os.unlink(temp_file_path)
        print("🧹 Cleaned up temporary file")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        if 'temp_file_path' in locals():
            try:
                os.unlink(temp_file_path)
            except:
                pass

if __name__ == "__main__":
    test_specific_file() 