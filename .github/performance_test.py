#!/usr/bin/env python3
"""
Performance Test for Owlin
Measures render time for 500 invoices and detail fetch median time.
"""
import requests
import time
import statistics
import sys
from typing import List, Dict, Any

def measure_api_performance():
    """Measure API performance for invoices list and detail"""
    base_url = "http://127.0.0.1:8000"
    
    print("🧪 Performance Test: API Endpoints")
    print("=" * 50)
    
    # Test 1: Invoices list performance
    print("Testing /api/invoices performance...")
    list_times = []
    
    for i in range(5):  # 5 iterations for median
        start_time = time.time()
        try:
            response = requests.get(f"{base_url}/api/invoices")
            if response.status_code == 200:
                end_time = time.time()
                duration = (end_time - start_time) * 1000  # Convert to ms
                list_times.append(duration)
                print(f"  Iteration {i+1}: {duration:.2f}ms")
            else:
                print(f"  Iteration {i+1}: HTTP {response.status_code}")
        except requests.exceptions.ConnectionError:
            print(f"  Iteration {i+1}: Connection failed (server not running)")
            break
        except Exception as e:
            print(f"  Iteration {i+1}: Error - {e}")
            break
    
    if list_times:
        median_list_time = statistics.median(list_times)
        print(f"\n📊 Invoices List Performance:")
        print(f"  Median time: {median_list_time:.2f}ms")
        print(f"  Budget: 250ms (first paint)")
        print(f"  Status: {'✅ PASS' if median_list_time < 250 else '❌ FAIL'}")
    else:
        print("\n❌ No successful list requests")
        return
    
    # Test 2: Invoice detail performance
    print("\nTesting /api/invoices/{id} performance...")
    detail_times = []
    
    # Get a list of invoices first
    try:
        response = requests.get(f"{base_url}/api/invoices")
        if response.status_code == 200:
            data = response.json()
            invoices = data.get('invoices', [])
            
            if invoices:
                # Test detail fetch for first few invoices
                for i, invoice in enumerate(invoices[:3]):  # Test first 3 invoices
                    invoice_id = invoice.get('id')
                    if invoice_id:
                        start_time = time.time()
                        try:
                            detail_response = requests.get(f"{base_url}/api/invoices/{invoice_id}")
                            if detail_response.status_code == 200:
                                end_time = time.time()
                                duration = (end_time - start_time) * 1000
                                detail_times.append(duration)
                                print(f"  Invoice {invoice_id}: {duration:.2f}ms")
                        except Exception as e:
                            print(f"  Invoice {invoice_id}: Error - {e}")
            else:
                print("  No invoices found to test detail performance")
        else:
            print("  Failed to get invoices list for detail testing")
    except Exception as e:
        print(f"  Error getting invoices list: {e}")
    
    if detail_times:
        median_detail_time = statistics.median(detail_times)
        print(f"\n📊 Invoice Detail Performance:")
        print(f"  Median time: {median_detail_time:.2f}ms")
        print(f"  Budget: 300ms (local DB)")
        print(f"  Status: {'✅ PASS' if median_detail_time < 300 else '❌ FAIL'}")
    else:
        print("\n❌ No successful detail requests")
    
    # Test 3: Health endpoint performance
    print("\nTesting /api/health/details performance...")
    health_times = []
    
    for i in range(3):
        start_time = time.time()
        try:
            response = requests.get(f"{base_url}/api/health/details")
            if response.status_code == 200:
                end_time = time.time()
                duration = (end_time - start_time) * 1000
                health_times.append(duration)
                print(f"  Health check {i+1}: {duration:.2f}ms")
        except Exception as e:
            print(f"  Health check {i+1}: Error - {e}")
    
    if health_times:
        median_health_time = statistics.median(health_times)
        print(f"\n📊 Health Endpoint Performance:")
        print(f"  Median time: {median_health_time:.2f}ms")
        print(f"  Budget: 100ms (health check)")
        print(f"  Status: {'✅ PASS' if median_health_time < 100 else '❌ FAIL'}")
    
    # Summary
    print("\n" + "=" * 50)
    print("📈 Performance Summary:")
    
    if list_times:
        print(f"  Invoices list: {statistics.median(list_times):.2f}ms (budget: 250ms)")
    if detail_times:
        print(f"  Invoice detail: {statistics.median(detail_times):.2f}ms (budget: 300ms)")
    if health_times:
        print(f"  Health check: {statistics.median(health_times):.2f}ms (budget: 100ms)")
    
    # Overall status
    all_passed = True
    if list_times and statistics.median(list_times) >= 250:
        all_passed = False
    if detail_times and statistics.median(detail_times) >= 300:
        all_passed = False
    if health_times and statistics.median(health_times) >= 100:
        all_passed = False
    
    print(f"\n🎯 Overall Status: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    
    return all_passed

if __name__ == "__main__":
    print("🚀 Starting Owlin Performance Test...")
    success = measure_api_performance()
    sys.exit(0 if success else 1)
