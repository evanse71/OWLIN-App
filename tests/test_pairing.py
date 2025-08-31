#!/usr/bin/env python3
"""
Comprehensive pairing system tests
"""

import os
import sys
import tempfile
import json
import sqlite3
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from db_manager_unified import DatabaseManager
from services.pairing_service import PairingService

def test_pairing_scoring():
    """Test deterministic scoring algorithm"""
    print("🧪 Testing pairing scoring algorithm...")
    
    # Test supplier name normalization
    assert PairingService.normalize_supplier_name("ABC Company Ltd") == "abc"
    assert PairingService.normalize_supplier_name("XYZ Corp.") == "xyz"
    
    # Test supplier scoring
    supplier_score = PairingService.calculate_supplier_score("ABC Company", "ABC Company Ltd")
    assert supplier_score > 0.8, f"Expected high supplier score, got {supplier_score}"
    
    # Test date scoring
    date_score = PairingService.calculate_date_score("2024-01-01", "2024-01-02")
    assert date_score == 1.0, f"Expected perfect date score, got {date_score}"
    
    # Test amount scoring
    amount_score = PairingService.calculate_amount_score(100.0, 102.0)
    assert amount_score > 0.5, f"Expected good amount score, got {amount_score}"
    
    # Test overall scoring
    overall_score = PairingService.calculate_overall_score(0.9, 1.0, 0.8)
    assert overall_score > 80, f"Expected high overall score, got {overall_score}"
    
    print("✅ Pairing scoring tests passed")

