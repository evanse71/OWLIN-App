#!/usr/bin/env python3
"""
Comprehensive OCR Pipeline Diagnostic Tests
Tests DPI impact, PaddleOCR, page splitting, and table extraction
"""
import sys
import os
from pathlib import Path
import json
from typing import Dict, Any, Optional

# Add project root to path
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

print("=" * 80)
print("OCR PIPELINE DIAGNOSTIC TESTS")
print("=" * 80)

# Test 1: Check DPI setting in code
print("\n[TEST 1] Checking DPI Configuration")
print("-" * 80)
try:
    from backend.ocr.owlin_scan_pipeline import _export_page_image
    import inspect
    source = inspect.getsource(_export_page_image)
    if 'dpi=200' in source:
        print("❌ ISSUE FOUND: DPI is set to 200 (too low for PaddleOCR)")
        print("   Location: backend/ocr/owlin_scan_pipeline.py:_export_page_image()")
        print("   Recommendation: Change to dpi=300")
    elif 'dpi=300' in source:
        print("✅ DPI is correctly set to 300")
    else:
        print("⚠️  DPI setting not found in source (may be configurable)")
        print(f"   Source preview: {source[:200]}...")
except Exception as e:
    print(f"❌ Error checking DPI: {e}")

# Test 2: Test PyMuPDF installation and page splitting
print("\n[TEST 2] Testing PyMuPDF (PDF Page Splitting)")
print("-" * 80)
try:
    import fitz
    print("✅ PyMuPDF (fitz) is installed")
    
    # Test with a dummy PDF path (will fail but shows capability)
    test_pdf = BASE_DIR / "data" / "uploads" / "test.pdf"
    if test_pdf.exists():
        doc = fitz.open(str(test_pdf))
        print(f"✅ Test PDF opened: {doc.page_count} page(s)")
        
        # Test DPI rendering
        for dpi in [200, 300]:
            page = doc.load_page(0)
            pix = page.get_pixmap(dpi=dpi)
            print(f"   DPI {dpi}: {pix.width}x{pix.height} pixels")
        
        # Test text extraction
        page = doc.load_page(0)
        text = page.get_text()
        print(f"   Page 1 text length: {len(text)} chars")
        if text:
            print(f"   Sample text: {text[:100]}...")
        
        doc.close()
    else:
        print(f"⚠️  No test PDF found at {test_pdf}")
        print("   Creating a minimal test PDF...")
        # Create minimal PDF for testing
        minimal_pdf = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj
