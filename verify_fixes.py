#!/usr/bin/env python3
"""
Quick verification script to confirm all incremental fixes are applied
"""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

print("=" * 80)
print("VERIFYING INCREMENTAL FIXES")
print("=" * 80)

# Check 1: Feature Flags
print("\n[1] Checking Feature Flags...")
try:
    from backend.config import FEATURE_OCR_V2_PREPROC, FEATURE_OCR_V2_LAYOUT, FEATURE_OCR_V3_TABLES
    flags_ok = (
        FEATURE_OCR_V2_PREPROC == True and
        FEATURE_OCR_V2_LAYOUT == True and
        FEATURE_OCR_V3_TABLES == True
    )
    if flags_ok:
        print("   ✅ All feature flags enabled")
        print(f"      PREPROC: {FEATURE_OCR_V2_PREPROC}")
        print(f"      LAYOUT: {FEATURE_OCR_V2_LAYOUT}")
        print(f"      TABLES: {FEATURE_OCR_V3_TABLES}")
    else:
        print("   ❌ Some flags still disabled")
        print(f"      PREPROC: {FEATURE_OCR_V2_PREPROC}")
        print(f"      LAYOUT: {FEATURE_OCR_V2_LAYOUT}")
        print(f"      TABLES: {FEATURE_OCR_V3_TABLES}")
except Exception as e:
    print(f"   ❌ Error checking flags: {e}")

# Check 2: DPI Setting
print("\n[2] Checking DPI Setting...")
try:
    from backend.ocr.owlin_scan_pipeline import _export_page_image
    import inspect
    source = inspect.getsource(_export_page_image)
    if 'dpi=300' in source:
        print("   ✅ DPI is set to 300")
    elif 'dpi=200' in source:
        print("   ❌ DPI is still 200 (should be 300)")
    else:
        print("   ⚠️  DPI setting not found in source")
except Exception as e:
    print(f"   ❌ Error checking DPI: {e}")

# Check 3: Logging in ocr_service.py
print("\n[3] Checking Enhanced Logging...")
try:
    ocr_service_path = BASE_DIR / "backend" / "services" / "ocr_service.py"
    content = ocr_service_path.read_text()
    
    checks = {
        "[TABLE_EXTRACT]": "[TABLE_EXTRACT]" in content,
        "[TABLE_FAIL]": "[TABLE_FAIL]" in content,
        "[FALLBACK]": "[FALLBACK]" in content and "No table_data" in content
    }
    
    all_ok = all(checks.values())
    if all_ok:
        print("   ✅ All logging markers found")
        for marker, found in checks.items():
            print(f"      {marker}: {'✅' if found else '❌'}")
    else:
        print("   ⚠️  Some logging markers missing")
        for marker, found in checks.items():
            print(f"      {marker}: {'✅' if found else '❌'}")
except Exception as e:
    print(f"   ❌ Error checking logging: {e}")

# Check 4: Enhanced Endpoint
print("\n[4] Checking Enhanced Endpoint...")
try:
    main_path = BASE_DIR / "backend" / "main.py"
    content = main_path.read_text(encoding='utf-8', errors='ignore')
    
    checks = {
        "raw_paddleocr_pages": "raw_paddleocr_pages" in content,
        "feature_flags": '"feature_flags"' in content or "'feature_flags'" in content,
        "raster_dpi_used": "raster_dpi_used" in content,
        "FEATURE_OCR_V2_PREPROC import": "FEATURE_OCR_V2_PREPROC" in content
    }
    
    all_ok = all(checks.values())
    if all_ok:
        print("   ✅ All endpoint enhancements found")
        for check, found in checks.items():
            print(f"      {check}: {'✅' if found else '❌'}")
    else:
        print("   ⚠️  Some endpoint enhancements missing")
        for check, found in checks.items():
            print(f"      {check}: {'✅' if found else '❌'}")
except Exception as e:
    print(f"   ❌ Error checking endpoint: {e}")

# Summary
print("\n" + "=" * 80)
print("VERIFICATION SUMMARY")
print("=" * 80)
print("\nAll fixes should be applied. Next steps:")
print("1. Start backend: python -m uvicorn backend.main:app --port 8000 --reload")
print("2. Upload test PDF to data/uploads/")
print("3. Test: GET /api/dev/ocr-test?filename=your-file.pdf")
print("4. Check logs for [TABLE_EXTRACT], [TABLE_FAIL], [FALLBACK] markers")
print("5. Verify JSON response has raw_paddleocr_pages, feature_flags, raster_dpi_used")
print("\n" + "=" * 80)

