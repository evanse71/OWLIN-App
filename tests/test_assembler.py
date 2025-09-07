"""
Tests for document assembly system
"""
import pytest
import sqlite3
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch
import sys
sys.path.insert(0, 'backend')

from backend.services.assemble_service import DocumentAssembler
from backend.db_manager_unified import get_db_manager

class TestDocumentAssembler:
    
    def setup_method(self):
        """Setup test database"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test.db"
        self.db = get_db_manager(str(self.db_path))
        self.db.run_migrations()
        self.assembler = DocumentAssembler()
        
    def teardown_method(self):
        """Cleanup"""
        shutil.rmtree(self.temp_dir)
    
    def test_three_png_reassembled_into_one_invoice(self):
        """Test that three separate PNGs are assembled into one invoice"""
        conn = self.db.get_connection()
        
        # Create batch
        batch_id = "batch_test_001"
        conn.execute("""
            INSERT INTO ingest_batches (id, uploader, source_hint)
            VALUES (?, 'test', 'three_png_test')
        """, (batch_id,))
        
        # Create three PNG assets with same header fingerprint
        assets = [
            {
                'id': 'asset_001',
                'path': f'{self.temp_dir}/invoice_p1.png',
                'mime': 'image/png',
                'header_id': 'header_abc123',
                'exif_ts': '2024-01-01T10:00:00Z',
                'checksum_sha256': 'sha_001'
            },
            {
                'id': 'asset_002', 
                'path': f'{self.temp_dir}/invoice_p2.png',
                'mime': 'image/png',
                'header_id': 'header_abc123',  # Same header
                'exif_ts': '2024-01-01T10:00:30Z',  # 30s later
                'checksum_sha256': 'sha_002'
            },
            {
                'id': 'asset_003',
                'path': f'{self.temp_dir}/invoice_p3.png', 
                'mime': 'image/png',
                'header_id': 'header_abc123',  # Same header
                'exif_ts': '2024-01-01T10:00:45Z',  # 45s later
                'checksum_sha256': 'sha_003'
            }
        ]
        
        # Insert assets
        for asset in assets:
            conn.execute("""
                INSERT INTO ingest_assets 
                (id, batch_id, path, mime, header_id, exif_ts, checksum_sha256)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (asset['id'], batch_id, asset['path'], asset['mime'], 
                  asset['header_id'], asset['exif_ts'], asset['checksum_sha256']))
        
        # Mock header fingerprinting to return consistent IDs
        with patch.object(self.assembler.fingerprinter, 'compute_header_id') as mock_fp:
            mock_fp.return_value = 'header_abc123'
            
            # Run assembly
            document_ids = self.assembler.assemble_batch(batch_id)
        
        # Verify: one document created with 3 pages
        assert len(document_ids) == 1
        
        doc_id = document_ids[0]
        
        # Check document record
        cur = conn.cursor()
        cur.execute("SELECT kind, page_count FROM documents WHERE id = ?", (doc_id,))
        doc_info = cur.fetchone()
        assert doc_info[0] == 'invoice'
        assert doc_info[1] == 3
        
        # Check page order
        cur.execute("""
            SELECT asset_id, page_order 
            FROM document_pages 
            WHERE document_id = ? 
            ORDER BY page_order
        """, (doc_id,))
        pages = cur.fetchall()
        assert len(pages) == 3
        assert pages[0][0] == 'asset_001'  # First page
        assert pages[1][0] == 'asset_002'  # Second page  
        assert pages[2][0] == 'asset_003'  # Third page
    
    def test_mixed_pdf_split_into_2inv_1dn(self):
        """Test that mixed PDF splits into separate documents"""
        conn = self.db.get_connection()
        
        # Create batch
        batch_id = "batch_mixed_001"
        conn.execute("""
            INSERT INTO ingest_batches (id, uploader, source_hint)
            VALUES (?, 'test', 'mixed_pdf_test')
        """, (batch_id,))
        
        # Create assets representing different document types
        assets = [
            {
                'id': 'page_001',
                'path': f'{self.temp_dir}/mixed_p1.png',
                'header_id': 'header_inv1',  # Invoice 1
                'exif_ts': '2024-01-01T10:00:00Z'
            },
            {
                'id': 'page_002',
                'path': f'{self.temp_dir}/mixed_p2.png', 
                'header_id': 'header_inv1',  # Invoice 1 page 2
                'exif_ts': '2024-01-01T10:00:01Z'
            },
            {
                'id': 'page_003',
                'path': f'{self.temp_dir}/mixed_p3.png',
                'header_id': 'header_dn1',   # Delivery note
                'exif_ts': '2024-01-01T10:00:02Z'
            },
            {
                'id': 'page_004',
                'path': f'{self.temp_dir}/mixed_p4.png',
                'header_id': 'header_inv2',  # Invoice 2
                'exif_ts': '2024-01-01T10:00:03Z'
            }
        ]
        
        # Insert assets
        for asset in assets:
            conn.execute("""
                INSERT INTO ingest_assets 
                (id, batch_id, path, mime, header_id, exif_ts, checksum_sha256)
                VALUES (?, ?, ?, 'image/png', ?, ?, ?)
            """, (asset['id'], batch_id, asset['path'], 
                  asset['header_id'], asset['exif_ts'], f"sha_{asset['id']}"))
        
        # Mock header comparison
        def mock_compare(h1, h2):
            return 1.0 if h1 == h2 else 0.2
            
        with patch.object(self.assembler.fingerprinter, 'compare_headers', side_effect=mock_compare):
            document_ids = self.assembler.assemble_batch(batch_id)
        
        # Verify: 3 documents created (2 invoices + 1 DN)
        assert len(document_ids) == 3
        
        # Check document types and page counts
        cur = conn.cursor()
        cur.execute("""
            SELECT id, kind, page_count 
            FROM documents 
            WHERE batch_id = ? 
            ORDER BY id
        """, (batch_id,))
        docs = cur.fetchall()
        
        # Should have documents with correct page counts
        page_counts = [doc[2] for doc in docs]
        assert 2 in page_counts  # Invoice 1 (2 pages)
        assert 1 in page_counts  # Delivery note (1 page) 
        assert 1 in page_counts  # Invoice 2 (1 page)
    
    def test_assembly_time_window_enforced(self):
        """Test that assets outside 60s window are split"""
        conn = self.db.get_connection()
        
        batch_id = "batch_time_001"
        conn.execute("""
            INSERT INTO ingest_batches (id) VALUES (?)
        """, (batch_id,))
        
        # Assets with same header but >60s apart
        assets = [
            {
                'id': 'early_001',
                'header_id': 'header_same',
                'exif_ts': '2024-01-01T10:00:00Z'
            },
            {
                'id': 'late_001',
                'header_id': 'header_same', 
                'exif_ts': '2024-01-01T10:02:00Z'  # 2 minutes later
            }
        ]
        
        for asset in assets:
            conn.execute("""
                INSERT INTO ingest_assets 
                (id, batch_id, path, mime, header_id, exif_ts, checksum_sha256)
                VALUES (?, ?, ?, 'image/png', ?, ?, ?)
            """, (asset['id'], batch_id, f"/tmp/{asset['id']}.png",
                  asset['header_id'], asset['exif_ts'], f"sha_{asset['id']}"))
        
        with patch.object(self.assembler.fingerprinter, 'compare_headers', return_value=1.0):
            document_ids = self.assembler.assemble_batch(batch_id)
        
        # Should create 2 separate documents due to time window
        assert len(document_ids) == 2

if __name__ == "__main__":
    pytest.main([__file__]) 