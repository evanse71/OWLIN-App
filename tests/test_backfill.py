"""
Test backfill functionality
"""

import pytest
import sys
import os
import tempfile
import sqlite3

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from db_manager_unified import DatabaseManager


class TestBackfill:
    """Test backfill normalisation functionality."""
    
    def test_backfill_writes_canonical_fields(self):
        """Test that backfill writes canonical fields and flags."""
        # Create temporary database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
            db_path = tmp_db.name
        
        try:
            # Initialize database
            db_manager = DatabaseManager(db_path)
            db_manager.run_migrations()
            
            # Insert test invoice data
            with db_manager.get_connection() as conn:
                # Insert uploaded file
                conn.execute("""
                    INSERT INTO uploaded_files (id, original_filename, canonical_path, file_size, file_hash, mime_type, doc_type, upload_timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
                """, ("FILE001", "test.pdf", "test.pdf", 1000, "hash123", "application/pdf", "invoice"))
                
                # Insert invoice
                conn.execute("""
                    INSERT INTO invoices (id, file_id, supplier_name, invoice_date, total_amount_pennies, created_at)
                    VALUES (?, ?, ?, ?, ?, datetime('now'))
                """, ("INV001", "FILE001", "Test Supplier", "2024-01-01", 5000))
                
                # Insert invoice line items
                conn.execute("""
                    INSERT INTO invoice_line_items (id, invoice_id, description, quantity, unit_price_pennies, line_total_pennies, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
                """, (1, "INV001", "24x275ml Cola", 1.0, 3000, 3000))
                
                conn.commit()
            
            # Run backfill
            from scripts.backfill_normalisation import main
            os.environ["OWLIN_DB"] = db_path; main()
            
            # Verify canonical fields were written
            with db_manager.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT canonical_quantities_json, line_flags_json
                    FROM invoice_line_items 
                    WHERE id = ?
                """, (1,))
                
                row = cursor.fetchone()
                assert row is not None, "Invoice line item not found"
                
                canonical_json, flags_json = row
                assert canonical_json is not None, "Canonical quantities not written"
                assert flags_json is not None, "Line flags not written"
                
        finally:
            # Cleanup
            os.unlink(db_path)
    
    def test_backfill_runs_cleanly_multiple_times(self):
        """Test that backfill can be re-run cleanly."""
        # Create temporary database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
            db_path = tmp_db.name
        
        try:
            # Initialize database
            db_manager = DatabaseManager(db_path)
            db_manager.run_migrations()
            
            # Insert test data
            with db_manager.get_connection() as conn:
                # Insert uploaded file
                conn.execute("""
                    INSERT INTO uploaded_files (id, original_filename, canonical_path, file_size, file_hash, mime_type, doc_type, upload_timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
                """, ("FILE001", "test.pdf", "test.pdf", 1000, "hash123", "application/pdf", "invoice"))
                
                conn.execute("""
                    INSERT INTO invoices (id, file_id, supplier_name, invoice_date, total_amount_pennies, created_at)
                    VALUES (?, ?, ?, ?, ?, datetime('now'))
                """, ("INV001", "FILE001", "Test Supplier", "2024-01-01", 5000))
                
                conn.execute("""
                    INSERT INTO invoice_line_items (id, invoice_id, description, quantity, unit_price_pennies, line_total_pennies, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
                """, (1, "INV001", "Test Item", 1.0, 5000, 5000))
                
                conn.commit()
            
            # Run backfill twice
            from scripts.backfill_normalisation import main
            
            # First run
            result1 = os.environ["OWLIN_DB"] = db_path; main()
            assert result1['invoices_processed'] == 1
            assert result1['invoices_failed'] == 0
            
            # Second run (should be idempotent)
            result2 = os.environ["OWLIN_DB"] = db_path; main()
            assert result2['invoices_processed'] == 1
            assert result2['invoices_failed'] == 0
            
            # Results should be identical
            assert result1 == result2
            
        finally:
            # Cleanup
            os.unlink(db_path) 