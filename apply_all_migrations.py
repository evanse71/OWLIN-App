#!/usr/bin/env python3
"""
Apply all pending migrations (invoice_number + bbox).

Usage:
    python apply_all_migrations.py
"""

import sys
from pathlib import Path

# Import migration scripts
try:
    from apply_invoice_number_migration import apply_migration as apply_invoice_number
    from apply_bbox_migration import apply_migration as apply_bbox
    
    print("=" * 80)
    print("APPLYING ALL PENDING MIGRATIONS")
    print("=" * 80)
    
    # Apply invoice_number migration
    print("\n" + "=" * 80)
    print("MIGRATION 1: Invoice Number")
    print("=" * 80)
    success1 = apply_invoice_number()
    
    # Apply bbox migration
    print("\n" + "=" * 80)
    print("MIGRATION 2: Bounding Box")
    print("=" * 80)
    success2 = apply_bbox()
    
    if success1 and success2:
        print("\n" + "=" * 80)
        print("✅ ALL MIGRATIONS COMPLETE")
        print("=" * 80)
        print("\nNext steps:")
        print("1. Clear OCR cache: python clear_ocr_cache.py --all")
        print("   (or manually delete: backend/data/uploads/*)")
        print("2. Restart backend service")
        print("3. Re-process invoices to populate new fields:")
        print("   - invoice_number will be extracted and saved")
        print("   - bbox coordinates will be calculated and saved")
        print("4. Open UI and verify visual verification works")
        print("=" * 80)
        sys.exit(0)
    else:
        print("\n" + "=" * 80)
        print("❌ SOME MIGRATIONS FAILED")
        print("=" * 80)
        if not success1:
            print("  - Invoice number migration failed")
        if not success2:
            print("  - Bbox migration failed")
        print("\nPlease review errors above and try again.")
        sys.exit(1)
        
except ImportError as e:
    print(f"❌ Failed to import migration scripts: {e}")
    print("Please ensure apply_invoice_number_migration.py and apply_bbox_migration.py exist")
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

