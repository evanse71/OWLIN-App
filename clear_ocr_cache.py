#!/usr/bin/env python3
"""
OCR Cache Cleanup Script

This script clears cached OCR results from the data/uploads/ directory
to force the pipeline to re-run with the new spatial clustering code.

Usage:
    python clear_ocr_cache.py                    # Interactive mode
    python clear_ocr_cache.py --all              # Delete all cache folders
    python clear_ocr_cache.py --pattern stori    # Delete folders matching pattern
    python clear_ocr_cache.py --dry-run          # Show what would be deleted
"""

import os
import shutil
import sys
from pathlib import Path
from datetime import datetime

# Paths
UPLOADS_DIR = Path("data") / "uploads"
BACKEND_UPLOADS_DIR = Path("backend") / "data" / "uploads"

def get_cache_folders():
    """Get all cache folders in uploads directory."""
    folders = []
    
    # Check both possible locations
    for base_dir in [UPLOADS_DIR, BACKEND_UPLOADS_DIR]:
        if base_dir.exists():
            for item in base_dir.iterdir():
                if item.is_dir():
                    # Check if it's an OCR cache folder (has ocr_output.json or pages/)
                    has_ocr_json = (item / "ocr_output.json").exists()
                    has_pages_dir = (item / "pages").exists()
                    has_original = (item / "original.pdf").exists()
                    
                    if has_ocr_json or has_pages_dir or has_original:
                        folders.append(item)
    
    return folders

def get_folder_info(folder: Path):
    """Get information about a cache folder."""
    info = {
        "path": str(folder),
        "name": folder.name,
        "size_mb": 0,
        "files": 0,
        "has_ocr_json": False,
        "has_pages": False,
        "has_original": False,
        "modified": None
    }
    
    try:
        # Calculate size
        total_size = 0
        file_count = 0
        for item in folder.rglob("*"):
            if item.is_file():
                total_size += item.stat().st_size
                file_count += 1
        
        info["size_mb"] = total_size / (1024 * 1024)
        info["files"] = file_count
        
        # Check contents
        info["has_ocr_json"] = (folder / "ocr_output.json").exists()
        info["has_pages"] = (folder / "pages").exists()
        info["has_original"] = (folder / "original.pdf").exists()
        
        # Get modification time
        if (folder / "ocr_output.json").exists():
            info["modified"] = datetime.fromtimestamp((folder / "ocr_output.json").stat().st_mtime)
        elif (folder / "original.pdf").exists():
            info["modified"] = datetime.fromtimestamp((folder / "original.pdf").stat().st_mtime)
        
    except Exception as e:
        info["error"] = str(e)
    
    return info

def delete_folder(folder: Path, dry_run: bool = False):
    """Delete a cache folder."""
    if dry_run:
        print(f"  [DRY RUN] Would delete: {folder}")
        return True
    
    try:
        shutil.rmtree(folder)
        print(f"  ✓ Deleted: {folder}")
        return True
    except Exception as e:
        print(f"  ✗ Failed to delete {folder}: {e}")
        return False

def main():
    """Main cleanup logic."""
    
    print("=" * 80)
    print("OCR CACHE CLEANUP SCRIPT")
    print("=" * 80)
    
    # Parse arguments
    dry_run = "--dry-run" in sys.argv
    delete_all = "--all" in sys.argv
    pattern = None
    
    for arg in sys.argv[1:]:
        if arg.startswith("--pattern="):
            pattern = arg.split("=", 1)[1].lower()
        elif not arg.startswith("--"):
            pattern = arg.lower()
    
    if dry_run:
        print("\n🔍 DRY RUN MODE - No files will be deleted\n")
    
    # Get all cache folders
    print("\n📁 Scanning for OCR cache folders...")
    folders = get_cache_folders()
    
    if not folders:
        print("\n✓ No cache folders found")
        print("  Locations checked:")
        print(f"    - {UPLOADS_DIR}")
        print(f"    - {BACKEND_UPLOADS_DIR}")
        return
    
    print(f"\n✓ Found {len(folders)} cache folder(s)\n")
    
    # Display folder information
    total_size_mb = 0
    folders_to_delete = []
    
    for folder in folders:
        info = get_folder_info(folder)
        total_size_mb += info["size_mb"]
        
        # Check if folder matches pattern
        should_delete = False
        if delete_all:
            should_delete = True
        elif pattern:
            if pattern in info["name"].lower():
                should_delete = True
        
        if should_delete:
            folders_to_delete.append(folder)
        
        # Display info
        status = "🗑️  DELETE" if should_delete else "⏭️  SKIP"
        print(f"{status}: {info['name']}")
        print(f"         Path: {info['path']}")
        print(f"         Size: {info['size_mb']:.2f} MB ({info['files']} files)")
        if info["modified"]:
            print(f"         Modified: {info['modified']}")
        print(f"         Contents: ", end="")
        contents = []
        if info["has_ocr_json"]:
            contents.append("ocr_output.json")
        if info["has_pages"]:
            contents.append("pages/")
        if info["has_original"]:
            contents.append("original.pdf")
        print(", ".join(contents) if contents else "unknown")
        print()
    
    # Summary
    print("=" * 80)
    print(f"Total cache size: {total_size_mb:.2f} MB")
    print(f"Folders to delete: {len(folders_to_delete)}")
    print(f"Folders to keep: {len(folders) - len(folders_to_delete)}")
    print("=" * 80)
    
    if not folders_to_delete:
        print("\n✓ No folders selected for deletion")
        print("\nUsage:")
        print("  python clear_ocr_cache.py --all              # Delete all cache")
        print("  python clear_ocr_cache.py --pattern stori    # Delete folders matching 'stori'")
        print("  python clear_ocr_cache.py --dry-run --all    # Preview what would be deleted")
        return
    
    # Confirm deletion (unless dry-run or --all)
    if not dry_run and not delete_all:
        print(f"\n⚠️  About to delete {len(folders_to_delete)} folder(s)")
        response = input("Continue? (yes/no): ").strip().lower()
        if response not in ['yes', 'y']:
            print("\n❌ Cancelled by user")
            return
    
    # Delete folders
    print("\n🗑️  Deleting cache folders...")
    deleted_count = 0
    failed_count = 0
    
    for folder in folders_to_delete:
        if delete_folder(folder, dry_run):
            deleted_count += 1
        else:
            failed_count += 1
    
    # Final summary
    print("\n" + "=" * 80)
    if dry_run:
        print("DRY RUN COMPLETE")
        print(f"Would delete: {deleted_count} folder(s)")
    else:
        print("CLEANUP COMPLETE")
        print(f"Deleted: {deleted_count} folder(s)")
        if failed_count > 0:
            print(f"Failed: {failed_count} folder(s)")
    print("=" * 80)
    
    if not dry_run and deleted_count > 0:
        print("\n✅ OCR cache cleared successfully!")
        print("\nNext steps:")
        print("  1. Restart backend service")
        print("  2. Re-upload your test invoices")
        print("  3. Watch logs for [SPATIAL_CLUSTER] markers")
        print("  4. Verify new extraction results")

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

