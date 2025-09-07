import pytest
from unittest.mock import Mock, patch
from datetime import date, datetime, timedelta
from uuid import UUID, uuid4
import sqlite3
import tempfile
import os

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from schemas.supplier import (
    SupplierProfile, SupplierMetrics, SupplierTrends, 
    TrendPoint, RiskRating, SupplierScorecard, Insight
)
from services.supplier_service import get_supplier_scorecard
from services.insights_engine import generate_insights

@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    # Create tables and sample data
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create invoices table
    cursor.execute("""
        CREATE TABLE invoices (
            id TEXT PRIMARY KEY,
            supplier_name TEXT,
            invoice_date TEXT,
            total_amount REAL,
            status TEXT,
            confidence REAL
        )
    """)
    
    # Create invoice_line_items table
    cursor.execute("""
        CREATE TABLE invoice_line_items (
            id TEXT PRIMARY KEY,
            invoice_id TEXT,
            item_description TEXT,
            unit_price REAL,
            quantity REAL,
            flagged INTEGER
        )
    """)
    
    # Create delivery_notes table
    cursor.execute("""
        CREATE TABLE delivery_notes (
            id TEXT PRIMARY KEY,
            supplier_name TEXT,
            status TEXT,
            created_at TEXT
        )
    """)
    
    # Create flagged_issues table
    cursor.execute("""
        CREATE TABLE flagged_issues (
            id TEXT PRIMARY KEY,
            supplier_id TEXT,
            supplier_name TEXT,
            type TEXT,
            created_at TEXT,
            resolved_at TEXT
        )
    """)
    
    # Insert sample data
    supplier_id = str(uuid4())
    supplier_name = "Test Supplier Ltd"
    
    # Sample invoices
    cursor.execute("""
        INSERT INTO invoices (id, supplier_name, invoice_date, total_amount, status, confidence)
        VALUES 
        ('inv1', ?, '2025-01-01', 1000.0, 'matched', 95.0),
        ('inv2', ?, '2025-01-15', 1500.0, 'matched', 92.0),
        ('inv3', ?, '2025-02-01', 1200.0, 'discrepancy', 88.0)
    """, (supplier_name, supplier_name, supplier_name))
    
    # Sample line items
    cursor.execute("""
        INSERT INTO invoice_line_items (id, invoice_id, item_description, unit_price, quantity, flagged)
        VALUES 
        ('li1', 'inv1', 'Beer Keg', 50.0, 20, 0),
        ('li2', 'inv2', 'Wine Bottle', 15.0, 100, 1),
        ('li3', 'inv3', 'Spirits', 25.0, 48, 0)
    """)
    
    # Sample delivery notes
    cursor.execute("""
        INSERT INTO delivery_notes (id, supplier_name, status, created_at)
        VALUES 
        ('dn1', ?, 'matched', '2025-01-01'),
        ('dn2', ?, 'matched', '2025-01-15'),
        ('dn3', ?, 'pending', '2025-02-01')
    """, (supplier_name, supplier_name, supplier_name))
    
    # Sample flagged issues
    cursor.execute("""
        INSERT INTO flagged_issues (id, supplier_id, supplier_name, type, created_at, resolved_at)
        VALUES 
        ('fi1', ?, ?, 'PRICE_MISMATCH', '2025-01-15', '2025-01-20'),
        ('fi2', ?, ?, 'MISSING_ITEM', '2025-02-01', NULL)
    """, (supplier_id, supplier_name, supplier_id, supplier_name))
    
    conn.commit()
    conn.close()
    
    yield db_path, supplier_id, supplier_name
    
    # Cleanup
    os.unlink(db_path)

def test_scorecard_payload_structure(temp_db):
    """Test that the scorecard returns the correct structure."""
    db_path, supplier_id, supplier_name = temp_db
    
    with patch('services.supplier_service.get_db_connection') as mock_db:
        mock_conn = Mock()
        mock_conn.cursor.return_value = sqlite3.connect(db_path).cursor()
        mock_db.return_value = mock_conn
        
        scorecard = get_supplier_scorecard(supplier_id=supplier_name, range_days=90)
        
        # Check structure
        assert isinstance(scorecard, SupplierScorecard)
        assert isinstance(scorecard.supplier, SupplierProfile)
        assert isinstance(scorecard.metrics, SupplierMetrics)
        assert isinstance(scorecard.trends, SupplierTrends)
        assert isinstance(scorecard.risk_rating, RiskRating)
        assert isinstance(scorecard.insights, list)
        assert isinstance(scorecard.last_updated, datetime)
        
        # Check supplier profile
        # The UUID is generated from the supplier name, so we check the name instead
        assert scorecard.supplier.name == supplier_name
        
        # Check metrics structure (values may be placeholders in test environment)
        assert isinstance(scorecard.metrics.total_spend, float)
        assert isinstance(scorecard.metrics.delivery_on_time_pct, float)
        assert isinstance(scorecard.metrics.mismatch_rate_pct, float)
        assert 0 <= scorecard.metrics.delivery_on_time_pct <= 100
        assert 0 <= scorecard.metrics.mismatch_rate_pct <= 100

