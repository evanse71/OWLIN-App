#!/usr/bin/env python3
"""
Simple test for single invoice processing
"""

import requests
import json

def test_simple_single():
    """Test simple single invoice processing"""
    print("🔍 Simple Single Invoice Test")
    print("=" * 40)
    
    # Test with a very simple single invoice
    simple_invoice = """
    INVOICE #73318
    WILD HORSE BREWING CO LTD
    
    Total: £264.30
    """
    
    try:
        files = {"file": ("simple_invoice.txt", simple_invoice, "text/plain")}
        response = requests.post("http://localhost:8002/api/upload", files=files, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Upload successful")
            print(f"  Message: {result.get('message', 'N/A')}")
            print(f"  Response keys: {list(result.keys())}")
            
            # Check if it's a single invoice or multi-invoice response
            if 'saved_invoices' in result:
                print("  ❌ Detected as multi-invoice (should be single)")
                invoices = result['saved_invoices']
                print(f"  Invoices: {len(invoices)}")
                for i, inv in enumerate(invoices):
                    print(f"    Invoice {i+1}: {inv.get('supplier_name', 'Unknown')} - £{inv.get('total_amount', 0)}")
            elif 'data' in result:
                data = result['data']
                print("  ✅ Detected as single invoice")
                print(f"  Supplier: {data.get('supplier_name', 'N/A')}")
                print(f"  Invoice Number: {data.get('invoice_number', 'N/A')}")
                print(f"  Total Amount: £{data.get('total_amount', 0)}")
                print(f"  Confidence: {data.get('confidence', 0):.2f}")
                
                # Verify the data
                supplier = data.get('supplier_name', '')
                if 'WILD HORSE' in supplier:
                    print("  ✅ Supplier extraction working")
                else:
                    print(f"  ❌ Supplier extraction issue: {supplier}")
                
                confidence = data.get('confidence', 0)
                if confidence > 0.5:
                    print("  ✅ Confidence normalization working")
                else:
                    print(f"  ❌ Confidence issue: {confidence}")
                
                total = data.get('total_amount', 0)
                if total >= 260:
                    print("  ✅ VAT handling working")
                else:
                    print(f"  ❌ VAT handling issue: {total}")
            else:
                print("  ❌ Unexpected response format")
                print(f"  Raw response: {json.dumps(result, indent=2)}")
                
        else:
            print(f"❌ Upload failed: {response.status_code}")
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    test_simple_single() 