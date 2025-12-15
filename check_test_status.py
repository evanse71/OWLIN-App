#!/usr/bin/env python3
"""Quick script to check test status and show results."""

import os
import time
from pathlib import Path

result_file = Path("test_stori_results.txt")
status_file = Path("test_status.txt")

print("=" * 80)
print("TEST STATUS CHECK")
print("=" * 80)

if result_file.exists():
    print(f"\n✅ Results file found: {result_file}")
    print(f"   Size: {result_file.stat().st_size} bytes")
    print(f"   Modified: {time.ctime(result_file.stat().st_mtime)}")
    print("\n" + "=" * 80)
    print("RESULTS:")
    print("=" * 80)
    print(result_file.read_text(encoding='utf-8'))
elif status_file.exists():
    print(f"\n⏳ Status file found: {status_file}")
    print(f"   Size: {status_file.stat().st_size} bytes")
    print(f"   Modified: {time.ctime(status_file.stat().st_mtime)}")
    print("\n" + "=" * 80)
    print("LATEST STATUS (last 30 lines):")
    print("=" * 80)
    lines = status_file.read_text(encoding='utf-8').split('\n')
    print('\n'.join(lines[-30:]))
else:
    print("\n❌ No test files found")
    print("   The test may still be initializing or may have failed")
    print("\nTo run the test:")
    print("  python backend/scripts/run_test_direct.py \"data\\uploads\\36d55f24-1a00-41f3-8467-015e11216c91__Storiinvoiceonly1.pdf\" \"test_stori_results.txt\"")
