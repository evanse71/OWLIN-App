#!/usr/bin/env python3
"""
Rebuild uploaded_files table by scanning storage directory.
This script matches files by their hash and creates canonical path mappings.
"""

import os
import sqlite3
import hashlib
from pathlib import Path

STORAGE = os.environ.get("OWLIN_STORAGE", "storage/uploads")
DB = os.environ.get("OWLIN_DB", "owlin.db")

def compute_file_hash(file_path):
    """Compute SHA256 hash of a file"""
    hash_sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()

def main():
    print(f"Rebuilding uploaded_files table...")
    print(f"Storage: {os.path.abspath(STORAGE)}")
    print(f"Database: {DB}")
    
    # Connect to database
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    
    # Ensure table exists
    cur.execute("""
        CREATE TABLE IF NOT EXISTS uploaded_files (
            file_hash TEXT PRIMARY KEY, 
            absolute_path TEXT NOT NULL, 
            size_bytes INTEGER, 
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Clear existing records (we're rebuilding)
    cur.execute("DELETE FROM uploaded_files")
    
    # Scan storage directory
    storage_path = Path(STORAGE)
    if not storage_path.exists():
        print(f"Storage directory {STORAGE} does not exist!")
        return
    
    files_processed = 0
    for file_path in storage_path.iterdir():
        if not file_path.is_file():
            continue
            
        try:
            # Compute hash of the file
            file_hash = compute_file_hash(file_path)
            size_bytes = file_path.stat().st_size
            absolute_path = str(file_path.absolute())
            
            # Insert into uploaded_files table
            cur.execute("""
                INSERT OR REPLACE INTO uploaded_files(file_hash, absolute_path, size_bytes, created_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (file_hash, absolute_path, size_bytes))
            
            files_processed += 1
            print(f"Processed: {file_path.name} -> {file_hash[:8]}...")
            
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
    
    # Commit changes
    con.commit()
    con.close()
    
    print(f"\nRebuild complete! Processed {files_processed} files.")
    
    # Show some stats
    con = sqlite3.connect(DB)
    cur = con.cursor()
    count = cur.execute("SELECT COUNT(*) FROM uploaded_files").fetchone()[0]
    print(f"Total records in uploaded_files: {count}")
    
    # Show sample records
    print("\nSample records:")
    for row in cur.execute("SELECT file_hash, absolute_path FROM uploaded_files LIMIT 5"):
        print(f"  {row[0][:8]}... -> {os.path.basename(row[1])}")
    
    con.close()

if __name__ == "__main__":
    main() 