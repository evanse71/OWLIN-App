"""
Test OCR confidence system: block/flag/pass tests
"""
import pytest
import tempfile
import sqlite3
from pathlib import Path
import sys
sys.path.insert(0, 'backend')

from ocr.confidence import page_confidence, line_confidence, calculate_invoice_confidence
from ocr.preprocess import preprocess_image
from services.ocr_writer import persist_page_confidence, persist_invoice_confidence

class TestOCRConfidence:
    """Test OCR confidence calculation and gating."""
    
    def test_page_confidence_calculation(self):
        """Test page confidence calculation from word confidence data."""
        # Test data: [(text, confidence)]
        words = [
            ("Invoice", 85.0),
            ("Number", 92.0),
            ("12345", 78.0),
            ("Supplier", 88.0),
            ("Ltd", 95.0)
        ]
        
        avg_conf, min_conf = page_confidence(words)
        
        assert avg_conf == pytest.approx(87.6, abs=0.1)
        assert min_conf == 78.0
    
    def test_empty_page_confidence(self):
        """Test confidence calculation with empty page."""
        words = []
        avg_conf, min_conf = page_confidence(words)
        
        assert avg_conf == 0.0
        assert min_conf == 0.0
    
    def test_line_confidence_weighting(self):
        """Test that longer words get more weight in line confidence."""
        line_words = [
            ("Short", 70.0),      # 5 chars
            ("MediumLength", 80.0), # 12 chars
            ("VeryLongWordHere", 90.0) # 16 chars
        ]
        
        conf = line_confidence(line_words)
        
        # Should be weighted toward longer words
        assert 80.0 < conf < 90.0
    
    def test_invoice_confidence_rollup(self):
        """Test invoice confidence calculation from page data."""
        pages_data = [
            {"avg_conf": 85.0, "min_conf": 75.0},
            {"avg_conf": 90.0, "min_conf": 80.0},
            {"avg_conf": 88.0, "min_conf": 70.0}
        ]
        
        invoice_avg, invoice_min = calculate_invoice_confidence(pages_data)
        
        assert invoice_avg == pytest.approx(87.67, abs=0.1)
        assert invoice_min == 70.0

class TestOCRPreprocessing:
    """Test OCR image preprocessing."""
    
    def test_preprocess_image_creates_binary(self):
        """Test that preprocessing creates a binary image."""
        # Create a simple test image
        from PIL import Image, ImageDraw
        
        img = Image.new('RGB', (100, 100), color='white')
        draw = ImageDraw.Draw(img)
        draw.text((10, 10), "Test", fill='black')
        
        # Preprocess
        processed = preprocess_image(img)
        
        # Should be binary (black and white)
        assert processed.mode in ['L', '1']
        
        # Should have some black pixels (text)
        pixels = list(processed.getdata())
        assert 0 in pixels  # Black pixels present

class TestOCRDatabase:
    """Test OCR confidence persistence."""
    
    def setup_method(self):
        """Set up test database."""
        self.test_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.test_db.name
        self.test_db.close()
        
        # Create test tables
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE invoice_pages (
                id TEXT PRIMARY KEY,
                invoice_id TEXT,
                page_no INTEGER,
                ocr_avg_conf_page REAL,
                ocr_min_conf_line REAL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE invoices (
                id TEXT PRIMARY KEY,
                supplier_name TEXT,
                ocr_avg_conf REAL,
                ocr_min_conf REAL
            )
        """)
        
        # Insert test data
        cursor.execute("""
            INSERT INTO invoices (id, supplier_name) VALUES (?, ?)
        """, ("test_inv_001", "Test Supplier"))
        
        cursor.execute("""
            INSERT INTO invoice_pages (id, invoice_id, page_no) VALUES (?, ?, ?)
        """, ("page_001", "test_inv_001", 1))
        
        conn.commit()
        conn.close()
    
    def teardown_method(self):
        """Clean up test database."""
        Path(self.db_path).unlink(missing_ok=True)
    
    def test_persist_page_confidence(self):
        """Test persisting page confidence scores."""
        # Mock the database connection
        import sys
        sys.path.insert(0, 'backend')
        import services.ocr_writer as ocr_writer
        ocr_writer.get_db_connection = lambda: sqlite3.connect(self.db_path)
        
        # Persist confidence
        persist_page_confidence("page_001", 85.5, 75.2)
        
        # Verify
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ocr_avg_conf_page, ocr_min_conf_line 
            FROM invoice_pages WHERE id = ?
        """, ("page_001",))
        
        result = cursor.fetchone()
        assert result[0] == 85.5
        assert result[1] == 75.2
        conn.close()
    
    def test_persist_invoice_confidence(self):
        """Test persisting invoice confidence scores."""
        # Mock the database connection
        import sys
        sys.path.insert(0, 'backend')
        import services.ocr_writer as ocr_writer
        ocr_writer.get_db_connection = lambda: sqlite3.connect(self.db_path)
        
        # Persist confidence
        persist_invoice_confidence("test_inv_001", 87.6, 70.0)
        
        # Verify
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ocr_avg_conf, ocr_min_conf 
            FROM invoices WHERE id = ?
        """, ("test_inv_001",))
        
        result = cursor.fetchone()
        assert result[0] == 87.6
        assert result[1] == 70.0
        conn.close()

class TestOCRConfidenceGating:
    """Test OCR confidence gating rules."""
    
    def test_blocking_low_confidence(self):
        """Test that pages with avg < 50 are blocked."""
        import sys
        sys.path.insert(0, 'backend')
        from ocr.pipeline import apply_confidence_gating
        
        # Low confidence
        decision = apply_confidence_gating(45.0)
        assert decision == "BLOCKED"
        
        # Very low confidence
        decision = apply_confidence_gating(10.0)
        assert decision == "BLOCKED"
    
    def test_warning_medium_confidence(self):
        """Test that pages with 50 ≤ avg < 70 get warning."""
        import sys
        sys.path.insert(0, 'backend')
        from ocr.pipeline import apply_confidence_gating
        
        # Boundary cases
        decision = apply_confidence_gating(50.0)
        assert decision == "WARN"
        
        decision = apply_confidence_gating(69.9)
        assert decision == "WARN"
        
        # Middle range
        decision = apply_confidence_gating(60.0)
        assert decision == "WARN"
    
    def test_passing_high_confidence(self):
        """Test that pages with avg ≥ 70 pass."""
        import sys
        sys.path.insert(0, 'backend')
        from ocr.pipeline import apply_confidence_gating
        
        # Boundary case
        decision = apply_confidence_gating(70.0)
        assert decision == "PASS"
        
        # High confidence
        decision = apply_confidence_gating(85.0)
        assert decision == "PASS"
        
        decision = apply_confidence_gating(95.0)
        assert decision == "PASS" 