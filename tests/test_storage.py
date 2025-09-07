#!/usr/bin/env python3
"""
Comprehensive storage invariants tests
"""

import os
import sys
import tempfile
import shutil
import hashlib
from pathlib import Path
import json

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from db_manager_unified import DatabaseManager

def test_canonical_storage():
    """Test canonical storage naming"""
    print("🧪 Testing canonical storage...")
    
    # Create temporary storage directory
    with tempfile.TemporaryDirectory() as temp_storage:
        storage_path = Path(temp_storage)
        
        # Create temporary database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
            db_path = tmp_db.name
        
        try:
            # Initialize database
            db = DatabaseManager(db_path)
            db.run_migrations()
            
            # Create test file
            test_content = b"test file content"
            file_hash = hashlib.sha256(test_content).hexdigest()
            canonical_path = storage_path / f"{file_hash}.pdf"
            
            # Write file with canonical name
            with open(canonical_path, 'wb') as f:
                f.write(test_content)
            
            # Insert into database
            with db.get_connection() as conn:
                conn.execute("""
                    INSERT INTO uploaded_files (id, original_filename, canonical_path, file_size, file_hash, mime_type, doc_type, upload_timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, ("test_file_1", "original_name.pdf", str(canonical_path), len(test_content), file_hash, "application/pdf", "invoice"))
                
                conn.commit()
            
            # Verify canonical path exists
            assert canonical_path.exists(), f"Canonical file should exist: {canonical_path}"
            
            # Verify database record matches file
            with db.get_connection() as conn:
                record = conn.execute("""
                    SELECT canonical_path, file_hash FROM uploaded_files WHERE id = ?
                """, ("test_file_1",)).fetchone()
                
                assert record['canonical_path'] == str(canonical_path)
                assert record['file_hash'] == file_hash
            
            print("✅ Canonical storage tests passed")
            
        finally:
            # Cleanup
            try:
                os.unlink(db_path)
            except FileNotFoundError:
                pass  # File already deleted

def test_orphan_cleanup():
    """Test orphan file cleanup"""
    print("🧪 Testing orphan cleanup...")
    
    # Create temporary storage directory
    with tempfile.TemporaryDirectory() as temp_storage:
        storage_path = Path(temp_storage)
        
        # Create temporary database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
            db_path = tmp_db.name
        
        try:
            # Initialize database
            db = DatabaseManager(db_path)
            db.run_migrations()
            
            # Create test files
            test_content_1 = b"test file 1 content"
            test_content_2 = b"test file 2 content"
            test_content_3 = b"orphan file content"
            
            file_hash_1 = hashlib.sha256(test_content_1).hexdigest()
            file_hash_2 = hashlib.sha256(test_content_2).hexdigest()
            file_hash_3 = hashlib.sha256(test_content_3).hexdigest()
            
            canonical_path_1 = storage_path / f"{file_hash_1}.pdf"
            canonical_path_2 = storage_path / f"{file_hash_2}.pdf"
            orphan_path = storage_path / f"{file_hash_3}.pdf"
            
            # Write files
            with open(canonical_path_1, 'wb') as f:
                f.write(test_content_1)
            with open(canonical_path_2, 'wb') as f:
                f.write(test_content_2)
            with open(orphan_path, 'wb') as f:
                f.write(test_content_3)
            
            # Insert only first two files into database
            with db.get_connection() as conn:
                conn.execute("""
                    INSERT INTO uploaded_files (id, original_filename, canonical_path, file_size, file_hash, mime_type, doc_type, upload_timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, ("test_file_1", "original_name1.pdf", str(canonical_path_1), len(test_content_1), file_hash_1, "application/pdf", "invoice"))
                
                conn.execute("""
                    INSERT INTO uploaded_files (id, original_filename, canonical_path, file_size, file_hash, mime_type, doc_type, upload_timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, ("test_file_2", "original_name2.pdf", str(canonical_path_2), len(test_content_2), file_hash_2, "application/pdf", "invoice"))
                
                conn.commit()
            
            # Verify orphan file exists
            assert orphan_path.exists(), "Orphan file should exist before cleanup"
            
            # Simulate orphan cleanup
            with db.get_connection() as conn:
                # Get all canonical paths from database
                db_files = conn.execute("""
                    SELECT canonical_path FROM uploaded_files
                """).fetchall()
                db_paths = {row['canonical_path'] for row in db_files}
                
                # Find orphan files
                storage_files = list(storage_path.glob("*.pdf"))
                orphan_files = [f for f in storage_files if str(f) not in db_paths]
                
                # Clean up orphan files
                for orphan_file in orphan_files:
                    orphan_file.unlink()
                    
                    # Log cleanup in audit
                    conn.execute("""
                        INSERT INTO audit_log (timestamp, action, entity_type, entity_id, metadata_json)
                        VALUES (CURRENT_TIMESTAMP, 'orphan_cleanup', 'file', ?, ?)
                    """, (str(orphan_file), '{"reason": "orphan_file_cleanup"}'))
                
                conn.commit()
            
            # Verify orphan file was cleaned up
            assert not orphan_path.exists(), "Orphan file should be cleaned up"
            
            # Verify referenced files still exist
            assert canonical_path_1.exists(), "Referenced file 1 should still exist"
            assert canonical_path_2.exists(), "Referenced file 2 should still exist"
            
            # Verify audit log was created
            with db.get_connection() as conn:
                audit = conn.execute("""
                    SELECT action, entity_type, entity_id FROM audit_log 
                    WHERE action = 'orphan_cleanup' AND entity_id = ?
                """, (str(orphan_path),)).fetchone()
                assert audit is not None
                assert audit['action'] == 'orphan_cleanup'
            
            print("✅ Orphan cleanup tests passed")
            
        finally:
            # Cleanup
            try:
                os.unlink(db_path)
            except FileNotFoundError:
                pass  # File already deleted

def test_storage_drift_detection():
    """Test storage drift detection and correction"""
    print("🧪 Testing storage drift detection...")
    
    # Create temporary storage directory
    with tempfile.TemporaryDirectory() as temp_storage:
        storage_path = Path(temp_storage)
        
        # Create temporary database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
            db_path = tmp_db.name
        
        try:
            # Initialize database
            db = DatabaseManager(db_path)
            db.run_migrations()
            
            # Create test file
            test_content = b"test file content"
            file_hash = hashlib.sha256(test_content).hexdigest()
            canonical_path = storage_path / f"{file_hash}.pdf"
            
            # Write file with canonical name
            with open(canonical_path, 'wb') as f:
                f.write(test_content)
            
            # Insert into database with wrong path
            wrong_path = storage_path / "wrong_name.pdf"
            with db.get_connection() as conn:
                conn.execute("""
                    INSERT INTO uploaded_files (id, original_filename, canonical_path, file_size, file_hash, mime_type, doc_type, upload_timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, ("test_file_1", "original_name.pdf", str(wrong_path), len(test_content), file_hash, "application/pdf", "invoice"))
                
                conn.commit()
            
            # Simulate drift detection and correction
            with db.get_connection() as conn:
                # Get all uploaded files
                files = conn.execute("""
                    SELECT id, canonical_path, file_hash FROM uploaded_files
                """).fetchall()
                
                for file_record in files:
                    db_path = Path(file_record['canonical_path'])
                    file_hash = file_record['file_hash']
                    
                    # Check if file exists at recorded path
                    if not db_path.exists():
                        # Look for file by hash
                        expected_path = storage_path / f"{file_hash}.pdf"
                        if expected_path.exists():
                            # Correct the path
                            conn.execute("""
                                UPDATE uploaded_files 
                                SET canonical_path = ?, updated_at = CURRENT_TIMESTAMP
                                WHERE id = ?
                            """, (str(expected_path), file_record['id']))
                            
                            # Log the correction
                            conn.execute("""
                                INSERT INTO audit_log (timestamp, action, entity_type, entity_id, metadata_json)
                                VALUES (CURRENT_TIMESTAMP, 'drift_correction', 'file', ?, ?)
                            """, (file_record['id'], json.dumps({
                                'old_path': str(db_path),
                                'new_path': str(expected_path),
                                'reason': 'path_drift_correction'
                            })))
                
                conn.commit()
            
            # Verify path was corrected
            with db.get_connection() as conn:
                record = conn.execute("""
                    SELECT canonical_path FROM uploaded_files WHERE id = ?
                """, ("test_file_1",)).fetchone()
                
                assert record['canonical_path'] == str(canonical_path), f"Path should be corrected to {canonical_path}"
            
            # Verify audit log was created
            with db.get_connection() as conn:
                audit = conn.execute("""
                    SELECT action, entity_type, entity_id FROM audit_log 
                    WHERE action = 'drift_correction' AND entity_id = ?
                """, ("test_file_1",)).fetchone()
                assert audit is not None
                assert audit['action'] == 'drift_correction'
            
            print("✅ Storage drift detection tests passed")
            
        finally:
            # Cleanup
            try:
                os.unlink(db_path)
            except FileNotFoundError:
                pass  # File already deleted

if __name__ == "__main__":
    print("🚀 Running comprehensive storage invariants tests...")
    
    test_canonical_storage()
    test_orphan_cleanup()
    test_storage_drift_detection()
    
    print("🎉 All storage invariants tests passed!") 