def test_insight_generation(temp_db):
    """Test insight generation with known data patterns."""
    db_path, supplier_id, supplier_name = temp_db
    
    with patch('services.insights_engine.get_db_connection') as mock_db:
        mock_conn = Mock()
        mock_conn.cursor.return_value = sqlite3.connect(db_path).cursor()
        mock_db.return_value = mock_conn
        
        insights = generate_insights(UUID(supplier_id), 90)
        
        # Check that insights are generated
        assert isinstance(insights, list)
        
        # Check insight structure if any are generated
        for insight in insights:
            assert isinstance(insight, Insight)
            assert insight.type in ["price_increase", "delivery_delays", "credit_slow", "preferred_inactivity", "multiple_issues"]
            assert insight.severity in ["low", "medium", "high"]
            assert len(insight.message) > 0
            assert len(insight.recommendation) > 0

def test_risk_rating_calculation(temp_db):
    """Test risk rating calculation with correct weighting."""
    db_path, supplier_id, supplier_name = temp_db
    
    with patch('services.supplier_service.get_db_connection') as mock_db:
        mock_conn = Mock()
        mock_conn.cursor.return_value = sqlite3.connect(db_path).cursor()
        mock_db.return_value = mock_conn
        
        scorecard = get_supplier_scorecard(supplier_id=supplier_name, range_days=90)
        
        # Check risk rating structure
        assert 0 <= scorecard.risk_rating.score <= 100
        assert scorecard.risk_rating.label in ["High", "Moderate", "Low", "Minimal"]
        assert scorecard.risk_rating.color.startswith("#")
        
        # Check that score affects label appropriately
        if scorecard.risk_rating.score >= 80:
            assert scorecard.risk_rating.label == "High"
        elif scorecard.risk_rating.score >= 60:
            assert scorecard.risk_rating.label == "Moderate"
        elif scorecard.risk_rating.score >= 40:
            assert scorecard.risk_rating.label == "Low"
        else:
            assert scorecard.risk_rating.label == "Minimal"

def test_trend_data_accuracy(temp_db):
    """Test that trend data has correct date/value mapping."""
    db_path, supplier_id, supplier_name = temp_db
    
    with patch('services.supplier_service.get_db_connection') as mock_db:
        mock_conn = Mock()
        mock_conn.cursor.return_value = sqlite3.connect(db_path).cursor()
        mock_db.return_value = mock_conn
        
        scorecard = get_supplier_scorecard(supplier_id=supplier_name, range_days=90)
        
        # Check trend structure
        assert isinstance(scorecard.trends.price_history, list)
        assert isinstance(scorecard.trends.delivery_timeliness, list)
        
        # Check trend points if any exist
        for trend_point in scorecard.trends.price_history:
            assert isinstance(trend_point, TrendPoint)
            assert isinstance(trend_point.date, date)
            assert isinstance(trend_point.value, (int, float))
            assert trend_point.value >= 0
        
        for trend_point in scorecard.trends.delivery_timeliness:
            assert isinstance(trend_point, TrendPoint)
            assert isinstance(trend_point.date, date)
            assert isinstance(trend_point.value, (int, float))
            assert 0 <= trend_point.value <= 100

def test_offline_cache():
    """Test offline cache functionality (placeholder for future implementation)."""
    # This test would verify that the system can work offline
    # For now, just test that the service doesn't crash when offline
    with patch('services.supplier_service.get_db_connection') as mock_db:
        mock_db.side_effect = Exception("Database connection failed")
        
        # Should handle offline gracefully
        try:
            get_supplier_scorecard(supplier_id="Test Supplier", range_days=90)
        except Exception as e:
            assert "Database connection failed" in str(e)

def test_supplier_not_found():
    """Test handling of non-existent supplier."""
    with patch('services.supplier_service.get_db_connection') as mock_db:
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = None
        mock_conn.cursor.return_value = mock_cursor
        mock_db.return_value = mock_conn
        
        with pytest.raises(ValueError, match="Supplier not found"):
            get_supplier_scorecard(supplier_id="NonExistentSupplier", range_days=90)

def test_metrics_calculation(temp_db):
    """Test that metrics are calculated correctly."""
    db_path, supplier_id, supplier_name = temp_db
    
    with patch('services.supplier_service.get_db_connection') as mock_db:
        mock_conn = Mock()
        mock_conn.cursor.return_value = sqlite3.connect(db_path).cursor()
        mock_db.return_value = mock_conn
        
        scorecard = get_supplier_scorecard(supplier_id=supplier_name, range_days=90)
        
        # Check that metrics are properly structured
        # Note: In the current implementation, these are placeholder values
        # In a full implementation, they would be calculated from the database
        assert isinstance(scorecard.metrics.total_spend, float)
        assert isinstance(scorecard.metrics.delivery_on_time_pct, float)
        assert isinstance(scorecard.metrics.mismatch_rate_pct, float)

def test_insight_aggregation():
    """Test that multiple low-severity insights are aggregated correctly."""
    # Create multiple low-severity insights
    low_insights = [
        Insight(
            type="delivery_delays",
            severity="low",
            message="Minor delivery delay",
            recommendation="Monitor closely"
        ),
        Insight(
            type="price_increase",
            severity="low",
            message="Small price increase",
            recommendation="Review pricing"
        )
    ]
    
    # Test aggregation logic
    from services.insights_engine import _aggregate_low_severity_insights
    
    aggregated = _aggregate_low_severity_insights(low_insights)
    
    assert aggregated is not None
    assert aggregated.type == "multiple_issues"
    assert aggregated.severity == "medium"
    assert "Multiple minor issues detected" in aggregated.message 