3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj
xref
0 4
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
trailer<</Size 4/Root 1 0 R>>
startxref
197
%%EOF"""
        test_pdf.parent.mkdir(parents=True, exist_ok=True)
        test_pdf.write_bytes(minimal_pdf)
        print(f"   ✅ Created minimal test PDF at {test_pdf}")
        
        # Test with minimal PDF
        doc = fitz.open(str(test_pdf))
        print(f"   ✅ Opened minimal PDF: {doc.page_count} page(s)")
        page = doc.load_page(0)
        pix_200 = page.get_pixmap(dpi=200)
        pix_300 = page.get_pixmap(dpi=300)
        print(f"   DPI 200: {pix_200.width}x{pix_200.height} pixels")
        print(f"   DPI 300: {pix_300.width}x{pix_300.height} pixels")
        print(f"   Size increase: {((pix_300.width * pix_300.height) / (pix_200.width * pix_200.height) - 1) * 100:.1f}%")
        doc.close()
        
except ImportError:
    print("❌ PyMuPDF (fitz) is NOT installed")
    print("   Install with: pip install PyMuPDF")
except Exception as e:
    print(f"❌ Error testing PyMuPDF: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Test PaddleOCR availability and raw OCR
print("\n[TEST 3] Testing PaddleOCR (Raw OCR Engine)")
print("-" * 80)
try:
    from paddleocr import PaddleOCR
    print("✅ PaddleOCR is installed")
    
    # Initialize OCR
    print("   Initializing PaddleOCR...")
    try:
        ocr = PaddleOCR(use_textline_orientation=True, lang='en')
    except TypeError:
        # Fallback for older versions
        try:
            ocr = PaddleOCR(use_angle_cls=True, lang='en')
        except Exception as e:
            print(f"   ❌ Error initializing PaddleOCR: {e}")
            ocr = None
    if ocr:
        print("   ✅ PaddleOCR initialized successfully")
    
    # Test with a sample image if available
    test_image = BASE_DIR / "data" / "uploads" / "test_image.png"
    if not test_image.exists():
        # Create a simple test image using PIL
        try:
            from PIL import Image, ImageDraw, ImageFont
            img = Image.new('RGB', (400, 200), color='white')
            draw = ImageDraw.Draw(img)
            draw.text((10, 10), "Test Invoice\nTotal: £123.45", fill='black')
            test_image.parent.mkdir(parents=True, exist_ok=True)
            img.save(str(test_image))
            print(f"   ✅ Created test image at {test_image}")
        except ImportError:
            print("   ⚠️  PIL not available, skipping image creation")
            test_image = None
    
    if test_image and test_image.exists():
        print(f"   Testing OCR on {test_image}...")
        result = ocr.ocr(str(test_image), cls=True)
        if result and result[0]:
            print(f"   ✅ OCR detected {len(result[0])} text regions")
            for idx, line in enumerate(result[0][:3]):  # Show first 3
                if len(line) >= 2:
                    box, (text, conf) = line[0], line[1]
                    print(f"      Region {idx+1}: '{text}' (confidence: {conf:.3f})")
        else:
            print("   ⚠️  No text detected in test image")
    else:
        print("   ⚠️  No test image available for OCR testing")
        
except ImportError:
    print("❌ PaddleOCR is NOT installed")
    print("   Install with: pip install paddleocr")
except Exception as e:
    print(f"❌ Error testing PaddleOCR: {e}")
    import traceback
    traceback.print_exc()

# Test 4: Test OCR Pipeline Import and Structure
print("\n[TEST 4] Testing OCR Pipeline Structure")
print("-" * 80)
try:
    from backend.ocr.owlin_scan_pipeline import (
        process_document,
        _export_page_image,
        preprocess_image,
        detect_layout,
        ocr_block,
        ModelRegistry
    )
    print("✅ OCR pipeline imports successfully")
    
    # Check ModelRegistry
    registry = ModelRegistry.get()
    print("✅ ModelRegistry singleton accessible")
    
    # Check if PaddleOCR is available in registry
    paddle = registry.paddle()
    if paddle:
        print("✅ PaddleOCR available via ModelRegistry")
    else:
        print("⚠️  PaddleOCR not available via ModelRegistry (may need initialization)")
    
except Exception as e:
    print(f"❌ Error importing OCR pipeline: {e}")
    import traceback
    traceback.print_exc()

# Test 5: Test Table Extraction Module
print("\n[TEST 5] Testing Table Extraction")
print("-" * 80)
try:
    from ocr.table_extractor import extract_table_from_block
    print("✅ Table extraction module imported")
except ImportError:
    print("⚠️  Table extraction module not found (may be optional)")
except Exception as e:
    print(f"⚠️  Error importing table extraction: {e}")

# Test 6: Test OCR Service Integration
print("\n[TEST 6] Testing OCR Service Integration")
print("-" * 80)
try:
    from backend.services.ocr_service import (
        process_document_ocr,
        _extract_invoice_data_from_page,
        _extract_line_items_from_page
    )
    print("✅ OCR service imports successfully")
    
    # Check line item extraction function
    import inspect
    extract_source = inspect.getsource(_extract_line_items_from_page)
    if 'table_data' in extract_source:
        print("✅ Line item extraction checks for table_data")
    if 'line_items' in extract_source:
        print("✅ Line item extraction looks for line_items field")
        
except Exception as e:
    print(f"❌ Error importing OCR service: {e}")
    import traceback
    traceback.print_exc()

# Test 7: Check Configuration Flags
print("\n[TEST 7] Checking Configuration Flags")
print("-" * 80)
try:
    from backend.config import (
        FEATURE_OCR_V2_PREPROC,
        FEATURE_OCR_V2_LAYOUT,
        FEATURE_OCR_V3_TABLES,
        FEATURE_OCR_PIPELINE_V2
    )
    print(f"   FEATURE_OCR_PIPELINE_V2: {FEATURE_OCR_PIPELINE_V2}")
    print(f"   FEATURE_OCR_V2_PREPROC: {FEATURE_OCR_V2_PREPROC}")
    print(f"   FEATURE_OCR_V2_LAYOUT: {FEATURE_OCR_V2_LAYOUT}")
    print(f"   FEATURE_OCR_V3_TABLES: {FEATURE_OCR_V3_TABLES}")
except Exception as e:
    print(f"⚠️  Error checking config: {e}")

# Test 8: Test Backend API Endpoint (if backend is running)
print("\n[TEST 8] Testing Backend API Endpoint")
print("-" * 80)
try:
    import requests
    health_url = "http://localhost:8000/api/health"
    response = requests.get(health_url, timeout=2)
    if response.status_code == 200:
        print("✅ Backend is running on port 8000")
        
        # Test OCR test endpoint structure
        ocr_test_url = "http://localhost:8000/api/dev/ocr-test"
        print(f"   OCR test endpoint available at: {ocr_test_url}")
        print("   Usage: GET /api/dev/ocr-test?filename=<file-in-data/uploads/>")
    else:
        print(f"⚠️  Backend returned status {response.status_code}")
except requests.exceptions.ConnectionError:
    print("⚠️  Backend is not running (connection refused)")
    print("   Start backend with: python -m uvicorn backend.main:app --port 8000")
except ImportError:
    print("⚠️  requests library not installed (pip install requests)")
except Exception as e:
    print(f"⚠️  Error testing backend: {e}")

# Summary
print("\n" + "=" * 80)
print("DIAGNOSTIC SUMMARY")
print("=" * 80)
print("\nNext Steps:")
print("1. If DPI is 200, change to 300 in backend/ocr/owlin_scan_pipeline.py:154")
print("2. Upload a test PDF to data/uploads/")
print("3. Run: curl 'http://localhost:8000/api/dev/ocr-test?filename=your-file.pdf'")
print("4. Check backend logs for [OCR_V2], [LINE_ITEMS], [TABLE_EXTRACT] markers")
print("\n" + "=" * 80)

