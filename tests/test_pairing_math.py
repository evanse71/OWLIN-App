"""
Tests for line-level pairing mathematics and many-to-one aggregation
"""
import pytest
import tempfile
import sqlite3
from pathlib import Path
import sys
sys.path.insert(0, 'backend')

from backend.services.pairing_service import PairingService
from backend.db_manager_unified import get_db_manager

class TestPairingMath:
    
    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test.db"
        self.db = get_db_manager(str(self.db_path))
        self.db.run_migrations()
        self.pairing_service = PairingService()
    
    def test_fixture_01_partial_delivery(self):
        """Fixture 1: Invoice 24×275ml, DN 12×275ml → 50% match"""
        conn = self.db.get_connection()
        
        # Create invoice with 24×275ml line
        invoice_id = self._create_test_invoice(conn, "INV001")
        self._add_invoice_line(conn, invoice_id, "BEER001", "24×275ml Premium Lager", 24.0, 2.0, 48.0)
        
        # Create DN with 12×275ml line  
        dn_id = self._create_test_dn(conn, "DN001")
        self._add_dn_line(conn, dn_id, "BEER001", "12×275ml Premium Lager", 12.0, 2.0, 24.0)
        
        # Run pairing
        result = self.pairing_service.calculate_line_item_score(invoice_id, dn_id)
        
        # Should detect 50% match
        assert result['qty_match_pct'] >= 45.0  # Allow some tolerance
        assert result['qty_match_pct'] <= 55.0
        assert 'PARTIAL_DELIVERY' in result['reasons']
    
    def test_fixture_02_over_supply(self):
        """Fixture 2: Invoice 12×275ml, DN 24×275ml → over-supply"""
        conn = self.db.get_connection()
        
        invoice_id = self._create_test_invoice(conn, "INV002")
        self._add_invoice_line(conn, invoice_id, "BEER002", "12×275ml Lager", 12.0, 2.0, 24.0)
        
        dn_id = self._create_test_dn(conn, "DN002")
        self._add_dn_line(conn, dn_id, "BEER002", "24×275ml Lager", 24.0, 2.0, 48.0)
        
        result = self.pairing_service.calculate_line_item_score(invoice_id, dn_id)
        
        assert 'OVER_SUPPLIED' in result['reasons']
        assert result['qty_match_pct'] > 100.0  # Over-supply
    
    def test_fixture_03_exact_match(self):
        """Fixture 3: Exact quantity match → 100%"""
        conn = self.db.get_connection()
        
        invoice_id = self._create_test_invoice(conn, "INV003")
        self._add_invoice_line(conn, invoice_id, "WINE001", "6×75cl Red Wine", 6.0, 15.0, 90.0)
        
        dn_id = self._create_test_dn(conn, "DN003")
        self._add_dn_line(conn, dn_id, "WINE001", "6×75cl Red Wine", 6.0, 15.0, 90.0)
        
        result = self.pairing_service.calculate_line_item_score(invoice_id, dn_id)
        
        assert result['qty_match_pct'] >= 95.0  # Near perfect match
        assert 'EXACT_MATCH' in result.get('reasons', [])
    
    def test_fixture_04_sku_mismatch(self):
        """Fixture 4: Different SKUs → no match"""
        conn = self.db.get_connection()
        
        invoice_id = self._create_test_invoice(conn, "INV004")
        self._add_invoice_line(conn, invoice_id, "BEER001", "24×275ml Lager", 24.0, 2.0, 48.0)
        
        dn_id = self._create_test_dn(conn, "DN004")
        self._add_dn_line(conn, dn_id, "WINE001", "6×75cl Wine", 6.0, 15.0, 90.0)
        
        result = self.pairing_service.calculate_line_item_score(invoice_id, dn_id)
        
        assert result['qty_match_pct'] == 0.0
        assert 'SKU_MISMATCH' in result['reasons']
    
    def test_fixture_05_uom_mismatch(self):
        """Fixture 5: Same SKU, different UOM → flag mismatch"""
        conn = self.db.get_connection()
        
        invoice_id = self._create_test_invoice(conn, "INV005")
        self._add_invoice_line(conn, invoice_id, "BEER001", "24×275ml", 24.0, 2.0, 48.0)
        
        dn_id = self._create_test_dn(conn, "DN005")
        self._add_dn_line(conn, dn_id, "BEER001", "12×275ml", 12.0, 2.0, 24.0)  # Different pack size
        
        result = self.pairing_service.calculate_line_item_score(invoice_id, dn_id)
        
        assert 'UOM_MISMATCH' in result['reasons']
    
    def test_fixture_06_many_to_one_aggregation(self):
        """Fixture 6: Multiple DN lines → one invoice line"""
        conn = self.db.get_connection()
        
        invoice_id = self._create_test_invoice(conn, "INV006")
        self._add_invoice_line(conn, invoice_id, "BEER001", "24×275ml", 24.0, 2.0, 48.0)
        
        dn_id = self._create_test_dn(conn, "DN006")
        # Two DN lines that sum to invoice line
        self._add_dn_line(conn, dn_id, "BEER001", "12×275ml", 12.0, 2.0, 24.0)
        self._add_dn_line(conn, dn_id, "BEER001", "12×275ml", 12.0, 2.0, 24.0)
        
        result = self.pairing_service.calculate_line_item_score(invoice_id, dn_id)
        
        assert result['qty_match_pct'] >= 95.0
        assert 'AGGREGATED_MATCH' in result.get('reasons', [])
    
    def test_fixture_07_canonical_quantity_compare(self):
        """Fixture 7: Compare using canonical quantities (ml/l/g)"""
        conn = self.db.get_connection()
        
        invoice_id = self._create_test_invoice(conn, "INV007")
        # Add canonical quantities to line
        invoice_line_id = self._add_invoice_line(conn, invoice_id, "BEER001", "24×275ml", 24.0, 2.0, 48.0)
        conn.execute("""
            UPDATE invoice_items 
            SET canonical_quantities = ?
            WHERE id = ?
        """, ('{"quantity_each": 24.0, "quantity_ml": 6600.0, "quantity_l": 6.6}', invoice_line_id))
        
        dn_id = self._create_test_dn(conn, "DN007")
        dn_line_id = self._add_dn_line(conn, dn_id, "BEER001", "24×275ml", 24.0, 2.0, 48.0)
        conn.execute("""
            UPDATE delivery_note_items 
            SET canonical_quantities = ?
            WHERE id = ?
        """, ('{"quantity_each": 24.0, "quantity_ml": 6600.0, "quantity_l": 6.6}', dn_line_id))
        
        result = self.pairing_service.calculate_line_item_score(invoice_id, dn_id)
        
        assert result['qty_match_pct'] >= 95.0
        assert 'CANONICAL_MATCH' in result.get('reasons', [])
    
    def test_fixture_08_manual_override(self):
        """Fixture 8: Manual pairing override"""
        conn = self.db.get_connection()
        
        invoice_id = self._create_test_invoice(conn, "INV008")
        dn_id = self._create_test_dn(conn, "DN008")
        
        # Manual pair
        result = self.pairing_service.manual_pair(invoice_id, dn_id)
        
        assert result['ok'] == True
        assert 'link_id' in result
        
        # Verify link created
        cur = conn.cursor()
        cur.execute("""
            SELECT status FROM match_links 
            WHERE invoice_id = ? AND dn_id = ?
        """, (invoice_id, dn_id))
        link = cur.fetchone()
        assert link[0] == 'confirmed'
    
    def test_fixture_09_multi_dn_scenario(self):
        """Fixture 9: One invoice, multiple DN candidates"""
        conn = self.db.get_connection()
        
        invoice_id = self._create_test_invoice(conn, "INV009")
        self._add_invoice_line(conn, invoice_id, "BEER001", "24×275ml", 24.0, 2.0, 48.0)
        
        # Create multiple DNs
        dn1_id = self._create_test_dn(conn, "DN009A")
        self._add_dn_line(conn, dn1_id, "BEER001", "12×275ml", 12.0, 2.0, 24.0)  # Partial
        
        dn2_id = self._create_test_dn(conn, "DN009B")
        self._add_dn_line(conn, dn2_id, "BEER001", "24×275ml", 24.0, 2.0, 48.0)  # Exact
        
        # Score both
        result1 = self.pairing_service.calculate_line_item_score(invoice_id, dn1_id)
        result2 = self.pairing_service.calculate_line_item_score(invoice_id, dn2_id)
        
        # Exact match should score higher
        assert result2['qty_match_pct'] > result1['qty_match_pct']
    
    def test_fixture_10_precision_recall_metrics(self):
        """Fixture 10: Calculate precision/recall for pairing quality"""
        # This would test the overall pairing system performance
        # Precision ≥0.97, Recall ≥0.94 as per requirements
        
        # Create test dataset with known ground truth
        test_pairs = [
            ("INV_MATCH_01", "DN_MATCH_01", True),   # Should match
            ("INV_MATCH_02", "DN_MATCH_02", True),   # Should match
            ("INV_NO_MATCH_01", "DN_DIFF_01", False), # Should not match
        ]
        
        conn = self.db.get_connection()
        
        correct_predictions = 0
        total_predictions = 0
        
        for inv_id, dn_id, should_match in test_pairs:
            # Create test documents
            self._create_test_invoice(conn, inv_id)
            self._create_test_dn(conn, dn_id)
            
            # Add matching or non-matching lines
            if should_match:
                self._add_invoice_line(conn, inv_id, "COMMON_SKU", "Test Item", 10.0, 5.0, 50.0)
                self._add_dn_line(conn, dn_id, "COMMON_SKU", "Test Item", 10.0, 5.0, 50.0)
            else:
                self._add_invoice_line(conn, inv_id, "SKU_A", "Item A", 10.0, 5.0, 50.0)
                self._add_dn_line(conn, dn_id, "SKU_B", "Item B", 15.0, 3.0, 45.0)
            
            # Test pairing
            result = self.pairing_service.calculate_line_item_score(inv_id, dn_id)
            predicted_match = result['qty_match_pct'] > 80.0
            
            if predicted_match == should_match:
                correct_predictions += 1
            total_predictions += 1
        
        # Calculate accuracy (simplified precision/recall for this test)
        accuracy = correct_predictions / total_predictions
        assert accuracy >= 0.90  # Should be high for simple test cases
    
    def _create_test_invoice(self, conn: sqlite3.Connection, invoice_id: str) -> str:
        """Create test invoice"""
        cur = conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO invoices 
            (id, supplier_name, invoice_no, date_iso, status)
            VALUES (?, 'Test Supplier', ?, '2024-01-01', 'pending')
        """, (invoice_id, invoice_id))
        conn.commit()
        return invoice_id
    
    def _create_test_dn(self, conn: sqlite3.Connection, dn_id: str) -> str:
        """Create test delivery note"""
        cur = conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO delivery_notes 
            (id, supplier_name, date_iso, status)
            VALUES (?, 'Test Supplier', '2024-01-01', 'pending')
        """, (dn_id,))
        conn.commit()
        return dn_id
    
    def _add_invoice_line(self, conn: sqlite3.Connection, invoice_id: str, 
                         sku: str, desc: str, qty: float, price: float, total: float) -> str:
        """Add line to invoice"""
        line_id = f"ili_{invoice_id}_{sku}"
        cur = conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO invoice_items 
            (id, invoice_id, sku, description, quantity, unit_price, line_total)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (line_id, invoice_id, sku, desc, qty, price, total))
        conn.commit()
        return line_id
    
    def _add_dn_line(self, conn: sqlite3.Connection, dn_id: str,
                    sku: str, desc: str, qty: float, price: float, total: float) -> str:
        """Add line to delivery note"""
        line_id = f"dnli_{dn_id}_{sku}"
        cur = conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO delivery_note_items 
            (id, dn_id, sku, description, quantity, unit_price, line_total)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (line_id, dn_id, sku, desc, qty, price, total))
        conn.commit()
        return line_id

if __name__ == "__main__":
    pytest.main([__file__]) 