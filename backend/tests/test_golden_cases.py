#!/usr/bin/env python3
"""
Golden Cases Acceptance Test

Tests the engine against known scenarios with expected outcomes.
"""

import sys
import os
import json
import tempfile
from pathlib import Path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.discount_solver import get_discount_solver
from engine.verdicts import get_verdict_engine, VerdictContext
from normalization.units import canonical_quantities

def load_golden_dataset(filename: str) -> dict:
    """Load golden dataset from JSON file"""
    golden_path = Path(__file__).parent / "golden" / filename
    with open(golden_path, 'r') as f:
        return json.load(f)

def test_percent_discount():
    """Test percent discount scenario (Tia Maria case)"""
    print("🧪 Testing percent discount scenario...")
    
    dataset = load_golden_dataset("discount_percent.json")
    solver = get_discount_solver()
    verdict_engine = get_verdict_engine()
    
    passed = 0
    total = len(dataset["test_cases"])
    
    for test_case in dataset["test_cases"]:
        input_data = test_case["input"]
        expected = test_case["expected"]
        
        # Normalize quantities
        canonical = canonical_quantities(input_data["qty"], input_data["description"])
        
        # Solve discount
        result = solver.solve_discount(
            qty=input_data["qty"],
            unit_price=input_data["unit_price"],
            nett_value=input_data["nett_value"],
            canonical_quantities=canonical
        )
        
        if result is None:
            print(f"❌ {test_case['name']}: No discount result")
            continue
        
        # Check discount kind
        if result.kind != expected["discount_kind"]:
            print(f"❌ {test_case['name']}: Expected {expected['discount_kind']}, got {result.kind}")
            continue
        
        # Check discount value (within tolerance)
        value_diff = abs(result.value - expected["discount_value"])
        if value_diff > dataset["expected_discount"]["tolerance"]:
            print(f"❌ {test_case['name']}: Expected {expected['discount_value']}, got {result.value}")
            continue
        
        # Check residual
        if result.residual_pennies > 50:  # 50p tolerance
            print(f"❌ {test_case['name']}: High residual {result.residual_pennies}p")
            continue
        
        # Check verdict
        context = VerdictContext(off_contract_discount=True)
        verdict = verdict_engine.assign_verdict(context)
        
        if verdict.value != expected["verdict"]:
            print(f"❌ {test_case['name']}: Expected verdict {expected['verdict']}, got {verdict.value}")
            continue
        
        print(f"✅ {test_case['name']}: PASS")
        passed += 1
    
    print(f"📊 Percent discount: {passed}/{total} passed")
    return passed == total

def test_per_case_discount():
    """Test per-case discount scenario"""
    print("🧪 Testing per-case discount scenario...")
    
    dataset = load_golden_dataset("discount_per_case.json")
    solver = get_discount_solver()
    verdict_engine = get_verdict_engine()
    
    passed = 0
    total = len(dataset["test_cases"])
    
    for test_case in dataset["test_cases"]:
        input_data = test_case["input"]
        expected = test_case["expected"]
        
        # Normalize quantities
        canonical = canonical_quantities(input_data["qty"], input_data["description"])
        
        # Solve discount
        result = solver.solve_discount(
            qty=input_data["qty"],
            unit_price=input_data["unit_price"],
            nett_value=input_data["nett_value"],
            canonical_quantities=canonical
        )
        
        if result is None:
            print(f"❌ {test_case['name']}: No discount result")
            continue
        
        # Check discount kind
        if result.kind != expected["discount_kind"]:
            print(f"❌ {test_case['name']}: Expected {expected['discount_kind']}, got {result.kind}")
            continue
        
        # Check discount value
        value_diff = abs(result.value - expected["discount_value"])
        if value_diff > dataset["expected_discount"]["tolerance"]:
            print(f"❌ {test_case['name']}: Expected {expected['discount_value']}, got {result.value}")
            continue
        
        # Check verdict
        context = VerdictContext(off_contract_discount=True)
        verdict = verdict_engine.assign_verdict(context)
        
        if verdict.value != expected["verdict"]:
            print(f"❌ {test_case['name']}: Expected verdict {expected['verdict']}, got {verdict.value}")
            continue
        
        print(f"✅ {test_case['name']}: PASS")
        passed += 1
    
    print(f"📊 Per-case discount: {passed}/{total} passed")
    return passed == total

