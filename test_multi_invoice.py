#!/usr/bin/env python3

import sys
import os
import asyncio
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.main_advanced_simple import process_file_with_advanced_ocr

async def test_multi_invoice():
    """Test multi-invoice processing"""
    print("🧪 Testing Multi-Invoice Processing...")
    
    # Create a test file with multiple invoices
    multi_invoice_content = """
    INVOICE 1
    
    Red Dragon Dispense Limited
    123 Main Street
    Cardiff, CF1 1AA
    
    Invoice Date: 30/06/2025
    Invoice Number: INV-001
    
    QTY CODE ITEM UNIT PRICE TOTAL
    2 ABC123 Beer Keg £10.50 £21.00
    1 DEF456 Wine Bottle £15.75 £15.75
    
    TOTAL DUE: £36.75
    
    ==========================================
    
    INVOICE 2
    
    Wild Horse Brewery
    456 Brewery Lane
    Cardiff, CF2 2BB
    
    Invoice Date: 01/07/2025
    Invoice Number: INV-002
    
    QTY CODE ITEM UNIT PRICE TOTAL
    3 GHI789 Ale Barrel £25.00 £75.00
    2 JKL012 Cider Bottle £8.50 £17.00
    
    TOTAL DUE: £92.00
    
    ==========================================
    
    INVOICE 3
    
    Snowdonia Hospitality
    789 Hotel Road
    Cardiff, CF3 3CC
    
    Invoice Date: 02/07/2025
    Invoice Number: INV-003
    
    QTY CODE ITEM UNIT PRICE TOTAL
    1 MNO345 Wine Case £45.00 £45.00
    4 PQR678 Spirit Bottle £12.00 £48.00
    
    TOTAL DUE: £93.00
    """
    
    # Save test file
    test_file = Path("test_multi_invoice.txt")
    with open(test_file, "w") as f:
        f.write(multi_invoice_content)
    
    print(f"📄 Created multi-invoice test file: {test_file}")
    
    # Test advanced OCR processing
    print("\n🔄 Testing Multi-Invoice OCR Processing...")
    try:
        result = await process_file_with_advanced_ocr(test_file, "test_multi_invoice.txt")
        print(f"✅ Multi-Invoice OCR Result:")
        print(f"   - Supplier: {result.get('supplier_name', 'Unknown')}")
        print(f"   - Date: {result.get('invoice_date', 'Unknown')}")
        print(f"   - Total: £{result.get('total_amount', 0)}")
        print(f"   - Confidence: {result.get('confidence', 0)}")
        print(f"   - Line Items: {len(result.get('line_items', []))}")
        
        # Check if it detected multiple sections
        if 'multi_section' in result:
            print(f"   - Multi-Section: {result['multi_section']}")
            print(f"   - Section Count: {result.get('section_count', 0)}")
        
        # Check if it combined multiple invoices properly
        if result.get('total_amount', 0) > 100:
            print(f"   ✅ Successfully combined multiple invoices (Total: £{result.get('total_amount', 0)})")
        else:
            print(f"   ⚠️ May not have combined invoices properly (Total: £{result.get('total_amount', 0)})")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Clean up
    if test_file.exists():
        test_file.unlink()
    
    print("\n✅ Multi-invoice test completed!")

if __name__ == "__main__":
    asyncio.run(test_multi_invoice()) 