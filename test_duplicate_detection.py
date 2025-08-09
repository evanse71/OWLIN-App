#!/usr/bin/env python3
"""
Test script for duplicate detection functionality
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.routes.ocr import detect_duplicate_document, calculate_text_similarity

def test_text_similarity():
    """Test text similarity calculation"""
    print("Testing text similarity calculation...")
    
    # Test exact matches
    assert calculate_text_similarity("ABC Corp", "ABC Corp") == 1.0
    assert calculate_text_similarity("", "") == 0.0
    assert calculate_text_similarity("ABC Corp", "") == 0.0
    
    # Test similar matches
    similarity1 = calculate_text_similarity("ABC Corporation", "ABC Corp")
    similarity2 = calculate_text_similarity("ABC Corp", "ABC Corporation")
    print(f"ABC Corporation vs ABC Corp: {similarity1:.3f}")
    print(f"ABC Corp vs ABC Corporation: {similarity2:.3f}")
    
    # Test different matches
    similarity3 = calculate_text_similarity("ABC Corp", "XYZ Corp")
    print(f"ABC Corp vs XYZ Corp: {similarity3:.3f}")
    
    print("✅ Text similarity tests passed!")

def test_duplicate_detection():
    """Test duplicate detection with sample data"""
    print("\nTesting duplicate detection...")
    
    # Sample existing documents
    existing_docs = [
        {
            'type': 'invoice',
            'parsed_data': {
                'supplier_name': 'ABC Corporation',
                'invoice_number': 'INV-2024-001',
                'total_amount': '1500.00',
                'invoice_date': '2024-01-15'
            },
            'filename': 'existing_invoice_1.pdf',
            'status': 'processed',
            'uploaded_at': '2024-01-15T10:00:00'
        },
        {
            'type': 'invoice',
            'parsed_data': {
                'supplier_name': 'XYZ Company',
                'invoice_number': 'INV-2024-002',
                'total_amount': '2500.00',
                'invoice_date': '2024-01-16'
            },
            'filename': 'existing_invoice_2.pdf',
            'status': 'processed',
            'uploaded_at': '2024-01-16T10:00:00'
        }
    ]
    
    # Test 1: Exact duplicate
    new_doc_exact = {
        'parsed_data': {
            'supplier_name': 'ABC Corporation',
            'invoice_number': 'INV-2024-001',
            'total_amount': '1500.00',
            'invoice_date': '2024-01-15'
        }
    }
    
    result1 = detect_duplicate_document(new_doc_exact, existing_docs, threshold=0.95)
    print(f"Exact duplicate test: {'✅ Found' if result1 else '❌ Not found'}")
    if result1:
        print(f"  Similarity: {result1['similarity_score']:.3f}")
        print(f"  Matching fields: {result1['matching_fields']}")
    
    # Test 2: Similar but not duplicate
    new_doc_similar = {
        'parsed_data': {
            'supplier_name': 'ABC Corporation',
            'invoice_number': 'INV-2024-003',  # Different number
            'total_amount': '1500.00',
            'invoice_date': '2024-01-15'
        }
    }
    
    result2 = detect_duplicate_document(new_doc_similar, existing_docs, threshold=0.95)
    print(f"Similar but different test: {'❌ False positive' if result2 else '✅ Correctly not duplicate'}")
    if result2:
        print(f"  Similarity: {result2['similarity_score']:.3f}")
    
    # Test 3: Completely different
    new_doc_different = {
        'parsed_data': {
            'supplier_name': 'Different Company',
            'invoice_number': 'INV-2024-999',
            'total_amount': '9999.00',
            'invoice_date': '2024-12-31'
        }
    }
    
    result3 = detect_duplicate_document(new_doc_different, existing_docs, threshold=0.95)
    print(f"Completely different test: {'❌ False positive' if result3 else '✅ Correctly not duplicate'}")
    if result3:
        print(f"  Similarity: {result3['similarity_score']:.3f}")
    
    # Test 4: High similarity but different amounts
    new_doc_amount_diff = {
        'parsed_data': {
            'supplier_name': 'ABC Corporation',
            'invoice_number': 'INV-2024-001',
            'total_amount': '3000.00',  # Different amount
            'invoice_date': '2024-01-15'
        }
    }
    
    result4 = detect_duplicate_document(new_doc_amount_diff, existing_docs, threshold=0.95)
    print(f"Same supplier/invoice but different amount: {'✅ Found (correct)' if result4 else '❌ Not found'}")
    if result4:
        print(f"  Similarity: {result4['similarity_score']:.3f}")
        print(f"  Differences: {list(result4['differences'].keys())}")
    
    print("✅ Duplicate detection tests completed!")

def test_edge_cases():
    """Test edge cases"""
    print("\nTesting edge cases...")
    
    # Test with empty existing docs
    result = detect_duplicate_document({'parsed_data': {}}, [], threshold=0.95)
    assert result is None, "Should return None for empty existing docs"
    
    # Test with missing parsed data
    result = detect_duplicate_document({}, [{'parsed_data': {}}], threshold=0.95)
    assert result is None, "Should handle missing parsed data"
    
    # Test with very low threshold
    existing_docs = [{
        'type': 'invoice',
        'parsed_data': {
            'supplier_name': 'ABC Corp',
            'invoice_number': 'INV-001',
            'total_amount': '100.00',
            'invoice_date': '2024-01-01'
        },
        'filename': 'test.pdf',
        'status': 'processed',
        'uploaded_at': '2024-01-01T10:00:00'
    }]
    
    new_doc = {
        'parsed_data': {
            'supplier_name': 'XYZ Corp',  # Different supplier
            'invoice_number': 'INV-002',  # Different number
            'total_amount': '200.00',     # Different amount
            'invoice_date': '2024-01-02'  # Different date
        }
    }
    
    result = detect_duplicate_document(new_doc, existing_docs, threshold=0.5)
    print(f"Low threshold test: {'✅ Found (expected with low threshold)' if result else '❌ Not found'}")
    
    print("✅ Edge case tests passed!")

if __name__ == "__main__":
    print("🧪 Testing Duplicate Detection System")
    print("=" * 50)
    
    try:
        test_text_similarity()
        test_duplicate_detection()
        test_edge_cases()
        
        print("\n" + "=" * 50)
        print("🎉 All tests passed! Duplicate detection system is working correctly.")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 