"""
Test that API reads from real SQLite database, not mocks
"""
import sqlite3
import os
import json
import pytest
from pathlib import Path
import tempfile

def seed(conn):
    """Seed test database with known data"""
    c = conn.cursor()
    c.execute("""
        INSERT OR IGNORE INTO invoices(id, created_at, total_amount_pennies) 
        VALUES('api_seed_inv', datetime('now'), 777)
    """)
    c.execute("""
        INSERT OR IGNORE INTO invoice_line_items
        (id, invoice_id, description, quantity_each, unit_price_pennies, line_total_pennies, line_flags)
        VALUES(999, 'api_seed_inv', 'API SEED', 3, 123, 369, '[]')
    """)
    conn.commit()

def test_invoice_api_reads_sqlite(tmp_path):
    """Test that invoice API reads from SQLite database"""
    # Point app to temp DB to avoid pollution
    db = tmp_path / "owlin.db"
    os.environ["OWLIN_DB_PATH"] = str(db)
    
    # Initialize db with migrations
    import sys
    sys.path.insert(0, "backend")
    from db_manager_unified import get_db_manager
    
    # Run migrations to create schema
    db_manager = get_db_manager()
    db_manager.run_migrations()
    
    # Seed with test data
    conn = db_manager.get_conn()
    seed(conn)
    
    # Test the API endpoint
    from backend.test_server import app
    from fastapi.testclient import TestClient
    
    client = TestClient(app)
    r = client.get("/api/invoices/api_seed_inv")
    
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    
    payload = r.json()
    assert payload["id"] == "api_seed_inv"
    assert payload["meta"]["total_inc"] == 7.77  # 777 pennies = 7.77 pounds
    assert payload["lines"][0]["desc"] == "API SEED"
    assert payload["lines"][0]["unit_price"] == 1.23  # 123 pennies = 1.23 pounds
    assert payload["lines"][0]["line_total"] == 3.69  # 369 pennies = 3.69 pounds

def test_api_returns_404_for_nonexistent_invoice():
    """Test that API returns proper 404 for missing invoices"""
    # Use temp DB
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
        db_path = tmp_db.name
    
    try:
        os.environ["OWLIN_DB_PATH"] = db_path
        
        import sys
        sys.path.insert(0, "backend")
        from db_manager_unified import get_db_manager
        
        # Initialize empty DB
        db_manager = get_db_manager()
        db_manager.run_migrations()
        
        # Test 404 response
        from backend.test_server import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        r = client.get("/api/invoices/nonexistent_invoice")
        
        assert r.status_code == 404
        assert "invoice not found" in r.json()["detail"]
        
    finally:
        os.unlink(db_path)
        os.environ.pop("OWLIN_DB_PATH", None) 