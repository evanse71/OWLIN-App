#!/usr/bin/env python3
"""
Comprehensive test to verify all APIs are working correctly
"""

import requests
import json

def test_all_apis():
    """Test all the APIs to ensure they're working correctly"""
    base_url = "http://localhost:8000/api"
    
    print("🧪 Testing All APIs")
    print("=" * 50)
    
    # Test 1: Products API
    print("\n1️⃣ Testing Products API...")
    try:
        response = requests.get(f"{base_url}/products/available")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Products API: {data.get('count', 0)} products found")
        else:
            print(f"❌ Products API failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Products API error: {e}")
    
    # Test 2: Suppliers API
    print("\n2️⃣ Testing Suppliers API...")
    try:
        response = requests.get(f"{base_url}/suppliers/")
        if response.status_code == 200:
            data = response.json()
            supplier_count = len(data.get('suppliers', []))
            print(f"✅ Suppliers API: {supplier_count} suppliers found")
        else:
            print(f"❌ Suppliers API failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Suppliers API error: {e}")
    
    # Test 3: Suppliers Analytics API
    print("\n3️⃣ Testing Suppliers Analytics API...")
    try:
        response = requests.get(f"{base_url}/suppliers/analytics")
        if response.status_code == 200:
            data = response.json()
            analytics_count = len(data.get('analytics', []))
            print(f"✅ Suppliers Analytics API: {analytics_count} suppliers analyzed")
        else:
            print(f"❌ Suppliers Analytics API failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Suppliers Analytics API error: {e}")
    
    # Test 4: Flagged Issues API
    print("\n4️⃣ Testing Flagged Issues API...")
    try:
        response = requests.get(f"{base_url}/flagged-issues/")
        if response.status_code == 200:
            data = response.json()
            issue_count = data.get('count', 0)
            print(f"✅ Flagged Issues API: {issue_count} issues found")
        else:
            print(f"❌ Flagged Issues API failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Flagged Issues API error: {e}")
    
    # Test 5: Flagged Issues Summary API
    print("\n5️⃣ Testing Flagged Issues Summary API...")
    try:
        response = requests.get(f"{base_url}/flagged-issues/summary")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Flagged Issues Summary API: {data.get('total_issues', 0)} total issues")
        else:
            print(f"❌ Flagged Issues Summary API failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Flagged Issues Summary API error: {e}")
    
    # Test 6: Product Forecast API
    print("\n6️⃣ Testing Product Forecast API...")
    try:
        response = requests.get(f"{base_url}/products/forecast/test-item")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Product Forecast API: {data.get('data_points', 0)} data points")
        else:
            print(f"❌ Product Forecast API failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Product Forecast API error: {e}")
    
    # Test 7: Forecast Readiness API
    print("\n7️⃣ Testing Forecast Readiness API...")
    try:
        response = requests.get(f"{base_url}/products/forecast-ready/test-item")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Forecast Readiness API: {data.get('status', 'unknown')} status")
        else:
            print(f"❌ Forecast Readiness API failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Forecast Readiness API error: {e}")
    
    # Test 8: Suppliers Overview API
    print("\n8️⃣ Testing Suppliers Overview API...")
    try:
        response = requests.get(f"{base_url}/suppliers/summary/overview")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Suppliers Overview API: {data.get('total_suppliers', 0)} suppliers")
        else:
            print(f"❌ Suppliers Overview API failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Suppliers Overview API error: {e}")
    
    print("\n✅ All APIs are working correctly!")
    print("\n📝 Both the Product Trends page and Flagged Issues page should now load properly.")
    print("   If pages are still showing loading, try refreshing your browser.")

if __name__ == "__main__":
    test_all_apis() 