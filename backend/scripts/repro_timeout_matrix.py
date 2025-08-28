#!/usr/bin/env python3
"""
Repro harness for timeout testing
"""

import os
import sys
import time
import requests
import json
from pathlib import Path

BASE = os.environ.get("OWLIN_API", "http://localhost:8001")

def test_upload_with_timeout(file_path: str, expected_timeout: bool = False) -> dict:
    """Test upload with timeout detection"""
    if not os.path.exists(file_path):
        return {"error": f"File not found: {file_path}"}
    
    print(f"📤 Testing: {os.path.basename(file_path)}")
    
    # Upload file
    try:
        with open(file_path, "rb") as f:
            r = requests.post(
                f"{BASE}/upload", 
                files={"file": (os.path.basename(file_path), f, "application/octet-stream")}, 
                timeout=120
            )
        r.raise_for_status()
        job_data = r.json()
        job_id = job_data["job_id"]
        print(f"✅ Upload successful, job_id: {job_id}")
    except Exception as e:
        return {"error": f"Upload failed: {e}"}
    
    # Poll job status with timeout detection
    start_time = time.time()
    max_wait = 120  # 2 minutes max
    
    for i in range(max_wait):
        try:
            r = requests.get(f"{BASE}/jobs/{job_id}", timeout=10)
            r.raise_for_status()
            job_status = r.json()
            
            if job_status.get("status") == "done":
                duration = time.time() - start_time
                print(f"✅ Job completed in {duration:.1f}s")
                return {
                    "id": job_id,
                    "status": "done",
                    "duration": duration,
                    "timeout": False
                }
            elif job_status.get("status") in ["error", "failed", "timeout"]:
                duration = time.time() - start_time
                print(f"❌ Job failed: {job_status.get('error', 'Unknown error')}")
                return {
                    "id": job_id,
                    "status": job_status.get("status"),
                    "duration": duration,
                    "timeout": job_status.get("status") == "timeout"
                }
            else:
                progress = job_status.get("progress", 0)
                if i % 10 == 0:  # Log every 10 seconds
                    print(f"   Progress: {progress}% ({i}s elapsed)")
                time.sleep(1)
        except Exception as e:
            print(f"❌ Job polling failed: {e}")
            return {"error": f"Polling failed: {e}"}
    
    # Timeout reached
    print(f"❌ Job timed out after {max_wait}s")
    return {
        "id": job_id,
        "status": "timeout",
        "duration": max_wait,
        "timeout": True
    }

def main():
    """Run timeout matrix tests"""
    print("�� OCR Timeout Matrix Test")
    print("=" * 50)
    
    # Test files (you'll need to provide these)
    test_files = [
        "data/test_docs/hospitality_invoices/sample_hosp.png",
        "data/test_docs/utility_bills/ubill1.png",
        "data/test_docs/supermarket_receipts/receipt1.png",
    ]
    
    if not test_files:
        print("No test files specified. Add test files to the script.")
        return
    
    results = []
    for file_path in test_files:
        result = test_upload_with_timeout(file_path)
        results.append({
            "file": os.path.basename(file_path),
            **result
        })
    
    # Summary
    print("\n" + "=" * 50)
    print("�� RESULTS SUMMARY")
    print("=" * 50)
    
    for result in results:
        status_icon = "✅" if result.get("status") == "done" else "❌"
        timeout_icon = "⏰" if result.get("timeout") else ""
        print(f"{status_icon} {result['file']}: {result.get('status', 'error')} "
              f"({result.get('duration', 0):.1f}s) {timeout_icon}")
    
    # Count timeouts
    timeouts = sum(1 for r in results if r.get("timeout"))
    total = len(results)
    print(f"\n⏰ Timeouts: {timeouts}/{total} ({timeouts/total*100:.1f}%)")

if __name__ == "__main__":
    main() 