#!/usr/bin/env python3
"""
Simple test to see the actual upload response
"""

import requests
import tempfile
import os

def create_test_pdf():
    """Create a minimal test PDF"""
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
/Length 100
>>
stream
BT
/F1 12 Tf
72 720 Td
(INVOICE) Tj
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

def test_upload():
    """Test upload and show full response"""
    base_url = "http://localhost:8000/api"
    
    print("🧪 Testing Upload Response")
    print("=" * 40)
    
    # Create test PDF
    test_pdf = create_test_pdf()
    
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
        f.write(test_pdf)
        temp_file = f.name
    
    try:
        with open(temp_file, 'rb') as f:
            files = {'file': f}
            response = requests.post(f"{base_url}/upload/invoice", files=files)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Text: {response.text}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"Response JSON: {data}")
            except:
                print("Response is not valid JSON")
        else:
            print(f"Upload failed with status {response.status_code}")
    
    finally:
        os.unlink(temp_file)

if __name__ == "__main__":
    test_upload() 