#!/usr/bin/env python3
"""
Direct test of LLM processing
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.llm.llm_client import parse_invoice
from backend.types.parsed_invoice import InvoiceParsingPayload
import base64
from PIL import Image
import io

def test_llm_direct():
    """Test LLM processing directly"""
    print("🧪 Testing LLM Processing Directly...")
    
    try:
        # Create a simple test image (1x1 pixel)
        img = Image.new('RGB', (1, 1), color='white')
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_b64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
        
        # Create payload
        payload = InvoiceParsingPayload(
            text=None,
            tables=None,
            page_images=[{
                "page": 1,
                "image_b64": img_b64
            }],
            hints={}
        )
        
        print("📤 Sending payload to LLM...")
        result = parse_invoice(payload)
        
        print("✅ LLM processing successful!")
        print(f"   - Supplier: {result.supplier_name}")
        print(f"   - Invoice number: {result.invoice_number}")
        print(f"   - Line items: {len(result.line_items)}")
        
        return True
        
    except Exception as e:
        print(f"❌ LLM processing failed: {e}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    test_llm_direct() 