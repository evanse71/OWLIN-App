#!/usr/bin/env python3
"""
Apply HTR database migration.

This script applies the HTR tables migration to the SQLite database.
"""

import sqlite3
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def apply_htr_migration(db_path: str = "data/owlin.db"):
    """Apply HTR migration to the database."""
    try:
        # Read migration file
        migration_file = Path(__file__).parent.parent / "migrations" / "0005_htr_tables.sql"
        
        if not migration_file.exists():
            print(f"Migration file not found: {migration_file}")
            return False
        
        with open(migration_file, 'r', encoding='utf-8') as f:
            migration_sql = f.read()
        
        # Apply migration
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Execute migration SQL
            cursor.executescript(migration_sql)
            conn.commit()
            
            print(f"HTR migration applied successfully to {db_path}")
            return True
            
    except Exception as e:
        print(f"Failed to apply HTR migration: {e}")
        return False


def main():
    """Main function."""
    db_path = sys.argv[1] if len(sys.argv) > 1 else "data/owlin.db"
    
    print(f"Applying HTR migration to {db_path}...")
    
    success = apply_htr_migration(db_path)
    
    if success:
        print("Migration completed successfully!")
        return 0
    else:
        print("Migration failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
