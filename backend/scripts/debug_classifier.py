#!/usr/bin/env python3
"""
Debug Classifier Script

Test the classifier to see what's happening with scores and confidence
"""

import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ocr.classifier import get_document_classifier

def test_classifier():
    """Test the classifier with sample text"""
    classifier = get_document_classifier()
    
    # Test invoice text
    invoice_text = """
    WILD HORSE BREWING CO LTD
    Invoice Number: INV-2025-001
    Date: 15/08/2025
    
    Description                    Qty    Unit Price    Total
    Premium Lager                  24     £2.50         £60.00
    Craft IPA                      12     £3.20         £38.40
    VAT (20%)                                      £19.68
    Total Amount Due:                              £118.08
    """
    
    print("🧪 Testing Invoice Classification")
    print("=" * 50)
    
    result = classifier.classify_document(invoice_text)
    
    print(f"Doc Type: {result.doc_type}")
    print(f"Confidence: {result.confidence:.3f}")
    print(f"Reasons: {result.reasons}")
    print(f"Features: {result.features}")
    print(f"Alternative Types: {result.alternative_types}")
    
    # Test menu text
    menu_text = """
    THE RED LION PUB
    Menu
    
    Starters
    - Soup of the Day          £5.50
    - Garlic Bread             £3.50
    
    Mains
    - Fish & Chips            £12.50
    - Steak & Ale Pie         £14.50
    """
    
    print("\n🧪 Testing Menu Classification")
    print("=" * 50)
    
    result = classifier.classify_document(menu_text)
    
    print(f"Doc Type: {result.doc_type}")
    print(f"Confidence: {result.confidence:.3f}")
    print(f"Reasons: {result.reasons}")
    print(f"Features: {result.features}")
    print(f"Alternative Types: {result.alternative_types}")

if __name__ == "__main__":
    test_classifier() 