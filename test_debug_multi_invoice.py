#!/usr/bin/env python3
"""
Debug test for multi-invoice detection
"""

import requests
import json

def test_debug_multi_invoice():
    """Debug multi-invoice detection"""
    print("🔍 Debug Multi-Invoice Detection")
    print("=" * 40)
    
    # Test with clear multi-invoice content
    multi_invoice = """
    INVOICE #001
    WILD HORSE BREWING CO LTD
    Page 1 of 2
    
    QTY ITEM UNIT PRICE TOTAL
    2 Beer Keg £50.00 £100.00
    Total: £120.00
    
    --- PAGE 2 ---
    
    INVOICE #002
    RED DRAGON DISPENSE LIMITED
    Page 2 of 2
    
    QTY ITEM UNIT PRICE TOTAL
    1 Wine Bottle £25.00 £25.00
    Total: £30.00
    """
    
    try:
        files = {"file": ("debug_multi.txt", multi_invoice, "text/plain")}
        response = requests.post("http://localhost:8002/api/upload", files=files, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Upload successful")
            print(f"  Message: {result.get('message', 'N/A')}")
            print(f"  Response keys: {list(result.keys())}")
            
            # Check if it has saved_invoices
            if 'saved_invoices' in result:
                invoices = result['saved_invoices']
                print(f"  ✅ Multi-invoice detected: {len(invoices)} invoices")
                for i, inv in enumerate(invoices):
                    print(f"    Invoice {i+1}: {inv.get('supplier_name', 'Unknown')} - £{inv.get('total_amount', 0)}")
            elif 'data' in result and 'saved_invoices' in result['data']:
                invoices = result['data']['saved_invoices']
                print(f"  ✅ Multi-invoice detected: {len(invoices)} invoices")
                for i, inv in enumerate(invoices):
                    print(f"    Invoice {i+1}: {inv.get('supplier_name', 'Unknown')} - £{inv.get('total_amount', 0)}")
            else:
                print("  ❌ No multi-invoice detection")
                print(f"  Raw response: {json.dumps(result, indent=2)}")
                
        else:
            print(f"❌ Upload failed: {response.status_code}")
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    test_debug_multi_invoice() 