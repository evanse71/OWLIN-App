#!/usr/bin/env python3
"""
Simple test for boundary detection logic
"""

import re
from dataclasses import dataclass
from typing import List

@dataclass
class MockOCRResult:
    """Mock OCR result for testing"""
    text: str
    confidence: float
    page_number: int

@dataclass
class MockInvoiceBlock:
    """Mock invoice block for testing"""
    page_start: int
    page_end: int
    confidence: float
    requires_manual_review: bool
    header_text: str = ""
    supplier_guess: str = ""

def detect_invoice_boundaries_mock(pages: List[MockOCRResult]) -> List[MockInvoiceBlock]:
    """
    Mock implementation of invoice boundary detection
    """
    print(f"🔍 Detecting invoice boundaries across {len(pages)} pages")
    
    if not pages:
        print("⚠️ No pages provided for boundary detection")
        return []
    
    # Header regexes to detect new invoice starts
    header_patterns = [
        r'\b(?:invoice|inv)\s*(?:no|number|#)\s*[:.]?\s*([A-Z0-9\-/]+)',
        r'\b(?:invoice|inv)\s*(?:date|dated)\s*[:.]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        r'\b(?:supplier|vendor|company)\s*[:.]?\s*([A-Za-z\s&]+)',
        r'\b(?:vat\s*reg|vat\s*registration)\s*[:.]?\s*([A-Z0-9]+)',
        r'\b(?:bill\s*to|ship\s*to)\s*[:.]?\s*([A-Za-z\s&]+)',
        r'\b(?:total|amount|sum)\s*[:.]?\s*[£$€]?\s*(\d+[.,]\d{2})',
    ]
    
    # Compile patterns for efficiency
    compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in header_patterns]
    
    invoice_blocks = []
    current_block_start = 0
    current_block_confidence = 0.0
    current_header_text = ""
    current_supplier_guess = ""
    
    # Track consecutive pages without new headers
    pages_without_header = 0
    max_pages_without_header = 5  # Assume continuation after 5 pages
    
    for i, page in enumerate(pages):
        page_text = page.text.lower() if page.text else ""
        page_confidence = page.confidence
        
        # Check for invoice headers
        header_found = False
        for pattern in compiled_patterns:
            matches = pattern.findall(page_text)
            if matches:
                header_found = True
                current_header_text = matches[0] if matches else ""
                print(f"📄 Page {i+1}: Found header pattern - {current_header_text}")
                break
        
        # If header found, start new block
        if header_found and i > 0:
            # End current block
            if current_block_start < i:
                avg_confidence = current_block_confidence / (i - current_block_start)
                requires_review = avg_confidence < 0.6
                
                invoice_blocks.append(MockInvoiceBlock(
                    page_start=current_block_start + 1,  # 1-indexed for UI
                    page_end=i,
                    confidence=avg_confidence,
                    requires_manual_review=requires_review,
                    header_text=current_header_text,
                    supplier_guess=current_supplier_guess
                ))
                print(f"📋 Invoice block {len(invoice_blocks)}: pages {current_block_start+1}-{i}, confidence: {avg_confidence:.2f}")
            
            # Start new block
            current_block_start = i
            current_block_confidence = page_confidence
            pages_without_header = 0
            
            # Try to extract supplier name from header
            supplier_match = re.search(r'\b(?:supplier|vendor|company)\s*[:.]?\s*([A-Za-z\s&]+)', page_text, re.IGNORECASE)
            if supplier_match:
                current_supplier_guess = supplier_match.group(1).strip()
        else:
            # Continue current block
            current_block_confidence += page_confidence
            pages_without_header += 1
            
            # Check if we've exceeded continuation threshold
            if pages_without_header > max_pages_without_header:
                print(f"⚠️ Page {i+1}: Exceeded continuation threshold, marking for manual review")
                # Force end of current block and start new one
                if current_block_start < i:
                    avg_confidence = current_block_confidence / (i - current_block_start)
                    invoice_blocks.append(MockInvoiceBlock(
                        page_start=current_block_start + 1,
                        page_end=i,
                        confidence=avg_confidence,
                        requires_manual_review=True,  # Force manual review
                        header_text=current_header_text,
                        supplier_guess=current_supplier_guess
                    ))
                
                current_block_start = i
                current_block_confidence = page_confidence
                pages_without_header = 0
    
    # Handle final block
    if current_block_start < len(pages):
        final_pages = len(pages) - current_block_start
        avg_confidence = current_block_confidence / final_pages
        requires_review = avg_confidence < 0.6
        
        invoice_blocks.append(MockInvoiceBlock(
            page_start=current_block_start + 1,
            page_end=len(pages),
            confidence=avg_confidence,
            requires_manual_review=requires_review,
            header_text=current_header_text,
            supplier_guess=current_supplier_guess
        ))
        print(f"📋 Final invoice block: pages {current_block_start+1}-{len(pages)}, confidence: {avg_confidence:.2f}")
    
    # Edge case: if no boundaries found, create single block
    if not invoice_blocks and pages:
        avg_confidence = sum(p.confidence for p in pages) / len(pages)
        invoice_blocks.append(MockInvoiceBlock(
            page_start=1,
            page_end=len(pages),
            confidence=avg_confidence,
            requires_manual_review=avg_confidence < 0.6
        ))
        print(f"📋 Single invoice block: pages 1-{len(pages)}, confidence: {avg_confidence:.2f}")
    
    print(f"✅ Detected {len(invoice_blocks)} invoice blocks")
    return invoice_blocks

