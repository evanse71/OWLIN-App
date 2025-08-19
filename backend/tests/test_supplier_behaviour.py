import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from uuid import UUID, uuid4
import sqlite3
import tempfile
import os

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.supplier_behaviour_service import (
    log_event, list_events, recalculate_insights, get_insights, list_alerts,
    _ensure_tables, _get_supplier_name, _calculate_missed_delivery_rate,
    _calculate_mismatch_rate, _calculate_price_spike_rate, _calculate_trend
)
from contracts import (
    SupplierEventRequest, SupplierEventResponse, SupplierEventsResponse,
    SupplierInsightsResponse, SupplierAlertsResponse
)


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    # Create tables and sample data
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create suppliers table
    cursor.execute("""
        CREATE TABLE suppliers (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL
        )
    """)
    
    # Create invoices table
    cursor.execute("""
        CREATE TABLE invoices (
            id TEXT PRIMARY KEY,
            supplier_name TEXT,
            invoice_date TEXT,
            total_amount REAL,
            status TEXT
        )
    """)
    
    # Create audit_log table
    cursor.execute("""
        CREATE TABLE audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            action TEXT,
            entity_type TEXT,
            entity_id TEXT,
            timestamp TEXT
        )
    """)
    
    # Insert sample data
    supplier_id = str(uuid4())
    supplier_name = "Test Supplier Ltd"
    
    cursor.execute("INSERT INTO suppliers (id, name) VALUES (?, ?)", (supplier_id, supplier_name))
    cursor.execute("INSERT INTO invoices (id, supplier_name, invoice_date, total_amount, status) VALUES (?, ?, ?, ?, ?)", 
                   (str(uuid4()), supplier_name, "2025-01-15", 1000.0, "matched"))
    
    conn.commit()
    conn.close()
    
    return db_path, supplier_id, supplier_name


@pytest.fixture
def sample_event_request():
    """Create a sample event request."""
    return SupplierEventRequest(
        supplier_id=UUID("00000000-0000-0000-0000-000000000001"),
        event_type="missed_delivery",
        severity="high",
        description="Delivery not received on agreed date",
        source="manual"
    )


@patch('services.supplier_behaviour_service.get_db_connection')
def test_log_event_success(mock_get_db_connection, temp_db, sample_event_request):
    """Test successful event logging."""
    db_path, supplier_id, supplier_name = temp_db
    
    # Mock database connection
    conn = sqlite3.connect(db_path)
    mock_get_db_connection.return_value = conn
    
    # Ensure tables exist first
    cursor = conn.cursor()
    _ensure_tables(cursor)
    conn.commit()
    
    # Test logging event
    result = log_event(sample_event_request, "test_user")
    
    # Verify result
    assert result.ok is True
    assert isinstance(result.event_id, UUID)
    assert result.created_at is not None
    
    # Verify event was stored by creating a new connection
    verify_conn = sqlite3.connect(db_path)
    verify_cursor = verify_conn.cursor()
    verify_cursor.execute("SELECT * FROM supplier_events WHERE supplier_id = ?", (str(sample_event_request.supplier_id),))
    rows = verify_cursor.fetchall()
    assert len(rows) == 1
    
    event_row = rows[0]
    assert event_row[2] == "missed_delivery"  # event_type
    assert event_row[3] == "high"  # severity
    assert event_row[4] == "Delivery not received on agreed date"  # description
    assert event_row[5] == "manual"  # source
    assert event_row[7] == "test_user"  # created_by
    
    verify_conn.close()
    conn.close()


