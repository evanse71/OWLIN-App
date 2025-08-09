#!/usr/bin/env python3
"""
Direct OCR test to isolate the processing issue
"""

import asyncio
import tempfile
import os
from pathlib import Path
from fastapi import UploadFile
import io

async def test_ocr_directly():
    """Test OCR processing directly"""
    
    print("🧪 Testing OCR Processing Directly")
    print("=" * 50)
    
    try:
        # Import the OCR function
        from backend.routes.ocr import parse_with_ocr
        print("✅ OCR module imported successfully")
        
        # Create a simple test file
        test_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Contents 4 0 R\n>>\nendobj\n4 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n/F1 12 Tf\n72 720 Td\n(Test PDF Content) Tj\nET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000204 00000 n \ntrailer\n<<\n/Size 5\n/Root 1 0 R\n>>\nstartxref\n297\n%%EOF"
        
        # Create a mock UploadFile
        file_content = io.BytesIO(test_content)
        upload_file = UploadFile(
            filename="test.pdf",
            file=file_content,
            size=len(test_content)
        )
        
        print(f"📄 Created test PDF file: {upload_file.filename}")
        print(f"📊 File size: {upload_file.size} bytes")
        
        # Test OCR processing
        print("🔄 Testing OCR processing...")
        result = await parse_with_ocr(upload_file, threshold=70, debug=True)
        
        print("✅ OCR processing completed")
        print(f"📋 Result keys: {list(result.keys())}")
        print(f"📋 Success: {result.get('success', False)}")
        
        if result.get('success'):
            print(f"📋 Confidence: {result.get('confidence_score', 0)}")
            print(f"📋 Parsed data: {result.get('parsed_data', {})}")
        else:
            print(f"❌ Error: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ OCR test failed: {str(e)}")
        import traceback
        print(f"❌ Full traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(test_ocr_directly()) 