"""
Comprehensive tests for addendum features

This module tests the document classification, enhanced pairing, and annotation detection
features implemented for the OWLIN addendum.
"""

import pytest
import sqlite3
import tempfile
import os
import json
from datetime import datetime, date
from unittest.mock import Mock, patch, MagicMock
import numpy as np

# Import the modules to test
from backend.services.document_classifier import DocumentClassifier, ClassificationResult
from backend.services.enhanced_pairing import EnhancedPairingService, PairingResult
from backend.extraction.parsers.invoice_parser import detect_annotations, _classify_annotation_shape


class TestDocumentClassifier:
    """Test the document type classifier"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.classifier = DocumentClassifier()
    
    def test_invoice_classification(self):
        """Test classification of invoice documents"""
        invoice_text = """
        INVOICE
        Invoice Number: INV-2024-001
        Invoice Date: 15/01/2024
        Supplier: Brakes Food Ltd
        
        Description    Quantity    Unit Price    Total
        Chicken Breast    10        5.50        55.00
        Beef Mince        5         8.00        40.00
        
        Subtotal: 95.00
        VAT (20%): 19.00
        Total Amount Due: 114.00
        
        Payment Terms: 30 days
        """
        
        result = self.classifier.classify_document(invoice_text)
        
        assert result.doc_type == 'invoice'
        assert result.confidence > 0.7
        assert 'invoice' in result.keywords_found
        assert 'amount due' in result.keywords_found
        assert 'vat' in result.keywords_found
    
    def test_delivery_note_classification(self):
        """Test classification of delivery note documents"""
        delivery_text = """
        DELIVERY NOTE
        Delivery Note Number: DN-2024-001
        Delivery Date: 15/01/2024
        Supplier: Brakes Food Ltd
        
        Description    Quantity Delivered
        Chicken Breast    10
        Beef Mince        5
        
        Delivered by: John Smith
        Signature: ________________
        """
        
        result = self.classifier.classify_document(delivery_text)
        
        assert result.doc_type == 'delivery_note'
        assert result.confidence > 0.6
        assert 'delivery note' in result.keywords_found
        assert 'delivered' in result.keywords_found
    
    def test_receipt_classification(self):
        """Test classification of receipt documents"""
        receipt_text = """
        RECEIPT
        Transaction ID: TXN-123456
        Date: 15/01/2024
        Store: Tesco Express
        
        Items:
        Bread        1.20
        Milk         0.80
        Total:       2.00
        
        Cash Tendered: 5.00
        Change Given: 3.00
        
        Thank you for your purchase!
        """
        
        result = self.classifier.classify_document(receipt_text)
        
        assert result.doc_type == 'receipt'
        assert result.confidence > 0.5
        assert 'receipt' in result.keywords_found
        assert 'thank you' in result.keywords_found
    
    def test_credit_note_classification(self):
        """Test classification of credit note documents"""
        credit_text = """
        CREDIT NOTE
        Credit Note Number: CN-2024-001
        Original Invoice: INV-2024-001
        Date: 20/01/2024
        
        Reason for Credit: Damaged goods returned
        
        Credit Amount: 25.00
        
        This credit note cancels the above invoice amount.
        """
        
        result = self.classifier.classify_document(credit_text)
        
        assert result.doc_type == 'credit_note'
        assert result.confidence > 0.6
        assert 'credit note' in result.keywords_found
        assert 'original invoice' in result.keywords_found
    
    def test_utility_bill_classification(self):
        """Test classification of utility bill documents"""
        utility_text = """
        ELECTRICITY BILL
        Account Number: 12345678
        Bill Date: 15/01/2024
        
        Previous Reading: 12345
        Current Reading: 12500
        Usage: 155 kWh
        
        Standing Charge: 15.00
        Unit Rate: 0.25 per kWh
        Total: 53.75
        """
        
        result = self.classifier.classify_document(utility_text)
        
        assert result.doc_type == 'utility_bill'
        assert result.confidence > 0.6
        assert 'electricity' in result.keywords_found
        assert 'account number' in result.keywords_found
    
    def test_purchase_order_classification(self):
        """Test classification of purchase order documents"""
        po_text = """
        PURCHASE ORDER
        PO Number: PO-2024-001
        Order Date: 15/01/2024
        
        Requested by: John Smith
        Authorized by: Jane Doe
        
        Items:
        Chicken Breast    10
        Beef Mince        5
        
        Delivery Address: 123 Main St, London
        Terms and Conditions: Net 30
        """
        
        result = self.classifier.classify_document(po_text)
        
        assert result.doc_type == 'purchase_order'
        assert result.confidence > 0.6
        assert 'purchase order' in result.keywords_found
        assert 'po number' in result.keywords_found
    
    def test_unknown_document_classification(self):
        """Test classification of unknown document types"""
        unknown_text = """
        Some random text that doesn't match any known document type.
        This could be a letter or some other document.
        """
        
        result = self.classifier.classify_document(unknown_text)
        
        # Should still classify as something, but with low confidence
        assert result.confidence < 0.5
        assert result.doc_type in ['invoice', 'delivery_note', 'receipt', 'credit_note', 'utility_bill', 'purchase_order']


class TestEnhancedPairing:
    """Test the enhanced pairing service"""
    
    def setup_method(self):
        """Set up test database and fixtures"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        # Create test database with required tables
        self.db = sqlite3.connect(self.temp_db.name)
        self._create_test_tables()
        self._insert_test_data()
        
        self.pairing_service = EnhancedPairingService(self.db)
    
    def teardown_method(self):
        """Clean up test database"""
        self.db.close()
        os.unlink(self.temp_db.name)
    
    def _create_test_tables(self):
        """Create test database tables"""
        cursor = self.db.cursor()
        
        # Create invoices table
        cursor.execute("""
            CREATE TABLE invoices (
                id TEXT PRIMARY KEY,
                supplier_name TEXT,
                invoice_date TEXT,
                invoice_number TEXT,
                total_amount_pennies INTEGER,
                status TEXT DEFAULT 'parsed'
            )
        """)
        
        # Create delivery_notes table
        cursor.execute("""
            CREATE TABLE delivery_notes (
                id TEXT PRIMARY KEY,
                supplier_name TEXT,
                delivery_date TEXT,
                delivery_note_number TEXT,
                total_items INTEGER,
                status TEXT DEFAULT 'parsed'
            )
        """)
        
        # Create doc_pairs table
        cursor.execute("""
            CREATE TABLE doc_pairs (
                id TEXT PRIMARY KEY,
                invoice_id TEXT,
                delivery_note_id TEXT,
                score REAL,
                pairing_method TEXT,
                supplier_match_score REAL,
                date_proximity_score REAL,
                line_item_similarity_score REAL,
                quantity_match_score REAL,
                price_match_score REAL,
                total_confidence REAL,
                status TEXT DEFAULT 'active',
                created_at TEXT
            )
        """)
        
        # Create pairing_rules table
        cursor.execute("""
            CREATE TABLE pairing_rules (
                id TEXT PRIMARY KEY,
                rule_name TEXT,
                rule_type TEXT,
                parameters TEXT,
                weight REAL,
                enabled BOOLEAN DEFAULT 1
            )
        """)
        
        # Insert default pairing rules
        cursor.execute("""
            INSERT INTO pairing_rules (id, rule_name, rule_type, parameters, weight) VALUES
            ('rule_001', 'Supplier Match', 'supplier_match', '{"threshold": 0.8, "fuzzy": true}', 0.4),
            ('rule_002', 'Date Window', 'date_window', '{"window_days": 30, "strict": false}', 0.3),
            ('rule_003', 'Line Item Similarity', 'line_item_similarity', '{"threshold": 0.7}', 0.2),
            ('rule_004', 'Quantity Match', 'quantity_match', '{"tolerance": 0.1}', 0.05),
            ('rule_005', 'Price Match', 'price_match', '{"tolerance": 0.05}', 0.05)
        """)
        
        self.db.commit()
    
    def _insert_test_data(self):
        """Insert test data"""
        cursor = self.db.cursor()
        
        # Insert test invoices
        cursor.execute("""
            INSERT INTO invoices (id, supplier_name, invoice_date, invoice_number, total_amount_pennies) VALUES
            ('inv_001', 'Brakes Food Ltd', '2024-01-15', 'INV-001', 11400),
            ('inv_002', 'Bidfood Ltd', '2024-01-16', 'INV-002', 8500),
            ('inv_003', 'Booker Wholesale', '2024-01-17', 'INV-003', 12000)
        """)
        
        # Insert test delivery notes
        cursor.execute("""
            INSERT INTO delivery_notes (id, supplier_name, delivery_date, delivery_note_number, total_items) VALUES
            ('dn_001', 'Brakes Food Ltd', '2024-01-15', 'DN-001', 15),
            ('dn_002', 'Bidfood Ltd', '2024-01-16', 'DN-002', 12),
            ('dn_003', 'Booker Wholesale', '2024-01-17', 'DN-003', 18),
            ('dn_004', 'Brakes Food', '2024-01-14', 'DN-004', 10)
        """)
        
        self.db.commit()
    
    def test_supplier_similarity_calculation(self):
        """Test supplier name similarity calculation"""
        # Exact match
        score1 = self.pairing_service._calculate_supplier_similarity("Brakes Food Ltd", "Brakes Food Ltd")
        assert score1 == 1.0
        
        # Similar match
        score2 = self.pairing_service._calculate_supplier_similarity("Brakes Food Ltd", "Brakes Food")
        assert score2 > 0.8
        
        # Different suppliers
        score3 = self.pairing_service._calculate_supplier_similarity("Brakes Food Ltd", "Tesco")
        assert score3 < 0.5
    
    def test_date_proximity_calculation(self):
        """Test date proximity calculation"""
        # Same date
        score1 = self.pairing_service._calculate_date_proximity("2024-01-15", "2024-01-15")
        assert score1 == 1.0
        
        # Close dates (within window)
        score2 = self.pairing_service._calculate_date_proximity("2024-01-15", "2024-01-16")
        assert score2 > 0.8
        
        # Far dates (outside window)
        score3 = self.pairing_service._calculate_date_proximity("2024-01-15", "2024-03-15")
        assert score3 < 0.3
    
    def test_auto_pairing(self):
        """Test automatic pairing functionality"""
        result = self.pairing_service.auto_pair()
        
        assert 'pairs_created' in result
        assert 'high_confidence_pairs' in result
        assert 'medium_confidence_pairs' in result
        assert result['pairs_created'] > 0
        
        # Check that pairs were actually created
        cursor = self.db.cursor()
        cursor.execute("SELECT COUNT(*) FROM doc_pairs")
        pair_count = cursor.fetchone()[0]
        assert pair_count > 0
    
    def test_pairing_candidate_finding(self):
        """Test finding pairing candidates"""
        candidates = self.pairing_service._find_candidate_delivery_notes(
            'inv_001', 'Brakes Food Ltd', '2024-01-15', 11400, 
            [('dn_001', 'Brakes Food Ltd', '2024-01-15', 'DN-001', 15)]
        )
        
        assert len(candidates) > 0
        assert candidates[0].invoice_id == 'inv_001'
        assert candidates[0].delivery_note_id == 'dn_001'
        assert candidates[0].total_score > 0.5
    
    def test_pairing_confidence_calculation(self):
        """Test pairing confidence calculation"""
        confidence = self.pairing_service._calculate_confidence(
            supplier_score=0.9,
            date_score=0.8,
            line_item_score=0.7,
            quantity_score=0.6,
            price_score=0.5
        )
        
        assert 0.0 <= confidence <= 1.0
        assert confidence > 0.7  # Should be high with good scores