@patch('services.supplier_behaviour_service.get_db_connection')
def test_list_events_success(mock_get_db_connection, temp_db):
    """Test listing events for a supplier."""
    db_path, supplier_id, supplier_name = temp_db
    
    # Mock database connection
    conn = sqlite3.connect(db_path)
    mock_get_db_connection.return_value = conn
    
    # Insert test events
    cursor = conn.cursor()
    _ensure_tables(cursor)
    
    event_id_1 = str(uuid4())
    event_id_2 = str(uuid4())
    
    cursor.execute("""
        INSERT INTO supplier_events 
        (id, supplier_id, event_type, severity, description, source, created_at, created_by, is_acknowledged)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (event_id_1, supplier_id, "missed_delivery", "high", "Test event 1", "manual", 
          datetime.utcnow().isoformat(), "test_user", False))
    
    cursor.execute("""
        INSERT INTO supplier_events 
        (id, supplier_id, event_type, severity, description, source, created_at, created_by, is_acknowledged)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (event_id_2, supplier_id, "invoice_mismatch", "medium", "Test event 2", "system", 
          datetime.utcnow().isoformat(), "test_user", True))
    
    conn.commit()
    
    # Test listing events
    result = list_events(supplier_id, limit=10)
    
    # Verify result
    assert result.supplier_id == UUID(supplier_id)
    assert len(result.events) == 2
    
    # Events should be ordered by created_at DESC
    assert result.events[0].id == UUID(event_id_2)  # More recent
    assert result.events[1].id == UUID(event_id_1)  # Less recent
    
    conn.close()


