#!/usr/bin/env python3
"""
Test script to verify path resolver functionality
"""

import os
import sys
sys.path.append('.')

from services import resolve_path_for_reprocess

def test_path_resolver():
    print("Testing path resolver...")
    
    # Test with a known file hash from the database
    test_hash = "1f9f28befc6b21049da294e2ff8e917b52634425e9b42338807b0caa3c9808c8"
    test_filename = "1f9f28be_853aeff791b14e2fad063410c0089c2e.png"
    
    print(f"Testing with hash: {test_hash[:8]}...")
    print(f"Fallback filename: {test_filename}")
    
    path = resolve_path_for_reprocess(test_hash, test_filename)
    
    if path:
        print(f"✅ Found path: {path}")
        print(f"File exists: {os.path.exists(path)}")
    else:
        print("❌ No path found")
    
    # List files in storage
    print("\nFiles in storage:")
    storage_root = os.environ.get("OWLIN_STORAGE", "storage/uploads")
    if os.path.exists(storage_root):
        for f in os.listdir(storage_root):
            print(f"  {f}")
    else:
        print(f"Storage directory {storage_root} does not exist")

if __name__ == "__main__":
    test_path_resolver() 