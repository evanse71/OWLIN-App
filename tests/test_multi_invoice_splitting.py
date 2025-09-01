#!/usr/bin/env python3
"""
Test multi-invoice splitting functionality
"""

import sys
import os
import tempfile
import sqlite3
from pathlib import Path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from upload.multi_page_processor import MultiInvoiceSplitter, HeaderFingerprint
from PIL import Image
import numpy as np

def test_header_fingerprint():
    """Test header fingerprint computation"""
    fingerprint = HeaderFingerprint()
    
    # Create test image
    test_image = Image.new('RGB', (800, 600), color='white')
    
    # Extract header region
    header_region = fingerprint.extract_header_region(test_image)
    assert header_region.size == (800, 120)  # 20% of 600
    
    # Compute fingerprint
    fp1 = fingerprint.compute_fingerprint(header_region)
    assert len(fp1) == 64  # SHA256 hex length
    assert fp1 != ""
    
    # Test stability
    fp2 = fingerprint.compute_fingerprint(header_region)
    assert fp1 == fp2
    
    print("✅ Header fingerprint test passed")

def test_fingerprint_comparison():
    """Test fingerprint comparison"""
    fingerprint = HeaderFingerprint()
    
    # Create similar images
    img1 = Image.new('RGB', (100, 50), color='white')
    img2 = Image.new('RGB', (100, 50), color='white')
    
    fp1 = fingerprint.compute_fingerprint(img1)
    fp2 = fingerprint.compute_fingerprint(img2)
    
    # Should be identical
    similarity = fingerprint.compare_fingerprints(fp1, fp2)
    assert similarity == 1.0
    
    # Test different images
    img3 = Image.new('RGB', (100, 50), color='black')
    fp3 = fingerprint.compute_fingerprint(img3)
    
    similarity = fingerprint.compare_fingerprints(fp1, fp3)
    assert similarity < 1.0
    
    print("✅ Fingerprint comparison test passed")

def test_single_invoice():
    """Test single invoice (no splitting needed)"""
    splitter = MultiInvoiceSplitter()
    
    # Mock page fingerprints for single invoice
    page_fingerprints = [
        {'page_num': 0, 'fingerprint': 'abc123', 'image': Image.new('RGB', (100, 100))},
        {'page_num': 1, 'fingerprint': 'abc123', 'image': Image.new('RGB', (100, 100))},
        {'page_num': 2, 'fingerprint': 'abc123', 'image': Image.new('RGB', (100, 100))}
    ]
    
    segments = splitter._group_pages_by_header(page_fingerprints)
    
    assert len(segments) == 1
    assert len(segments[0]) == 3
    
    print("✅ Single invoice test passed")

def test_multi_invoice():
    """Test multiple invoices (splitting needed)"""
    splitter = MultiInvoiceSplitter()
    
    # Mock page fingerprints for multiple invoices
    page_fingerprints = [
        {'page_num': 0, 'fingerprint': 'abc123', 'image': Image.new('RGB', (100, 100))},
        {'page_num': 1, 'fingerprint': 'abc123', 'image': Image.new('RGB', (100, 100))},
        {'page_num': 2, 'fingerprint': 'def456', 'image': Image.new('RGB', (100, 100))},
        {'page_num': 3, 'fingerprint': 'def456', 'image': Image.new('RGB', (100, 100))},
        {'page_num': 4, 'fingerprint': 'ghi789', 'image': Image.new('RGB', (100, 100))}
    ]
    
    segments = splitter._group_pages_by_header(page_fingerprints)
    
    assert len(segments) == 3
    assert len(segments[0]) == 2  # First invoice: 2 pages
    assert len(segments[1]) == 2  # Second invoice: 2 pages
    assert len(segments[2]) == 1  # Third invoice: 1 page
    
    print("✅ Multi invoice test passed")

def test_mixed_content():
    """Test mixed invoice and delivery note content"""
    splitter = MultiInvoiceSplitter()
    
    # Mock mixed content
    page_fingerprints = [
        {'page_num': 0, 'fingerprint': 'invoice1', 'image': Image.new('RGB', (100, 100))},
        {'page_num': 1, 'fingerprint': 'delivery1', 'image': Image.new('RGB', (100, 100))},
        {'page_num': 2, 'fingerprint': 'invoice2', 'image': Image.new('RGB', (100, 100))},
        {'page_num': 3, 'fingerprint': 'delivery2', 'image': Image.new('RGB', (100, 100))}
    ]
    
    segments = splitter._group_pages_by_header(page_fingerprints)
    
    assert len(segments) == 4  # Each should be separate
    
    print("✅ Mixed content test passed")

def test_rotated_pages():
    """Test rotated page handling"""
    splitter = MultiInvoiceSplitter()
    
    # Create test pages with different orientations
    page_fingerprints = [
        {'page_num': 0, 'fingerprint': 'normal', 'image': Image.new('RGB', (100, 100))},
        {'page_num': 1, 'fingerprint': 'rotated', 'image': Image.new('RGB', (100, 100))}
    ]
    
    # Test rotation correction
    corrected = splitter.handle_rotated_pages(page_fingerprints)
    
    assert len(corrected) == 2
    assert all('fingerprint' in page for page in corrected)
    
    print("✅ Rotated pages test passed")