class TestAnnotationDetection:
    """Test the annotation detection functionality"""
    
    def test_annotation_shape_classification(self):
        """Test annotation shape classification"""
        # Mock contour for testing
        mock_contour = Mock()
        
        # Test circular annotation
        kind, confidence = _classify_annotation_shape(mock_contour, 1.0, 0.8, 1000)
        assert kind in ['CIRCLE', 'MARK']
        assert confidence > 0.0
        
        # Test line-like annotation
        kind, confidence = _classify_annotation_shape(mock_contour, 4.0, 0.3, 500)
        assert kind in ['CROSS', 'MARK']
        assert confidence > 0.0
        
        # Test tick-like annotation
        kind, confidence = _classify_annotation_shape(mock_contour, 1.5, 0.7, 800)
        assert kind in ['TICK', 'MARK']
        assert confidence > 0.0
    
    @patch('cv2.imread')
    @patch('cv2.cvtColor')
    @patch('cv2.inRange')
    @patch('cv2.findContours')
    def test_annotation_detection_with_mocks(self, mock_find_contours, mock_in_range, mock_cvt_color, mock_imread):
        """Test annotation detection with mocked OpenCV functions"""
        # Mock image data
        mock_img = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_imread.return_value = mock_img
        mock_cvt_color.return_value = mock_img
        
        # Mock color detection
        mock_mask = np.zeros((100, 100), dtype=np.uint8)
        mock_in_range.return_value = mock_mask
        
        # Mock contour detection
        mock_contour = np.array([[[10, 10]], [[20, 10]], [[20, 20]], [[10, 20]]])
        mock_find_contours.return_value = ([mock_contour], None)
        
        # Test annotation detection
        annotations = detect_annotations("test_image.png")
        
        # Should return empty list since no actual annotations detected
        assert isinstance(annotations, list)
    
    def test_annotation_detection_error_handling(self):
        """Test annotation detection error handling"""
        # Test with non-existent image
        annotations = detect_annotations("non_existent_image.png")
        assert annotations == []
        
        # Test with invalid path
        annotations = detect_annotations("")
        assert annotations == []


