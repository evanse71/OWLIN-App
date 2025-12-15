#!/usr/bin/env python3
"""
Red Dragon Hash Buster - Force Fresh Invoice Processing

This script modifies a PDF file by appending a timestamp, changing its SHA-256 hash.
It works with Red Dragon or any PDF file.

Usage:
    python make_unique_red_dragon.py [path/to/red_dragon.pdf]
    python make_unique_red_dragon.py  # Auto-searches for Red Dragon PDFs
"""

import os
import glob
import sys
import time
from pathlib import Path

def find_red_dragon_pdf():
    """Find Red Dragon PDF in Downloads or uploads."""
    # Check Downloads first
    downloads_dir = Path.home() / "Downloads"
    if downloads_dir.exists():
        candidates = list(downloads_dir.glob("*Dragon*.pdf")) + list(downloads_dir.glob("*Red*.pdf"))
        if candidates:
            # Prefer files with "Red" and "Dragon" in name
            preferred = [f for f in candidates if "Red" in f.name and "Dragon" in f.name]
            if preferred:
                return preferred[0]
            return candidates[0]
    
    # Check uploads
    uploads_dir = Path("data") / "uploads"
    if uploads_dir.exists():
        candidates = list(uploads_dir.glob("*Dragon*.pdf")) + list(uploads_dir.glob("*Red*.pdf"))
        if candidates:
            preferred = [f for f in candidates if "Red" in f.name and "Dragon" in f.name]
            if preferred:
                return preferred[0]
            return candidates[0]
    
    return None

def main():
    """Main entry point."""
    print("=" * 80)
    print("RED DRAGON HASH BUSTER")
    print("=" * 80)
    print()
    
    # 1. Find source file
    if len(sys.argv) > 1:
        source_file = sys.argv[1]
        if not os.path.exists(source_file):
            print(f"❌ File not found: {source_file}")
            sys.exit(1)
    else:
        print("🔍 Searching for Red Dragon PDF...")
        source_file = find_red_dragon_pdf()
        
        if not source_file:
            print("❌ No Red Dragon PDF found.")
            print()
            print("Looking for:")
            print("  - C:/Users/tedev/Downloads/*Dragon*.pdf")
            print("  - C:/Users/tedev/Downloads/*Red*.pdf")
            print("  - data/uploads/*Dragon*.pdf")
            print()
            print("Usage:")
            print("  python make_unique_red_dragon.py [path/to/red_dragon.pdf]")
            sys.exit(1)
    
    source_file = Path(source_file)
    print(f"📖 Source: {source_file.name}")
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
    timestamp = str(time.time()).encode()
    new_content = content + b'\n% ' + timestamp
    
    new_size = len(new_content)
    print(f"📝 Modified content (added timestamp)")
    print(f"   New size: {new_size / 1024:.2f} KB (+{new_size - original_size} bytes)")
    print()
    
    # 4. Save with descriptive name
    output_name = "Red_Dragon_Fresh.pdf"
    output_path = Path("data") / "uploads" / output_name
    
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
    print("  2. Check backend logs for OCR text quality")
    print("  3. Verify line items in database")
    print()
    print("=" * 80)

if __name__ == "__main__":
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