def test_per_litre_discount():
    """Test per-litre discount scenario"""
    print("🧪 Testing per-litre discount scenario...")
    
    dataset = load_golden_dataset("discount_per_litre.json")
    solver = get_discount_solver()
    verdict_engine = get_verdict_engine()
    
    passed = 0
    total = len(dataset["test_cases"])
    
    for test_case in dataset["test_cases"]:
        input_data = test_case["input"]
        expected = test_case["expected"]
        
        # Normalize quantities
        canonical = canonical_quantities(input_data["qty"], input_data["description"])
        
        # Solve discount
        result = solver.solve_discount(
            qty=input_data["qty"],
            unit_price=input_data["unit_price"],
            nett_value=input_data["nett_value"],
            canonical_quantities=canonical
        )
        
        if result is None:
            print(f"❌ {test_case['name']}: No discount result")
            continue
        
        # Check discount kind
        if result.kind != expected["discount_kind"]:
            print(f"❌ {test_case['name']}: Expected {expected['discount_kind']}, got {result.kind}")
            continue
        
        # Check discount value
        value_diff = abs(result.value - expected["discount_value"])
        if value_diff > dataset["expected_discount"]["tolerance"]:
            print(f"❌ {test_case['name']}: Expected {expected['discount_value']}, got {result.value}")
            continue
        
        # Check verdict
        context = VerdictContext(off_contract_discount=True)
        verdict = verdict_engine.assign_verdict(context)
        
        if verdict.value != expected["verdict"]:
            print(f"❌ {test_case['name']}: Expected verdict {expected['verdict']}, got {verdict.value}")
            continue
        
        print(f"✅ {test_case['name']}: PASS")
        passed += 1
    
    print(f"📊 Per-litre discount: {passed}/{total} passed")
    return passed == total

def test_mixed_invoice_dn():
    """Test mixed invoice and delivery note scenario"""
    print("🧪 Testing mixed invoice and delivery note scenario...")
    
    # This would test the pairing functionality
    # For now, we'll create a simple test
    from services.pairing_service import PairingService
    
    pairing_service = PairingService()
    
    # Mock invoice and delivery note lines
    invoice_lines = [
        {
            'id': 1,
            'quantity': 24,
            'description': 'Heineken Lager 330ml',
            'unit_price': 1.50,
            'sku': 'HEINEKEN001'
        }
    ]
    
    delivery_lines = [
        {
            'id': 101,
            'quantity': 24,
            'description': 'Heineken Lager 330ml cans',
            'unit_price': 1.55,
            'sku': 'HEINEKEN001'
        }
    ]
    
    # Test pairing
    pairings = pairing_service.pair_line_items(invoice_lines, delivery_lines)
    
    if len(pairings) == 1 and pairings[0]['score'] > 0.7:
        print("✅ Mixed invoice/DN pairing: PASS")
        return True
    else:
        print("❌ Mixed invoice/DN pairing: FAIL")
        return False

def run_all_golden_tests():
    """Run all golden tests"""
    print("🏆 GOLDEN CASES ACCEPTANCE TEST")
    print("="*50)
    
    results = []
    
    # Test percent discount
    results.append(("Percent Discount", test_percent_discount()))
    
    # Test per-case discount
    results.append(("Per-Case Discount", test_per_case_discount()))
    
    # Test per-litre discount
    results.append(("Per-Litre Discount", test_per_litre_discount()))
    
    # Test mixed invoice/DN
    results.append(("Mixed Invoice/DN", test_mixed_invoice_dn()))
    
    # Summary
    print("\n" + "="*50)
    print("📊 SUMMARY")
    print("="*50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:20} {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL GOLDEN TESTS PASSED!")
        return True
    else:
        print("💥 SOME TESTS FAILED!")
        return False

if __name__ == "__main__":
    success = run_all_golden_tests()
    sys.exit(0 if success else 1) 