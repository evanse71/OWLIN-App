#!/usr/bin/env python3
"""
Test frontend-backend connection
"""

import requests
import json

def test_frontend_backend_connection():
    """Test if frontend can fetch data from backend"""
    backend_url = "http://localhost:8000/api"
    frontend_url = "http://localhost:3000"
    
    print("🧪 Testing Frontend-Backend Connection")
    print("=" * 50)
    
    # Test 1: Backend API health
    print("\n1️⃣ Testing Backend API...")
    try:
        response = requests.get(f"{backend_url}/health")
        if response.status_code == 200:
            print("✅ Backend API is responding")
        else:
            print(f"❌ Backend API error: {response.status_code}")
    except Exception as e:
        print(f"❌ Backend API connection failed: {e}")
        return
    
    # Test 2: Backend invoices endpoint
    print("\n2️⃣ Testing Backend Invoices Endpoint...")
    try:
        response = requests.get(f"{backend_url}/documents/invoices")
        if response.status_code == 200:
            data = response.json()
            invoice_count = len(data.get('invoices', []))
            print(f"✅ Backend invoices endpoint working. Found {invoice_count} invoices")
            
            # Show recent invoices
            recent_invoices = data.get('invoices', [])[:3]
            for i, inv in enumerate(recent_invoices):
                print(f"   Invoice {i+1}: {inv['invoice_number']} - {inv['status']} - {inv['supplier_name']}")
        else:
            print(f"❌ Backend invoices endpoint error: {response.status_code}")
    except Exception as e:
        print(f"❌ Backend invoices endpoint failed: {e}")
    
    # Test 3: Frontend page loading
    print("\n3️⃣ Testing Frontend Page Loading...")
    try:
        response = requests.get(frontend_url)
        if response.status_code == 200:
            print("✅ Frontend page is loading")
        else:
            print(f"❌ Frontend page error: {response.status_code}")
    except Exception as e:
        print(f"❌ Frontend page connection failed: {e}")
    
    # Test 4: Check if invoices with 'waiting' status exist
    print("\n4️⃣ Checking for 'waiting' status invoices...")
    try:
        response = requests.get(f"{backend_url}/documents/invoices")
        if response.status_code == 200:
            data = response.json()
            waiting_invoices = [inv for inv in data.get('invoices', []) if inv['status'] == 'waiting']
            error_invoices = [inv for inv in data.get('invoices', []) if inv['status'] == 'error']
            utility_invoices = [inv for inv in data.get('invoices', []) if inv['status'] == 'utility']
            
            print(f"📊 Invoice status breakdown:")
            print(f"   Waiting: {len(waiting_invoices)}")
            print(f"   Error: {len(error_invoices)}")
            print(f"   Utility: {len(utility_invoices)}")
            print(f"   Total: {len(data.get('invoices', []))}")
            
            if waiting_invoices:
                print("✅ Found invoices with 'waiting' status - these should appear in the frontend")
            else:
                print("⚠️ No invoices with 'waiting' status found")
    except Exception as e:
        print(f"❌ Failed to check invoice statuses: {e}")
    
    print("\n✅ Frontend-Backend connection test completed!")

if __name__ == "__main__":
    test_frontend_backend_connection() 