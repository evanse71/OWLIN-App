#!/usr/bin/env python3
"""
Test script for manual invoice CRUD operations
"""
import requests
import json
import time

BASE_URL = "http://127.0.0.1:8080"

def test_health():
    """Test health endpoint"""
    print("🔍 Testing health endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/api/health")
        print(f"✅ Health: {response.json()}")
        return True
    except Exception as e:
        print(f"❌ Health failed: {e}")
        return False

def test_create_manual_invoice():
    """Test creating a manual invoice with line items"""
    print("\n📝 Testing manual invoice creation...")
    
    invoice_data = {
        "supplier": "Test Supplier Ltd",
        "invoice_date": "2025-09-16",
        "reference": "INV-001",
        "currency": "GBP",
        "line_items": [
            {
                "description": "Keg Lager 11g",
                "quantity": 2,
                "unit_price": 99.5,
                "uom": "each",
                "vat_rate": 20
            },
            {
                "description": "Limes (box)",
                "quantity": 1,
                "unit_price": 18.0,
                "uom": "box",
                "vat_rate": 0
            }
        ]
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/invoices/manual", json=invoice_data)
        print(f"✅ Invoice created: {response.json()}")
        return response.json()["id"]
    except Exception as e:
        print(f"❌ Invoice creation failed: {e}")
        return None

def test_get_line_items(invoice_id):
    """Test getting line items for an invoice"""
    print(f"\n📋 Testing get line items for invoice {invoice_id}...")
    
    try:
        response = requests.get(f"{BASE_URL}/api/invoices/{invoice_id}/line-items")
        print(f"✅ Line items: {json.dumps(response.json(), indent=2)}")
        return response.json()["items"]
    except Exception as e:
        print(f"❌ Get line items failed: {e}")
        return None

def test_add_line_items(invoice_id):
    """Test adding more line items"""
    print(f"\n➕ Testing add line items to invoice {invoice_id}...")
    
    new_items = [
        {
            "description": "Cocktail Shaker",
            "quantity": 1,
            "unit_price": 25.0,
            "uom": "each",
            "vat_rate": 20
        }
    ]
    
    try:
        response = requests.post(f"{BASE_URL}/api/invoices/{invoice_id}/line-items", json=new_items)
        print(f"✅ Added line items: {json.dumps(response.json(), indent=2)}")
        return response.json()["items"]
    except Exception as e:
        print(f"❌ Add line items failed: {e}")
        return None

def test_update_line_item(invoice_id, line_items):
    """Test updating a line item"""
    if not line_items:
        print("❌ No line items to update")
        return None
        
    line_id = line_items[0]["id"]
    print(f"\n✏️ Testing update line item {line_id}...")
    
    update_data = {
        "description": "Updated Keg Lager 11g",
        "quantity": 3,
        "unit_price": 95.0,
        "uom": "each",
        "vat_rate": 20
    }
    
    try:
        response = requests.put(f"{BASE_URL}/api/invoices/{invoice_id}/line-items/{line_id}", json=update_data)
        print(f"✅ Updated line item: {json.dumps(response.json(), indent=2)}")
        return response.json()
    except Exception as e:
        print(f"❌ Update line item failed: {e}")
        return None

def test_delete_line_item(invoice_id, line_items):
    """Test deleting a line item"""
    if len(line_items) < 2:
        print("❌ Not enough line items to delete")
        return False
        
    line_id = line_items[1]["id"]
    print(f"\n🗑️ Testing delete line item {line_id}...")
    
    try:
        response = requests.delete(f"{BASE_URL}/api/invoices/{invoice_id}/line-items/{line_id}")
        print(f"✅ Deleted line item: {response.json()}")
        return True
    except Exception as e:
        print(f"❌ Delete line item failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting Manual Invoice CRUD Tests")
    print("=" * 50)
    
    # Wait for server to start
    print("⏳ Waiting for server to start...")
    time.sleep(3)
    
    # Test health
    if not test_health():
        print("❌ Server not ready, exiting")
        return
    
    # Test create invoice
    invoice_id = test_create_manual_invoice()
    if not invoice_id:
        print("❌ Cannot continue without invoice ID")
        return
    
    # Test get line items
    line_items = test_get_line_items(invoice_id)
    if not line_items:
        print("❌ Cannot continue without line items")
        return
    
    # Test add line items
    new_items = test_add_line_items(invoice_id)
    
    # Test update line item
    test_update_line_item(invoice_id, line_items)
    
    # Test delete line item
    test_delete_line_item(invoice_id, line_items)
    
    # Final check
    print(f"\n🔍 Final line items for invoice {invoice_id}:")
    test_get_line_items(invoice_id)
    
    print("\n✅ All tests completed!")

if __name__ == "__main__":
    main()
