#!/usr/bin/env python3
"""
Verify OCR endpoint is registered correctly
"""
import sys
from pathlib import Path

# Add project root to path
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

print("=" * 80)
print("OCR ENDPOINT VERIFICATION")
print("=" * 80)

# Import app
try:
    from backend.main import app
    print("✅ Backend app imported successfully")
except Exception as e:
    print(f"❌ Failed to import backend.main: {e}")
    sys.exit(1)

# Check routes
print("\n[1] Checking registered routes...")
ocr_test_found = False
get_endpoints = []

for route in app.routes:
    if hasattr(route, 'path'):
        if route.path == "/api/dev/ocr-test":
            ocr_test_found = True
            methods = getattr(route, 'methods', set())
            print(f"✅ FOUND: /api/dev/ocr-test (methods: {methods})")
        elif route.path.startswith("/api/") and "GET" in str(getattr(route, 'methods', set())):
            get_endpoints.append(route.path)

if not ocr_test_found:
    print("❌ /api/dev/ocr-test NOT FOUND!")
    print("\nRegistered /api/ GET endpoints:")
    for ep in sorted(get_endpoints)[:10]:
        print(f"   - {ep}")
else:
    print("✅ OCR test endpoint is registered")

# Check uploads directory
print("\n[2] Checking uploads directory...")
uploads_dir = BASE_DIR / "data" / "uploads"
print(f"   Path: {uploads_dir}")
print(f"   Exists: {uploads_dir.exists()}")

if uploads_dir.exists():
    pdfs = list(uploads_dir.glob("*.pdf"))
    print(f"   PDFs found: {len(pdfs)}")
    if pdfs:
        print("\n   First 5 PDFs:")
        for pdf in pdfs[:5]:
            print(f"      - {pdf.name}")
else:
    print("   ❌ Directory does not exist!")

# Check if endpoint has list_uploads parameter
print("\n[3] Checking endpoint signature...")
try:
    from backend.main import ocr_sanity_test
    import inspect
    sig = inspect.signature(ocr_sanity_test)
    params = list(sig.parameters.keys())
    print(f"   Parameters: {params}")
    
    if 'list_uploads' in params:
        print("   ✅ list_uploads parameter found")
    else:
        print("   ❌ list_uploads parameter NOT found (old endpoint)")
    
    if 'filename' in params:
        print("   ✅ filename parameter found")
except Exception as e:
    print(f"   ⚠️  Could not inspect function: {e}")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

if ocr_test_found:
    print("✅ Endpoint is registered")
    print("\nTest with:")
    print('   curl "http://localhost:8000/api/dev/ocr-test?list_uploads=true"')
else:
    print("❌ Endpoint NOT registered - check backend/main.py")

print("\n" + "=" * 80)

