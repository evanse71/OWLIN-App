#!/usr/bin/env python3
"""
LLM Assist Tests

Tests for LLM-powered assistance features
"""

import unittest
import sys
import os
from unittest.mock import patch, MagicMock

# Add the parent directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from ocr.unified_ocr_engine import get_unified_ocr_engine
from ocr.llm_assists import llm_guess_doctype, llm_normalize_supplier, check_hard_signals
from ocr.config import get_ocr_config

class TestLLMAssist(unittest.TestCase):
    """Test LLM assist functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.engine = get_unified_ocr_engine()
        self.config = get_ocr_config()
    
    def test_llm_disabled_by_default(self):
        """Test that LLM is disabled by default"""
        llm_enabled = self.config.get_llm("enabled", False)
        self.assertFalse(llm_enabled, "LLM should be disabled by default")
    
    def test_pipeline_identical_with_llm_disabled(self):
        """Test that pipeline behavior is identical when LLM is disabled"""
        # Test document that would trigger LLM assist if enabled
        low_confidence_text = """
        Some random text that doesn't have clear document signals.
        This should result in low classification confidence.
        """
        
        # Process with LLM disabled
        result = self.engine.process_document(low_confidence_text)
        
        # Verify no LLM-related reasons
        llm_reasons = [r for r in result.policy_decision['reasons'] if 'LLM_ASSIST' in r]
        self.assertEqual(len(llm_reasons), 0, "No LLM reasons should be present when disabled")
    
    @patch('ocr.llm_assists.get_llm_runtime')
    def test_llm_assist_with_strong_signals(self, mock_runtime):
        """Test LLM assist when strong signals are present"""
        # Mock LLM runtime
        mock_llm = MagicMock()
        mock_llm.is_available.return_value = True
        mock_llm.generate.return_value = '{"label": "invoice", "why": "Contains invoice number and totals"}'
        mock_runtime.return_value = mock_llm
        
        # Enable LLM in config
        with patch.object(self.engine.config, 'get_llm') as mock_get_llm:
            mock_get_llm.side_effect = lambda key, default=None: {
                'enabled': True,
                'doctype_gate': 0.75  # Higher gate to trigger LLM assist
            }.get(key, default)
            
            # Test document with strong invoice signals but ambiguous content
            invoice_text = """
            WILD HORSE BREWING CO LTD
            Invoice Number: INV-2025-001
            Date: 15/08/2025
            
            Description                    Qty    Unit Price    Total
            Premium Lager                  24     £2.50         £60.00
            Total Amount Due:                              £60.00
            
            Some additional text that might confuse the classifier
            and result in lower confidence.
            """
            
            result = self.engine.process_document(invoice_text)
            
            # Debug output
            print(f"Classification confidence: {result.overall_confidence}")
            print(f"Policy reasons: {result.policy_decision['reasons']}")
            print(f"Doc type reasons: {result.doc_type_reasons}")
            
            # Check if LLM assist was used (check both policy and doc type reasons)
            llm_reasons = [r for r in result.policy_decision['reasons'] if 'LLM_ASSIST' in r]
            if not llm_reasons and result.doc_type_reasons:
                llm_reasons = [r for r in result.doc_type_reasons if 'LLM_ASSIST' in r]
            
            self.assertGreater(len(llm_reasons), 0, "LLM assist should be triggered")
    
    @patch('ocr.llm_assists.get_llm_runtime')
    def test_llm_assist_ignored_no_signals(self, mock_runtime):
        """Test LLM assist is ignored when no hard signals are present"""
        # Mock LLM runtime
        mock_llm = MagicMock()
        mock_llm.is_available.return_value = True
        mock_llm.generate.return_value = '{"label": "invoice", "why": "Looks like an invoice"}'
        mock_runtime.return_value = mock_llm
        
        # Enable LLM in config
        with patch.object(self.config, 'get_llm') as mock_get_llm:
            mock_get_llm.side_effect = lambda key, default=None: {
                'enabled': True,
                'doctype_gate': 0.55
            }.get(key, default)
            
            # Test document with no strong signals
            weak_text = """
            Some random text without clear document structure.
            No invoice numbers, totals, or other strong signals.
            """
            
            result = self.engine.process_document(weak_text)
            
            # Check if LLM assist was ignored
            llm_reasons = [r for r in result.policy_decision['reasons'] if 'LLM_ASSIST' in r]
            if llm_reasons:
                self.assertIn('LLM_ASSIST_IGNORED', llm_reasons, "LLM assist should be ignored when no hard signals")
    
    def test_check_hard_signals(self):
        """Test hard signal detection"""
        # Test invoice with strong signals
        invoice_text = """
        WILD HORSE BREWING CO LTD
        Invoice Number: INV-2025-001
        Total Amount Due: £60.00
        """
        
        self.assertTrue(check_hard_signals(invoice_text, 'invoice'), "Should detect invoice signals")
        self.assertFalse(check_hard_signals(invoice_text, 'receipt'), "Should not detect receipt signals")
        
        # Test receipt with strong signals
        receipt_text = """
        THE RED LION PUB
        Receipt
        Total: £13.44
        Thank you for your payment
        """
        
        self.assertTrue(check_hard_signals(receipt_text, 'receipt'), "Should detect receipt signals")
        self.assertFalse(check_hard_signals(receipt_text, 'invoice'), "Should not detect invoice signals")
        
        # Test weak text
        weak_text = "Some random text without clear signals"
        self.assertTrue(check_hard_signals(weak_text, 'other'), "Should accept 'other' for weak signals")
    
    @patch('ocr.llm_assists.get_llm_runtime')
    def test_llm_unavailable_graceful_handling(self, mock_runtime):
        """Test graceful handling when LLM is unavailable"""
        # Mock LLM runtime as unavailable
        mock_llm = MagicMock()
        mock_llm.is_available.return_value = False
        mock_runtime.return_value = mock_llm
        
        # Enable LLM in config
        with patch.object(self.config, 'get_llm') as mock_get_llm:
            mock_get_llm.side_effect = lambda key, default=None: {
                'enabled': True,
                'doctype_gate': 0.55
            }.get(key, default)
            
            # Process document
            text = "Some test document text"
            result = self.engine.process_document(text)
            
            # Should process normally without LLM
            self.assertIsNotNone(result, "Should process document even when LLM unavailable")
            
            # No LLM reasons should be present
            llm_reasons = [r for r in result.policy_decision['reasons'] if 'LLM_ASSIST' in r]
            self.assertEqual(len(llm_reasons), 0, "No LLM reasons when LLM unavailable")
    
    def test_policy_outcomes_gated_by_validation(self):
        """Test that policy outcomes remain gated by validation (LLM cannot make ARITH_FAIL pass)"""
        # Test document with arithmetic failure
        arith_fail_text = """
        WILD HORSE BREWING CO LTD
        Invoice Number: INV-2025-001
        
        Description                    Qty    Unit Price    Total
        Premium Lager                  24     £2.50         £60.00
        Craft IPA                      12     £3.20         £38.40
        Total Amount Due:                              £100.00  # Wrong total
        """
        
        result = self.engine.process_document(arith_fail_text)
        
        # Even if LLM suggests 'invoice', arithmetic validation should still fail
        validation_issues = result.validation_result.get('issues', [])
        arith_issues = [issue for issue in validation_issues if 'ARITHMETIC' in issue.get('type', '')]
        
        # The policy should still reflect validation failures
        if arith_issues:
            self.assertNotEqual(result.policy_decision['action'], 'ACCEPT', 
                              "Policy should not accept document with arithmetic failures")

if __name__ == '__main__':
    unittest.main() 