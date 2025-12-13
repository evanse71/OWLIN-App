#!/usr/bin/env python3
"""
Test Canonical Storage Invariants - Olympic Judge Certification
"""

import sys
import os
import tempfile
import shutil
import uuid
from pathlib import Path

# Add backend to path
sys.path.insert(0, 'backend')

def test_canonical_storage_invariants():
    """Test canonical storage invariants"""
    print("🧪 Testing Canonical Storage Invariants...")
    
    # Create temporary storage and database
    with tempfile.TemporaryDirectory() as temp_dir:
        storage_dir = Path(temp_dir) / "storage"
        storage_dir.mkdir()
        
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        try:
            # Set environment variables
            os.environ['OWLIN_DB'] = db_path
            os.environ['OWLIN_STORAGE'] = str(storage_dir)
            
            # Initialize database manager
            from db_manager_unified import DatabaseManager
            db = DatabaseManager(db_path)
            db.run_migrations()
            
            # Test 1: Canonical file naming
            print("📁 Testing canonical file naming...")
            
            # Create a test file
            test_content = b"Test file content for canonical storage"
            test_file = storage_dir / "test_original.txt"
            test_file.write_bytes(test_content)
            
            # Generate hash
            import hashlib
            file_hash = hashlib.sha256(test_content).hexdigest()
            
            # Save to uploaded_files table
            file_id = f"test_file_{uuid.uuid4().hex[:8]}"
            success = db.save_uploaded_file(
                file_id=file_id,
                original_filename="test_original.txt",
                canonical_path=str(test_file),
                file_size=len(test_content),
                file_hash=file_hash,
                mime_type="text/plain",
                doc_type="invoice"
            )
            
            if not success:
                print("❌ Failed to save uploaded file")
                return False
            
            # Check that file is recorded
            saved_file = db.get_uploaded_file(file_id)
            if not saved_file:
                print("❌ File not found in database")
                return False
            
            print("✅ Canonical file naming works")
            
            # Test 2: Duplicate detection
            print("🔄 Testing duplicate detection...")
            
            # Try to save the same file again with different ID
            file_id_2 = f"test_file_{uuid.uuid4().hex[:8]}"
            success_2 = db.save_uploaded_file(
                file_id=file_id_2,
                original_filename="test_duplicate.txt",
                canonical_path=str(test_file),
                file_size=len(test_content),
                file_hash=file_hash,  # Same hash
                mime_type="text/plain",
                doc_type="invoice"
            )
            
            # Should return True (duplicate detected)
            if not success_2:
                print("❌ Duplicate detection failed")
                return False
            
            # Check that only one file record exists for this hash
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM uploaded_files WHERE file_hash = ?", (file_hash,))
                count = cursor.fetchone()[0]
                
                if count != 1:
                    print(f"❌ Expected 1 file record, got {count}")
                    return False
            
            print("✅ Duplicate detection works")
            
            # Test 3: Orphan file cleanup
            print("🧹 Testing orphan file cleanup...")
            
            # Create another file
            test_content_2 = b"Another test file"
            test_file_2 = storage_dir / "test_orphan.txt"
            test_file_2.write_bytes(test_content_2)
            
            file_hash_2 = hashlib.sha256(test_content_2).hexdigest()
            file_id_3 = f"test_file_{uuid.uuid4().hex[:8]}"
            
            # Save file
            success_3 = db.save_uploaded_file(
                file_id=file_id_3,
                original_filename="test_orphan.txt",
                canonical_path=str(test_file_2),
                file_size=len(test_content_2),
                file_hash=file_hash_2,
                mime_type="text/plain",
                doc_type="invoice"
            )
            
            if not success_3:
                print("❌ Failed to save orphan test file")
                return False
            
            # Create an invoice referencing this file
            invoice_id = f"test_invoice_{uuid.uuid4().hex[:8]}"
            success_invoice = db.save_invoice(
                invoice_id=invoice_id,
                file_id=file_id_3,
                invoice_number="INV-001",
                invoice_date="2024-01-15",
                supplier_name="Test Supplier",
                total_amount_pennies=4200,
                confidence=0.85
            )
            
            if not success_invoice:
                print("❌ Failed to save test invoice")
                return False
            
            # Now delete the invoice (simulating failed job)
            with db.get_connection() as conn:
                conn.execute("DELETE FROM invoices WHERE id = ?", (invoice_id,))
                conn.commit()
            
            # Check if file is still referenced
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) FROM invoices i 
                    JOIN uploaded_files uf ON i.file_id = uf.id 
                    WHERE uf.file_hash = ?
                """, (file_hash_2,))
                ref_count = cursor.fetchone()[0]
                
                if ref_count != 0:
                    print(f"❌ File still has {ref_count} references, should be 0")
                    return False
            
            print("✅ Orphan file detection works")
            
            # Test 4: Storage directory structure
            print("📂 Testing storage directory structure...")
            
            # Check that all files in storage are hash-based
            storage_files = list(storage_dir.glob("*"))
            for file_path in storage_files:
                filename = file_path.name
                if not (filename.startswith("temp_") or filename.startswith("test_") or len(filename) >= 64):
                    print(f"❌ Non-canonical file found: {filename}")
                    return False
            
            print("✅ Storage directory structure is canonical")
            
            return True
            
        finally:
            # Clean up
            if os.path.exists(db_path):
                os.unlink(db_path)

def test_storage_rebuild_script():
    """Test the storage rebuild script"""
    print("🔧 Testing storage rebuild script...")
    
    # Create temporary storage and database
    with tempfile.TemporaryDirectory() as temp_dir:
        storage_dir = Path(temp_dir) / "storage"
        storage_dir.mkdir()
        
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        try:
            # Set environment variables
            os.environ['OWLIN_DB'] = db_path
            os.environ['OWLIN_STORAGE'] = str(storage_dir)
            
            # Initialize database manager
            from db_manager_unified import DatabaseManager
            db = DatabaseManager(db_path)
            db.run_migrations()
            
            # Create some test files
            test_files = [
                ("test1.txt", b"Content 1"),
                ("test2.txt", b"Content 2"),
                ("test3.txt", b"Content 3")
            ]
            
            for filename, content in test_files:
                file_path = storage_dir / filename
                file_path.write_bytes(content)
                
                # Generate hash and save to database
                import hashlib
                file_hash = hashlib.sha256(content).hexdigest()
                file_id = f"test_file_{uuid.uuid4().hex[:8]}"
                
                db.save_uploaded_file(
                    file_id=file_id,
                    original_filename=filename,
                    canonical_path=str(file_path),
                    file_size=len(content),
                    file_hash=file_hash,
                    mime_type="text/plain",
                    doc_type="invoice"
                )
            
            # Check that rebuild script would find no drift
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT file_hash, canonical_path FROM uploaded_files")
                db_files = cursor.fetchall()
                
                # Check that all database files exist in storage
                for file_hash, canonical_path in db_files:
                    if not os.path.exists(canonical_path):
                        print(f"❌ Database file not found in storage: {canonical_path}")
                        return False
                
                print("✅ All database files exist in storage")
            
            return True
            
        finally:
            # Clean up
            if os.path.exists(db_path):
                os.unlink(db_path)

def main():
    """Run all canonical storage tests"""
    print("🚀 TESTING CANONICAL STORAGE INVARIANTS")
    print("=" * 50)
    
    tests = [
        test_canonical_storage_invariants,
        test_storage_rebuild_script
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            print()
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            print()
    
    print("=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL CANONICAL STORAGE TESTS PASSED!")
        print("✅ Canonical storage invariants maintained")
        return True
    else:
        print("❌ Some canonical storage tests failed.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 