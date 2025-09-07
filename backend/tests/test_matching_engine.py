"""
Test matching engine functionality.
"""

import pytest
import os
import sys
import json
from datetime import datetime, timedelta

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.matching_service import compute_matching_pair, rebuild_matching, get_matching_summary
from services.matching_config import get_matching_config, normalize_uom, convert_quantity
from contracts import MatchReason

class TestMatchingConfig:
    def test_get_matching_config(self):
        """Test that matching config returns expected structure."""
        config = get_matching_config()
        assert hasattr(config, 'date_window_days')
        assert hasattr(config, 'amount_proximity_pct')
        assert hasattr(config, 'qty_tol_rel')
        assert hasattr(config, 'price_tol_rel')
        assert hasattr(config, 'fuzzy_desc_threshold')

    def test_normalize_uom(self):
        """Test UOM normalization."""
        assert normalize_uom('kg') == 'kg'
        assert normalize_uom('KILO') == 'kg'
        assert normalize_uom('each') == 'each'
        assert normalize_uom('EA') == 'each'
        assert normalize_uom('') == 'each'
        assert normalize_uom(None) == 'each'

    def test_convert_quantity(self):
        """Test quantity conversion."""
        assert convert_quantity(1, 'case', 'each') == 24.0
        assert convert_quantity(24, 'each', 'case') == 1.0
        assert convert_quantity(1, 'kg', 'g') == 1000.0
        assert convert_quantity(1000, 'g', 'kg') == 1.0
        assert convert_quantity(1, 'each', 'each') == 1.0
        assert convert_quantity(1, 'unknown', 'each') == 1.0

class TestMatchingService:
    def test_get_matching_summary_empty(self):
        """Test getting matching summary when no pairs exist."""
        summary = get_matching_summary()
        assert summary.totals == {}
        assert summary.pairs == []

    def test_rebuild_matching_no_data(self):
        """Test rebuilding matching with no data."""
        result = rebuild_matching(days=1)
        assert result['pairs_created'] == 0
        assert result['invoices_processed'] >= 0
        assert result['date_window_days'] == 1

class TestMatchReason:
    def test_match_reason_creation(self):
        """Test creating match reasons."""
        reason = MatchReason(
            code="TEST_MATCH",
            detail="Test matching reason",
            weight=10.0
        )
        assert reason.code == "TEST_MATCH"
        assert reason.detail == "Test matching reason"
        assert reason.weight == 10.0

if __name__ == "__main__":
    pytest.main([__file__]) 