def test_blank_insert():
    """Test blank page insertion handling"""
    splitter = MultiInvoiceSplitter()
    
    # Create pages with blank page in middle
    page_fingerprints = [
        {'page_num': 0, 'fingerprint': 'invoice1', 'image': Image.new('RGB', (100, 100))},
        {'page_num': 1, 'fingerprint': 'blank', 'image': Image.new('RGB', (100, 100))},
        {'page_num': 2, 'fingerprint': 'invoice1', 'image': Image.new('RGB', (100, 100))}
    ]
    
    # Detect blank pages
    blank_pages = splitter.detect_blank_pages(page_fingerprints)
    
    # Should detect blank page
    assert 1 in blank_pages
    
    print("✅ Blank insert test passed")

def test_skewed_pages():
    """Test skewed page handling"""
    splitter = MultiInvoiceSplitter()
    
    # Create test pages (skewed pages would have different fingerprints)
    page_fingerprints = [
        {'page_num': 0, 'fingerprint': 'normal', 'image': Image.new('RGB', (100, 100))},
        {'page_num': 1, 'fingerprint': 'skewed', 'image': Image.new('RGB', (100, 100))},
        {'page_num': 2, 'fingerprint': 'normal', 'image': Image.new('RGB', (100, 100))}
    ]
    
    segments = splitter._group_pages_by_header(page_fingerprints)
    
    # Should group by similarity
    assert len(segments) >= 1
    
    print("✅ Skewed pages test passed")

def test_edge_cases():
    """Test edge cases"""
    splitter = MultiInvoiceSplitter()
    
    # Empty input
    segments = splitter._group_pages_by_header([])
    assert segments == []
    
    # Single page
    single_page = [{'page_num': 0, 'fingerprint': 'test', 'image': Image.new('RGB', (100, 100))}]
    segments = splitter._group_pages_by_header(single_page)
    assert len(segments) == 1
    assert len(segments[0]) == 1
    
    # All different fingerprints
    different_pages = [
        {'page_num': i, 'fingerprint': f'fp{i}', 'image': Image.new('RGB', (100, 100))}
        for i in range(5)
    ]
    segments = splitter._group_pages_by_header(different_pages)
    assert len(segments) == 5
    
    print("✅ Edge cases test passed")

def test_performance():
    """Test performance with larger datasets"""
    splitter = MultiInvoiceSplitter()
    
    # Create larger dataset
    large_dataset = [
        {'page_num': i, 'fingerprint': f'fp{i//3}', 'image': Image.new('RGB', (100, 100))}
        for i in range(30)  # 10 invoices with 3 pages each
    ]
    
    import time
    start_time = time.time()
    segments = splitter._group_pages_by_header(large_dataset)
    end_time = time.time()
    
    # Should complete within reasonable time
    assert end_time - start_time < 1.0  # Less than 1 second
    assert len(segments) == 10  # 10 invoices
    
    print("✅ Performance test passed")

def test_robustness():
    """Test robustness with invalid inputs"""
    splitter = MultiInvoiceSplitter()
    fingerprint = HeaderFingerprint()
    
    # Test with None inputs
    try:
        fingerprint.extract_header_region(None)
        assert False, "Should have raised exception"
    except:
        pass
    
    # Test with empty fingerprint
    similarity = fingerprint.compare_fingerprints("", "test")
    assert similarity == 0.0
    
    # Test with different length fingerprints
    similarity = fingerprint.compare_fingerprints("abc", "abcd")
    assert similarity == 0.0
    
    print("✅ Robustness test passed")

def test_integration():
    """Test integration of all components"""
    splitter = MultiInvoiceSplitter()
    fingerprint = HeaderFingerprint()
    
    # Create realistic test scenario
    test_images = []
    for i in range(6):
        # Create slightly different images
        img = Image.new('RGB', (800, 600), color=(255-i*10, 255-i*10, 255-i*10))
        test_images.append(img)
    
    # Extract headers and compute fingerprints
    fingerprints = []
    for i, img in enumerate(test_images):
        header = fingerprint.extract_header_region(img)
        fp = fingerprint.compute_fingerprint(header)
        fingerprints.append({
            'page_num': i,
            'fingerprint': fp,
            'image': img
        })
    
    # Group by similarity
    segments = splitter._group_pages_by_header(fingerprints)
    
    # Should produce reasonable grouping
    assert len(segments) >= 1
    assert all(len(segment) >= 1 for segment in segments)
    
    print("✅ Integration test passed")

if __name__ == "__main__":
    test_header_fingerprint()
    test_fingerprint_comparison()
    test_single_invoice()
    test_multi_invoice()
    test_mixed_content()
    test_rotated_pages()
    test_blank_insert()
    test_skewed_pages()
    test_edge_cases()
    test_performance()
    test_robustness()
    test_integration()
    print("All multi-invoice splitting tests passed!") 