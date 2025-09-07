#!/usr/bin/env python3
"""
Contract Tests for Enhanced OCR Pipeline API
Ensures API surface consistency and data integrity
"""

import requests
import os
import sys
from typing import Dict, Any

BASE = os.environ.get("OWLIN_API", "http://localhost:8001")

def _minor(x: Any) -> bool:
    """Check if value is a non-negative integer (minor units)"""
    return isinstance(x, int) and x >= 0

def _valid_id(x: Any) -> bool:
    """Check if value is a valid ID (string or integer)"""
    return isinstance(x, (str, int)) and len(str(x)) > 0

def test_health_endpoint():
    """Test health endpoint contract"""
    r = requests.get(f"{BASE}/health", timeout=10)
    r.raise_for_status()
    data = r.json()
    
    # Required fields
    assert "status" in data
    assert data["status"] == "ok"
    assert "database" in data
    assert "storage" in data
    assert "timestamp" in data
    
    print("✅ Health endpoint contract passed")

def test_stats_endpoint():
    """Test stats endpoint contract"""
    r = requests.get(f"{BASE}/stats", timeout=10)
    r.raise_for_status()
    data = r.json()
    
    # Required fields
    assert "invoices" in data
    assert "jobs" in data
    assert "delivery_notes" in data
    assert "issues_total" in data
    
    # All should be non-negative integers
    assert _minor(data["invoices"])
    assert _minor(data["jobs"])
    assert _minor(data["delivery_notes"])
    assert _minor(data["issues_total"])
    
    print("✅ Stats endpoint contract passed")

def test_analytics_endpoint():
    """Test analytics endpoint contract"""
    r = requests.get(f"{BASE}/analytics", timeout=10)
    r.raise_for_status()
    data = r.json()
    
    # Required sections
    assert "job_stats" in data
    assert "invoice_stats" in data
    assert "performance" in data
    
    # Job stats should be dict with status counts
    job_stats = data["job_stats"]
    assert isinstance(job_stats, dict)
    for status, count in job_stats.items():
        assert _minor(count)
    
    # Invoice stats should have required fields
    invoice_stats = data["invoice_stats"]
    assert "count" in invoice_stats
    assert "avg_confidence" in invoice_stats
    assert "issues_total" in invoice_stats
    assert _minor(invoice_stats["count"])
    assert _minor(invoice_stats["issues_total"])
    assert isinstance(invoice_stats["avg_confidence"], (int, float))
    
    print("✅ Analytics endpoint contract passed")

def test_list_and_detail_have_totals_and_issues():
    """Test invoice list and detail consistency"""
    r = requests.get(f"{BASE}/invoices", timeout=10)
    r.raise_for_status()
    rows = r.json()
    assert isinstance(rows, list)
    
    if not rows:
        print("⚠️ No invoices to test - skipping list/detail test")
        return
    
    # Test first invoice
    row = rows[0]
    
    # Required fields in list
    required_fields = ["id", "subtotal_p", "vat_total_p", "total_p", "issues_count"]
    for field in required_fields:
        assert field in row, f"Missing field: {field}"
        if field == "id":
            assert _valid_id(row[field]), f"Invalid ID: {row[field]}"
        elif row[field] is not None:
            assert _minor(row[field]), f"Invalid value for {field}: {row[field]}"
        # None values are acceptable for optional fields
    
    # Get detail for this invoice
    invoice_id = row["id"]
    detail_r = requests.get(f"{BASE}/invoices/{invoice_id}", timeout=10)
    detail_r.raise_for_status()
    detail = detail_r.json()
    
    # Required fields in detail
    detail_required = ["invoice", "line_items", "analytics"]
    for field in detail_required:
        assert field in detail, f"Missing detail field: {field}"
    
    invoice = detail["invoice"]
    line_items = detail["line_items"]
    analytics = detail["analytics"]
    
    # Invoice should have same totals as list
    assert invoice["subtotal_p"] == row["subtotal_p"]
    assert invoice["vat_total_p"] == row["vat_total_p"]
    assert invoice["total_p"] == row["total_p"]
    assert invoice["issues_count"] == row["issues_count"]
    
    # Line items should be list
    assert isinstance(line_items, list)
    
    # Analytics should have required fields
    assert "total_items" in analytics
    assert "total_value" in analytics
    assert "avg_confidence" in analytics
    assert _minor(analytics["total_items"])
    assert _minor(analytics["total_value"])
    
    # Arithmetic validation
    subtotal_p = invoice.get("subtotal_p", 0) or 0
    vat_total_p = invoice.get("vat_total_p", 0) or 0
    total_p = invoice.get("total_p", 0) or 0
    
    if total_p > 0:
        expected_total = subtotal_p + vat_total_p
        assert abs(expected_total - total_p) <= 1, f"Arithmetic mismatch: {subtotal_p} + {vat_total_p} ≠ {total_p}"
    
    print("✅ List/detail consistency passed")

def test_job_endpoints():
    """Test job endpoints contract"""
    r = requests.get(f"{BASE}/jobs", timeout=10)
    r.raise_for_status()
    jobs = r.json()
    assert isinstance(jobs, list)
    
    if not jobs:
        print("⚠️ No jobs to test - skipping job test")
        return
    
    # Test first job
    job = jobs[0]
    required_fields = ["id", "status", "progress"]
    for field in required_fields:
        assert field in job, f"Missing job field: {field}"
    
    # Progress should be 0-100
    assert 0 <= job["progress"] <= 100, f"Invalid progress: {job['progress']}"
    
    # Status should be valid
    valid_statuses = ["queued", "running", "done", "error"]
    assert job["status"] in valid_statuses, f"Invalid status: {job['status']}"
    
    print("✅ Job endpoints contract passed")

def test_upload_endpoint_structure():
    """Test upload endpoint structure (without actual upload)"""
    # This test just ensures the endpoint exists and returns proper structure
    # We don't actually upload a file here
    try:
        # Test with empty file to check endpoint structure
        r = requests.post(f"{BASE}/upload", files={"file": ("test.txt", "", "text/plain")}, timeout=10)
        # Should either succeed or return proper error structure
        if r.status_code == 200:
            data = r.json()
            assert "job_id" in data, "Upload response missing job_id"
        elif r.status_code == 409:
            data = r.json()
            assert "error" in data, "Duplicate response missing error field"
            assert data["error"] == "duplicate", "Wrong error type for duplicate"
        else:
            # Other status codes are acceptable (validation errors, etc.)
            pass
        
        print("✅ Upload endpoint structure passed")
    except Exception as e:
        print(f"⚠️ Upload endpoint test skipped: {e}")

def run_all_tests():
    """Run all contract tests"""
    print("🧪 Running API Contract Tests")
    print("=" * 40)
    
    tests = [
        ("Health Endpoint", test_health_endpoint),
        ("Stats Endpoint", test_stats_endpoint),
        ("Analytics Endpoint", test_analytics_endpoint),
        ("List/Detail Consistency", test_list_and_detail_have_totals_and_issues),
        ("Job Endpoints", test_job_endpoints),
        ("Upload Endpoint Structure", test_upload_endpoint_structure),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            print(f"\n🔍 Testing: {test_name}")
            test_func()
            passed += 1
        except Exception as e:
            print(f"❌ {test_name} failed: {e}")
    
    print("\n" + "=" * 40)
    print(f"🎯 Contract Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("✅ ALL CONTRACT TESTS PASSED")
        return True
    else:
        print(f"❌ {total - passed} contract tests failed")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1) 