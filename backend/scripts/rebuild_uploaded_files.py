#!/usr/bin/env python3
"""
Storage Invariants Check - Zero Drift Detection

Scans OWLIN_STORAGE directory and compares with uploaded_files table.
Detects orphaned files, missing database records, and path mismatches.

Usage:
    python3 backend/scripts/rebuild_uploaded_files.py
    
Exit codes:
    0: No drift detected (storage and database are in sync)
    1: Drift detected (orphaned files, missing records, or path mismatches)
    2: Error during scan
"""

import sys
import os
import hashlib
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Add backend to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

def scan_storage_directory(storage_path: str) -> Dict[str, str]:
    """
    Scan storage directory and return file_hash -> file_path mapping
    
    Args:
        storage_path: Path to storage directory
        
    Returns:
        Dictionary mapping file hashes to file paths
    """
    storage_files = {}
    storage_dir = Path(storage_path)
    
    if not storage_dir.exists():
        print(f"❌ Storage directory does not exist: {storage_path}")
        return storage_files
    
    print(f"🔍 Scanning storage directory: {storage_path}")
    
    for file_path in storage_dir.rglob("*"):
        if file_path.is_file():
            try:
                # Generate hash for file
                file_hash = generate_file_hash(str(file_path))
                storage_files[file_hash] = str(file_path)
                print(f"   Found: {file_hash} -> {file_path.name}")
            except Exception as e:
                print(f"   ❌ Error processing {file_path}: {e}")
    
    print(f"📊 Found {len(storage_files)} files in storage")
    return storage_files

def generate_file_hash(file_path: str) -> str:
    """Generate SHA256 hash for file"""
    hash_sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()

def get_database_files() -> Dict[str, str]:
    """
    Get file_hash -> canonical_path mapping from database
    
    Returns:
        Dictionary mapping file hashes to canonical paths
    """
    try:
        from db_manager_unified import get_db_manager
        
        db_manager = get_db_manager()
        database_files = {}
        
        with db_manager.get_connection() as conn:
            cursor = conn.execute("""
                SELECT file_hash, canonical_path, original_filename 
                FROM uploaded_files
            """)
            
            for row in cursor.fetchall():
                database_files[row['file_hash']] = row['canonical_path']
                print(f"   DB Record: {row['file_hash']} -> {row['canonical_path']}")
        
        print(f"📊 Found {len(database_files)} records in database")
        return database_files
        
    except Exception as e:
        print(f"❌ Error accessing database: {e}")
        return {}

def detect_drift(storage_files: Dict[str, str], database_files: Dict[str, str]) -> Tuple[bool, List[str]]:
    """
    Detect drift between storage and database
    
    Args:
        storage_files: file_hash -> file_path mapping from storage
        database_files: file_hash -> canonical_path mapping from database
        
    Returns:
        Tuple of (has_drift: bool, issues: List[str])
    """
    issues = []
    
    # Files in storage but not in database (orphaned files)
    orphaned_hashes = set(storage_files.keys()) - set(database_files.keys())
    if orphaned_hashes:
        for file_hash in orphaned_hashes:
            issues.append(f"ORPHANED_FILE: {file_hash} -> {storage_files[file_hash]}")
    
    # Files in database but not in storage (missing files)
    missing_hashes = set(database_files.keys()) - set(storage_files.keys())
    if missing_hashes:
        for file_hash in missing_hashes:
            issues.append(f"MISSING_FILE: {file_hash} -> {database_files[file_hash]}")
    
    # Files with path mismatches
    common_hashes = set(storage_files.keys()) & set(database_files.keys())
    for file_hash in common_hashes:
        storage_path = storage_files[file_hash]
        db_path = database_files[file_hash]
        
        if storage_path != db_path:
            issues.append(f"PATH_MISMATCH: {file_hash} -> storage: {storage_path}, db: {db_path}")
    
    # Check for files that don't follow canonical naming pattern
    for file_hash, file_path in storage_files.items():
        file_name = Path(file_path).name
        if not file_name.startswith(file_hash):
            issues.append(f"NON_CANONICAL_NAME: {file_hash} -> {file_name}")
    
    has_drift = len(issues) > 0
    return has_drift, issues

def cleanup_orphaned_files(storage_files: Dict[str, str], database_files: Dict[str, str]) -> int:
    """
    Clean up orphaned files (files in storage but not in database)
    
    Args:
        storage_files: file_hash -> file_path mapping from storage
        database_files: file_hash -> canonical_path mapping from database
        
    Returns:
        Number of files cleaned up
    """
    orphaned_hashes = set(storage_files.keys()) - set(database_files.keys())
    cleaned_count = 0
    
    for file_hash in orphaned_hashes:
        file_path = storage_files[file_hash]
        try:
            os.remove(file_path)
            print(f"🗑️ Cleaned up orphaned file: {file_path}")
            cleaned_count += 1
        except Exception as e:
            print(f"❌ Failed to clean up {file_path}: {e}")
    
    return cleaned_count

def main():
    """Main function"""
    print("🔍 STORAGE INVARIANTS CHECK - ZERO DRIFT DETECTION")
    print("=" * 60)
    
    # Get storage path from environment
    storage_path = os.environ.get("OWLIN_STORAGE", "data/uploads")
    print(f"📁 Storage path: {storage_path}")
    
    try:
        # Scan storage directory
        storage_files = scan_storage_directory(storage_path)
        
        # Get database records
        database_files = get_database_files()
        
        if not storage_files and not database_files:
            print("✅ No files found in storage or database - no drift possible")
            return 0
        
        # Detect drift
        has_drift, issues = detect_drift(storage_files, database_files)
        
        if has_drift:
            print(f"\n🚨 DRIFT DETECTED ({len(issues)} issues):")
            for issue in issues:
                print(f"   ❌ {issue}")
            
            # Ask if user wants to clean up orphaned files
            orphaned_count = len([i for i in issues if i.startswith("ORPHANED_FILE")])
            if orphaned_count > 0:
                print(f"\n🗑️ Found {orphaned_count} orphaned files")
                response = input("Clean up orphaned files? (y/N): ").strip().lower()
                if response == 'y':
                    cleaned = cleanup_orphaned_files(storage_files, database_files)
                    print(f"✅ Cleaned up {cleaned} orphaned files")
                    # If cleanup was successful, consider it a success
                    if cleaned == orphaned_count:
                        print("\n✅ ORPHANED FILES CLEANED UP SUCCESSFULLY")
                        return 0
            
            print(f"\n🚫 STORAGE DRIFT DETECTED ({len(issues)} issues)")
            return 1
        else:
            print("\n✅ NO DRIFT DETECTED")
            print("🎉 Storage and database are in sync")
            return 0
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return 2

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 