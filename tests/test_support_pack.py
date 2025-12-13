"""
Tests for support pack generation and quarantine system
"""
import pytest
import tempfile
import sqlite3
import json
import zipfile
from pathlib import Path
import sys
sys.path.insert(0, 'backend')

from backend.services.support_pack import SupportPackService, QuarantineService
from backend.db_manager_unified import get_db_manager

class TestSupportPack:
    
    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test.db"
        self.db = get_db_manager(str(self.db_path))
        self.db.run_migrations()
        self.service = SupportPackService()
    
    def test_support_pack_generation(self):
        """Test complete support pack generation"""
        conn = self.db.get_connection()
        
        # Create test invoice
        invoice_id = "test_invoice_001"
        self._create_test_invoice(conn, invoice_id)
        
        # Generate support pack
        zip_path = self.service.generate_support_pack(invoice_id)
        
        # Verify zip file created
        assert Path(zip_path).exists()
        assert Path(zip_path).suffix == '.zip'
        
        # Verify zip contents
        with zipfile.ZipFile(zip_path, 'r') as zipf:
            files = zipf.namelist()
            
            # Should contain expected files
            assert "invoice_metadata.json" in files
            assert any(f.startswith("ocr_results/") for f in files)
            
            # Verify metadata content
            with zipf.open("invoice_metadata.json") as f:
                metadata = json.load(f)
                assert metadata['invoice_id'] == invoice_id
                assert 'pack_generated_at' in metadata
    
    def test_quarantine_asset(self):
        """Test asset quarantine functionality"""
        conn = self.db.get_connection()
        quarantine_service = QuarantineService()
        
        # Create test asset
        asset_id = "test_asset_001"
        self._create_test_asset(conn, asset_id)
        
        # Quarantine asset
        reason = "unsupported_mime"
        details = {"mime_type": "application/unknown", "size_mb": 45}
        quarantine_service.quarantine_asset(asset_id, reason, details)
        
        # Verify quarantine
        quarantined = quarantine_service.list_quarantined_assets()
        assert len(quarantined) == 1
        assert quarantined[0]['asset_id'] == asset_id
        assert quarantined[0]['reason'] == reason
        assert quarantined[0]['details'] == details
    
    def test_promote_quarantined_asset(self):
        """Test promoting asset from quarantine"""
        conn = self.db.get_connection()
        quarantine_service = QuarantineService()
        
        # Create and quarantine asset
        asset_id = "test_asset_002"
        self._create_test_asset(conn, asset_id)
        quarantine_service.quarantine_asset(asset_id, "test_reason")
        
        # Verify quarantined
        quarantined = quarantine_service.list_quarantined_assets()
        assert len(quarantined) == 1
        
        # Promote asset
        success = quarantine_service.promote_asset(asset_id)
        assert success == True
        
        # Verify no longer quarantined
        quarantined_after = quarantine_service.list_quarantined_assets()
        assert len(quarantined_after) == 0
    
    def test_support_pack_with_minimal_data(self):
        """Test support pack generation with minimal invoice data"""
        conn = self.db.get_connection()
        
        # Create minimal invoice
        invoice_id = "minimal_invoice"
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO invoices (id, supplier_name, invoice_no, date_iso)
            VALUES (?, 'Test Supplier', 'MIN001', '2024-01-01')
        """, (invoice_id,))
        conn.commit()
        
        # Generate pack (should not fail with minimal data)
        zip_path = self.service.generate_support_pack(invoice_id)
        
        assert Path(zip_path).exists()
        
        # Verify contains at least metadata
        with zipfile.ZipFile(zip_path, 'r') as zipf:
            assert "invoice_metadata.json" in zipf.namelist()
    
    def _create_test_invoice(self, conn: sqlite3.Connection, invoice_id: str):
        """Create comprehensive test invoice"""
        cur = conn.cursor()
        
        # Create invoice
        cur.execute("""
            INSERT INTO invoices 
            (id, supplier_name, invoice_no, date_iso, currency, total_inc, ocr_avg_conf, ocr_min_conf)
            VALUES (?, 'Test Supplier', 'TEST001', '2024-01-01', 'GBP', 100.0, 85.5, 75.2)
        """, (invoice_id,))
        
        # Create invoice page
        cur.execute("""
            INSERT INTO invoice_pages 
            (invoice_id, page_number, ocr_text, ocr_avg_conf_page, ocr_min_conf_line)
            VALUES (?, 1, 'Test OCR Text', 85.5, 75.2)
        """, (invoice_id,))
        
        # Create invoice line
        cur.execute("""
            INSERT INTO invoice_items 
            (id, invoice_id, sku, description, quantity, unit_price, line_total, line_verdict)
            VALUES (?, ?, 'TEST_SKU', 'Test Item', 10.0, 5.0, 50.0, 'OK_ON_CONTRACT')
        """, (f"ili_{invoice_id}_001", invoice_id))
        
        conn.commit()
    
    def _create_test_asset(self, conn: sqlite3.Connection, asset_id: str):
        """Create test asset"""
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO ingest_assets 
            (id, batch_id, path, mime, checksum_sha256)
            VALUES (?, 'test_batch', '/tmp/test.png', 'image/png', 'test_checksum')
        """, (asset_id,))
        conn.commit()

if __name__ == "__main__":
    pytest.main([__file__]) 