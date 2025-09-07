#!/usr/bin/env python3
"""
Test verdict system
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.verdicts import VerdictEngine, VerdictContext, Verdict, VERDICT_PRIORITY

def test_verdict_priority():
    """Test that verdict priority is correctly ordered"""
    engine = VerdictEngine()
    
    # Test priority order (lower number = higher priority)
    assert VERDICT_PRIORITY[Verdict.PRICE_INCOHERENT] == 1
    assert VERDICT_PRIORITY[Verdict.VAT_MISMATCH] == 2
    assert VERDICT_PRIORITY[Verdict.PACK_MISMATCH] == 3
    assert VERDICT_PRIORITY[Verdict.OCR_LOW_CONF] == 4
    assert VERDICT_PRIORITY[Verdict.OFF_CONTRACT_DISCOUNT] == 5
    assert VERDICT_PRIORITY[Verdict.OK_ON_CONTRACT] == 6
    
    print("✅ Verdict priority test passed")

def test_single_verdict():
    """Test single verdict assignment"""
    engine = VerdictEngine()
    
    # Test each verdict individually
    context = VerdictContext(price_incoherent=True)
    verdict = engine.assign_verdict(context)
    assert verdict == Verdict.PRICE_INCOHERENT
    
    context = VerdictContext(vat_mismatch=True)
    verdict = engine.assign_verdict(context)
    assert verdict == Verdict.VAT_MISMATCH
    
    context = VerdictContext(pack_mismatch=True)
    verdict = engine.assign_verdict(context)
    assert verdict == Verdict.PACK_MISMATCH
    
    context = VerdictContext(ocr_low_conf=True)
    verdict = engine.assign_verdict(context)
    assert verdict == Verdict.OCR_LOW_CONF
    
    context = VerdictContext(off_contract_discount=True)
    verdict = engine.assign_verdict(context)
    assert verdict == Verdict.OFF_CONTRACT_DISCOUNT
    
    context = VerdictContext()  # No flags
    verdict = engine.assign_verdict(context)
    assert verdict == Verdict.OK_ON_CONTRACT
    
    print("✅ Single verdict test passed")

def test_conflicting_verdicts():
    """Test conflicting inputs → exactly one verdict returned"""
    engine = VerdictEngine()
    
    # Multiple flags set - should return highest priority
    context = VerdictContext(
        price_incoherent=True,
        vat_mismatch=True,
        pack_mismatch=True,
        ocr_low_conf=True,
        off_contract_discount=True
    )
    verdict = engine.assign_verdict(context)
    assert verdict == Verdict.PRICE_INCOHERENT  # Highest priority
    
    # Test other combinations
    context = VerdictContext(
        vat_mismatch=True,
        pack_mismatch=True,
        ocr_low_conf=True
    )
    verdict = engine.assign_verdict(context)
    assert verdict == Verdict.VAT_MISMATCH  # Highest priority among these
    
    context = VerdictContext(
        pack_mismatch=True,
        ocr_low_conf=True,
        off_contract_discount=True
    )
    verdict = engine.assign_verdict(context)
    assert verdict == Verdict.PACK_MISMATCH  # Highest priority among these
    
    print("✅ Conflicting verdicts test passed")

def test_context_from_flags():
    """Test creating context from flags"""
    engine = VerdictEngine()
    
    flags = {
        'PRICE_INCOHERENT': True,
        'VAT_MISMATCH': False,
        'PACK_MISMATCH': True,
        'OCR_LOW_CONF': False
    }
    
    discount_data = {
        'is_off_contract': True,
        'value': 15.5,
        'kind': 'percent',
        'residual_pennies': 25
    }
    
    context = engine.create_context_from_flags(flags, discount_data)
    
    assert context.price_incoherent == True
    assert context.vat_mismatch == False
    assert context.pack_mismatch == True
    assert context.ocr_low_conf == False
    assert context.off_contract_discount == True
    assert context.discount_value == 15.5
    assert context.discount_kind == 'percent'
    assert context.residual_pennies == 25
    
    print("✅ Context from flags test passed")

def test_verdict_descriptions():
    """Test verdict descriptions"""
    engine = VerdictEngine()
    
    for verdict in Verdict:
        description = engine.get_verdict_description(verdict)
        assert description is not None
        assert len(description) > 0
        assert "Unknown verdict" not in description
    
    print("✅ Verdict descriptions test passed")

def test_verdict_severity():
    """Test verdict severity levels"""
    engine = VerdictEngine()
    
    # Test severity levels
    assert engine.get_verdict_severity(Verdict.PRICE_INCOHERENT) == "critical"
    assert engine.get_verdict_severity(Verdict.VAT_MISMATCH) == "critical"
    assert engine.get_verdict_severity(Verdict.PACK_MISMATCH) == "warning"
    assert engine.get_verdict_severity(Verdict.OCR_LOW_CONF) == "warning"
    assert engine.get_verdict_severity(Verdict.OFF_CONTRACT_DISCOUNT) == "info"
    assert engine.get_verdict_severity(Verdict.OK_ON_CONTRACT) == "info"
    
    print("✅ Verdict severity test passed")

def test_exclusive_verdict():
    """Test that exactly one verdict is always returned"""
    engine = VerdictEngine()
    
    # Test with no flags
    context = VerdictContext()
    verdict = engine.assign_verdict(context)
    assert verdict is not None
    assert isinstance(verdict, Verdict)
    
    # Test with all flags
    context = VerdictContext(
        price_incoherent=True,
        vat_mismatch=True,
        pack_mismatch=True,
        ocr_low_conf=True,
        off_contract_discount=True
    )
    verdict = engine.assign_verdict(context)
    assert verdict is not None
    assert isinstance(verdict, Verdict)
    
    # Test with random combinations
    import random
    for _ in range(10):
        context = VerdictContext(
            price_incoherent=random.choice([True, False]),
            vat_mismatch=random.choice([True, False]),
            pack_mismatch=random.choice([True, False]),
            ocr_low_conf=random.choice([True, False]),
            off_contract_discount=random.choice([True, False])
        )
        verdict = engine.assign_verdict(context)
        assert verdict is not None
        assert isinstance(verdict, Verdict)
    
    print("✅ Exclusive verdict test passed")

if __name__ == "__main__":
    test_verdict_priority()
    test_single_verdict()
    test_conflicting_verdicts()
    test_context_from_flags()
    test_verdict_descriptions()
    test_verdict_severity()
    test_exclusive_verdict()
    print("All verdict tests passed!") 