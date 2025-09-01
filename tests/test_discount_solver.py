"""
Tests for discount solver engine including golden cases
"""
import pytest
import json
from pathlib import Path
import sys
sys.path.insert(0, 'backend')

from backend.engine.discount_solver import DiscountSolver

class TestDiscountSolver:
    
    def setup_method(self):
        """Setup test environment"""
        self.solver = DiscountSolver()
    
    def test_tia_maria_golden_case(self):
        """Test Tia Maria golden case: unit £60.55 → nett £32.22 should select percent"""
        # Load golden fixture
        golden_path = Path('tests/fixtures/golden/tia_maria.json')
        if not golden_path.exists():
            pytest.skip("Tia Maria golden fixture not found")
            
        with open(golden_path) as f:
            golden = json.load(f)
        
        line_item = golden['line_item']
        expected = golden['expected_result']
        
        # Prepare solver input
        line_data = {
            'quantity_each': line_item['quantity'],
            'quantity_l': line_item['canonical_quantities']['quantity_l'],
            'unit_price': line_item['unit_price'],
            'line_total': line_item['line_total'],
            'expected_price': line_item['unit_price']
        }
        
        # Run solver
        result = self.solver.solve_discount(
            qty=line_data['quantity_each'],
            unit_price=line_data['unit_price'],
            nett_value=line_data['line_total']
        )
        
        # Verify result
        assert result is not None, "Solver should find a solution for Tia Maria"
        assert result.kind == expected['kind'], f"Expected {expected['kind']}, got {result.kind}"
        
        # Check discount percentage is in expected range
        assert 46.0 <= result.value <= 47.0, f"Discount {result.value}% outside expected range"
        
        # Check residual is within tolerance
        assert result.residual_pennies <= 1, f"Residual {result.residual_pennies}p exceeds 1p tolerance"
    
    def test_percent_discount_hypothesis(self):
        """Test percent discount calculation"""
        line_data = {
            'quantity_each': 2.0,
            'unit_price': 10.0,
            'line_total': 16.0,  # 20% discount
            'expected_price': 10.0
        }
        
        result = self.solver.solve_discount(line_data)
        
        assert result is not None
        assert result['kind'] == 'percent'
        assert abs(result.get('implied_pct', result['value']) - 20.0) < 0.1
        assert result['residual_pennies'] <= 1
    
    def test_per_case_discount_hypothesis(self):
        """Test per-case discount calculation"""
        line_data = {
            'quantity_each': 24.0,  # 2 cases of 12
            'quantity_l': 8.25,     # 24 x 275ml = 6.6L
            'unit_price': 1.0,
            'line_total': 20.0,     # £24 - £4 = £20 (£2 per case)
            'expected_price': 1.0
        }
        
        # Mock canonical quantities for cases
        canonical = {
            'packs': 2.0,
            'units_per_pack': 12.0,
            'quantity_each': 24.0,
            'quantity_l': 8.25
        }
        
        # Update solver to accept canonical quantities
        result = self.solver._test_per_case_discount(
            line_data['quantity_each'], 
            line_data['unit_price'],
            line_data['line_total'],
            line_data['expected_price']
        )
        
        assert result['residual_pennies'] <= 50  # Within tolerance
    
    def test_per_litre_discount_hypothesis(self):
        """Test per-litre discount calculation"""
        line_data = {
            'quantity_each': 12.0,
            'quantity_l': 3.3,      # 12 x 275ml
            'unit_price': 2.0,
            'line_total': 20.7,     # £24 - £3.30 = £20.70 (£1 per litre)
            'expected_price': 2.0
        }
        
        result = self.solver._test_per_litre_discount(
            line_data['quantity_l'],
            line_data['unit_price'], 
            line_data['line_total'],
            line_data['expected_price']
        )
        
        assert result['residual_pennies'] <= 50  # Within tolerance
    
    def test_no_discount_case(self):
        """Test case where no discount is applied"""
        line_data = {
            'quantity_each': 1.0,
            'unit_price': 10.0,
            'line_total': 10.0,  # No discount
            'expected_price': 10.0
        }
        
        result = self.solver.solve_discount(line_data)
        
        # Should return None for no discount case
        assert result is None
    
    def test_invalid_input_handling(self):
        """Test handling of invalid inputs"""
        # Zero quantity
        result = self.solver.solve_discount({
            'quantity_each': 0,
            'unit_price': 10.0,
            'line_total': 5.0
        })
        assert result['error'] == 'invalid_input'
        
        # Negative price
        result = self.solver.solve_discount({
            'quantity_each': 1.0,
            'unit_price': -5.0,
            'line_total': 5.0
        })
        assert result['error'] == 'invalid_input'

import pytest
import json
from pathlib import Path

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

def test_discount_solver_exists():
    """Test that discount solver class exists and can be instantiated"""
    from backend.engine.discount_solver import DiscountSolver
    
    solver = DiscountSolver()
    assert solver is not None
    assert hasattr(solver, 'solve_discount')
    assert callable(solver.solve_discount)

if __name__ == "__main__":
    pytest.main([__file__]) 