class TestIntegration:
    """Integration tests for the complete addendum features"""
    
    def setup_method(self):
        """Set up integration test environment"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        self.db = sqlite3.connect(self.temp_db.name)
        self._create_integration_tables()
    
    def teardown_method(self):
        """Clean up integration test environment"""
        self.db.close()
        os.unlink(self.temp_db.name)
    
    def _create_integration_tables(self):
        """Create tables for integration testing"""
        cursor = self.db.cursor()
        
        # Create all required tables
        cursor.execute("""
            CREATE TABLE uploaded_files (
                id TEXT PRIMARY KEY,
                original_filename TEXT,
                doc_type TEXT,
                doc_type_confidence REAL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE invoices (
                id TEXT PRIMARY KEY,
                supplier_name TEXT,
                invoice_date TEXT,
                invoice_number TEXT,
                total_amount_pennies INTEGER,
                status TEXT DEFAULT 'parsed'
            )
        """)
        
        cursor.execute("""
            CREATE TABLE delivery_notes (
                id TEXT PRIMARY KEY,
                supplier_name TEXT,
                delivery_date TEXT,
                delivery_note_number TEXT,
                total_items INTEGER,
                status TEXT DEFAULT 'parsed'
            )
        """)
        
        cursor.execute("""
            CREATE TABLE doc_pairs (
                id TEXT PRIMARY KEY,
                invoice_id TEXT,
                delivery_note_id TEXT,
                score REAL,
                pairing_method TEXT,
                supplier_match_score REAL,
                date_proximity_score REAL,
                line_item_similarity_score REAL,
                quantity_match_score REAL,
                price_match_score REAL,
                total_confidence REAL,
                status TEXT DEFAULT 'active',
                created_at TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE annotations (
                id TEXT PRIMARY KEY,
                invoice_id TEXT,
                line_item_id INTEGER,
                kind TEXT,
                text TEXT,
                x REAL,
                y REAL,
                w REAL,
                h REAL,
                confidence REAL,
                color TEXT,
                page_number INTEGER,
                created_at TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE document_classification (
                id TEXT PRIMARY KEY,
                file_id TEXT,
                doc_type TEXT,
                confidence REAL,
                classification_method TEXT,
                keywords_found TEXT,
                layout_features TEXT,
                text_patterns TEXT,
                created_at TEXT
            )
        """)
        
        self.db.commit()
    
    def test_end_to_end_document_processing(self):
        """Test complete document processing pipeline"""
        # Test document classification
        classifier = DocumentClassifier()
        result = classifier.classify_document("INVOICE\nInvoice Number: TEST-001\nAmount Due: £100.00")
        
        assert result.doc_type == 'invoice'
        assert result.confidence > 0.5
        
        # Test pairing
        cursor = self.db.cursor()
        cursor.execute("""
            INSERT INTO invoices (id, supplier_name, invoice_date, invoice_number, total_amount_pennies) VALUES
            ('test_inv', 'Test Supplier', '2024-01-15', 'TEST-001', 10000)
        """)
        
        cursor.execute("""
            INSERT INTO delivery_notes (id, supplier_name, delivery_date, delivery_note_number, total_items) VALUES
            ('test_dn', 'Test Supplier', '2024-01-15', 'TEST-DN-001', 10)
        """)
        
        self.db.commit()
        
        # Test pairing service
        pairing_service = EnhancedPairingService(self.db)
        pairing_result = pairing_service.auto_pair()
        
        assert pairing_result['pairs_created'] >= 0
        
        # Test annotation detection (with mocked image)
        with patch('cv2.imread', return_value=np.zeros((100, 100, 3), dtype=np.uint8)):
            annotations = detect_annotations("test.png")
            assert isinstance(annotations, list)
    
    def test_database_schema_compatibility(self):
        """Test that all new tables and fields are properly created"""
        cursor = self.db.cursor()
        
        # Test that all tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        required_tables = [
            'uploaded_files', 'invoices', 'delivery_notes', 'doc_pairs',
            'annotations', 'document_classification'
        ]
        
        for table in required_tables:
            assert table in tables, f"Table {table} not found"
        
        # Test that key columns exist
        cursor.execute("PRAGMA table_info(doc_pairs)")
        doc_pairs_columns = [row[1] for row in cursor.fetchall()]
        
        required_columns = [
            'id', 'invoice_id', 'delivery_note_id', 'score', 'pairing_method',
            'supplier_match_score', 'date_proximity_score', 'total_confidence'
        ]
        
        for column in required_columns:
            assert column in doc_pairs_columns, f"Column {column} not found in doc_pairs"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
