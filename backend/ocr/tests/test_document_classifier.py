#!/usr/bin/env python3
"""
Unit tests for document type classifier
"""

import unittest
from backend.ocr.document_type_classifier import DocumentTypeClassifier, classify_document_type, DocumentClassification


class TestDocumentTypeClassifier(unittest.TestCase):
    """Test cases for document type classification"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.classifier = DocumentTypeClassifier()
    
    def test_invoice_classification(self):
        """Test classification of invoice documents"""
        # Sample invoice text
        invoice_text = """
        TAX INVOICE
        Invoice Number: INV-2024-001
        VAT Registration: GB123456789
        Supplier: ABC Company Ltd
        
        Item Description    Quantity    Unit Price    Total
        Widget A           10          £5.00         £50.00
        Widget B           5           £10.00        £50.00
        
        Subtotal: £100.00
        VAT (20%): £20.00
        Total Due: £120.00
        
        Payment Terms: Net 30
        Due Date: 2024-12-31
        """
        
        result = self.classifier.classify(invoice_text)
        
        self.assertEqual(result.doc_type, "invoice")
        self.assertGreater(result.confidence, 70.0)
        self.assertIsInstance(result.reasons, list)
        self.assertGreater(len(result.reasons), 0)
    
    def test_delivery_note_classification(self):
        """Test classification of delivery note documents"""
        # Sample delivery note text
        delivery_text = """
        DELIVERY NOTE
        Delivery Note Number: DN-2024-001
        Delivery Date: 15/11/2024
        
        Item Description    Quantity    Delivered
        Widget A           10          Yes
        Widget B           5           Yes
        
        Delivered To: Customer Warehouse
        Received By: John Smith
        Signature: ________________
        
        Driver: Mike Johnson
        """
        
        result = self.classifier.classify(delivery_text)
        
        self.assertEqual(result.doc_type, "delivery_note")
        self.assertGreater(result.confidence, 70.0)
        self.assertIsInstance(result.reasons, list)
        self.assertGreater(len(result.reasons), 0)
    
    def test_unknown_classification(self):
        """Test classification of ambiguous/unknown documents"""
        # Ambiguous text with no clear indicators
        ambiguous_text = """
        Document
        Date: 2024-11-15
        Items: Various
        """
        
        result = self.classifier.classify(ambiguous_text)
        
        self.assertEqual(result.doc_type, "unknown")
        self.assertLess(result.confidence, 60.0)
    
    def test_empty_text(self):
        """Test classification with empty text"""
        result = self.classifier.classify("")
        
        self.assertEqual(result.doc_type, "unknown")
        self.assertEqual(result.confidence, 0.0)
        self.assertIn("Text too short", result.reasons[0])
    
    def test_short_text(self):
        """Test classification with very short text"""
        result = self.classifier.classify("Hi")
        
        self.assertEqual(result.doc_type, "unknown")
        self.assertEqual(result.confidence, 0.0)
    
    def test_multi_page_classification(self):
        """Test classification with multi-page documents"""
        page1 = """
        TAX INVOICE
        Invoice Number: INV-2024-001
        """
        
        page2 = """
        VAT Registration: GB123456789
        Total Due: £120.00
        """
        
        result = self.classifier.classify("\n".join([page1, page2]), pages=[page1, page2])
        
        self.assertEqual(result.doc_type, "invoice")
        self.assertGreater(result.confidence, 70.0)
        # Should mention multiple pages in reasons
        page_mentions = [r for r in result.reasons if "page" in r.lower()]
        self.assertGreater(len(page_mentions), 0)
    
    def test_invoice_keywords(self):
        """Test that invoice keywords are detected"""
        test_cases = [
            "INVOICE",
            "TAX INVOICE",
            "VAT INVOICE",
            "INVOICE NUMBER",
            "TOTAL DUE",
            "AMOUNT DUE"
        ]
        
        for keyword in test_cases:
            result = self.classifier.classify(f"Document\n{keyword}\nDetails")
            # Should at least recognize it's not a delivery note
            self.assertNotEqual(result.doc_type, "delivery_note")
    
    def test_delivery_note_keywords(self):
        """Test that delivery note keywords are detected"""
        test_cases = [
            "DELIVERY NOTE",
            "DEL NOTE",
            "D/N",
            "GOODS RECEIPT",
            "RECEIVED BY",
            "SIGNATURE"
        ]
        
        for keyword in test_cases:
            result = self.classifier.classify(f"Document\n{keyword}\nDetails")
            # Should at least recognize it's not an invoice
            self.assertNotEqual(result.doc_type, "invoice")
    
    def test_field_patterns_invoice(self):
        """Test that invoice field patterns are detected"""
        invoice_text = """
        Invoice No: INV-123
        VAT Reg: GB123456789
        Total: £100.00
        VAT Rate: 20%
        """
        
        result = self.classifier.classify(invoice_text)
        
        self.assertEqual(result.doc_type, "invoice")
        # Should mention field detection in reasons
        field_mentions = [r for r in result.reasons if "field" in r.lower()]
        self.assertGreater(len(field_mentions), 0)
    
    def test_field_patterns_delivery_note(self):
        """Test that delivery note field patterns are detected"""
        delivery_text = """
        Delivery Date: 15/11/2024
        Received By: John Smith
        Delivered To: Warehouse
        Signature: ________
        """
        
        result = self.classifier.classify(delivery_text)
        
        self.assertEqual(result.doc_type, "delivery_note")
        # Should mention field detection in reasons
        field_mentions = [r for r in result.reasons if "field" in r.lower()]
        self.assertGreater(len(field_mentions), 0)
    
    def test_confidence_scoring(self):
        """Test that confidence scores are reasonable"""
        # Strong invoice indicators
        strong_invoice = """
        TAX INVOICE
        Invoice Number: INV-001
        VAT Registration: GB123456789
        Total Due: £100.00
        Payment Terms: Net 30
        """
        
        result = self.classifier.classify(strong_invoice)
        self.assertGreaterEqual(result.confidence, 50.0)
        self.assertLessEqual(result.confidence, 100.0)
    
    def test_convenience_function(self):
        """Test the convenience function"""
        text = "TAX INVOICE\nInvoice Number: INV-001"
        result = classify_document_type(text)
        
        self.assertIsInstance(result, DocumentClassification)
        self.assertEqual(result.doc_type, "invoice")
        self.assertGreater(result.confidence, 0.0)
    
    def test_ambiguous_equal_scores(self):
        """Test classification when invoice and delivery note scores are equal"""
        # Text with equal indicators for both types
        ambiguous_text = """
        Document
        Invoice: INV-001
        Delivery: DN-001
        """
        
        result = self.classifier.classify(ambiguous_text)
        
        # Should default to unknown when scores are equal
        self.assertEqual(result.doc_type, "unknown")
        self.assertIn("Ambiguous", " ".join(result.reasons))


if __name__ == "__main__":
    unittest.main()

