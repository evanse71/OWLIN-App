"""
Test script for the pairing system.

Creates sample invoices and delivery notes, then tests the pairing endpoints.
"""
import os
import sys
from datetime import datetime, timedelta

# Force path so imports always work
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import sqlite3
from backend.app.db import DB_PATH

def create_test_data():
    """Create test invoices and delivery notes"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("=" * 60)
    print("Creating Test Data")
    print("=" * 60)
    
    # Create test supplier
    supplier = "Test Supplier Ltd"
    
    # Create test invoice document
    invoice_doc_id = "test-inv-doc-1"
    cursor.execute("""
        INSERT OR REPLACE INTO documents 
        (id, filename, stored_path, size_bytes, uploaded_at, status, ocr_stage, ocr_confidence, sha256, supplier, doc_date, total, doc_type, venue)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        invoice_doc_id,
        "Test Invoice 001.pdf",
        None,
        0,
        datetime.now().isoformat(),
        'completed',
        'manual',
        1.0,
        'test-hash-inv-1',
        supplier,
        datetime.now().strftime('%Y-%m-%d'),
        150.00,
        'invoice',
        'Main Restaurant'
    ))
    
    # Create test invoice
    invoice_id = "test-inv-1"
    cursor.execute("""
        INSERT OR REPLACE INTO invoices 
        (id, doc_id, supplier, date, value, confidence, status, venue, issues_count, paired, created_at, pairing_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        invoice_id,
        invoice_doc_id,
        supplier,
        datetime.now().strftime('%Y-%m-%d'),
        150.00,
        1.0,
        'ready',
        'Main Restaurant',
        0,
        0,
        datetime.now().isoformat(),
        'unpaired'
    ))
    
    # Create test delivery note document (same supplier, same date, similar total)
    dn_doc_id = "test-dn-doc-1"
    cursor.execute("""
        INSERT OR REPLACE INTO documents 
        (id, filename, stored_path, size_bytes, uploaded_at, status, ocr_stage, ocr_confidence, sha256, supplier, delivery_no, doc_date, total, doc_type, venue)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        dn_doc_id,
        "Test Delivery Note 001.pdf",
        None,
        0,
        datetime.now().isoformat(),
        'completed',
        'manual',
        1.0,
        'test-hash-dn-1',
        supplier,
        'DN-001',
        datetime.now().strftime('%Y-%m-%d'),
        150.00,
        'delivery_note',
        'Main Restaurant'
    ))
    
    # Create another delivery note (different date, should not match)
    dn_doc_id_2 = "test-dn-doc-2"
    cursor.execute("""
        INSERT OR REPLACE INTO documents 
        (id, filename, stored_path, size_bytes, uploaded_at, status, ocr_stage, ocr_confidence, sha256, supplier, delivery_no, doc_date, total, doc_type, venue)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        dn_doc_id_2,
        "Test Delivery Note 002.pdf",
        None,
        0,
        (datetime.now() - timedelta(days=30)).isoformat(),
        'completed',
        'manual',
        1.0,
        'test-hash-dn-2',
        supplier,
        'DN-002',
        (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
        200.00,
        'delivery_note',
        'Main Restaurant'
    ))
    
    conn.commit()
    conn.close()
    
    print(f"\n✓ Created test invoice: {invoice_id}")
    print(f"✓ Created test delivery note 1: {dn_doc_id} (should match)")
    print(f"✓ Created test delivery note 2: {dn_doc_id_2} (should not match)")
    print(f"\nInvoice details:")
    print(f"  Supplier: {supplier}")
    print(f"  Date: {datetime.now().strftime('%Y-%m-%d')}")
    print(f"  Total: £150.00")
    print(f"\nDelivery Note 1 details:")
    print(f"  Supplier: {supplier}")
    print(f"  Date: {datetime.now().strftime('%Y-%m-%d')}")
    print(f"  Total: £150.00")
    print(f"  → Should be a high-confidence match!")
    
    return invoice_id, dn_doc_id

def test_pairing_endpoint(invoice_id):
    """Test the pairing endpoint"""
    import requests
    
    print("\n" + "=" * 60)
    print("Testing Pairing Endpoint")
    print("=" * 60)
    
    try:
        url = f"http://localhost:8000/api/pairing/invoice/{invoice_id}"
        print(f"\nGET {url}")
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print("\n✅ Pairing endpoint responded successfully!")
            print(f"\nStatus: {data.get('status')}")
            print(f"Confidence: {data.get('confidence')}")
            
            if data.get('best_candidate'):
                best = data['best_candidate']
                print(f"\nBest Candidate:")
                print(f"  Delivery Note ID: {best.get('delivery_note_id')}")
                print(f"  Probability: {best.get('probability', 0):.2%}")
                print(f"  Features:")
                features = best.get('features_summary', {})
                for key, value in features.items():
                    print(f"    {key}: {value}")
            
            if data.get('candidates'):
                print(f"\nTotal Candidates: {len(data['candidates'])}")
                for i, cand in enumerate(data['candidates'][:3], 1):
                    print(f"  {i}. DN {cand.get('delivery_note_id')}: {cand.get('probability', 0):.2%}")
        else:
            print(f"\n❌ Error: {response.status_code}")
            print(response.text)
    except requests.exceptions.ConnectionError:
        print("\n❌ Could not connect to backend. Is it running on port 8000?")
        print("   Start it with: python -m uvicorn backend.main:app --port 8000")
    except Exception as e:
        print(f"\n❌ Error: {e}")

def show_pairing_events():
    """Show recent pairing events"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("\n" + "=" * 60)
    print("Recent Pairing Events")
    print("=" * 60)
    
    cursor.execute("""
        SELECT timestamp, invoice_id, delivery_note_id, action, actor_type, model_version
        FROM pairing_events
        ORDER BY timestamp DESC
        LIMIT 10
    """)
    
    events = cursor.fetchall()
    if events:
        print(f"\nFound {len(events)} events:\n")
        for event in events:
            timestamp, inv_id, dn_id, action, actor, model = event
            print(f"  {timestamp} | {action} | Invoice: {inv_id} | DN: {dn_id or 'N/A'} | Actor: {actor}")
    else:
        print("\nNo pairing events yet. Create an invoice and delivery note to see pairing in action!")
    
    conn.close()

def main():
    print("\n" + "=" * 60)
    print("Pairing System Test")
    print("=" * 60)
    
    # Create test data
    invoice_id, dn_id = create_test_data()
    
    # Test pairing endpoint
    test_pairing_endpoint(invoice_id)
    
    # Show pairing events
    show_pairing_events()
    
    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)
    print(f"\nTo test manually:")
    print(f"  1. Check pairing: http://localhost:8000/api/pairing/invoice/{invoice_id}")
    print(f"  2. Confirm pairing: POST http://localhost:8000/api/pairing/invoice/{invoice_id}/confirm")
    print(f"     Body: {{'delivery_note_id': '{dn_id}'}}")
    print()

if __name__ == "__main__":
    main()

