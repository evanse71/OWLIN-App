#!/usr/bin/env python3
"""
Test discount solver
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.discount_solver import DiscountSolver, DiscountResult

def test_tia_maria_case():
    """Test Tia Maria case: unit £60.55 → nett £32.22"""
    solver = DiscountSolver()
    
    # Tia Maria case: 1 unit at £60.55, nett £32.22
    result = solver.solve_discount(
        qty=1.0,
        unit_price=60.55,
        nett_value=32.22,
        canonical_quantities={'quantity_each': 1.0, 'packs': 1.0, 'units_per_pack': 1.0}
    )
    
    assert result is not None
    assert result.kind == "percent"
    assert abs(result.value - 46.8) < 1.0  # Should be ~46.8% discount
    assert result.residual_pennies < 50  # Low residual
    assert result.confidence > 0.9  # High confidence
    
    print("✅ Tia Maria case test passed")

def test_percent_discount():
    """Test percent discount calculation"""
    solver = DiscountSolver()
    
    # 20% discount case
    result = solver.solve_discount(
        qty=2.0,
        unit_price=10.0,
        nett_value=16.0,  # 20% off £20
        canonical_quantities={'quantity_each': 2.0, 'packs': 1.0, 'units_per_pack': 2.0}
    )
    
    assert result is not None
    assert result.kind == "percent"
    assert abs(result.value - 20.0) < 0.1
    assert result.residual_pennies < 10
    assert result.confidence > 0.95
    
    print("✅ Percent discount test passed")

def test_per_case_discount():
    """Test per-case discount calculation"""
    solver = DiscountSolver()
    
    # £5 per case discount
    result = solver.solve_discount(
        qty=24.0,
        unit_price=1.0,
        nett_value=19.0,  # £24 - £5 = £19
        canonical_quantities={'quantity_each': 24.0, 'packs': 1.0, 'units_per_pack': 24.0}
    )
    
    assert result is not None
    assert result.kind == "per_case"
    assert abs(result.value - 5.0) < 0.1
    assert result.residual_pennies < 10
    assert result.confidence > 0.95
    
    print("✅ Per-case discount test passed")

def test_per_litre_discount():
    """Test per-litre discount calculation"""
    solver = DiscountSolver()
    
    # £2 per litre discount
    result = solver.solve_discount(
        qty=12.0,
        unit_price=2.0,
        nett_value=20.0,  # £24 - £4 = £20 (2L total)
        canonical_quantities={'quantity_each': 12.0, 'packs': 1.0, 'units_per_pack': 12.0, 'quantity_l': 2.0}
    )
    
    assert result is not None
    assert result.kind == "per_litre"
    assert abs(result.value - 2.0) < 0.1
    assert result.residual_pennies < 10
    assert result.confidence > 0.95
    
    print("✅ Per-litre discount test passed")

def test_no_discount():
    """Test case where no discount is applied"""
    solver = DiscountSolver()
    
    # No discount case
    result = solver.solve_discount(
        qty=1.0,
        unit_price=10.0,
        nett_value=10.0,
        canonical_quantities={'quantity_each': 1.0, 'packs': 1.0, 'units_per_pack': 1.0}
    )
    
    assert result is None
    
    print("✅ No discount test passed")

def test_invalid_inputs():
    """Test invalid inputs"""
    solver = DiscountSolver()
    
    # Zero values
    result = solver.solve_discount(0.0, 10.0, 10.0)
    assert result is None
    
    # Negative values
    result = solver.solve_discount(1.0, -10.0, 10.0)
    assert result is None
    
    # Nett greater than expected
    result = solver.solve_discount(1.0, 10.0, 15.0)
    assert result is None
    
    print("✅ Invalid inputs test passed")

def test_hypothesis_selection():
    """Test hypothesis selection logic"""
    solver = DiscountSolver()
    
    # Create a case where multiple hypotheses are possible
    # but one should be clearly better
    result = solver.solve_discount(
        qty=1.0,
        unit_price=100.0,
        nett_value=80.0,  # 20% discount
        canonical_quantities={'quantity_each': 1.0, 'packs': 1.0, 'units_per_pack': 1.0}
    )
    
    assert result is not None
    # Should prefer percent discount for this case
    assert result.kind == "percent"
    assert result.confidence > 0.9
    
    print("✅ Hypothesis selection test passed")

if __name__ == "__main__":
    test_tia_maria_case()
    test_percent_discount()
    test_per_case_discount()
    test_per_litre_discount()
    test_no_discount()
    test_invalid_inputs()
    test_hypothesis_selection()
    print("All discount solver tests passed!") 