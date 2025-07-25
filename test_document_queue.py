#!/usr/bin/env python3
"""
Test script for Document Queue implementation.
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000/api"

def test_document_queue_api():
    """Test the document queue API endpoints"""
    print("🧪 Testing Document Queue API...")
    
    try:
        # Test 1: Get documents for review
        print("\n1. Testing GET /documents/queue")
        response = requests.get(f"{BASE_URL}/documents/queue")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Documents found: {len(data.get('documents', []))}")
            if data.get('documents'):
                print("Sample document:")
                doc = data['documents'][0]
                print(f"  - ID: {doc.get('id')}")
                print(f"  - Filename: {doc.get('filename')}")
                print(f"  - Status: {doc.get('status')}")
                print(f"  - Status Badge: {doc.get('status_badge')}")
                print(f"  - Confidence: {doc.get('confidence')}")
        else:
            print(f"Error: {response.text}")
        
        # Test 2: Approve a document (if documents exist)
        if response.status_code == 200 and data.get('documents'):
            print("\n2. Testing POST /documents/{id}/approve")
            doc_id = data['documents'][0]['id']
            review_data = {
                "document_type": "invoice",
                "supplier_name": "Test Supplier",
                "invoice_number": "INV-001",
                "invoice_date": "2024-01-15",
                "total_amount": 1500.00,
                "confidence": 0.95,
                "extracted_text": "Sample extracted text",
                "reviewed_by": "test_user"
            }
            
            response = requests.post(
                f"{BASE_URL}/documents/{doc_id}/approve",
                json=review_data
            )
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                print("Document approved successfully!")
            else:
                print(f"Error: {response.text}")
        
        # Test 3: Escalate a document
        print("\n3. Testing POST /documents/{id}/escalate")
        escalation_data = {
            "reason": "Test escalation",
            "comments": "This is a test escalation"
        }
        
        response = requests.post(
            f"{BASE_URL}/documents/test-id/escalate",
            json=escalation_data
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("Document escalated successfully!")
        else:
            print(f"Error: {response.text}")
        
        # Test 4: Delete a document
        print("\n4. Testing DELETE /documents/{id}")
        response = requests.delete(f"{BASE_URL}/documents/test-id")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("Document deleted successfully!")
        else:
            print(f"Error: {response.text}")
        
        print("\n✅ Document Queue API tests completed!")
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to the API server. Make sure the backend is running on http://localhost:8000")
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")

def test_frontend_components():
    """Test the frontend components"""
    print("\n🧪 Testing Frontend Components...")
    
    try:
        # Test if the document queue page exists
        import os
        if os.path.exists("pages/document-queue.tsx"):
            print("✅ Document Queue page exists")
        else:
            print("❌ Document Queue page not found")
        
        if os.path.exists("components/document-queue/DocumentQueueCard.tsx"):
            print("✅ DocumentQueueCard component exists")
        else:
            print("❌ DocumentQueueCard component not found")
        
        if os.path.exists("components/document-queue/DocumentReviewModal.tsx"):
            print("✅ DocumentReviewModal component exists")
        else:
            print("❌ DocumentReviewModal component not found")
        
        # Test if API service functions exist
        if os.path.exists("services/api.ts"):
            with open("services/api.ts", "r") as f:
                content = f.read()
                if "getDocumentsForReview" in content:
                    print("✅ getDocumentsForReview API function exists")
                else:
                    print("❌ getDocumentsForReview API function not found")
                
                if "approveDocument" in content:
                    print("✅ approveDocument API function exists")
                else:
                    print("❌ approveDocument API function not found")
                
                if "escalateDocument" in content:
                    print("✅ escalateDocument API function exists")
                else:
                    print("❌ escalateDocument API function not found")
                
                if "deleteDocument" in content:
                    print("✅ deleteDocument API function exists")
                else:
                    print("❌ deleteDocument API function not found")
        
        print("\n✅ Frontend component tests completed!")
        
    except Exception as e:
        print(f"❌ Frontend test failed with error: {str(e)}")

def main():
    """Run all tests"""
    print("🚀 Starting Document Queue Implementation Tests...")
    print("=" * 50)
    
    test_frontend_components()
    test_document_queue_api()
    
    print("\n" + "=" * 50)
    print("🎉 All tests completed!")

if __name__ == "__main__":
    main() 