def test_single_invoice():
    """Test detection with single invoice (no boundaries)"""
    print("\n=== Test: Single Invoice ===")
    
    # Create mock OCR results for a single invoice
    pages = [
        MockOCRResult(text="Invoice No: INV-001\nSupplier: Test Corp\nTotal: £100", confidence=0.9, page_number=1),
        MockOCRResult(text="Line Item 1: £50\nLine Item 2: £50", confidence=0.8, page_number=2),
    ]
    
    blocks = detect_invoice_boundaries_mock(pages)
    
    assert len(blocks) == 1
    assert blocks[0].page_start == 1
    assert blocks[0].page_end == 2
    assert blocks[0].requires_manual_review == False
    print("✅ Single invoice test passed")

def test_multiple_invoices():
    """Test detection with multiple invoices"""
    print("\n=== Test: Multiple Invoices ===")
    
    # Create mock OCR results for multiple invoices
    pages = [
        MockOCRResult(text="Invoice No: INV-001\nSupplier: Test Corp\nTotal: £100", confidence=0.9, page_number=1),
        MockOCRResult(text="Line Item 1: £50\nLine Item 2: £50", confidence=0.8, page_number=2),
        MockOCRResult(text="Invoice No: INV-002\nSupplier: Another Corp\nTotal: £200", confidence=0.9, page_number=3),
        MockOCRResult(text="Line Item 1: £100\nLine Item 2: £100", confidence=0.8, page_number=4),
    ]
    
    blocks = detect_invoice_boundaries_mock(pages)
    
    assert len(blocks) == 2
    assert blocks[0].page_start == 1
    assert blocks[0].page_end == 2
    assert blocks[0].requires_manual_review == False
    assert blocks[1].page_start == 3
    assert blocks[1].page_end == 4
    assert blocks[1].requires_manual_review == False
    print("✅ Multiple invoices test passed")

def test_low_confidence():
    """Test detection with low confidence pages"""
    print("\n=== Test: Low Confidence ===")
    
    # Create mock OCR results with low confidence
    pages = [
        MockOCRResult(text="Invoice No: INV-001\nSupplier: Test Corp\nTotal: £100", confidence=0.3, page_number=1),
        MockOCRResult(text="Line Item 1: £50\nLine Item 2: £50", confidence=0.4, page_number=2),
    ]
    
    blocks = detect_invoice_boundaries_mock(pages)
    
    assert len(blocks) == 1
    assert blocks[0].requires_manual_review == True  # Should require review due to low confidence
    print("✅ Low confidence test passed")

def test_header_pattern_matching():
    """Test header pattern matching logic"""
    print("\n=== Test: Header Pattern Matching ===")
    
    # Header patterns from the engine
    header_patterns = [
        r'\b(?:invoice|inv)\s*(?:no|number|#)\s*[:.]?\s*([A-Z0-9\-/]+)',
        r'\b(?:invoice|inv)\s*(?:date|dated)\s*[:.]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        r'\b(?:supplier|vendor|company)\s*[:.]?\s*([A-Za-z\s&]+)',
    ]
    
    compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in header_patterns]
    
    # Test text with invoice header
    test_text = "Invoice No: INV-001\nSupplier: Test Corp\nTotal: £100"
    
    header_found = False
    for pattern in compiled_patterns:
        matches = pattern.findall(test_text)
        if matches:
            header_found = True
            break
    
    assert header_found == True
    print("✅ Header pattern matching test passed")

if __name__ == "__main__":
    print("🧪 Running Multi-Invoice Boundary Detection Tests")
    
    test_header_pattern_matching()
    test_single_invoice()
    test_multiple_invoices()
    test_low_confidence()
    
    print("\n🎉 All tests passed!") 