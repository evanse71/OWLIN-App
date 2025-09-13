#!/usr/bin/env python3
"""
Hard Line Item Extraction Tests

Tests for robust line item extraction with Welsh support and wrapped descriptions
"""

import unittest
import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from ocr.enhanced_line_item_extractor import EnhancedLineItemExtractor, LineItem

class TestHardLineItemExtraction(unittest.TestCase):
    """Test robust line item extraction functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.extractor = EnhancedLineItemExtractor()
    
    def test_standard_invoice_extraction(self):
        """Test standard invoice line item extraction"""
        ocr_result = {
            'word_boxes': [
                {'text': 'Premium', 'bbox': [100, 200, 180, 220]},
                {'text': 'Lager', 'bbox': [190, 200, 250, 220]},
                {'text': '24', 'bbox': [300, 200, 320, 220]},
                {'text': 'case', 'bbox': [330, 200, 370, 220]},
                {'text': '£2.50', 'bbox': [400, 200, 450, 220]},
                {'text': '£60.00', 'bbox': [500, 200, 550, 220]},
                {'text': 'Craft', 'bbox': [100, 240, 150, 260]},
                {'text': 'IPA', 'bbox': [160, 240, 190, 260]},
                {'text': '12', 'bbox': [300, 240, 320, 260]},
                {'text': 'bottles', 'bbox': [330, 240, 390, 260]},
                {'text': '£3.20', 'bbox': [400, 240, 450, 260]},
                {'text': '£38.40', 'bbox': [500, 240, 550, 260]}
            ],
            'text': 'Premium Lager 24 case £2.50 £60.00 Craft IPA 12 bottles £3.20 £38.40'
        }
        
        result = self.extractor.extract_line_items(ocr_result, 'invoice')
        
        self.assertTrue(result.table_detected, "Should detect table structure")
        self.assertGreaterEqual(len(result.line_items), 2, "Should extract at least 2 line items")
        self.assertGreater(result.extraction_confidence, 0.7, "Should have good confidence")
        
        # Check first line item
        first_item = result.line_items[0]
        self.assertIn('Premium Lager', first_item.description, "Should extract description")
        self.assertEqual(first_item.quantity, 24.0, "Should extract quantity")
        self.assertEqual(first_item.unit, 'case', "Should extract unit")
        self.assertEqual(first_item.unit_price, 2.50, "Should extract unit price")
        self.assertEqual(first_item.line_total, 60.0, "Should extract line total")
    
    def test_wrapped_description_extraction(self):
        """Test extraction of wrapped descriptions"""
        ocr_result = {
            'word_boxes': [
                {'text': 'Prosciutto', 'bbox': [100, 200, 200, 220]},
                {'text': 'di', 'bbox': [210, 200, 230, 220]},
                {'text': 'Parma', 'bbox': [240, 200, 300, 220]},
                {'text': 'Premium', 'bbox': [310, 200, 380, 220]},
                {'text': 'Quality', 'bbox': [390, 200, 450, 220]},
                {'text': '500g', 'bbox': [500, 200, 540, 220]},
                {'text': '£8.50', 'bbox': [600, 200, 650, 220]},
                {'text': '£8.50', 'bbox': [700, 200, 750, 220]}
            ],
            'text': 'Prosciutto di Parma Premium Quality 500g £8.50 £8.50'
        }
        
        result = self.extractor.extract_line_items(ocr_result, 'invoice')
        
        self.assertGreaterEqual(len(result.line_items), 1, "Should extract line item")
        
        # Check wrapped description
        first_item = result.line_items[0]
        self.assertIn('Prosciutto di Parma', first_item.description, "Should handle wrapped description")
        self.assertEqual(first_item.quantity, 500.0, "Should extract quantity")
        self.assertEqual(first_item.unit, 'g', "Should extract unit")
    
    def test_welsh_unit_extraction(self):
        """Test extraction with Welsh units"""
        ocr_result = {
            'word_boxes': [
                {'text': 'Cwrw', 'bbox': [100, 200, 150, 220]},
                {'text': 'Premium', 'bbox': [160, 200, 230, 220]},
                {'text': '24', 'bbox': [300, 200, 320, 220]},
                {'text': 'casiau', 'bbox': [330, 200, 380, 220]},
                {'text': '£2.50', 'bbox': [400, 200, 450, 220]},
                {'text': '£60.00', 'bbox': [500, 200, 550, 220]},
                {'text': 'Cwrw', 'bbox': [100, 240, 150, 260]},
                {'text': 'Craft', 'bbox': [160, 240, 210, 260]},
                {'text': '12', 'bbox': [300, 240, 320, 260]},
                {'text': 'boteli', 'bbox': [330, 240, 380, 260]},
                {'text': '£3.20', 'bbox': [400, 240, 450, 260]},
                {'text': '£38.40', 'bbox': [500, 240, 550, 260]}
            ],
            'text': 'Cwrw Premium 24 casiau £2.50 £60.00 Cwrw Craft 12 boteli £3.20 £38.40'
        }
        
        result = self.extractor.extract_line_items(ocr_result, 'invoice')
        
        self.assertGreaterEqual(len(result.line_items), 2, "Should extract Welsh line items")
        
        # Check Welsh units
        first_item = result.line_items[0]
        self.assertEqual(first_item.unit, 'case', "Should normalize Welsh unit 'casiau' to 'case'")
        self.assertEqual(first_item.unit_original, 'casiau', "Should store original Welsh unit")
        
        second_item = result.line_items[1]
        self.assertEqual(second_item.unit, 'bottle', "Should normalize Welsh unit 'boteli' to 'bottle'")
    
    def test_delivery_note_extraction(self):
        """Test delivery note extraction (no prices)"""
        ocr_result = {
            'word_boxes': [
                {'text': 'Cwrw', 'bbox': [100, 200, 150, 220]},
                {'text': 'Premium', 'bbox': [160, 200, 230, 220]},
                {'text': '24', 'bbox': [300, 200, 320, 220]},
                {'text': 'casiau', 'bbox': [330, 200, 380, 220]},
                {'text': 'Delivered', 'bbox': [400, 200, 480, 220]},
                {'text': 'Cwrw', 'bbox': [100, 240, 150, 260]},
                {'text': 'Craft', 'bbox': [160, 240, 210, 260]},
                {'text': '12', 'bbox': [300, 240, 320, 260]},
                {'text': 'boteli', 'bbox': [330, 240, 380, 260]},
                {'text': 'Pending', 'bbox': [400, 240, 470, 260]}
            ],
            'text': 'Cwrw Premium 24 casiau Delivered Cwrw Craft 12 boteli Pending'
        }
        
        result = self.extractor.extract_line_items(ocr_result, 'delivery_note')
        
        self.assertGreaterEqual(len(result.line_items), 2, "Should extract delivery note items")
        
        # Check delivery note specific behavior
        for item in result.line_items:
            self.assertIsNone(item.unit_price, "Delivery notes should not have unit prices")
            self.assertIsNone(item.line_total, "Delivery notes should not have line totals")
            self.assertIn('DN_NO_PRICES', item.row_reasons, "Should have delivery note reason")
    
    def test_receipt_extraction_with_meta_rows(self):
        """Test receipt extraction with meta rows ignored"""
        ocr_result = {
            'word_boxes': [
                {'text': 'Cwrw', 'bbox': [100, 200, 150, 220]},
                {'text': 'Premium', 'bbox': [160, 200, 230, 220]},
                {'text': '2', 'bbox': [300, 200, 310, 220]},
                {'text': '£3.50', 'bbox': [400, 200, 450, 220]},
                {'text': '£7.00', 'bbox': [500, 200, 550, 220]},
                {'text': 'Subtotal', 'bbox': [100, 240, 180, 260]},
                {'text': '£7.00', 'bbox': [500, 240, 550, 260]},
                {'text': 'VAT', 'bbox': [100, 280, 130, 300]},
                {'text': '20%', 'bbox': [140, 280, 170, 300]},
                {'text': '£1.40', 'bbox': [500, 280, 550, 300]},
                {'text': 'Total', 'bbox': [100, 320, 150, 340]},
                {'text': '£8.40', 'bbox': [500, 320, 550, 340]},
                {'text': 'Card', 'bbox': [100, 360, 140, 380]},
                {'text': 'Payment', 'bbox': [150, 360, 220, 380]},
                {'text': '£10.00', 'bbox': [500, 360, 550, 380]},
                {'text': 'Change', 'bbox': [100, 400, 160, 420]},
                {'text': '£1.60', 'bbox': [500, 400, 550, 420]}
            ],
            'text': 'Cwrw Premium 2 £3.50 £7.00 Subtotal £7.00 VAT 20% £1.40 Total £8.40 Card Payment £10.00 Change £1.60'
        }
        
        result = self.extractor.extract_line_items(ocr_result, 'receipt')
        
        # Should extract line items but ignore meta rows
        line_items = [item for item in result.line_items if 'Cwrw' in item.description]
        self.assertGreaterEqual(len(line_items), 1, "Should extract receipt line items")
        
        # Check receipt specific behavior
        for item in line_items:
            self.assertIn('RECEIPT_MODE', item.row_reasons, "Should have receipt mode reason")
    
    def test_no_word_boxes_fallback(self):
        """Test fallback to regex extraction when no word boxes"""
        ocr_result = {
            'word_boxes': [],
            'text': 'Premium Lager 24 case £2.50 £60.00'
        }
        
        result = self.extractor.extract_line_items(ocr_result, 'invoice')
        
        self.assertFalse(result.table_detected, "Should not detect table without word boxes")
        self.assertGreaterEqual(len(result.line_items), 1, "Should extract line items via regex fallback")
        self.assertIn('REGEX_FALLBACK', result.extraction_reasons, "Should indicate regex fallback")
    
    def test_computed_line_totals(self):
        """Test computation of line totals when missing"""
        ocr_result = {
            'word_boxes': [
                {'text': 'Premium', 'bbox': [100, 200, 180, 220]},
                {'text': 'Lager', 'bbox': [190, 200, 250, 220]},
                {'text': '24', 'bbox': [300, 200, 320, 220]},
                {'text': 'case', 'bbox': [330, 200, 370, 220]},
                {'text': '£2.50', 'bbox': [400, 200, 450, 220]}
                # Missing line total
            ],
            'text': 'Premium Lager 24 case £2.50'
        }
        
        result = self.extractor.extract_line_items(ocr_result, 'invoice')
        
        self.assertGreaterEqual(len(result.line_items), 1, "Should extract line item")
        
        first_item = result.line_items[0]
        self.assertEqual(first_item.line_total, 60.0, "Should compute line total (24 * £2.50)")
        self.assertTrue(first_item.computed_total, "Should flag as computed total")
        self.assertIn('LINE_TOTAL_COMPUTED', first_item.row_reasons, "Should indicate computed total")

if __name__ == '__main__':
    unittest.main() 