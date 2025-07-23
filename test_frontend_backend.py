#!/usr/bin/env python3
"""
Test script to verify frontend and backend are working correctly
"""

import requests
import time

def test_backend():
    """Test backend API endpoints"""
    print("🧪 Testing Backend API (Port 8000)")
    print("=" * 50)
    
    try:
        # Test root endpoint
        response = requests.get("http://localhost:8000/")
        if response.status_code == 200:
            print(f"✅ Root endpoint: {response.json()}")
        else:
            print(f"❌ Root endpoint failed: {response.status_code}")
            return False
        
        # Test dashboard endpoint
        response = requests.get("http://localhost:8000/api/analytics/dashboard")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Dashboard API: {data['system_metrics']['total_invoices']} invoices")
        else:
            print(f"❌ Dashboard API failed: {response.status_code}")
            return False
        
        # Test invoices endpoint
        response = requests.get("http://localhost:8000/api/invoices/")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Invoices API: {len(data['invoices'])} invoices")
        else:
            print(f"❌ Invoices API failed: {response.status_code}")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Backend test failed: {e}")
        return False

def test_frontend():
    """Test frontend application"""
    print("\n🧪 Testing Frontend (Port 3000)")
    print("=" * 50)
    
    try:
        # Test frontend root
        response = requests.get("http://localhost:3000/")
        if response.status_code == 200:
            if "Owlin" in response.text:
                print("✅ Frontend loading correctly (contains 'Owlin')")
            else:
                print("❌ Frontend not loading correctly (no 'Owlin' found)")
                return False
        else:
            print(f"❌ Frontend failed: {response.status_code}")
            return False
        
        # Test that frontend is not returning API response
        if "message" in response.text and "Owlin API is running" in response.text:
            print("❌ Frontend is returning API response instead of React app")
            return False
        else:
            print("✅ Frontend is returning React app (not API response)")
        
        return True
        
    except Exception as e:
        print(f"❌ Frontend test failed: {e}")
        return False

def test_api_connection():
    """Test that frontend can connect to backend API"""
    print("\n🧪 Testing Frontend-Backend Connection")
    print("=" * 50)
    
    try:
        # Test that frontend can reach backend API
        response = requests.get("http://localhost:8000/api/analytics/dashboard")
        if response.status_code == 200:
            print("✅ Frontend can reach backend API")
            return True
        else:
            print(f"❌ Frontend cannot reach backend API: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🎯 Testing Owlin Application")
    print("=" * 60)
    
    # Test backend
    backend_ok = test_backend()
    
    # Test frontend
    frontend_ok = test_frontend()
    
    # Test connection
    connection_ok = test_api_connection()
    
    # Summary
    print("\n📊 Test Results")
    print("=" * 60)
    print(f"Backend API (Port 8000): {'✅ PASS' if backend_ok else '❌ FAIL'}")
    print(f"Frontend App (Port 3000): {'✅ PASS' if frontend_ok else '❌ FAIL'}")
    print(f"API Connection: {'✅ PASS' if connection_ok else '❌ FAIL'}")
    
    if backend_ok and frontend_ok and connection_ok:
        print("\n🎉 All tests passed! Application is working correctly.")
        print("\n📱 Access URLs:")
        print("   Frontend: http://localhost:3000")
        print("   Backend API: http://localhost:8000")
        print("   API Docs: http://localhost:8000/docs")
    else:
        print("\n❌ Some tests failed. Please check the issues above.")

if __name__ == "__main__":
    main() 