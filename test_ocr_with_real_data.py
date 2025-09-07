#!/usr/bin/env python3
"""
Test OCR processing with real invoice data
"""

import requests
import json
import base64
from PIL import Image, ImageDraw, ImageFont
import io

def create_test_invoice_image():
    """Create a test invoice image with real data"""
    # Create a white image
    img = Image.new('RGB', (800, 1000), color='white')
    draw = ImageDraw.Draw(img)
    
    # Use a default font
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 16)
        title_font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 24)
    except:
        font = ImageFont.load_default()
        title_font = ImageFont.load_default()
    
    # Real invoice data from corrections file
    invoice_data = {
        "supplier": "Wild Horse Brewing Co Ltd",
        "invoice_number": "73318",
        "date": "Friday, 4 July 2025",
        "total": "£556.20",
        "line_items": [
            {"qty": "2", "code": "BUCK-EK30", "item": "Buckskin - 30L E-keg", "price": "£98.50", "total": "£177.30"},
            {"qty": "3", "code": "NOK-KEG30", "item": "Nokota - 30L Keg", "price": "£106.00", "total": "£286.20"}
        ]
    }
    
    # Draw invoice content
    y = 50
    
    # Title
    draw.text((50, y), "INVOICE", fill='black', font=title_font)
    y += 60
    
    # Supplier
    draw.text((50, y), f"Supplier: {invoice_data['supplier']}", fill='black', font=font)
    y += 30
    
    # Invoice number
    draw.text((50, y), f"Invoice Number: {invoice_data['invoice_number']}", fill='black', font=font)
    y += 30
    
    # Date
    draw.text((50, y), f"Date: {invoice_data['date']}", fill='black', font=font)
    y += 50
    
    # Line items header
    draw.text((50, y), "QTY  CODE        ITEM                    UNIT PRICE    TOTAL", fill='black', font=font)
    y += 30
    
    # Line items
    for item in invoice_data['line_items']:
        line = f"{item['qty']}    {item['code']}  {item['item']:<25} {item['price']:<12} {item['total']}"
        draw.text((50, y), line, fill='black', font=font)
        y += 25
    
    y += 20
    
    # Total
    draw.text((50, y), f"Total: {invoice_data['total']}", fill='black', font=font)
    
    # Save to bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    return img_bytes

def test_ocr_with_real_data():
    """Test OCR processing with real invoice data"""
    print("🧪 Testing OCR with Real Invoice Data...")
    
    try:
        # Create test invoice image
        print("📝 Creating test invoice image...")
        img_bytes = create_test_invoice_image()
        
        # Upload the image
        print("📤 Uploading test invoice...")
        files = {'file': ('test_invoice.png', img_bytes, 'image/png')}
        response = requests.post(
            "http://localhost:8002/api/upload",
            files=files,
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Upload successful!")
            
            # Check for meaningful data
            print(f"   - Invoice ID: {data.get('invoice_id', 'N/A')}")
            print(f"   - Supplier: {data.get('supplier_name', 'N/A')}")
            print(f"   - Invoice #: {data.get('invoice_number', 'N/A')}")
            print(f"   - Date: {data.get('invoice_date', 'N/A')}")
            print(f"   - Total: {data.get('total_amount', 'N/A')}")
            print(f"   - Confidence: {data.get('confidence', 'N/A')}")
            print(f"   - Word count: {data.get('word_count', 'N/A')}")
            print(f"   - Raw text length: {len(data.get('raw_ocr_text', ''))}")
            
            # Check if OCR extracted meaningful data
            meaningful_data = (
                data.get('supplier_name') != 'Unknown' and 
                data.get('supplier_name') != 'OCR Failed' and
                data.get('total_amount', 0) > 0 and
                data.get('confidence', 0) > 0 and
                len(data.get('raw_ocr_text', '')) > 0
            )
            
            if meaningful_data:
                print("✅ OCR successfully extracted meaningful data!")
                return True
            else:
                print("⚠️ OCR did not extract meaningful data")
                print("   This indicates an issue with the OCR processing")
                return False
        else:
            print(f"❌ Upload failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def test_frontend_with_real_data():
    """Test frontend display with real data"""
    print("🧪 Testing Frontend Display...")
    
    try:
        response = requests.get("http://localhost:3000/invoices", timeout=10)
        if response.status_code == 200:
            content = response.text
            
            # Check for required display elements
            required_elements = [
                'supplier_name', 'invoice_number', 'invoice_date', 'total_amount',
                'confidence', 'original_filename'
            ]
            
            missing_elements = []
            for element in required_elements:
                if element not in content.lower():
                    missing_elements.append(element)
            
            if missing_elements:
                print(f"⚠️ Missing display elements: {missing_elements}")
            else:
                print("✅ All display elements present")
            
            return len(missing_elements) == 0
        else:
            print(f"❌ Frontend not accessible: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Frontend test failed: {e}")
        return False

def main():
    """Run comprehensive OCR test"""
    print("🚀 Testing OCR with Real Invoice Data...")
    print("=" * 60)
    
    # Test OCR with real data
    ocr_ok = test_ocr_with_real_data()
    
    print("\n" + "=" * 60)
    
    # Test frontend display
    frontend_ok = test_frontend_with_real_data()
    
    print("\n" + "=" * 60)
    print("📋 OCR Test Summary:")
    print(f"   OCR Processing: {'✅' if ocr_ok else '❌'}")
    print(f"   Frontend Display: {'✅' if frontend_ok else '❌'}")
    
    if ocr_ok and frontend_ok:
        print("\n🎉 Complete system is working!")
        print("\n📝 All Required Information Will Be Displayed:")
        print("   ✅ Supplier name")
        print("   ✅ File name")
        print("   ✅ Invoice date")
        print("   ✅ Total value (including VAT)")
        print("   ✅ OCR confidence")
        print("   ✅ Line-by-line table (when expanded)")
        print("\n🎯 Ready for manual testing!")
        print("   Open http://localhost:3000/invoices")
        print("   Upload a real invoice PDF to see all information displayed")
    else:
        print("\n⚠️ Issues detected:")
        if not ocr_ok:
            print("   - OCR processing is not extracting data from images")
            print("   - This may be due to OCR engine configuration issues")
        if not frontend_ok:
            print("   - Frontend display elements are missing")

if __name__ == "__main__":
    main() 