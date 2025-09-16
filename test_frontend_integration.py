#!/usr/bin/env python3
"""
Test script to verify frontend integration with backend API
"""
import requests
import json
import time

BASE_URL = "http://127.0.0.1:8080"

def test_manual_invoice_creation():
    """Test manual invoice creation with line items"""
    print("🧪 Testing Manual Invoice Creation with Line Items...")
    
    invoice_data = {
        "supplier": "Frontend Test Supplier",
        "invoice_date": "2025-09-16",
        "reference": "FRONTEND-TEST-001",
        "currency": "GBP",
        "line_items": [
            {
                "description": "Test Product A",
                "quantity": 2,
                "unit_price": 25.50,
                "uom": "each",
                "vat_rate": 20
            },
            {
                "description": "Test Product B",
                "quantity": 1,
                "unit_price": 15.00,
                "uom": "box",
                "vat_rate": 0
            }
        ]
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/invoices/manual", json=invoice_data)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Manual invoice created: {result}")
            return result.get("id")
        else:
            print(f"❌ Failed to create manual invoice: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error creating manual invoice: {e}")
        return None

def test_line_items_retrieval(invoice_id):
    """Test line items retrieval"""
    print(f"\n📋 Testing Line Items Retrieval for invoice {invoice_id}...")
    
    try:
        response = requests.get(f"{BASE_URL}/api/invoices/{invoice_id}/line-items")
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Line items retrieved: {len(result.get('items', []))} items")
            for item in result.get('items', []):
                print(f"   - {item.get('description')}: {item.get('quantity')} x £{item.get('unit_price')} = £{item.get('total')}")
            return result.get('items', [])
        else:
            print(f"❌ Failed to retrieve line items: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        print(f"❌ Error retrieving line items: {e}")
        return []

def test_line_items_crud(invoice_id):
    """Test line items CRUD operations"""
    print(f"\n🔧 Testing Line Items CRUD for invoice {invoice_id}...")
    
    # Test adding line items
    new_items = [
        {
            "description": "Additional Product",
            "quantity": 3,
            "unit_price": 10.00,
            "uom": "each",
            "vat_rate": 20
        }
    ]
    
    try:
        response = requests.post(f"{BASE_URL}/api/invoices/{invoice_id}/line-items", json=new_items)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Added {len(result.get('items', []))} new line items")
            
            # Get updated line items
            response = requests.get(f"{BASE_URL}/api/invoices/{invoice_id}/line-items")
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Total line items after addition: {len(result.get('items', []))}")
                return result.get('items', [])
        else:
            print(f"❌ Failed to add line items: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        print(f"❌ Error in CRUD operations: {e}")
        return []

def main():
    """Run all frontend integration tests"""
    print("🚀 Starting Frontend Integration Tests")
    print("=" * 50)
    
    # Wait for server to start
    print("⏳ Waiting for server to start...")
    time.sleep(3)
    
    # Test manual invoice creation
    invoice_id = test_manual_invoice_creation()
    if not invoice_id:
        print("❌ Cannot continue without invoice ID")
        return
    
    # Test line items retrieval
    line_items = test_line_items_retrieval(invoice_id)
    if not line_items:
        print("❌ Cannot continue without line items")
        return
    
    # Test line items CRUD
    updated_items = test_line_items_crud(invoice_id)
    
    print(f"\n✅ Frontend Integration Tests Completed!")
    print(f"📊 Final Results:")
    print(f"   - Invoice ID: {invoice_id}")
    print(f"   - Total Line Items: {len(updated_items)}")
    print(f"   - Total Value: £{sum(item.get('total', 0) for item in updated_items):.2f}")

if __name__ == "__main__":
    main()
