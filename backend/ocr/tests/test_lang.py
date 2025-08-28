#!/usr/bin/env python3
"""
Language Detection Tests

Tests for bilingual language detection and field extraction
"""

import unittest
import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from ocr.lang import detect_lang, get_bilingual_field_mapping, get_language_specific_patterns
from ocr.classifier import get_document_classifier

class TestLanguageDetection(unittest.TestCase):
    """Test language detection functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.classifier = get_document_classifier()
    
    def test_welsh_invoice_detection(self):
        """Test Welsh invoice language detection"""
        welsh_invoice = """
        ANFONEB
        
        Rhif Anfoneb: ANF-2025-001
        Dyddiad: 15/08/2025
        
        Cyfanswm: £60.00
        TAW (20%): £12.00
        Cyfanswm i Dalu: £72.00
        """
        
        detected_lang = detect_lang(welsh_invoice)
        self.assertEqual(detected_lang, "cy", "Should detect Welsh invoice")
        
        # Test classification
        result = self.classifier.classify_document(welsh_invoice)
        self.assertEqual(result.doc_type, "invoice", "Should classify as invoice")
        self.assertGreater(result.confidence, 0.5, "Should have reasonable confidence")
    
    def test_english_invoice_detection(self):
        """Test English invoice language detection"""
        english_invoice = """
        INVOICE
        
        Invoice Number: INV-2025-001
        Date: 15/08/2025
        
        Total: £60.00
        VAT (20%): £12.00
        Amount Due: £72.00
        """
        
        detected_lang = detect_lang(english_invoice)
        self.assertEqual(detected_lang, "en", "Should detect English invoice")
        
        # Test classification
        result = self.classifier.classify_document(english_invoice)
        self.assertEqual(result.doc_type, "invoice", "Should classify as invoice")
        self.assertGreater(result.confidence, 0.5, "Should have reasonable confidence")
    
    def test_bilingual_utility_bill_detection(self):
        """Test bilingual utility bill detection"""
        bilingual_bill = """
        BIL TRYDAN / ELECTRICITY BILL
        
        Rhif Cyfrif / Account Number: 1234567890
        Dyddiad / Date: 15/08/2025
        
        Defnydd / Usage: 150 kWh
        Cyfradd Uned / Unit Rate: £0.15 per kWh
        Cyfanswm / Total: £22.50
        """
        
        detected_lang = detect_lang(bilingual_bill)
        self.assertEqual(detected_lang, "bi", "Should detect bilingual document")
        
        # Test classification
        result = self.classifier.classify_document(bilingual_bill)
        self.assertEqual(result.doc_type, "utility", "Should classify as utility")
        self.assertGreater(result.confidence, 0.5, "Should have reasonable confidence")
    
    def test_short_text_defaults_to_english(self):
        """Test that very short text defaults to English"""
        short_text = "Hello"
        detected_lang = detect_lang(short_text)
        self.assertEqual(detected_lang, "en", "Short text should default to English")
    
    def test_bilingual_field_mapping(self):
        """Test bilingual field mapping"""
        mapping = get_bilingual_field_mapping()
        
        # Check structure
        self.assertIn('invoice_number', mapping)
        self.assertIn('total', mapping)
        self.assertIn('vat', mapping)
        self.assertIn('date', mapping)
        self.assertIn('supplier', mapping)
        
        # Check Welsh mappings
        self.assertIn('en', mapping['invoice_number'])
        self.assertIn('cy', mapping['invoice_number'])
        
        # Check specific Welsh terms
        cy_total = mapping['total']['cy']
        self.assertIn('cyfanswm', cy_total)
        self.assertIn('swm', cy_total)
        
        cy_vat = mapping['vat']['cy']
        self.assertIn('taw', cy_vat)
        self.assertIn('treth ar werth', cy_vat)
    
    def test_language_specific_patterns(self):
        """Test language-specific regex patterns"""
        # Test Welsh patterns
        cy_patterns = get_language_specific_patterns('cy')
        self.assertIn('date', cy_patterns)
        self.assertIn('currency', cy_patterns)
        self.assertIn('vat_rate', cy_patterns)
        self.assertIn('total', cy_patterns)
        
        # Test English patterns
        en_patterns = get_language_specific_patterns('en')
        self.assertIn('date', en_patterns)
        self.assertIn('currency', en_patterns)
        self.assertIn('vat_rate', en_patterns)
        self.assertIn('total', en_patterns)
        
        # Test Welsh VAT pattern
        import re
        welsh_vat_text = "TAW 20%"
        match = re.search(cy_patterns['vat_rate'], welsh_vat_text)
        self.assertIsNotNone(match, "Should match Welsh VAT pattern")
        
        # Test English VAT pattern
        english_vat_text = "VAT 20%"
        match = re.search(en_patterns['vat_rate'], english_vat_text)
        self.assertIsNotNone(match, "Should match English VAT pattern")
    
    def test_welsh_delivery_note_classification(self):
        """Test Welsh delivery note classification"""
        welsh_delivery = """
        NODIADAU CYFLENWI
        
        Rhif: DN-2025-089
        Dyddiad: 14/08/2025
        
        Disgrifiad                    Nifer    Uned
        Cwrw Premium                  24       casiau
        Cwrw Craft                    12       casiau
        Danfon i: Storfa Cegin
        """
        
        detected_lang = detect_lang(welsh_delivery)
        self.assertEqual(detected_lang, "cy", "Should detect Welsh delivery note")
        
        result = self.classifier.classify_document(welsh_delivery)
        self.assertEqual(result.doc_type, "delivery_note", "Should classify as delivery note")
    
    def test_welsh_receipt_classification(self):
        """Test Welsh receipt classification"""
        welsh_receipt = """
        Y TAFARN COCH
        
        Derbyn
        
        Cwrw Premium                  2     £3.50         £7.00
        Cwrw Craft                    1     £4.20         £4.20
        Is-gyfanswm:                                    £11.20
        TAW (20%):                                    £2.24
        Cyfanswm:                                        £13.44
        Taliad Cerdyn:                                 £15.00
        Newid:                                         £1.56
        """
        
        detected_lang = detect_lang(welsh_receipt)
        self.assertEqual(detected_lang, "cy", "Should detect Welsh receipt")
        
        result = self.classifier.classify_document(welsh_receipt)
        self.assertEqual(result.doc_type, "receipt", "Should classify as receipt")
    
    def test_negative_lexicon_detection(self):
        """Test negative lexicon detection for non-business documents"""
        menu_text = """
        RESTAURANT MENU
        
        Starters
        - Soup of the Day          £5.50
        - Garlic Bread             £3.50
        
        Mains
        - Fish & Chips            £12.50
        - Steak & Ale Pie         £14.50
        """
        
        detected_lang = detect_lang(menu_text)
        self.assertEqual(detected_lang, "en", "Should detect English")
        
        result = self.classifier.classify_document(menu_text)
        self.assertEqual(result.doc_type, "other", "Should classify as other due to negative lexicon")
    
    def test_welsh_negative_lexicon_detection(self):
        """Test Welsh negative lexicon detection"""
        welsh_menu = """
        BWYDLEN BWYTY
        
        Cyflenwadau
        - Cawl y Dydd              £5.50
        - Bara Garlleg             £3.50
        
        Prif Gyrsiau
        - Pysgod a Sglodion        £12.50
        - Pastai Eidion ac Ale     £14.50
        """
        
        detected_lang = detect_lang(welsh_menu)
        self.assertEqual(detected_lang, "cy", "Should detect Welsh")
        
        result = self.classifier.classify_document(welsh_menu)
        self.assertEqual(result.doc_type, "other", "Should classify as other due to Welsh negative lexicon")

if __name__ == '__main__':
    unittest.main() 