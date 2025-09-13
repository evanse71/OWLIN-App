"""
Tests for verdict system - exclusive verdict assignment
"""
import pytest
import sys
sys.path.insert(0, 'backend')

from backend.engine.verdicts import VerdictEngine, Verdict, VerdictContext

class TestVerdictSystem:
    
    def setup_method(self):
        """Setup test environment"""
        self.engine = VerdictEngine()
    
    def test_single_issue_assigns_correct_verdict(self):
        """Test that single issues assign the correct verdict"""
        # OCR issue only
        context = VerdictContext(ocr_low_conf=True)
        verdict = self.engine.assign_verdict(context)
        assert verdict == Verdict.OCR_LOW_CONF
        
        # Pack mismatch only
        context = VerdictContext(pack_mismatch=True)
        verdict = self.engine.assign_verdict(context)
        assert verdict == Verdict.PACK_MISMATCH
        
        # Price incoherent only
        context = VerdictContext(price_incoherent=True)
        verdict = self.engine.assign_verdict(context)
        assert verdict == Verdict.PRICE_INCOHERENT
        
        # VAT mismatch only
        context = VerdictContext(vat_mismatch=True)
        verdict = self.engine.assign_verdict(context)
        assert verdict == Verdict.VAT_MISMATCH
        
        # Off-contract discount only
        context = VerdictContext(off_contract_discount=True)
        verdict = self.engine.assign_verdict(context)
        assert verdict == Verdict.OFF_CONTRACT_DISCOUNT
        
        # No issues
        context = VerdictContext()
        verdict = self.engine.assign_verdict(context)
        assert verdict == Verdict.OK_ON_CONTRACT
    
    def test_conflicting_inputs_priority_enforced(self):
        """Test that conflicting inputs resolve to exactly one verdict with correct priority"""
        # Multiple issues - should select highest priority (PRICE_INCOHERENT)
        context = VerdictContext(
            price_incoherent=True,
            pack_mismatch=True,
            ocr_low_conf=True,
            off_contract_discount=True
        )
        verdict = self.engine.assign_verdict(context)
        assert verdict == Verdict.PRICE_INCOHERENT
        
        # OCR + Pack issues - should select OCR (higher priority per spec)
        context = VerdictContext(
            ocr_low_conf=True,
            pack_mismatch=True
        )
        verdict = self.engine.assign_verdict(context)
        assert verdict == Verdict.OCR_LOW_CONF
        
        # VAT + Discount issues - should select VAT
        context = VerdictContext(
            vat_mismatch=True,
            off_contract_discount=True
        )
        verdict = self.engine.assign_verdict(context)
        assert verdict == Verdict.VAT_MISMATCH
    
    def test_verdict_context_from_flags(self):
        """Test creating VerdictContext from flags dictionary"""
        flags = {
            'PRICE_INCOHERENT': True,
            'OCR_LOW_CONF': True,
            'PACK_MISMATCH': False
        }
        
        discount_data = {
            'is_off_contract': True,
            'value': 20.0,
            'kind': 'percent',
            'residual_pennies': 0
        }
        
        context = self.engine.create_context_from_flags(flags, discount_data)
        
        assert context.price_incoherent == True
        assert context.ocr_low_conf == True
        assert context.pack_mismatch == False
        assert context.off_contract_discount == True
        assert context.discount_value == 20.0
        assert context.discount_kind == 'percent'
    
    def test_verdict_descriptions(self):
        """Test verdict descriptions are meaningful"""
        for verdict in Verdict:
            description = self.engine.get_verdict_description(verdict)
            assert len(description) > 10
            assert isinstance(description, str)
    
    def test_verdict_severity_mapping(self):
        """Test verdict severity levels"""
        assert self.engine.get_verdict_severity(Verdict.PRICE_INCOHERENT) == "critical"
        assert self.engine.get_verdict_severity(Verdict.VAT_MISMATCH) == "critical"
        assert self.engine.get_verdict_severity(Verdict.PACK_MISMATCH) == "warning"
        assert self.engine.get_verdict_severity(Verdict.OCR_LOW_CONF) == "warning"
        assert self.engine.get_verdict_severity(Verdict.OFF_CONTRACT_DISCOUNT) == "info"
        assert self.engine.get_verdict_severity(Verdict.OK_ON_CONTRACT) == "info"
    
    def test_exactly_one_verdict_always_returned(self):
        """Test that exactly one verdict is always returned, never multiple"""
        # Test various combinations
        test_cases = [
            VerdictContext(),  # No issues
            VerdictContext(price_incoherent=True),
            VerdictContext(price_incoherent=True, vat_mismatch=True),
            VerdictContext(ocr_low_conf=True, pack_mismatch=True, off_contract_discount=True),
            VerdictContext(
                price_incoherent=True,
                vat_mismatch=True,
                pack_mismatch=True,
                ocr_low_conf=True,
                off_contract_discount=True
            )  # All issues
        ]
        
        for context in test_cases:
            verdict = self.engine.assign_verdict(context)
            
            # Must be exactly one verdict
            assert isinstance(verdict, Verdict)
            assert verdict in Verdict
            
            # Must be deterministic (same input = same output)
            verdict2 = self.engine.assign_verdict(context)
            assert verdict == verdict2

if __name__ == "__main__":
    pytest.main([__file__]) 