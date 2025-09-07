#!/usr/bin/env python3
"""
Simple test to verify basic functionality
"""

import sys
import os
import tempfile
import sqlite3
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_basic_functionality():
    """Test basic functionality without complex migrations"""
    print("🧪 Testing basic functionality...")
    
    # Test 1: Import modules
    try:
        from normalization.units import canonical_quantities
        print("✅ Units normalization imported")
    except ImportError as e:
        print(f"❌ Units normalization import failed: {e}")
        return False
    
    try:
        from engine.discount_solver import get_discount_solver
        print("✅ Discount solver imported")
    except ImportError as e:
        print(f"❌ Discount solver import failed: {e}")
        return False
    
    try:
        from engine.verdicts import get_verdict_engine, VerdictContext
        print("✅ Verdict engine imported")
    except ImportError as e:
        print(f"❌ Verdict engine import failed: {e}")
        return False
    
    # Test 2: Basic functionality
    try:
        # Test canonical quantities
        result = canonical_quantities(24, "24x330ml cans")
        assert result["quantity_each"] == 24
        assert result["quantity_ml"] == 7920  # 24 * 330
        print("✅ Canonical quantities working")
    except Exception as e:
        print(f"❌ Canonical quantities failed: {e}")
        return False
    
    try:
        # Test discount solver
        solver = get_discount_solver()
        result = solver.solve_discount(1.0, 60.55, 32.22)
        assert result is not None
        assert result.kind == "percent"
        print("✅ Discount solver working")
    except Exception as e:
        print(f"❌ Discount solver failed: {e}")
        return False
    
    try:
        # Test verdict engine
        engine = get_verdict_engine()
        context = VerdictContext(off_contract_discount=True)
        verdict = engine.assign_verdict(context)
        assert verdict.value == "off_contract_discount"
        print("✅ Verdict engine working")
    except Exception as e:
        print(f"❌ Verdict engine failed: {e}")
        return False
    
    print("🎉 All basic functionality tests passed!")
    return True

if __name__ == "__main__":
    success = test_basic_functionality()
    sys.exit(0 if success else 1) 