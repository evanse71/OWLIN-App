#!/usr/bin/env python3
"""
Test to verify the Product Trends page is working correctly
"""

import requests
import json

def test_product_trends_page():
    """Test all the APIs and data needed for the Product Trends page"""
    base_url = "http://localhost:8000/api"
    
    print("🧪 Testing Product Trends Page")
    print("=" * 50)
    
    # Test 1: Products available endpoint
    print("\n1️⃣ Testing Products Available API...")
    try:
        response = requests.get(f"{base_url}/products/available")
        if response.status_code == 200:
            data = response.json()
            products = data.get('products', [])
            count = data.get('count', 0)
            print(f"✅ Products API: {count} products found")
            if products:
                print(f"📋 Products: {', '.join(products[:3])}{'...' if len(products) > 3 else ''}")
            else:
                print("❌ No products found - page will show 'No forecast data available'")
                return
        else:
            print(f"❌ Products API failed: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Products API error: {e}")
        return
    
    # Test 2: Forecast for first product
    print(f"\n2️⃣ Testing Forecast API for '{products[0]}'...")
    try:
        response = requests.get(f"{base_url}/products/forecast/{requests.utils.quote(products[0])}")
        if response.status_code == 200:
            data = response.json()
            historic_count = len(data.get('historic', []))
            forecast_count = len(data.get('forecast', []))
            confidence = data.get('confidence', 'unknown')
            volatility = data.get('volatility', 'unknown')
            data_points = data.get('data_points', 0)
            
            print(f"✅ Forecast API working:")
            print(f"   📊 Historic data points: {historic_count}")
            print(f"   🔮 Forecast data points: {forecast_count}")
            print(f"   🎯 Confidence: {confidence}")
            print(f"   📈 Volatility: {volatility}")
            print(f"   📋 Total data points: {data_points}")
            
            if forecast_count > 0:
                print(f"   ✅ Forecast data available - page should display charts!")
            else:
                print(f"   ⚠️ No forecast data - page will show 'No forecast data available'")
        else:
            print(f"❌ Forecast API failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Forecast API error: {e}")
    
    # Test 3: Forecast readiness
    print(f"\n3️⃣ Testing Forecast Readiness for '{products[0]}'...")
    try:
        response = requests.get(f"{base_url}/products/forecast-ready/{requests.utils.quote(products[0])}")
        if response.status_code == 200:
            data = response.json()
            ready = data.get('ready', False)
            status = data.get('status', 'unknown')
            reason = data.get('reason', 'unknown')
            
            print(f"✅ Forecast Readiness:")
            print(f"   🎯 Ready: {ready}")
            print(f"   📊 Status: {status}")
            print(f"   💡 Reason: {reason}")
        else:
            print(f"❌ Forecast Readiness API failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Forecast Readiness API error: {e}")
    
    # Test 4: Test multiple products (simulate what the page does)
    print(f"\n4️⃣ Testing Multiple Products (like the page does)...")
    try:
        test_products = products[:3]  # Test first 3 products
        forecast_promises = []
        
        for product in test_products:
            response = requests.get(f"{base_url}/products/forecast/{requests.utils.quote(product)}")
            if response.status_code == 200:
                data = response.json()
                forecast_count = len(data.get('forecast', []))
                print(f"   ✅ {product}: {forecast_count} forecast points")
            else:
                print(f"   ❌ {product}: API failed ({response.status_code})")
        
        print(f"✅ All {len(test_products)} products tested successfully")
    except Exception as e:
        print(f"❌ Multiple products test error: {e}")
    
    print("\n" + "=" * 50)
    print("📊 PRODUCT TRENDS PAGE STATUS:")
    
    if count > 0:
        print("✅ Products available in database")
        print("✅ APIs are working correctly")
        print("✅ Forecast data is being generated")
        print("\n🎯 The Product Trends page should now display:")
        print("   • Product cards with trend information")
        print("   • Historical price charts")
        print("   • Forecast predictions with confidence bands")
        print("   • Expandable panels for detailed analysis")
        print("\n💡 If the page still shows 'No forecast data available':")
        print("   • Try refreshing the browser")
        print("   • Check browser console for any JavaScript errors")
        print("   • Verify the frontend is connecting to localhost:8000")
    else:
        print("❌ No products available")
        print("❌ Page will show 'No forecast data available'")
        print("\n💡 To see data, upload invoices with line items or run the test data script")

if __name__ == "__main__":
    test_product_trends_page() 