def test_pairing_suggestions():
    """Test pairing suggestions with real database"""
    print("🧪 Testing pairing suggestions...")
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
        db_path = tmp_db.name
    
    try:
        # Initialize database
        db = DatabaseManager(db_path)
        db.run_migrations()
        
        # Insert test data
        with db.get_connection() as conn:
            # Insert test uploaded files
            conn.execute("""
                INSERT INTO uploaded_files (id, original_filename, canonical_path, file_size, file_hash, mime_type, doc_type, upload_timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, ("test_file_1", "test_invoice.pdf", "/tmp/test_invoice.pdf", 1024, "test_hash_1", "application/pdf", "invoice"))
            
            conn.execute("""
                INSERT INTO uploaded_files (id, original_filename, canonical_path, file_size, file_hash, mime_type, doc_type, upload_timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, ("test_file_2", "test_dn1.pdf", "/tmp/test_dn1.pdf", 1024, "test_hash_2", "application/pdf", "delivery_note"))
            
            conn.execute("""
                INSERT INTO uploaded_files (id, original_filename, canonical_path, file_size, file_hash, mime_type, doc_type, upload_timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, ("test_file_3", "test_dn2.pdf", "/tmp/test_dn2.pdf", 1024, "test_hash_3", "application/pdf", "delivery_note"))
            
            # Insert test invoice
            conn.execute("""
                INSERT INTO invoices (id, file_id, supplier_name, invoice_date, total_amount_pennies, doc_type, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, ("test_inv_1", "test_file_1", "ABC Company", "2024-01-01", 10000, "invoice", "parsed"))
            
            # Insert test delivery notes
            conn.execute("""
                INSERT INTO delivery_notes (id, file_id, supplier_name, delivery_date, doc_type, matched_invoice_id, total_items)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, ("test_dn_1", "test_file_2", "ABC Company", "2024-01-02", "delivery_note", None, 100))
            
            conn.execute("""
                INSERT INTO delivery_notes (id, file_id, supplier_name, delivery_date, doc_type, matched_invoice_id, total_items)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, ("test_dn_2", "test_file_3", "XYZ Company", "2024-01-01", "delivery_note", None, 50))
            
            conn.commit()
            
            # Debug: check if delivery notes were inserted
            dn_count = conn.execute("SELECT COUNT(*) FROM delivery_notes").fetchone()[0]
            print(f"Inserted {dn_count} delivery notes")
            
            # Debug: check delivery notes data
            dns = conn.execute("SELECT id, matched_invoice_id FROM delivery_notes").fetchall()
            for dn in dns:
                print(f"DN {dn['id']}: matched_invoice_id = {dn['matched_invoice_id']}")
        
        # Test pairing suggestions
        with db.get_connection() as conn:
            suggestions = PairingService.get_pairing_suggestions(limit=5, db_conn=conn)
        
        # Should find suggestions
        assert len(suggestions) > 0, "Should find pairing suggestions"
        
        # Check suggestion structure
        for suggestion in suggestions:
            assert 'delivery_note_id' in suggestion
            assert 'invoice_id' in suggestion
            assert 'score' in suggestion
            assert 'reasons' in suggestion
            assert isinstance(suggestion['score'], int)
            assert 0 <= suggestion['score'] <= 100
        
        print("✅ Pairing suggestions tests passed")
        
    finally:
        # Cleanup
        os.unlink(db_path)

def test_pairing_confirmation():
    """Test pairing confirmation with audit logging"""
    print("🧪 Testing pairing confirmation...")
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
        db_path = tmp_db.name
    
    try:
        # Initialize database
        db = DatabaseManager(db_path)
        db.run_migrations()
        
        # Insert test data
        with db.get_connection() as conn:
            # Insert test uploaded files
            conn.execute("""
                INSERT INTO uploaded_files (id, original_filename, canonical_path, file_size, file_hash, mime_type, doc_type, upload_timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, ("test_file_1", "test_invoice.pdf", "/tmp/test_invoice.pdf", 1024, "test_hash_1", "application/pdf", "invoice"))
            
            conn.execute("""
                INSERT INTO uploaded_files (id, original_filename, canonical_path, file_size, file_hash, mime_type, doc_type, upload_timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, ("test_file_2", "test_dn1.pdf", "/tmp/test_dn1.pdf", 1024, "test_hash_2", "application/pdf", "delivery_note"))
            
            # Insert test invoice and delivery note
            conn.execute("""
                INSERT INTO invoices (id, file_id, supplier_name, invoice_date, total_amount_pennies, doc_type, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, ("test_inv_1", "test_file_1", "ABC Company", "2024-01-01", 10000, "invoice", "parsed"))
            
            conn.execute("""
                INSERT INTO delivery_notes (id, file_id, supplier_name, delivery_date, doc_type, matched_invoice_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """, ("test_dn_1", "test_file_2", "ABC Company", "2024-01-02", "delivery_note", None))
            
            conn.commit()
        
        # Test pairing confirmation
        with db.get_connection() as conn:
            result = PairingService.confirm_pairing("test_dn_1", "test_inv_1", db_conn=conn)
        
        assert "error" not in result, f"Pairing confirmation failed: {result}"
        assert result["matched"] == True
        assert "score" in result
        
        # Verify database was updated
        with db.get_connection() as conn:
            # Check delivery note was linked
            dn = conn.execute("""
                SELECT matched_invoice_id FROM delivery_notes WHERE id = ?
            """, ("test_dn_1",)).fetchone()
            assert dn['matched_invoice_id'] == "test_inv_1"
            
            # Check invoice was marked as paired
            inv = conn.execute("""
                SELECT paired FROM invoices WHERE id = ?
            """, ("test_inv_1",)).fetchone()
            assert inv['paired'] == 1
            
            # Check audit log was created
            audit = conn.execute("""
                SELECT action, entity_type, entity_id FROM audit_log 
                WHERE action = 'pairing_confirmed' AND entity_id = ?
            """, ("test_dn_1",)).fetchone()
            assert audit is not None
            assert audit['action'] == 'pairing_confirmed'
        
        print("✅ Pairing confirmation tests passed")
        
    finally:
        # Cleanup
        os.unlink(db_path)

def test_pairing_rejection():
    """Test pairing rejection with audit logging"""
    print("🧪 Testing pairing rejection...")
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
        db_path = tmp_db.name
    
    try:
        # Initialize database
        db = DatabaseManager(db_path)
        db.run_migrations()
        
        # Test pairing rejection
        with db.get_connection() as conn:
            result = PairingService.reject_pairing("test_suggestion_1", db_conn=conn)
        
        assert "error" not in result, f"Pairing rejection failed: {result}"
        assert result["rejected"] == True
        
        # Verify audit log was created
        with db.get_connection() as conn:
            audit = conn.execute("""
                SELECT action, entity_type, entity_id FROM audit_log 
                WHERE action = 'pairing_rejected' AND entity_id = ?
            """, ("test_suggestion_1",)).fetchone()
            assert audit is not None
            assert audit['action'] == 'pairing_rejected'
        
        print("✅ Pairing rejection tests passed")
        
    finally:
        # Cleanup
        os.unlink(db_path)

def test_auto_pairing():
    """Test auto-pairing functionality"""
    print("🧪 Testing auto-pairing...")
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
        db_path = tmp_db.name
    
    try:
        # Initialize database
        db = DatabaseManager(db_path)
        db.run_migrations()
        
        # Insert test data with high confidence match
        with db.get_connection() as conn:
            # Insert test uploaded files
            conn.execute("""
                INSERT INTO uploaded_files (id, original_filename, canonical_path, file_size, file_hash, mime_type, doc_type, upload_timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, ("test_file_1", "test_invoice.pdf", "/tmp/test_invoice.pdf", 1024, "test_hash_1", "application/pdf", "invoice"))
            
            conn.execute("""
                INSERT INTO uploaded_files (id, original_filename, canonical_path, file_size, file_hash, mime_type, doc_type, upload_timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, ("test_file_2", "test_dn1.pdf", "/tmp/test_dn1.pdf", 1024, "test_hash_2", "application/pdf", "delivery_note"))
            
            # Insert test invoice and delivery note with identical supplier and close dates
            conn.execute("""
                INSERT INTO invoices (id, file_id, supplier_name, invoice_date, total_amount_pennies, doc_type, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, ("test_inv_1", "test_file_1", "ABC Company Ltd", "2024-01-01", 10000, "invoice", "parsed"))
            
            conn.execute("""
                INSERT INTO delivery_notes (id, file_id, supplier_name, delivery_date, doc_type, matched_invoice_id, total_items)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, ("test_dn_1", "test_file_2", "ABC Company Ltd", "2024-01-02", "delivery_note", None, 100))
            
            conn.commit()
        
        # Test auto-pairing
        with db.get_connection() as conn:
            auto_paired = PairingService.auto_pair_high_confidence(db_conn=conn)
        
        # Should auto-pair the high confidence match
        assert len(auto_paired) > 0, "Should auto-pair high confidence matches"
        
        # Verify the pairing was actually done
        with db.get_connection() as conn:
            dn = conn.execute("""
                SELECT matched_invoice_id FROM delivery_notes WHERE id = ?
            """, ("test_dn_1",)).fetchone()
            assert dn['matched_invoice_id'] == "test_inv_1"
        
        print("✅ Auto-pairing tests passed")
        
    finally:
        # Cleanup
        os.unlink(db_path)

if __name__ == "__main__":
    print("🚀 Running comprehensive pairing system tests...")
    
    test_pairing_scoring()
    test_pairing_suggestions()
    test_pairing_confirmation()
    test_pairing_rejection()
    test_auto_pairing()
    
    print("🎉 All pairing system tests passed!") 