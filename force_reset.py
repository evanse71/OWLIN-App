#!/usr/bin/env python3
"""
Aggressive Cache Reset Script

This script performs a complete reset of the OCR/LLM pipeline by:
1. Deleting all files in data/uploads/ (all uploaded files and OCR artifacts)
2. Deleting data/owlin.db (all database records including hash lookups)
3. Re-initializing a fresh database with init_db()

This ensures NO hash matches and forces the backend to run LLM extraction
from scratch on the next upload.

Usage:
    python force_reset.py
"""

import os
import shutil
import sys
from pathlib import Path

# Add backend to path so we can import init_db
sys.path.insert(0, str(Path(__file__).parent))

from backend.app.db import init_db

def main():
    """Main reset logic."""
    
    print("=" * 80)
    print("AGGRESSIVE CACHE RESET - FORCE FRESH LLM PROCESSING")
    print("=" * 80)
    print()
    
    # Resolve paths relative to project root (where this script is located)
    project_root = Path(__file__).parent
    uploads_dir = project_root / "data" / "uploads"
    db_path = project_root / "data" / "owlin.db"
    
    deleted_items = []
    errors = []
    
    # Step 1: Delete all files in data/uploads/
    print("📁 Step 1: Clearing uploads directory...")
    if uploads_dir.exists():
        try:
            # Count items before deletion
            items = list(uploads_dir.iterdir())
            item_count = len(items)
            
            # Delete all contents
            for item in items:
                try:
                    if item.is_file():
                        item.unlink()
                        deleted_items.append(f"File: {item.name}")
                    elif item.is_dir():
                        shutil.rmtree(item)
                        deleted_items.append(f"Directory: {item.name}")
                except Exception as e:
                    errors.append(f"Failed to delete {item}: {e}")
            
            print(f"  ✓ Deleted {item_count} item(s) from {uploads_dir}")
        except Exception as e:
            errors.append(f"Failed to clear uploads directory: {e}")
            print(f"  ✗ Error clearing uploads directory: {e}")
    else:
        print(f"  ⏭️  Uploads directory does not exist: {uploads_dir}")
        print(f"     (This is OK if no files have been uploaded yet)")
    
    print()
    
    # Step 2: Delete database file
    print("🗄️  Step 2: Deleting database...")
    if db_path.exists():
        try:
            db_size = db_path.stat().st_size / (1024 * 1024)  # Size in MB
            db_path.unlink()
            print(f"  ✓ Deleted database: {db_path}")
            print(f"    Size: {db_size:.2f} MB")
            deleted_items.append(f"Database: {db_path.name}")
        except Exception as e:
            errors.append(f"Failed to delete database: {e}")
            print(f"  ✗ Error deleting database: {e}")
    else:
        print(f"  ⏭️  Database does not exist: {db_path}")
        print(f"     (This is OK if database hasn't been initialized yet)")
    
    print()
    
    # Step 3: Re-initialize database
    print("🔄 Step 3: Re-initializing database...")
    try:
        init_db()
        print(f"  ✓ Database re-initialized successfully")
        print(f"    Fresh tables created with WAL mode enabled")
    except Exception as e:
        errors.append(f"Failed to initialize database: {e}")
        print(f"  ✗ Error initializing database: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    
    # Summary
    print("=" * 80)
    print("RESET SUMMARY")
    print("=" * 80)
    print(f"Items deleted: {len(deleted_items)}")
    if deleted_items:
        for item in deleted_items[:10]:  # Show first 10
            print(f"  - {item}")
        if len(deleted_items) > 10:
            print(f"  ... and {len(deleted_items) - 10} more")
    
    if errors:
        print(f"\nErrors encountered: {len(errors)}")
        for error in errors:
            print(f"  ✗ {error}")
    
    print()
    print("=" * 80)
    if not errors:
        print("✅ RESET COMPLETE - Fresh start ready!")
        print()
        print("Next steps:")
        print("  1. Restart backend: ./start_backend_5176.bat")
        print("  2. Upload a test invoice")
        print("  3. Watch logs for [LLM_EXTRACTION] markers")
        print("  4. Verify new extraction results (no 'Unknown Item' data)")
    else:
        print("⚠️  RESET COMPLETE WITH ERRORS")
        print("   Please review errors above and retry if needed")
    print("=" * 80)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

