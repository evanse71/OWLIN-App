#!/usr/bin/env python3
"""Quick setup check for invoice validation testing."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

print("=" * 80)
print("SETUP CHECK FOR INVOICE VALIDATION TESTS")
print("=" * 80)

# Check 1: Imports
print("\n[1/4] Checking imports...")
try:
    from backend.ocr.owlin_scan_pipeline import process_document
    print("✓ OCR pipeline import successful")
except Exception as e:
    print(f"✗ OCR pipeline import failed: {e}")
    sys.exit(1)

try:
    from backend.llm.invoice_parser import create_invoice_parser
    print("✓ LLM parser import successful")
except Exception as e:
    print(f"✗ LLM parser import failed: {e}")
    sys.exit(1)

# Check 2: Config
print("\n[2/4] Checking configuration...")
try:
    from backend.config import FEATURE_OCR_V2_PREPROC, LLM_VALIDATION_ERROR_THRESHOLD, FEATURE_LLM_EXTRACTION
    print(f"✓ FEATURE_OCR_V2_PREPROC = {FEATURE_OCR_V2_PREPROC}")
    print(f"✓ FEATURE_LLM_EXTRACTION = {FEATURE_LLM_EXTRACTION}")
    print(f"✓ LLM_VALIDATION_ERROR_THRESHOLD = {LLM_VALIDATION_ERROR_THRESHOLD}")
except Exception as e:
    print(f"✗ Config check failed: {e}")
    sys.exit(1)

# Check 3: Ollama connection
print("\n[3/4] Checking Ollama connection...")
try:
    import requests
    response = requests.get("http://localhost:11434/api/tags", timeout=5)
    if response.status_code == 200:
        models = response.json().get("models", [])
        model_names = [m.get("name", "") for m in models]
        print(f"✓ Ollama is running")
        print(f"  Available models: {', '.join(model_names[:3])}{'...' if len(model_names) > 3 else ''}")
    else:
        print(f"✗ Ollama returned status {response.status_code}")
        sys.exit(1)
except requests.exceptions.ConnectionError:
    print("✗ Cannot connect to Ollama at http://localhost:11434")
    print("  Please start Ollama before running tests")
    sys.exit(1)
except Exception as e:
    print(f"✗ Ollama check failed: {e}")
    sys.exit(1)

# Check 4: Test file existence
print("\n[4/4] Checking test files...")
test_files = [
    "data/uploads/36d55f24-1a00-41f3-8467-015e11216c91__Storiinvoiceonly1.pdf",
]
for test_file in test_files:
    if Path(test_file).exists():
        print(f"✓ Found: {test_file}")
    else:
        print(f"✗ Missing: {test_file}")

print("\n" + "=" * 80)
print("SETUP CHECK COMPLETE")
print("=" * 80)
print("\nIf all checks passed, you can run:")
print("  python backend/scripts/test_invoice_validation.py <invoice_file> [output_file]")

# Also write to file for easier reading
output_file = "setup_check_results.txt"
with open(output_file, 'w', encoding='utf-8') as f:
    f.write("Setup check completed - see console output above\n")
print(f"\nResults also written to: {output_file}")
