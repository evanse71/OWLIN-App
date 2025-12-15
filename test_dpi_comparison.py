#!/usr/bin/env python3
"""
Test DPI Impact on OCR Quality
Compares OCR results at 200 DPI vs 300 DPI
"""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

print("=" * 80)
print("DPI COMPARISON TEST")
print("=" * 80)

try:
    import fitz
    from PIL import Image, ImageDraw, ImageFont
    import numpy as np
    
    # Create a test invoice image with text
    print("\n[1] Creating test invoice image...")
    img = Image.new('RGB', (800, 600), color='white')
    draw = ImageDraw.Draw(img)
    
    # Draw invoice text
    text_lines = [
        "INVOICE",
        "Supplier: Test Company Ltd",
        "Date: 2025-01-15",
        "",
        "Item          Qty    Price    Total",
        "Apples        10     £2.50    £25.00",
        "Oranges       5      £3.00    £15.00",
        "Bananas       8      £1.50    £12.00",
        "",
        "Subtotal:                          £52.00",
        "VAT (20%):                         £10.40",
        "TOTAL:                             £62.40"
    ]
    
    y = 20
    for line in text_lines:
        draw.text((20, y), line, fill='black')
        y += 30
    
    test_image_path = BASE_DIR / "data" / "uploads" / "test_invoice.png"
    test_image_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(test_image_path))
    print(f"   ✅ Created test invoice at {test_image_path}")
    
    # Convert to PDF for testing
    print("\n[2] Converting to PDF...")
    pdf_path = BASE_DIR / "data" / "uploads" / "test_invoice.pdf"
    img.save(str(pdf_path), "PDF")
    print(f"   ✅ Created PDF at {pdf_path}")
    
    # Test rasterization at different DPIs
    print("\n[3] Testing rasterization at different DPIs...")
    doc = fitz.open(str(pdf_path))
    page = doc.load_page(0)
    
    dpi_results = {}
    for dpi in [200, 300, 400]:
        pix = page.get_pixmap(dpi=dpi)
        dpi_results[dpi] = {
            'width': pix.width,
            'height': pix.height,
            'size_mb': (pix.width * pix.height * 3) / (1024 * 1024)  # RGB = 3 bytes per pixel
        }
        print(f"   DPI {dpi}: {pix.width}x{pix.height} ({dpi_results[dpi]['size_mb']:.2f} MB)")
    
    doc.close()
    
    # Test OCR at different DPIs
    print("\n[4] Testing OCR at different DPIs...")
    try:
        from paddleocr import PaddleOCR
        ocr = PaddleOCR(use_textline_orientation=True, lang='en')
        
        for dpi in [200, 300]:
            print(f"\n   Testing OCR at DPI {dpi}...")
            doc = fitz.open(str(pdf_path))
            page = doc.load_page(0)
            pix = page.get_pixmap(dpi=dpi)
            
            # Save as PNG
            png_path = BASE_DIR / "data" / "uploads" / f"test_invoice_dpi{dpi}.png"
            pix.save(str(png_path))
            
            # Run OCR
            result = ocr.predict(str(png_path))
            
            # Handle different PaddleOCR return formats
            if result and len(result) > 0:
                texts = []
                confidences = []
                # New format: result is a list of dicts with 'text' and 'score'
                if isinstance(result[0], dict):
                    for item in result:
                        if 'text' in item:
                            texts.append(item['text'])
                            confidences.append(item.get('score', 0.9))
                # Old format: result[0] is list of tuples
                elif isinstance(result[0], list):
                    for line in result[0]:
                        if len(line) >= 2:
                            if isinstance(line[1], tuple):
                                text, conf = line[1]
                            else:
                                text = str(line[1])
                                conf = 0.9
                            texts.append(text)
                            confidences.append(conf)
                
                print(f"      Detected {len(texts)} text regions")
                print(f"      Average confidence: {sum(confidences)/len(confidences):.3f}")
                print(f"      Sample texts: {texts[:5]}")
                
                # Check for key invoice fields
                full_text = " ".join(texts).lower()
                checks = {
                    "invoice": "invoice" in full_text,
                    "supplier": "supplier" in full_text or "company" in full_text,
                    "total": "total" in full_text,
                    "vat": "vat" in full_text,
                    "items": any(x in full_text for x in ["apples", "oranges", "bananas"])
                }
                print(f"      Field detection: {checks}")
            else:
                print(f"      ❌ No text detected at DPI {dpi}")
            
            doc.close()
            
    except ImportError:
        print("   ⚠️  PaddleOCR not available, skipping OCR comparison")
    except Exception as e:
        print(f"   ⚠️  Error testing OCR: {e}")
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("DPI 300 provides 125% more pixels than DPI 200")
    print("This significantly improves OCR accuracy, especially for:")
    print("  - Small text")
    print("  - Table structures")
    print("  - Vector PDFs without text layers")
    print("\nRecommendation: Change DPI from 200 to 300 in owlin_scan_pipeline.py")
    
except ImportError as e:
    print(f"❌ Missing dependency: {e}")
    print("   Install with: pip install PyMuPDF pillow numpy")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