@patch('services.supplier_behaviour_service.get_db_connection')
def test_list_events_limit(mock_get_db_connection, temp_db):
    """Test that event listing respects the limit parameter."""
    db_path, supplier_id, supplier_name = temp_db
    
    # Mock database connection
    conn = sqlite3.connect(db_path)
    mock_get_db_connection.return_value = conn
    
    # Insert multiple test events
    cursor = conn.cursor()
    _ensure_tables(cursor)
    
    for i in range(5):
        event_id = str(uuid4())
        cursor.execute("""
            INSERT INTO supplier_events 
            (id, supplier_id, event_type, severity, description, source, created_at, created_by, is_acknowledged)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (event_id, supplier_id, "missed_delivery", "high", f"Test event {i}", "manual", 
              datetime.utcnow().isoformat(), "test_user", False))
    
    conn.commit()
    
    # Test with limit
    result = list_events(supplier_id, limit=3)
    
    # Verify result
    assert len(result.events) == 3
    
    conn.close()


@patch('services.supplier_behaviour_service.get_db_connection')
def test_recalculate_insights_success(mock_get_db_connection, temp_db):
    """Test insights recalculation."""
    db_path, supplier_id, supplier_name = temp_db
    
    # Mock database connection
    conn = sqlite3.connect(db_path)
    mock_get_db_connection.return_value = conn
    
    # Insert test events for insights calculation
    cursor = conn.cursor()
    _ensure_tables(cursor)
    
    # Add some events
    cursor.execute("""
        INSERT INTO supplier_events 
        (id, supplier_id, event_type, severity, description, source, created_at, created_by, is_acknowledged)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (str(uuid4()), supplier_id, "missed_delivery", "high", "Test missed delivery", "manual", 
          datetime.utcnow().isoformat(), "test_user", False))
    
    cursor.execute("""
        INSERT INTO supplier_events 
        (id, supplier_id, event_type, severity, description, source, created_at, created_by, is_acknowledged)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (str(uuid4()), supplier_id, "invoice_mismatch", "medium", "Test mismatch", "system", 
          datetime.utcnow().isoformat(), "test_user", False))
    
    conn.commit()
    
    # Test insights recalculation
    insights = recalculate_insights(supplier_id)
    
    # Verify insights were calculated and stored
    assert len(insights) > 0
    
    # Check that insights were stored in database
    verify_conn = sqlite3.connect(db_path)
    verify_cursor = verify_conn.cursor()
    verify_cursor.execute("SELECT * FROM supplier_insights WHERE supplier_id = ?", (supplier_id,))
    stored_insights = verify_cursor.fetchall()
    assert len(stored_insights) > 0
    
    verify_conn.close()
    conn.close()


@patch('services.supplier_behaviour_service.get_db_connection')
def test_get_insights_success(mock_get_db_connection, temp_db):
    """Test getting stored insights."""
    db_path, supplier_id, supplier_name = temp_db
    
    # Mock database connection
    conn = sqlite3.connect(db_path)
    mock_get_db_connection.return_value = conn
    
    # Insert test insights
    cursor = conn.cursor()
    _ensure_tables(cursor)
    
    insight_id = str(uuid4())
    cursor.execute("""
        INSERT INTO supplier_insights 
        (id, supplier_id, metric_name, metric_value, trend_direction, trend_percentage, period_days, last_updated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (insight_id, supplier_id, "Missed Deliveries %", 15.5, "up", 25.0, 90, 
          datetime.utcnow().isoformat()))
    
    conn.commit()
    
    # Test getting insights
    result = get_insights(supplier_id)
    
    # Verify result
    assert result.supplier_id == UUID(supplier_id)
    assert len(result.insights) == 1
    
    insight = result.insights[0]
    assert insight.metric_name == "Missed Deliveries %"
    assert insight.metric_value == 15.5
    assert insight.trend_direction == "up"
    assert insight.trend_percentage == 25.0
    assert insight.period_days == 90
    
    conn.close()


@patch('services.supplier_behaviour_service.get_db_connection')
def test_list_alerts_success(mock_get_db_connection, temp_db):
    """Test listing alerts."""
    db_path, supplier_id, supplier_name = temp_db
    
    # Mock database connection
    conn = sqlite3.connect(db_path)
    mock_get_db_connection.return_value = conn
    
    # Insert test events that should trigger alerts
    cursor = conn.cursor()
    _ensure_tables(cursor)
    
    # Add high severity events
    for i in range(3):
        cursor.execute("""
            INSERT INTO supplier_events 
            (id, supplier_id, event_type, severity, description, source, created_at, created_by, is_acknowledged)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (str(uuid4()), supplier_id, "missed_delivery", "high", f"High severity event {i}", "manual", 
              datetime.utcnow().isoformat(), "test_user", False))
    
    # Add missed delivery events
    for i in range(4):
        cursor.execute("""
            INSERT INTO supplier_events 
            (id, supplier_id, event_type, severity, description, source, created_at, created_by, is_acknowledged)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (str(uuid4()), supplier_id, "missed_delivery", "medium", f"Missed delivery {i}", "manual", 
              datetime.utcnow().isoformat(), "test_user", False))
    
    conn.commit()
    
    # Test listing alerts
    result = list_alerts()
    
    # Verify result
    assert len(result.alerts) > 0
    
    # Check that we have alerts for our supplier
    supplier_alerts = [alert for alert in result.alerts if alert.supplier_id == UUID(supplier_id)]
    assert len(supplier_alerts) > 0
    
    conn.close()


def test_calculate_missed_delivery_rate(temp_db):
    """Test missed delivery rate calculation."""
    db_path, supplier_id, supplier_name = temp_db
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    _ensure_tables(cursor)
    
    # Add test events
    cursor.execute("""
        INSERT INTO supplier_events 
        (id, supplier_id, event_type, severity, description, source, created_at, created_by, is_acknowledged)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (str(uuid4()), supplier_id, "missed_delivery", "high", "Missed delivery", "manual", 
          datetime.utcnow().isoformat(), "test_user", False))
    
    cursor.execute("""
        INSERT INTO supplier_events 
        (id, supplier_id, event_type, severity, description, source, created_at, created_by, is_acknowledged)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (str(uuid4()), supplier_id, "late_delivery", "medium", "Late delivery", "manual", 
          datetime.utcnow().isoformat(), "test_user", False))
    
    conn.commit()
    
    # Test calculation
    rate = _calculate_missed_delivery_rate(cursor, supplier_id, 90)
    
    # Should be 50% (1 missed out of 2 total delivery events)
    assert rate == 50.0
    
    conn.close()


def test_calculate_trend(temp_db):
    """Test trend calculation."""
    db_path, supplier_id, supplier_name = temp_db
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    _ensure_tables(cursor)
    
    # Add previous insight
    cursor.execute("""
        INSERT INTO supplier_insights 
        (id, supplier_id, metric_name, metric_value, trend_direction, trend_percentage, period_days, last_updated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (str(uuid4()), supplier_id, "missed_delivery_rate", 10.0, "flat", 0.0, 90, 
          datetime.utcnow().isoformat()))
    
    conn.commit()
    
    # Test trend calculation
    trend = _calculate_trend(cursor, supplier_id, "missed_delivery_rate", 15.0, 90)
    
    # Should show upward trend
    assert trend["direction"] == "up"
    assert trend["percentage"] == 50.0  # 50% increase from 10 to 15
    
    conn.close()


def test_ensure_tables(temp_db):
    """Test that tables are created correctly."""
    db_path, supplier_id, supplier_name = temp_db
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Test table creation
    _ensure_tables(cursor)
    
    # Verify tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='supplier_events'")
    assert cursor.fetchone() is not None
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='supplier_insights'")
    assert cursor.fetchone() is not None
    
    # Verify indexes exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_supplier_events_sup_type'")
    assert cursor.fetchone() is not None
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_supplier_events_created'")
    assert cursor.fetchone() is not None
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_supplier_insights_sup_updated'")
    assert cursor.fetchone() is not None
    
    conn.close()


def test_get_supplier_name(temp_db):
    """Test supplier name retrieval."""
    db_path, supplier_id, supplier_name = temp_db
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Test getting supplier name
    name = _get_supplier_name(cursor, supplier_id)
    assert name == supplier_name
    
    # Test with non-existent supplier - should fall back to invoices table
    name = _get_supplier_name(cursor, "non-existent-id")
    assert name == supplier_name  # Falls back to invoices table
    
    conn.close()


def test_log_event_invalid_data(temp_db):
    """Test event logging with invalid data."""
    db_path, supplier_id, supplier_name = temp_db
    
    # Test with invalid event type (should be handled by Pydantic validation)
    with pytest.raises(ValueError):
        invalid_request = SupplierEventRequest(
            supplier_id=UUID("00000000-0000-0000-0000-000000000001"),
            event_type="invalid_type",  # This should fail Pydantic validation
            severity="high",
            description="Test",
            source="manual"
        )


@patch('services.supplier_behaviour_service.get_db_connection')
def test_list_events_empty(mock_get_db_connection, temp_db):
    """Test listing events when none exist."""
    db_path, supplier_id, supplier_name = temp_db
    
    # Mock database connection
    conn = sqlite3.connect(db_path)
    mock_get_db_connection.return_value = conn
    
    # Test listing events for supplier with no events
    result = list_events(supplier_id, limit=10)
    
    # Verify result
    assert result.supplier_id == UUID(supplier_id)
    assert len(result.events) == 0
    
    conn.close()


def test_calculate_mismatch_rate_no_events(temp_db):
    """Test mismatch rate calculation with no events."""
    db_path, supplier_id, supplier_name = temp_db
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    _ensure_tables(cursor)
    
    # Test calculation with no events
    rate = _calculate_mismatch_rate(cursor, supplier_id, 90)
    
    # Should be 0% when no events exist
    assert rate == 0.0
    
    conn.close()


def test_calculate_price_spike_rate_no_events(temp_db):
    """Test price spike rate calculation with no events."""
    db_path, supplier_id, supplier_name = temp_db
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    _ensure_tables(cursor)
    
    # Test calculation with no events
    rate = _calculate_price_spike_rate(cursor, supplier_id, 90)
    
    # Should be 0% when no events exist
    assert rate == 0.0
    
    conn.close() 