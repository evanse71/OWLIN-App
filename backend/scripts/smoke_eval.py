#!/usr/bin/env python3
"""
End-to-End Smoke Test for Enhanced OCR Pipeline
Validates: upload → job → fetch → arithmetic consistency
"""

import requests
import time
import sys
import os
import json
from pathlib import Path

BASE = os.environ.get("OWLIN_API", "http://localhost:8001")

def test_health():
    """Test basic health"""
    try:
        r = requests.get(f"{BASE}/health", timeout=10)
        r.raise_for_status()
        print("✅ Health check passed")
        return True
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

def test_upload_and_process(file_path):
    """Test complete upload → job → fetch pipeline"""
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return False
    
    print(f"📤 Uploading: {os.path.basename(file_path)}")
    
    # Upload file
    try:
        with open(file_path, "rb") as f:
            r = requests.post(
                f"{BASE}/upload", 
                files={"file": (os.path.basename(file_path), f, "application/octet-stream")}, 
                timeout=60
            )
        r.raise_for_status()
        job_data = r.json()
        job_id = job_data["job_id"]
        print(f"✅ Upload successful, job_id: {job_id}")
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        return False
    
    # Poll job status
    print("⏳ Polling job status...")
    for i in range(180):  # 3 minutes max
        try:
            r = requests.get(f"{BASE}/jobs/{job_id}", timeout=10)
            r.raise_for_status()
            job_status = r.json()
            
            if job_status.get("status") == "done":
                print(f"✅ Job completed in {i+1}s")
                break
            elif job_status.get("status") == "error":
                print(f"❌ Job failed: {job_status.get('error', 'Unknown error')}")
                return False
            elif job_status.get("status") == "failed":
                print(f"❌ Job failed: {job_status.get('error', 'Unknown error')}")
                return False
            else:
                progress = job_status.get("progress", 0)
                print(f"   Progress: {progress}%")
                time.sleep(1)
        except Exception as e:
            print(f"❌ Job polling failed: {e}")
            return False
    else:
        print("❌ Job timed out after 3 minutes")
        return False
    
    # Get invoice details
    try:
        result = job_status.get("result_json")
        if not result:
            print("❌ No result_json in job")
            return False
        
        result_data = json.loads(result)
        invoice_id = result_data.get("invoice_id")
        if not invoice_id:
            print("❌ No invoice_id in result")
            return False
        
        print(f"📄 Fetching invoice: {invoice_id}")
        r = requests.get(f"{BASE}/invoices/{invoice_id}", timeout=10)
        r.raise_for_status()
        invoice_data = r.json()
        
        # Extract key fields
        invoice = invoice_data.get("invoice", {})
        line_items = invoice_data.get("line_items", [])
        
        print("📊 Invoice Data:")
        print(f"   Supplier: {invoice.get('supplier_name', 'N/A')}")
        print(f"   Status: {invoice.get('status', 'N/A')}")
        print(f"   Confidence: {invoice.get('confidence', 0)}%")
        print(f"   Subtotal: £{(invoice.get('subtotal_p', 0) or 0)/100:.2f}")
        print(f"   VAT: £{(invoice.get('vat_total_p', 0) or 0)/100:.2f}")
        print(f"   Total: £{(invoice.get('total_p', 0) or 0)/100:.2f}")
        print(f"   Issues: {invoice.get('issues_count', 0)}")
        print(f"   Line Items: {len(line_items)}")
        
        # Validate arithmetic
        subtotal_p = invoice.get("subtotal_p", 0) or 0
        vat_total_p = invoice.get("vat_total_p", 0) or 0
        total_p = invoice.get("total_p", 0) or 0
        
        if total_p > 0:
            expected_total = subtotal_p + vat_total_p
            if abs(expected_total - total_p) <= 1:  # Allow 1p tolerance
                print("✅ Arithmetic validation passed")
            else:
                print(f"❌ Arithmetic mismatch: {subtotal_p} + {vat_total_p} ≠ {total_p}")
                return False
        else:
            print("⚠️ Total is zero, skipping arithmetic validation")
        
        # Validate line items
        if len(line_items) >= 1:
            print("✅ Line items validation passed")
        else:
            print("⚠️ No line items found")
        
        return True
        
    except Exception as e:
        print(f"❌ Invoice fetch failed: {e}")
        return False

def test_endpoints():
    """Test all diagnostic endpoints"""
    print("\n🔍 Testing Diagnostic Endpoints...")
    
    endpoints = [
        ("/health", "Health check"),
        ("/stats", "System statistics"),
        ("/analytics", "Analytics"),
        ("/invoices", "Invoice listing"),
    ]
    
    for endpoint, description in endpoints:
        try:
            r = requests.get(f"{BASE}{endpoint}", timeout=10)
            r.raise_for_status()
            data = r.json()
            print(f"✅ {description}: {len(str(data))} chars")
        except Exception as e:
            print(f"❌ {description} failed: {e}")
            return False
    
    return True

def main():
    """Main smoke test"""
    print("🚀 Enhanced OCR Pipeline - Smoke Test")
    print("=" * 50)
    
    # Check if file path provided
    if len(sys.argv) < 2:
        print("Usage: python3 smoke_eval.py <invoice.pdf|image>")
        print("Example: python3 smoke_eval.py ../test_docs/sample_invoice.pdf")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    # Run tests
    tests = [
        ("Health Check", test_health),
        ("Diagnostic Endpoints", test_endpoints),
        ("Upload & Process", lambda: test_upload_and_process(file_path)),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running: {test_name}")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} passed")
            else:
                print(f"❌ {test_name} failed")
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
    
    print("\n" + "=" * 50)
    print(f"🎯 RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ ALL TESTS PASSED - Pipeline is working correctly!")
        print("\n🚀 Ready for production use")
    else:
        print(f"❌ {total - passed} tests failed - check system status")
        sys.exit(1)

if __name__ == "__main__":
    main() 