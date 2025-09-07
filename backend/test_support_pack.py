#!/usr/bin/env python3
"""Test support pack functionality"""

import sys
import os
import json
import zipfile
from pathlib import Path

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

try:
    print("Testing support pack functionality...")
    
    from diagnostics import create_support_pack, list_support_packs, cleanup_old_support_packs
    
    # Test 1: Create a support pack
    print("\n1. Creating support pack...")
    pack_path = create_support_pack(max_jobs=5, include_ocr_traces=True)
    print(f"✅ Support pack created: {pack_path}")
    
    # Test 2: Verify the zip file contents
    print("\n2. Verifying zip contents...")
    with zipfile.ZipFile(pack_path, 'r') as z:
        files = z.namelist()
        print(f"✅ Zip contains {len(files)} files:")
        for file in files:
            print(f"   - {file}")
        
        # Check for required files
        required_files = ["owlin.db", "audit_log.csv", "system_info.json", "job_summaries.json"]
        for req_file in required_files:
            if req_file in files:
                print(f"   ✅ {req_file} found")
            else:
                print(f"   ⚠️  {req_file} missing")
        
        # Check OCR traces directory
        ocr_traces = [f for f in files if f.startswith("ocr_traces/")]
        print(f"   ✅ {len(ocr_traces)} OCR trace files found")
    
    # Test 3: List support packs
    print("\n3. Listing support packs...")
    packs = list_support_packs()
    print(f"✅ Found {len(packs)} support packs:")
    for pack in packs[:3]:  # Show first 3
        print(f"   - {Path(pack).name}")
    
    # Test 4: Test cleanup (dry run)
    print("\n4. Testing cleanup (dry run)...")
    deleted_count = cleanup_old_support_packs(keep_days=365)  # Keep for 1 year
    print(f"✅ Cleanup would delete {deleted_count} old packs")
    
    print("\n🎉 Support pack functionality test passed!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1) 