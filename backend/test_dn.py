#!/usr/bin/env python3
"""
Test the delivery notes endpoint
"""
import sys
sys.path.insert(0, '.')

from main import app
from fastapi.testclient import TestClient

client = TestClient(app)
response = client.get('/api/delivery-notes')
print('Delivery notes endpoint response:', response.status_code)
if response.status_code != 200:
    print('Error:', response.text)
else:
    data = response.json()
    print('Found', len(data.get('items', [])), 'delivery notes')
    for item in data.get('items', [])[:3]:
        print(f'  - {item.get("id")}: {item.get("supplier")} ({item.get("status")})')
