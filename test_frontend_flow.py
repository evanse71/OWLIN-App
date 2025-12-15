#!/usr/bin/env python3
"""Simulate frontend upload + polling flow to debug card creation"""
import requests
import time
import json
import sys
from pathlib import Path

API_BASE = "http://127.0.0.1:8000"

def test_frontend_flow():
    """Simulate exactly what the frontend does"""
    pdf_path = Path("data/dev/test_invoice.pdf")
    if not pdf_path.exists():
        print(f"[ERROR] Test file not found: {pdf_path}")
        sys.exit(1)
    
    print("="*70)
    print("SIMULATING FRONTEND UPLOAD + POLLING FLOW")
    print("="*70)
    
    # Step 1: POST /api/upload (what frontend does)
    print("\n[STEP 1] POST /api/upload")
    print("-" * 70)
    
    with open(pdf_path, 'rb') as f:
        files = {'file': (pdf_path.name, f, 'application/pdf')}
        upload_response = requests.post(f"{API_BASE}/api/upload", files=files)
    
    print(f"Status Code: {upload_response.status_code}")
    print(f"Response Headers: {dict(upload_response.headers)}")
    
    if upload_response.status_code != 200:
        print(f"[CASE 1] POST /api/upload FAILED")
        print(f"Response: {upload_response.text}")
        return "CASE_1"
    
    upload_data = upload_response.json()
    print(f"Response JSON:")
    print(json.dumps(upload_data, indent=2))
    
    doc_id = upload_data.get('doc_id')
    if not doc_id:
        print(f"[CASE 1] POST /api/upload returned no doc_id")
        return "CASE_1"
    
    print(f"\n[OK] Upload successful, doc_id={doc_id}")
    
    # Step 2: Poll /api/upload/status (what frontend does)
    print("\n[STEP 2] Polling GET /api/upload/status (max 40 attempts, 1.5s interval)")
    print("-" * 70)
    
    max_attempts = 40
    last_status_data = None
    
    for attempt in range(max_attempts):
        time.sleep(1.5)
        
        try:
            status_response = requests.get(
                f"{API_BASE}/api/upload/status",
                params={'doc_id': doc_id},
                timeout=5
            )
            
            print(f"\nAttempt {attempt+1}/{max_attempts}:")
            print(f"  Status Code: {status_response.status_code}")
            
            if status_response.status_code != 200:
                print(f"[CASE 2] GET /api/upload/status FAILED (HTTP {status_response.status_code})")
                print(f"  Response: {status_response.text[:500]}")
                return "CASE_2", status_response.text
            
            status_data = status_response.json()
            last_status_data = status_data
            
            status = status_data.get('status', 'unknown')
            has_items = len(status_data.get('items', [])) > 0
            has_parsed = status_data.get('parsed') is not None
            parsed = status_data.get('parsed', {})
            supplier = parsed.get('supplier', 'N/A') if parsed else 'N/A'
            
            print(f"  Response JSON:")
            print(f"    status: {status}")
            print(f"    has_items: {has_items} (count: {len(status_data.get('items', []))})")
            print(f"    has_parsed: {has_parsed}")
            print(f"    parsed.supplier: {supplier}")
            
            # Check frontend conditions (from upload.ts:270)
            is_ready = status in ['ready', 'scanned', 'completed', 'submitted', 'duplicate']
            is_duplicate_or_error_with_data = (status in ['duplicate', 'error']) and (has_items or has_parsed)
            
            should_create_card = has_items or is_ready or is_duplicate_or_error_with_data
            
            print(f"  Frontend logic:")
            print(f"    is_ready: {is_ready}")
            print(f"    is_duplicate_or_error_with_data: {is_duplicate_or_error_with_data}")
            print(f"    should_create_card: {should_create_card}")
            
            if should_create_card:
                print(f"\n[OK] Frontend should create card now!")
                print(f"\n[STEP 3] Final response that frontend would use:")
                print("-" * 70)
                print(json.dumps(status_data, indent=2))
                return "CASE_3_SUCCESS", status_data
            
            if attempt < 5 or attempt % 10 == 0:
                print(f"  (Still polling, waiting for completion...)")
                
        except requests.exceptions.RequestException as e:
            print(f"[CASE 2] GET /api/upload/status FAILED (Network error)")
            print(f"  Error: {e}")
            return "CASE_2", str(e)
        except json.JSONDecodeError as e:
            print(f"[CASE 2] GET /api/upload/status FAILED (Invalid JSON)")
            print(f"  Response: {status_response.text[:500]}")
            print(f"  Error: {e}")
            return "CASE_2", status_response.text
    
    # Timeout
    print(f"\n[WARN] Timeout after {max_attempts} attempts")
    print(f"Last status: {last_status_data.get('status') if last_status_data else 'unknown'}")
    
    if last_status_data and last_status_data.get('status') in ['ready', 'scanned']:
        print(f"\n[CASE 3] Backend says ready, but frontend logic didn't trigger card creation")
        print(f"Last response:")
        print(json.dumps(last_status_data, indent=2))
        return "CASE_3_FRONTEND_BUG", last_status_data
    
    return "TIMEOUT", last_status_data

if __name__ == "__main__":
    result = test_frontend_flow()
    case = result[0] if isinstance(result, tuple) else result
    
    print("\n" + "="*70)
    print(f"DIAGNOSIS: {case}")
    print("="*70)
    
    if case == "CASE_1":
        print("\n[FIX NEEDED] Backend upload endpoint is failing")
        print("Check backend logs for errors during upload")
    elif case == "CASE_2":
        print("\n[FIX NEEDED] Backend status endpoint is failing")
        print("Check backend logs for errors during status polling")
    elif case == "CASE_3_SUCCESS":
        print("\n[OK] Backend working, frontend should create card")
    elif case == "CASE_3_FRONTEND_BUG":
        print("\n[FIX NEEDED] Backend returns ready, but frontend logic doesn't create card")
        print("Need to fix frontend polling conditions in upload.ts")
    else:
        print("\n[UNKNOWN] Unexpected result")
