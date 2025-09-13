#!/usr/bin/env python3
"""
Minimal test for startup migrations
"""

import os
import tempfile
import sqlite3
import sys
sys.path.append('.')

from migrations import run_startup_migrations

def test_startup_migrations():
    """Test that startup migrations create required tables and columns"""
    print("Testing startup migrations...")
    
    # Create a temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    try:
        # Set environment variable
        os.environ['OWLIN_DB'] = db_path
        
        # Run migrations
        run_startup_migrations(db_path)
        
        # Verify uploaded_files table exists
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        # Check uploaded_files table
        tables = [row['name'] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        assert 'uploaded_files' in tables, "uploaded_files table should exist"
        
        # Check uploaded_files schema
        columns = [row['name'] for row in conn.execute("PRAGMA table_info(uploaded_files)")]
        expected_columns = ['file_hash', 'absolute_path', 'size_bytes', 'created_at']
        for col in expected_columns:
            assert col in columns, f"Column {col} should exist in uploaded_files"
        
        # Check invoices table columns (create if doesn't exist)
        try:
            conn.execute("CREATE TABLE IF NOT EXISTS invoices (id TEXT PRIMARY KEY)")
        except:
            pass
        
        columns = [row['name'] for row in conn.execute("PRAGMA table_info(invoices)")]
        expected_columns = ['line_items', 'error_message', 'page_range']
        for col in expected_columns:
            assert col in columns, f"Column {col} should exist in invoices"
        
        conn.close()
        print("✅ Startup migrations test passed!")
        
    except Exception as e:
        print(f"❌ Startup migrations test failed: {e}")
        raise
    finally:
        # Clean up
        if os.path.exists(db_path):
            os.unlink(db_path)

if __name__ == "__main__":
    test_startup_migrations() 