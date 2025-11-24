"""Test the upload status endpoint"""
import requests
import sqlite3
import json

doc_id = "697fe122-9c7a-47f3-aefa-447568faef2e"

# Test status endpoint
print("Testing /api/upload/status endpoint...")
try:
    r = requests.get(f"http://localhost:8000/api/upload/status?doc_id={doc_id}")
    print(f"Status: {r.status_code}")
    data = r.json()
    print(f"\nResponse keys: {list(data.keys())}")
    print(f"Status: {data.get('status')}")
    print(f"Items count: {len(data.get('items', []))}")
    if data.get('items'):
        print(f"First item: {data['items'][0]}")
    if data.get('parsed'):
        print(f"Parsed data exists: {bool(data.get('parsed'))}")
    if data.get('invoice'):
        print(f"Invoice data exists: {bool(data.get('invoice'))}")
except Exception as e:
    print(f"Error: {e}")

# Check database
print("\nChecking database...")
conn = sqlite3.connect("data/owlin.db")
cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM invoice_line_items WHERE doc_id = ?", (doc_id,))
count = cur.fetchone()[0]
print(f"Line items in DB for doc_id: {count}")

cur.execute("SELECT id FROM invoices WHERE doc_id = ?", (doc_id,))
inv = cur.fetchone()
if inv:
    invoice_id = inv[0]
    print(f"Invoice ID: {invoice_id}")
    cur.execute("SELECT COUNT(*) FROM invoice_line_items WHERE invoice_id = ?", (invoice_id,))
    count_by_inv = cur.fetchone()[0]
    print(f"Line items in DB for invoice_id: {count_by_inv}")
else:
    print("No invoice found for this doc_id")

conn.close()

