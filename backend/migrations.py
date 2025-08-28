#!/usr/bin/env python3
"""
Startup migration system for Owlin OCR
Ensures all required tables and columns exist on startup
"""

import os
import sqlite3
import logging
from pathlib import Path

log = logging.getLogger("migrations")

def run_startup_migrations(db_path: str):
    """Run all startup migrations to ensure schema consistency"""
    log.info(f"Running startup migrations on {db_path}")
    
    # Ensure database directory exists
    db_dir = Path(db_path).parent
    db_dir.mkdir(parents=True, exist_ok=True)
    
    # Connect to database (creates if doesn't exist)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    try:
        # 1. Ensure uploaded_files table exists
        conn.execute("""
            CREATE TABLE IF NOT EXISTS uploaded_files (
                file_hash TEXT PRIMARY KEY,
                absolute_path TEXT NOT NULL,
                size_bytes INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        log.info("✅ uploaded_files table ensured")
        
        # 2. Add missing columns to invoices table
        columns_to_add = [
            ("line_items", "TEXT DEFAULT '[]'"),
            ("error_message", "TEXT"),
            ("page_range", "TEXT")
        ]
        
        # Get existing columns
        existing_columns = set()
        for row in conn.execute("PRAGMA table_info(invoices)"):
            existing_columns.add(row["name"])
        
        # Add missing columns
        for col_name, col_def in columns_to_add:
            if col_name not in existing_columns:
                conn.execute(f"ALTER TABLE invoices ADD COLUMN {col_name} {col_def}")
                log.info(f"✅ Added column invoices.{col_name}")
            else:
                log.info(f"ℹ️ Column invoices.{col_name} already exists")
        
        # 3. Run integrity tripwires
        run_integrity_tripwires(conn)
        
        conn.commit()
        log.info("✅ Startup migrations completed successfully")
        
    except Exception as e:
        log.error(f"❌ Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def run_integrity_tripwires(conn: sqlite3.Connection):
    """Run integrity checks and log results"""
    log.info("Running integrity tripwires...")
    
    try:
        # Count invoices still in processing
        processing_count = conn.execute(
            "SELECT COUNT(*) FROM invoices WHERE status='processing'"
        ).fetchone()[0]
        log.info(f"📊 Invoices in processing: {processing_count}")
        
        # Count invoices with file_hash not present in uploaded_files
        missing_files_count = conn.execute("""
            SELECT COUNT(*) FROM invoices i
            LEFT JOIN uploaded_files u ON u.file_hash = i.file_hash
            WHERE i.file_hash IS NOT NULL AND u.absolute_path IS NULL
        """).fetchone()[0]
        log.info(f"📊 Invoices missing from uploaded_files: {missing_files_count}")
        
        # Count high-confidence zero-line invoices
        hi_conf_zero_lines = conn.execute("""
            SELECT COUNT(*) FROM invoices
            WHERE confidence >= 80 
            AND (line_items IS NULL OR line_items = '' OR line_items = '[]')
        """).fetchone()[0]
        log.info(f"📊 High-confidence zero-line invoices: {hi_conf_zero_lines}")
        
        # Overall health assessment
        if processing_count > 0:
            log.warning(f"⚠️ {processing_count} invoices stuck in processing")
        if missing_files_count > 0:
            log.warning(f"⚠️ {missing_files_count} invoices missing file records")
        if hi_conf_zero_lines > 5:
            log.warning(f"⚠️ {hi_conf_zero_lines} high-confidence invoices with no line items")
        
    except Exception as e:
        log.warning(f"⚠️ Integrity tripwire failed: {e}")

def get_db_path() -> str:
    """Get database path from environment or default"""
    db_path = os.environ.get("OWLIN_DB", "owlin.db")
    
    # Resolve relative paths
    if not os.path.isabs(db_path):
        db_path = os.path.abspath(db_path)
    
    log.info(f"Database path: {db_path}")
    return db_path

if __name__ == "__main__":
    # Run migrations directly if called as script
    logging.basicConfig(level=logging.INFO)
    db_path = get_db_path()
    run_startup_migrations(db_path) 