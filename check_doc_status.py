#!/usr/bin/env python3
"""Check document status and diagnose polling issue"""
import sqlite3
import requests
import json

DB_PATH = "data/owlin.db"
API_BASE = "http://127.0.0.1:8000"

def main():
    doc_id = "5cd7c9f7-25a5-405c-b632-ca49cc589545"
    
    # Check database
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, status, ocr_stage, ocr_error FROM documents WHERE id = ?", (doc_id,))
    doc = cur.fetchone()
    
    print("="*70)
    print("DOCUMENT STATUS CHECK")
    print("="*70)
    
    if doc:
        print(f"\nDatabase Status:")
        print(f"  ID: {doc[0]}")
        print(f"  Status: {doc[1]}")
        print(f"  OCR Stage: {doc[2]}")
        print(f"  Error: {doc[3]}")
    else:
        print(f"\nDocument {doc_id} not found in database")
        conn.close()
        return
    
    # Check API status
    print(f"\nAPI Status Endpoint:")
    try:
        response = requests.get(f"{API_BASE}/api/upload/status", params={'doc_id': doc_id})
        if response.status_code == 200:
            data = response.json()
            print(f"  Status: {data.get('status')}")
            print(f"  Has parsed: {data.get('parsed') is not None}")
            print(f"  Has items: {len(data.get('items', [])) > 0}")
            print(f"  Full response:")
            print(json.dumps(data, indent=2))
        else:
            print(f"  Error: HTTP {response.status_code}")
            print(f"  Response: {response.text}")
    except Exception as e:
        print(f"  Error: {e}")
    
    # Check recent audit logs
    print(f"\nRecent Audit Logs for this document:")
    cur.execute("SELECT ts, actor, action, detail FROM audit_log WHERE detail LIKE ? ORDER BY ts DESC LIMIT 10", (f'%{doc_id}%',))
    rows = cur.fetchall()
    for row in rows:
        detail = row[3][:100] if row[3] else ""
        print(f"  {row[0]}: {row[2]} - {detail}")
    
    conn.close()
    
    # Frontend logic check
    print(f"\n" + "="*70)
    print("FRONTEND POLLING LOGIC CHECK")
    print("="*70)
    
    if doc[1] == "processing":
        print("\n[ISSUE] Document stuck in 'processing' status")
        print("Frontend will keep polling until:")
        print("  1. hasItems = True, OR")
        print("  2. status in ['ready', 'scanned', 'completed', 'submitted', 'duplicate'], OR")
        print("  3. (status in ['duplicate', 'error']) AND (hasItems OR hasData)")
        print("\nCurrent state doesn't meet any of these conditions.")
        print("\nPossible fixes:")
        print("  1. Wait longer for OCR to complete (may take 60-120 seconds)")
        print("  2. Fix frontend to show 'processing' card with basic info")
        print("  3. Check if OCR background task is actually running")

if __name__ == "__main__":
    main()
