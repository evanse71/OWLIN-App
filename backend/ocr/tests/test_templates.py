#!/usr/bin/env python3
"""
Template Memory System Tests

Tests for supplier template memory and auto-retry functionality
"""

import unittest
import tempfile
import sqlite3
from pathlib import Path
import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from ocr.templates import TemplateManager, SupplierTemplate
from ocr.unified_ocr_engine import get_unified_ocr_engine

class TestTemplateMemory(unittest.TestCase):
    """Test template memory functionality"""
    
    def setUp(self):
        """Set up test database"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db_path = self.temp_db.name
        self.temp_db.close()
        
        # Create test database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create supplier_templates table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS supplier_templates (
                supplier_key TEXT PRIMARY KEY,
                header_zones_json TEXT NOT NULL,
                currency_hint TEXT,
                vat_hint TEXT,
                samples_count INTEGER DEFAULT 0,
                updated_at TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
        
        # Create template manager with test database
        self.template_manager = TemplateManager(self.db_path)
    
    def tearDown(self):
        """Clean up test database"""
        Path(self.db_path).unlink(missing_ok=True)
    
    def test_save_and_load_template(self):
        """Test saving and loading templates"""
        supplier_key = "test_supplier_123"
        header_zones = {
            "invoice": [100, 50, 200, 30],
            "date": [400, 50, 150, 30]
        }
        currency_hint = "GBP"
        vat_hint = "VAT_REG_GB123456789"
        
        # Save template
        success = self.template_manager.save_template(
            supplier_key, header_zones, currency_hint, vat_hint
        )
        self.assertTrue(success)
        
        # Load template
        template = self.template_manager.load_template(supplier_key)
        self.assertIsNotNone(template)
        self.assertEqual(template.supplier_key, supplier_key)
        self.assertEqual(template.header_zones, header_zones)
        self.assertEqual(template.currency_hint, currency_hint)
        self.assertEqual(template.vat_hint, vat_hint)
        self.assertEqual(template.samples_count, 1)
    
    def test_template_update(self):
        """Test updating existing template"""
        supplier_key = "test_supplier_456"
        
        # Save initial template
        self.template_manager.save_template(
            supplier_key, {"invoice": [100, 50, 200, 30]}, "GBP", None
        )
        
        # Update template
        self.template_manager.save_template(
            supplier_key, {"invoice": [150, 60, 250, 40]}, "EUR", "VAT_123"
        )
        
        # Check updated template
        template = self.template_manager.load_template(supplier_key)
        self.assertEqual(template.samples_count, 2)
        self.assertEqual(template.currency_hint, "EUR")
        self.assertEqual(template.vat_hint, "VAT_123")
    
    def test_supplier_matching(self):
        """Test supplier matching functionality"""
        # Save a template with a realistic supplier name
        supplier_key = "wild_horse_brewing_co_ltd_789"
        self.template_manager.save_template(
            supplier_key, {"invoice": [100, 50, 200, 30]}, "GBP", None
        )
        
        # Test matching with similar text
        text = "WILD HORSE BREWING CO LTD\nInvoice Number: INV-2025-001"
        matched_key = self.template_manager.match_supplier(text)
        
        # Should match due to fuzzy matching
        self.assertIsNotNone(matched_key)
        self.assertEqual(matched_key, supplier_key)
    
    def test_extract_header_zones(self):
        """Test header zone extraction"""
        text = "WILD HORSE BREWING CO LTD\nInvoice Number: INV-2025-001\nDate: 15/08/2025"
        word_boxes = [
            {"text": "WILD", "bbox": [100, 50, 50, 20]},
            {"text": "HORSE", "bbox": [160, 50, 60, 20]},
            {"text": "Invoice", "bbox": [100, 80, 70, 20]},
            {"text": "Number", "bbox": [180, 80, 60, 20]},
            {"text": "Date", "bbox": [100, 110, 40, 20]}
        ]
        
        header_zones = self.template_manager.extract_header_zones(text, word_boxes)
        
        # Should extract zones for invoice-related keywords
        self.assertIn("invoice", header_zones)
        self.assertIn("date", header_zones)
    
    def test_template_hints(self):
        """Test template hints retrieval"""
        supplier_key = "test_supplier_hints"
        header_zones = {"invoice": [100, 50, 200, 30]}
        currency_hint = "GBP"
        
        self.template_manager.save_template(supplier_key, header_zones, currency_hint, None)
        
        hints = self.template_manager.get_template_hints(supplier_key)
        
        self.assertEqual(hints["header_zones"], header_zones)
        self.assertEqual(hints["currency_hint"], currency_hint)
        self.assertEqual(hints["samples_count"], 1)

class TestAutoRetry(unittest.TestCase):
    """Test auto-retry functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.engine = get_unified_ocr_engine()
    
    def test_auto_retry_trigger(self):
        """Test auto-retry trigger conditions"""
        # Test low confidence trigger
        low_confidence = 0.4  # 40%
        high_confidence = 0.8  # 80%
        
        # Mock policy decision
        from ocr.policy import PolicyDecision, PolicyAction
        policy_decision = PolicyDecision(
            action=PolicyAction.QUARANTINE,
            reasons=[],
            confidence_threshold_met=False,
            validation_passed=False,
            auto_retry_used=False
        )
        
        # Should trigger auto-retry for low confidence
        should_retry_low = self.engine._should_auto_retry(low_confidence, policy_decision)
        self.assertTrue(should_retry_low)
        
        # Should not trigger for high confidence
        should_retry_high = self.engine._should_auto_retry(high_confidence, policy_decision)
        self.assertFalse(should_retry_high)
    
    def test_auto_retry_no_loop(self):
        """Test that auto-retry doesn't loop"""
        # Mock policy decision with auto-retry already used
        from ocr.policy import PolicyDecision, PolicyAction
        policy_decision = PolicyDecision(
            action=PolicyAction.QUARANTINE,
            reasons=[],
            confidence_threshold_met=False,
            validation_passed=False,
            auto_retry_used=True  # Already used
        )
        
        # Should not trigger auto-retry if already used
        should_retry = self.engine._should_auto_retry(0.3, policy_decision)
        self.assertFalse(should_retry)

if __name__ == '__main__':
    unittest.main() 