"""
Simple test that proves the invoice query service reads from SQLite
"""
import sqlite3
import os
import json
import pytest
from pathlib import Path
import tempfile

def test_invoice_query_reads_sqlite(temp_db_path, migrate_temp_db):
    """Test that invoice query service reads from SQLite database"""
    # seed via the exact same connection class used by the app
    conn = migrate_temp_db.get_conn()
    c = conn.cursor()
    
    # Create uploaded file first (required by foreign key)
    c.execute("INSERT OR IGNORE INTO uploaded_files(id, original_filename, canonical_path, file_size, file_hash, mime_type, upload_timestamp) VALUES('test_file_001', 'test.pdf', '/tmp/test.pdf', 1024, 'hash123', 'application/pdf', datetime('now'))")
    conn.commit()
    
    # Insert invoice first
    c.execute("INSERT OR IGNORE INTO invoices(id, file_id, created_at, total_amount_pennies) VALUES('test_query_inv', 'test_file_001', datetime('now'), 777)")
    conn.commit()  # Commit invoice first
    
    # Then insert line items
    c.execute("""INSERT OR IGNORE INTO invoice_line_items
        (id, invoice_id, description, quantity_each, unit_price_pennies, line_total_pennies, line_flags)
        VALUES(999, 'test_query_inv', 'API SEED', 3, 123, 369, '[]')""")
    conn.commit()

    # call the service directly (integration, not HTTP)
    # Force the service to use the same DB manager instance
    import sys; sys.path.insert(0, "backend")
    from services.invoice_query import fetch_invoice
    
    # Temporarily override the environment to ensure service uses temp DB
    old_env = os.environ.get("OWLIN_DB_PATH")
    try:
        os.environ["OWLIN_DB_PATH"] = str(temp_db_path)
        payload = fetch_invoice("test_query_inv")
        assert payload is not None
        assert payload["meta"]["total_amount_pennies"] == 777
        ln = payload["lines"][0]
        assert ln["unit_price_pennies"] == 123
        assert ln["line_total_pennies"] == 369
    finally:
        if old_env:
            os.environ["OWLIN_DB_PATH"] = old_env
        else:
            os.environ.pop("OWLIN_DB_PATH", None)

def test_invoice_query_returns_none_for_missing(temp_db_path, migrate_temp_db):
    """Test that query service returns None for missing invoices"""
    # call the service directly
    import sys; sys.path.insert(0, "backend")
    from services.invoice_query import fetch_invoice
    
    result = fetch_invoice('nonexistent_invoice')
    assert result is None, "Query service should return None for missing invoice" 