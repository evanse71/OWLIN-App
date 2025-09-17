#!/usr/bin/env python3
"""
Test the pairing functionality
"""
import sys
sys.path.insert(0, '.')

from main import app
from fastapi.testclient import TestClient

client = TestClient(app)

# Test pairing
print("Testing pairing...")
response = client.post('/api/delivery-notes/pair', json={
    "delivery_note_id": "DN-TEST-001",
    "invoice_id": "INV-TEST-001"
})
print(f'Pairing response: {response.status_code}')
if response.status_code != 200:
    print('Error:', response.text)
else:
    print('Pairing successful!')

# Test unpairing
print("\nTesting unpairing...")
response = client.post('/api/delivery-notes/unpair', json={
    "delivery_note_id": "DN-TEST-001"
})
print(f'Unpairing response: {response.status_code}')
if response.status_code != 200:
    print('Error:', response.text)
else:
    print('Unpairing successful!')

# Check delivery notes after unpairing
print("\nChecking delivery notes after unpairing...")
response = client.get('/api/delivery-notes')
if response.status_code == 200:
    data = response.json()
    for item in data.get('items', []):
        if item.get('id') == 'DN-TEST-001':
            print(f'DN-TEST-001 status: {item.get("status")}, matched_invoice_id: {item.get("matched_invoice_id")}')
