#!/usr/bin/env python3
"""
VAT Summary Zone Extraction Tests

Tests for VAT summary zone extraction and template management
"""

import unittest
import sys
import os
import tempfile
import shutil

# Add the parent directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from ocr.templates import TemplateManager, SupplierTemplate
from ocr.fields import extract_vat_summary

class TestVATZoneExtraction(unittest.TestCase):
    """Test VAT summary zone extraction functionality"""
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary database for testing
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_owlin.db")
        
        # Initialize database with schema
        self._init_test_db()
        
        self.template_manager = TemplateManager(self.db_path)
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir)
    
    def _init_test_db(self):
        """Initialize test database with schema"""
        import sqlite3
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create supplier_templates table with VAT summary zones
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS supplier_templates (
                supplier_key TEXT PRIMARY KEY,
                header_zones_json TEXT NOT NULL,
                currency_hint TEXT,
                vat_hint TEXT,
                vat_summary_zones_json TEXT,
                samples_count INTEGER DEFAULT 0,
                updated_at TEXT NOT NULL
            )
        """)
        
        conn.commit()
        conn.close()
    
    def test_english_vat_summary_extraction(self):
        """Test VAT summary extraction from English invoice"""
        words = [
            {'text': 'Subtotal', 'bbox': [100, 200, 200, 220]},
            {'text': '£100.00', 'bbox': [300, 200, 400, 220]},
            {'text': 'VAT', 'bbox': [100, 240, 150, 260]},
            {'text': '20%', 'bbox': [160, 240, 200, 260]},
            {'text': '£20.00', 'bbox': [300, 240, 400, 260]},
            {'text': 'Total', 'bbox': [100, 280, 200, 300]},
            {'text': '£120.00', 'bbox': [300, 280, 400, 300]}
        ]
        
        segments = [{'text': ' '.join([w['text'] for w in words])}]
        
        result = extract_vat_summary(words, segments, 'en')
        
        self.assertGreater(result['confidence'], 0.7, "Should have good confidence")
        self.assertEqual(len(result['rates']), 1, "Should find 1 VAT rate")
        self.assertEqual(result['rates'][0]['rate'], 20.0, "Should find 20% VAT rate")
        self.assertIsNotNone(result['subtotal'], "Should find subtotal")
        self.assertEqual(result['subtotal']['amount'], 100.0, "Should find £100.00 subtotal")
        self.assertIsNotNone(result['vat_total'], "Should find VAT total")
        self.assertEqual(result['vat_total']['amount'], 20.0, "Should find £20.00 VAT total")
        self.assertIsNotNone(result['total'], "Should find total")
        self.assertEqual(result['total']['amount'], 120.0, "Should find £120.00 total")
    
    def test_welsh_vat_summary_extraction(self):
        """Test VAT summary extraction from Welsh invoice"""
        words = [
            {'text': 'Is-gyfanswm', 'bbox': [100, 200, 200, 220]},
            {'text': '£100.00', 'bbox': [300, 200, 400, 220]},
            {'text': 'TAW', 'bbox': [100, 240, 150, 260]},
            {'text': '20%', 'bbox': [160, 240, 200, 260]},
            {'text': '£20.00', 'bbox': [300, 240, 400, 260]},
            {'text': 'Cyfanswm', 'bbox': [100, 280, 200, 300]},
            {'text': '£120.00', 'bbox': [300, 280, 400, 300]}
        ]
        
        segments = [{'text': ' '.join([w['text'] for w in words])}]
        
        result = extract_vat_summary(words, segments, 'cy')
        
        self.assertGreater(result['confidence'], 0.7, "Should have good confidence")
        self.assertEqual(len(result['rates']), 1, "Should find 1 VAT rate")
        self.assertEqual(result['rates'][0]['rate'], 20.0, "Should find 20% VAT rate")
        self.assertIsNotNone(result['subtotal'], "Should find subtotal")
        self.assertEqual(result['subtotal']['amount'], 100.0, "Should find £100.00 subtotal")
        self.assertIsNotNone(result['vat_total'], "Should find VAT total")
        self.assertEqual(result['vat_total']['amount'], 20.0, "Should find £20.00 VAT total")
        self.assertIsNotNone(result['total'], "Should find total")
        self.assertEqual(result['total']['amount'], 120.0, "Should find £120.00 total")
    
    def test_bilingual_vat_summary_extraction(self):
        """Test VAT summary extraction from bilingual invoice"""
        words = [
            {'text': 'Subtotal', 'bbox': [100, 200, 200, 220]},
            {'text': 'Is-gyfanswm', 'bbox': [250, 200, 350, 220]},
            {'text': '£100.00', 'bbox': [400, 200, 500, 220]},
            {'text': 'VAT', 'bbox': [100, 240, 150, 260]},
            {'text': 'TAW', 'bbox': [250, 240, 300, 260]},
            {'text': '20%', 'bbox': [350, 240, 390, 260]},
            {'text': '£20.00', 'bbox': [400, 240, 500, 260]},
            {'text': 'Total', 'bbox': [100, 280, 200, 300]},
            {'text': 'Cyfanswm', 'bbox': [250, 280, 350, 300]},
            {'text': '£120.00', 'bbox': [400, 280, 500, 300]}
        ]
        
        segments = [{'text': ' '.join([w['text'] for w in words])}]
        
        # Test English extraction (should find some fields)
        result_en = extract_vat_summary(words, segments, 'en')
        self.assertGreater(result_en['confidence'], 0.2, "English extraction should find some fields")
        self.assertEqual(len(result_en['rates']), 1, "Should find VAT rate")
        
        # Test Welsh extraction (should find all fields)
        result_cy = extract_vat_summary(words, segments, 'cy')
        self.assertGreater(result_cy['confidence'], 0.7, "Welsh extraction should have good confidence")
        self.assertEqual(len(result_cy['rates']), 1, "Should find VAT rate")
        self.assertIsNotNone(result_cy['subtotal'], "Should find subtotal")
        self.assertIsNotNone(result_cy['vat_total'], "Should find VAT total")
        self.assertIsNotNone(result_cy['total'], "Should find total")
    
    def test_template_vat_zone_saving(self):
        """Test saving templates with VAT summary zones"""
        supplier_key = "WILD_HORSE_BREWING"
        header_zones = {
            'invoice_number': [100, 50, 200, 80],
            'date': [100, 100, 200, 130],
            'total': [300, 200, 400, 230],
            'vat': [300, 240, 400, 270],
            'subtotal': [300, 160, 400, 190]
        }
        
        # Save template
        success = self.template_manager.save_template(
            supplier_key, header_zones, 'GBP', '20%'
        )
        
        self.assertTrue(success, "Should save template successfully")
        
        # Load template
        template = self.template_manager.load_template(supplier_key)
        
        self.assertIsNotNone(template, "Should load template")
        self.assertEqual(template.supplier_key, supplier_key)
        self.assertIsNotNone(template.vat_summary_zones, "Should have VAT summary zones")
        self.assertIn('vat', template.vat_summary_zones, "Should have VAT zone")
        self.assertIn('subtotal', template.vat_summary_zones, "Should have subtotal zone")
        self.assertIn('total', template.vat_summary_zones, "Should have total zone")
    
    def test_template_vat_zone_updating(self):
        """Test updating templates with new VAT summary zones"""
        supplier_key = "TEST_SUPPLIER"
        
        # Initial header zones
        header_zones_1 = {
            'total': [300, 200, 400, 230],
            'vat': [300, 240, 400, 270]
        }
        
        # Save initial template
        self.template_manager.save_template(supplier_key, header_zones_1, 'GBP', '20%')
        
        # Updated header zones with more VAT zones
        header_zones_2 = {
            'total': [300, 200, 400, 230],
            'vat': [300, 240, 400, 270],
            'subtotal': [300, 160, 400, 190],
            'tax_rate': [100, 240, 200, 270]
        }
        
        # Update template
        self.template_manager.save_template(supplier_key, header_zones_2, 'GBP', '20%')
        
        # Load updated template
        template = self.template_manager.load_template(supplier_key)
        
        self.assertEqual(template.samples_count, 2, "Should have 2 samples")
        self.assertIsNotNone(template.vat_summary_zones, "Should have VAT summary zones")
        self.assertIn('subtotal', template.vat_summary_zones, "Should have new subtotal zone")
        self.assertIn('tax_rate', template.vat_summary_zones, "Should have new tax_rate zone")
    
    def test_no_vat_zones_extraction(self):
        """Test extraction when no VAT zones are present"""
        words = [
            {'text': 'Invoice', 'bbox': [100, 50, 200, 80]},
            {'text': 'Number', 'bbox': [100, 100, 200, 130]},
            {'text': 'Date', 'bbox': [100, 150, 200, 180]}
        ]
        
        segments = [{'text': ' '.join([w['text'] for w in words])}]
        
        result = extract_vat_summary(words, segments, 'en')
        
        self.assertEqual(len(result['rates']), 0, "Should find no VAT rates")
        self.assertIsNone(result['subtotal'], "Should find no subtotal")
        self.assertIsNone(result['vat_total'], "Should find no VAT total")
        self.assertIsNone(result['total'], "Should find no total")
        self.assertEqual(result['confidence'], 0.0, "Should have zero confidence")

if __name__ == '__main__':
    unittest.main() 