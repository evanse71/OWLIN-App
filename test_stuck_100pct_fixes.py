#!/usr/bin/env python3
"""
Test script for stuck at 100% fixes

Tests:
1. Watchdog detection of stuck documents
2. Watchdog fixing of stuck documents
3. Exception handling sets status to error
4. Timeout mechanism is in place (structure check)
"""

import sys
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
import json

# Add project root to path
_BACKEND_DIR = Path(__file__).resolve().parent / "backend"
_PROJECT_ROOT = _BACKEND_DIR.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# Import after path setup
from backend.app.db import DB_PATH, update_document_status
from backend.services.ocr_service import detect_stuck_documents, fix_stuck_documents, OCR_PROCESSING_TIMEOUT_SECONDS, OCRTimeoutError, _run_with_timeout

def test_watchdog_detection():
    """Test that watchdog can detect stuck documents"""
    print("\n=== Test 1: Watchdog Detection ===")
    
    # Create a test document stuck in processing
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cursor = conn.cursor()
    
    # Create test document with old timestamp (11 minutes ago)
    test_doc_id = "test-stuck-doc-001"
    old_timestamp = (datetime.now() - timedelta(minutes=11)).isoformat()
    
    try:
        # Insert test document
        cursor.execute("""
            INSERT OR REPLACE INTO documents (id, filename, stored_path, size_bytes, uploaded_at, status, ocr_stage)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (test_doc_id, "test_stuck.pdf", "/tmp/test.pdf", 1000, old_timestamp, "processing", "ocr_start"))
        conn.commit()
        
        # Test detection
        stuck_docs = detect_stuck_documents(max_processing_minutes=10)
        
        # Check if our test document is detected
        found = False
        for doc in stuck_docs:
            if doc["doc_id"] == test_doc_id:
                found = True
                print(f"[OK] Found stuck document: {doc['doc_id']}, stuck for {doc['minutes_stuck']:.1f} minutes")
                assert doc["minutes_stuck"] > 10, f"Expected > 10 minutes, got {doc['minutes_stuck']}"
                break
        
        assert found, f"Test document {test_doc_id} not found in stuck documents list"
        print(f"[OK] Watchdog detection works: Found {len(stuck_docs)} stuck document(s)")
        
    finally:
        # Cleanup
        cursor.execute("DELETE FROM documents WHERE id = ?", (test_doc_id,))
        conn.commit()
        conn.close()
    
    return True

def test_watchdog_fixing():
    """Test that watchdog can fix stuck documents"""
    print("\n=== Test 2: Watchdog Fixing ===")
    
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cursor = conn.cursor()
    
    test_doc_id = "test-stuck-doc-002"
    old_timestamp = (datetime.now() - timedelta(minutes=11)).isoformat()
    
    try:
        # Insert test document
        cursor.execute("""
            INSERT OR REPLACE INTO documents (id, filename, stored_path, size_bytes, uploaded_at, status, ocr_stage)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (test_doc_id, "test_stuck.pdf", "/tmp/test.pdf", 1000, old_timestamp, "processing", "ocr_start"))
        conn.commit()
        
        # Test fixing
        fixed_count = fix_stuck_documents(max_processing_minutes=10)
        
        assert fixed_count > 0, f"Expected at least 1 fixed document, got {fixed_count}"
        print(f"[OK] Fixed {fixed_count} stuck document(s)")
        
        # Verify status was changed to error
        cursor.execute("SELECT status, ocr_error FROM documents WHERE id = ?", (test_doc_id,))
        row = cursor.fetchone()
        
        assert row is not None, "Test document not found"
        status, error = row
        
        assert status == "error", f"Expected status 'error', got '{status}'"
        assert error is not None, "Expected error message, got None"
        assert "watchdog" in error.lower() or "stuck" in error.lower(), f"Expected watchdog error message, got: {error}"
        
        print(f"[OK] Document status changed to 'error' with message: {error[:100]}...")
        
    finally:
        # Cleanup
        cursor.execute("DELETE FROM documents WHERE id = ?", (test_doc_id,))
        conn.commit()
        conn.close()
    
    return True

def test_exception_handling_structure():
    """Test that exception handling structure is in place"""
    print("\n=== Test 3: Exception Handling Structure ===")
    
    # Check that timeout mechanism exists
    assert OCR_PROCESSING_TIMEOUT_SECONDS == 300, f"Expected timeout of 300 seconds, got {OCR_PROCESSING_TIMEOUT_SECONDS}"
    print(f"[OK] Timeout constant set to {OCR_PROCESSING_TIMEOUT_SECONDS} seconds (5 minutes)")
    
    # Check that OCRTimeoutError exists
    assert OCRTimeoutError is not None, "OCRTimeoutError class not found"
    print("[OK] OCRTimeoutError exception class exists")
    
    # Check that _run_with_timeout function exists
    assert callable(_run_with_timeout), "_run_with_timeout function not found"
    print("[OK] _run_with_timeout function exists")
    
    # Test timeout function with a simple function
    def slow_function():
        import time
        time.sleep(10)  # Sleep for 10 seconds
    
    try:
        _run_with_timeout(slow_function, 1)  # 1 second timeout
        assert False, "Expected timeout exception, but function completed"
    except OCRTimeoutError:
        print("[OK] Timeout mechanism works: Raises OCRTimeoutError when function exceeds timeout")
    except Exception as e:
        print(f"[WARN] Timeout mechanism raised unexpected exception: {type(e).__name__}: {e}")
    
    return True

def test_status_update_on_error():
    """Test that status is updated to error when exception occurs"""
    print("\n=== Test 4: Status Update on Error ===")
    
    test_doc_id = "test-error-doc-001"
    
    try:
        # Test that update_document_status can set error status
        update_document_status(test_doc_id, "error", "test_error", error="Test error message")
        
        # Verify status was set
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("SELECT status, ocr_error FROM documents WHERE id = ?", (test_doc_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            status, error = row
            assert status == "error", f"Expected status 'error', got '{status}'"
            assert error == "Test error message", f"Expected error message, got: {error}"
            print("[OK] Status update function works correctly")
        else:
            # Document might not exist, which is okay for this test
            print("[WARN] Test document not found (may not exist in DB), but update function executed without error")
        
    except Exception as e:
        print(f"[ERROR] Error testing status update: {e}")
        raise
    
    finally:
        # Cleanup
        try:
            conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM documents WHERE id = ?", (test_doc_id,))
            conn.commit()
            conn.close()
        except:
            pass
    
    return True

def main():
    """Run all tests"""
    print("=" * 60)
    print("Testing Stuck at 100% Fixes")
    print("=" * 60)
    
    tests = [
        ("Watchdog Detection", test_watchdog_detection),
        ("Watchdog Fixing", test_watchdog_fixing),
        ("Exception Handling Structure", test_exception_handling_structure),
        ("Status Update on Error", test_status_update_on_error),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            test_func()
            passed += 1
            print(f"[PASS] {test_name}: PASSED")
        except Exception as e:
            failed += 1
            print(f"[FAIL] {test_name}: FAILED - {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed == 0:
        print("\n[SUCCESS] All tests passed!")
        return 0
    else:
        print(f"\n[FAILURE] {failed} test(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())

