#!/usr/bin/env python3
"""
Short & Sweet Hash Buster - Force Fresh Invoice Processing

This script modifies a PDF file by appending a timestamp, changing its SHA-256 hash.
It always saves as "Stori_Short.pdf" to avoid Windows path length limits.

Usage:
    python make_unique_invoice.py
"""

import os
import glob
import time
from pathlib import Path

def main():
    """Main entry point."""
    print("=" * 80)
    print("SHORT & SWEET HASH BUSTER")
    print("=" * 80)
    print()
    
    # 1. Find the ORIGINAL source file (Shortest name)
    # Look for the one in Downloads first, or the shortest one in uploads
    source_candidates = glob.glob('C:/Users/tedev/Downloads/Stori*.pdf')
    if not source_candidates:
        # Fallback to uploads, picking shortest filename
        uploads_dir = Path("data") / "uploads"
        if uploads_dir.exists():
            source_candidates = sorted(
                [str(f) for f in uploads_dir.glob("*.pdf") if "Stori" in f.name.lower()],
                key=len
            )
    
    if not source_candidates:
        print("❌ No source PDF found.")
        print()
        print("Looking for:")
        print("  - C:/Users/tedev/Downloads/Stori*.pdf")
        print("  - data/uploads/*Stori*.pdf")
        sys.exit(1)
    
    source_file = source_candidates[0]
    print(f"📖 Source: {os.path.basename(source_file)}")
    print(f"   Path: {source_file}")
    print()
    
    # 2. Read Content
    print("📄 Reading file...")
    with open(source_file, 'rb') as f:
        content = f.read()
    
    original_size = len(content)
    print(f"   Size: {original_size / 1024:.2f} KB")
    print()
    
    # 3. Modify Hash (Append timestamp as comment)
    # This changes the SHA256 without changing the filename length
    timestamp = str(time.time()).encode()
    new_content = content + b'\n% ' + timestamp
    
    new_size = len(new_content)
    print(f"📝 Modified content (added timestamp)")
    print(f"   New size: {new_size / 1024:.2f} KB (+{new_size - original_size} bytes)")
    print()
    
    # 4. Save with SHORT name
    output_name = "Stori_Short.pdf"
    output_path = os.path.join("data", "uploads", output_name)
    
    os.makedirs("data/uploads", exist_ok=True)
    print(f"💾 Saving to: {output_path}")
    with open(output_path, 'wb') as f:
        f.write(new_content)
    
    print()
    print("=" * 80)
    print("✅ SUCCESS")
    print("=" * 80)
    print()
    print(f"Created: {output_path}")
    print(f"Size: {new_size / 1024:.2f} KB")
    print()
    print("🚀 Ready to upload!")
    print()
    print("Next steps:")
    print("  1. Run: python force_upload.py")
    print("  2. Run: python check_result.py")
    print()
    print("=" * 80)

if __name__ == "__main__":
    import sys
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
