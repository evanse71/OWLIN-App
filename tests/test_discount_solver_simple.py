"""
Simple tests for discount solver engine
"""
import pytest
import json
from pathlib import Path

def test_discount_solver_exists():
    """Test that discount solver class exists and can be instantiated"""
    from backend.engine.discount_solver import DiscountSolver
    
    solver = DiscountSolver()
    assert solver is not None
    assert hasattr(solver, 'solve_discount')
    assert callable(solver.solve_discount)

def test_tia_maria_percent_discount():
    """Test that Tia Maria discount scenario works correctly"""
    # Load golden fixture
    fixture_path = Path(__file__).parent / "fixtures" / "golden" / "tia_maria.json"
    with open(fixture_path) as f:
        fixture = json.load(f)
    
    # This test will FAIL if solver is a stub - good, red is truth
    from backend.engine.discount_solver import DiscountSolver
    
    solver = DiscountSolver()
    
    # Test data: £60.55 unit price, £32.22 line total, quantity 1
    # Expected: ~46.8% discount
    unit_price = fixture["unit_price_pennies"] / 100.0  # Convert pennies to pounds
    line_total = fixture["line_total_pennies"] / 100.0
    quantity = fixture["quantity_each"]
    
    result = solver.solve_discount(
        qty=quantity,
        unit_price=unit_price,
        nett_value=line_total
    )
    
    # This will fail if solver is not implemented
    assert result is not None, "Discount solver returned None - not implemented"
    assert result.kind == "percent", f"Expected percent discount, got {result.kind}"
    assert abs(result.value - 46.8) < 1.0, f"Expected ~46.8% discount, got {result.value}%"
    assert result.residual_pennies <= 1, f"Expected residual ≤1p, got {result.residual_pennies}p"

def test_basic_percent_discount():
    """Test basic percent discount calculation"""
    from backend.engine.discount_solver import DiscountSolver
    
    solver = DiscountSolver()
    
    # Simple case: 2 items at £10 each, total £16 (20% discount)
    result = solver.solve_discount(
        qty=2.0,
        unit_price=10.0,
        nett_value=16.0
    )
    
    assert result is not None, "Solver should find solution for simple case"
    assert result.kind == "percent", f"Expected percent discount, got {result.kind}"
    assert abs(result.value - 20.0) < 0.1, f"Expected 20% discount, got {result.value}%"
    assert result.residual_pennies <= 1, f"Expected residual ≤1p, got {result.residual_pennies}p" 