"""
Tests for Delivery Matching System

Tests the confidence scoring algorithm, matching endpoints, and edge cases.
"""

import pytest
import sqlite3
import tempfile
import os
import json
from datetime import datetime, timedelta
from uuid import uuid4

# Add project root to path for imports
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.delivery_matching import (
    calculate_confidence, find_candidates, confirm_match, reject_match, retry_late_uploads,
    _calculate_supplier_score, _calculate_date_score, _calculate_line_items_score, _calculate_value_score
)

@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    db_fd, db_path = tempfile.mkstemp()
    
    # Create database schema
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create invoices table
    cursor.execute("""
        CREATE TABLE invoices (
            id TEXT PRIMARY KEY,
            supplier_name TEXT,
            invoice_date TEXT,
            total_amount REAL,
            line_items TEXT,
            status TEXT DEFAULT 'scanned',
            confidence REAL
        )
    """)
    
    # Create delivery_notes table
    cursor.execute("""
        CREATE TABLE delivery_notes (
            id TEXT PRIMARY KEY,
            supplier_name TEXT,
            delivery_date TEXT,
            total_amount REAL,
            line_items TEXT,
            status TEXT DEFAULT 'parsed',
            confidence REAL
        )
    """)
    
    # Create invoice_delivery_pairs table
    cursor.execute("""
        CREATE TABLE invoice_delivery_pairs (
            id TEXT PRIMARY KEY,
            invoice_id TEXT NOT NULL,
            delivery_note_id TEXT NOT NULL,
            confidence_score REAL NOT NULL,
            breakdown_supplier REAL NOT NULL,
            breakdown_date REAL NOT NULL,
            breakdown_line_items REAL NOT NULL,
            breakdown_value REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            confirmed_by TEXT,
            confirmed_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(invoice_id, delivery_note_id)
        )
    """)
    
    # Create matching_history table
    cursor.execute("""
        CREATE TABLE matching_history (
            id TEXT PRIMARY KEY,
            invoice_id TEXT NOT NULL,
            delivery_note_id TEXT NOT NULL,
            action TEXT NOT NULL,
            confidence_score REAL NOT NULL,
            breakdown_supplier REAL NOT NULL,
            breakdown_date REAL NOT NULL,
            breakdown_line_items REAL NOT NULL,
            breakdown_value REAL NOT NULL,
            actor_role TEXT,
            notes TEXT,
            created_at TEXT NOT NULL
        )
    """)
    
    # Create unmatched_delivery_notes table
    cursor.execute("""
        CREATE TABLE unmatched_delivery_notes (
            id TEXT PRIMARY KEY,
            delivery_note_id TEXT NOT NULL,
            supplier_name TEXT,
            delivery_date TEXT,
            total_amount REAL,
            line_items_count INTEGER,
            created_at TEXT NOT NULL,
            matched_at TEXT,
            UNIQUE(delivery_note_id)
        )
    """)
    
    conn.commit()
    conn.close()
    
    # Store the path for the service to use
    original_db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "owlin.db")
    
    # Monkey patch the database path
    import services.delivery_matching as dm
    dm.get_db_connection = lambda: sqlite3.connect(db_path)
    
    yield db_path
    
    # Cleanup
    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture
def sample_data(temp_db):
    """Insert sample data for testing"""
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    
    # Sample invoice
    invoice_id = str(uuid4())
    invoice_line_items = json.dumps([
        {"description": "Heineken Lager 24x330ml", "qty": 10, "unit_price": 2400, "total": 24000},
        {"description": "Corona Extra 24x330ml", "qty": 5, "unit_price": 2800, "total": 14000}
    ])
    
    cursor.execute("""
        INSERT INTO invoices (id, supplier_name, invoice_date, total_amount, line_items, status)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (invoice_id, "Heineken UK", "2025-01-15", 38000, invoice_line_items, "scanned"))
    
    # Sample delivery note - exact match
    delivery_id_1 = str(uuid4())
    delivery_line_items_1 = json.dumps([
        {"description": "Heineken Lager 24x330ml", "qty": 10, "unit_price": 2400, "total": 24000},
        {"description": "Corona Extra 24x330ml", "qty": 5, "unit_price": 2800, "total": 14000}
    ])
    
    cursor.execute("""
        INSERT INTO delivery_notes (id, supplier_name, delivery_date, total_amount, line_items, status)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (delivery_id_1, "Heineken UK", "2025-01-15", 38000, delivery_line_items_1, "parsed"))
    
    # Sample delivery note - partial match
    delivery_id_2 = str(uuid4())
    delivery_line_items_2 = json.dumps([
        {"description": "Heineken Lager 24x330ml", "qty": 10, "unit_price": 2400, "total": 24000},
        {"description": "Budweiser 24x330ml", "qty": 5, "unit_price": 2200, "total": 11000}
    ])
    
    cursor.execute("""
        INSERT INTO delivery_notes (id, supplier_name, delivery_date, total_amount, line_items, status)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (delivery_id_2, "Heineken UK", "2025-01-16", 35000, delivery_line_items_2, "parsed"))
    
    # Sample delivery note - no match
    delivery_id_3 = str(uuid4())
    delivery_line_items_3 = json.dumps([
        {"description": "Carlsberg Pilsner 24x330ml", "qty": 8, "unit_price": 2000, "total": 16000},
        {"description": "Stella Artois 24x330ml", "qty": 6, "unit_price": 2600, "total": 15600}
    ])
    
    cursor.execute("""
        INSERT INTO delivery_notes (id, supplier_name, delivery_date, total_amount, line_items, status)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (delivery_id_3, "Carlsberg UK", "2025-01-20", 31600, delivery_line_items_3, "parsed"))
    
    conn.commit()
    conn.close()
    
    return {
        "invoice_id": invoice_id,
        "delivery_id_1": delivery_id_1,
        "delivery_id_2": delivery_id_2,
        "delivery_id_3": delivery_id_3
    }

def test_exact_match_case(sample_data):
    """Test exact match case - same supplier, date, line items"""
    invoice_data = {
        "supplier_name": "Heineken UK",
        "invoice_date": "2025-01-15",
        "total_amount": 38000,
        "line_items": [
            {"description": "Heineken Lager 24x330ml", "qty": 10, "unit_price": 2400, "total": 24000},
            {"description": "Corona Extra 24x330ml", "qty": 5, "unit_price": 2800, "total": 14000}
        ]
    }
    
    delivery_data = {
        "supplier_name": "Heineken UK",
        "delivery_date": "2025-01-15",
        "total_amount": 38000,
        "items": [
            {"description": "Heineken Lager 24x330ml", "qty": 10, "unit_price": 2400, "total": 24000},
            {"description": "Corona Extra 24x330ml", "qty": 5, "unit_price": 2800, "total": 14000}
        ]
    }
    
    confidence, breakdown = calculate_confidence(invoice_data, delivery_data)
    
    # Should be very high confidence (close to 100%)
    assert confidence >= 95
    assert breakdown.supplier == 40  # Exact supplier match
    assert breakdown.date == 25      # Same date
    assert breakdown.line_items == 30  # All items match
    assert breakdown.value == 5      # Exact value match

def test_partial_date_offset(sample_data):
    """Test partial match with date offset"""
    invoice_data = {
        "supplier_name": "Heineken UK",
        "invoice_date": "2025-01-15",
        "total_amount": 38000,
        "line_items": [
            {"description": "Heineken Lager 24x330ml", "qty": 10, "unit_price": 2400, "total": 24000},
            {"description": "Corona Extra 24x330ml", "qty": 5, "unit_price": 2800, "total": 14000}
        ]
    }
    
    delivery_data = {
        "supplier_name": "Heineken UK",
        "delivery_date": "2025-01-16",  # +1 day
        "total_amount": 35000,  # Different total
        "items": [
            {"description": "Heineken Lager 24x330ml", "qty": 10, "unit_price": 2400, "total": 24000},
            {"description": "Budweiser 24x330ml", "qty": 5, "unit_price": 2200, "total": 11000}  # Different item
        ]
    }
    
    confidence, breakdown = calculate_confidence(invoice_data, delivery_data)
    
    # Should be medium-high confidence
    assert 60 <= confidence <= 85
    assert breakdown.supplier == 40  # Exact supplier match
    assert breakdown.date == 20      # ±1 day (80% of 25)
    assert breakdown.line_items == 15  # 50% of items match
    assert breakdown.value < 5       # Value mismatch

def test_value_mismatch(sample_data):
    """Test large value difference reduces score"""
    invoice_data = {
        "supplier_name": "Heineken UK",
        "invoice_date": "2025-01-15",
        "total_amount": 38000,
        "line_items": [
            {"description": "Heineken Lager 24x330ml", "qty": 10, "unit_price": 2400, "total": 24000}
        ]
    }
    
    delivery_data = {
        "supplier_name": "Heineken UK",
        "delivery_date": "2025-01-15",
        "total_amount": 20000,  # Large difference
        "items": [
            {"description": "Heineken Lager 24x330ml", "qty": 10, "unit_price": 2400, "total": 24000}
        ]
    }
    
    confidence, breakdown = calculate_confidence(invoice_data, delivery_data)
    
    # Should have high confidence but reduced value score
    assert confidence >= 70
    assert breakdown.supplier == 40
    assert breakdown.date == 25
    assert breakdown.line_items == 30
    assert breakdown.value == 0  # Large value difference

def test_low_confidence_unrelated(sample_data):
    """Test unrelated delivery note gets low score"""
    invoice_data = {
        "supplier_name": "Heineken UK",
        "invoice_date": "2025-01-15",
        "total_amount": 38000,
        "line_items": [
            {"description": "Heineken Lager 24x330ml", "qty": 10, "unit_price": 2400, "total": 24000}
        ]
    }
    
    delivery_data = {
        "supplier_name": "Carlsberg UK",  # Different supplier
        "delivery_date": "2025-01-20",    # Different date
        "total_amount": 31600,
        "items": [
            {"description": "Carlsberg Pilsner 24x330ml", "qty": 8, "unit_price": 2000, "total": 16000}
        ]
    }
    
    confidence, breakdown = calculate_confidence(invoice_data, delivery_data)
    
    # Should be low confidence
    assert confidence < 50
    assert breakdown.supplier == 0   # Different supplier
    assert breakdown.date == 0       # Different date
    assert breakdown.line_items == 0 # Different items
    assert breakdown.value < 5       # Different value

def test_find_candidates(sample_data):
    """Test finding candidates for an invoice"""
    candidates = find_candidates(sample_data["invoice_id"], min_confidence=30, limit=5)
    
    # Should find 2 candidates (exact and partial match)
    assert len(candidates) == 2
    
    # First candidate should be the exact match (higher confidence)
    assert candidates[0].confidence > candidates[1].confidence
    
    # Check that the exact match has high confidence
    assert candidates[0].confidence >= 90

def test_confirm_match(sample_data, temp_db):
    """Test confirming a match"""
    result = confirm_match(sample_data["invoice_id"], sample_data["delivery_id_1"], "test_user")
    
    assert result["status"] == "confirmed"
    assert result["confidence"] > 0
    
    # Check database was updated
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    
    cursor.execute("SELECT status FROM invoices WHERE id = ?", (sample_data["invoice_id"],))
    invoice_status = cursor.fetchone()[0]
    assert invoice_status == "matched"
    
    cursor.execute("SELECT status FROM delivery_notes WHERE id = ?", (sample_data["delivery_id_1"],))
    delivery_status = cursor.fetchone()[0]
    assert delivery_status == "matched"
    
    cursor.execute("SELECT status FROM invoice_delivery_pairs WHERE invoice_id = ? AND delivery_note_id = ?", 
                   (sample_data["invoice_id"], sample_data["delivery_id_1"]))
    pair_status = cursor.fetchone()[0]
    assert pair_status == "confirmed"
    
    conn.close()

def test_reject_match(sample_data, temp_db):
    """Test rejecting a match"""
    result = reject_match(sample_data["invoice_id"], sample_data["delivery_id_2"], "test_user", "Test rejection")
    
    assert result["status"] == "rejected"
    
    # Check rejection was recorded in history
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    
    cursor.execute("SELECT action FROM matching_history WHERE invoice_id = ? AND delivery_note_id = ?", 
                   (sample_data["invoice_id"], sample_data["delivery_id_2"]))
    history_action = cursor.fetchone()[0]
    assert history_action == "rejected"
    
    conn.close()

def test_retry_late_uploads(sample_data):
    """Test retry late uploads functionality"""
    # First, confirm one match to reduce unmatched count
    confirm_match(sample_data["invoice_id"], sample_data["delivery_id_1"], "test_user")
    
    # Run retry
    result = retry_late_uploads()
    
    assert "new_matches_found" in result
    assert "message" in result
    
    # Should find the remaining partial match if it meets high confidence threshold
    # (This depends on the exact confidence calculation)

def test_supplier_name_normalization():
    """Test supplier name normalization"""
    # Exact match
    assert _calculate_supplier_score("Heineken UK", "Heineken UK") == 40
    
    # Case insensitive
    assert _calculate_supplier_score("Heineken UK", "heineken uk") == 40
    
    # With common suffixes
    assert _calculate_supplier_score("Heineken UK Ltd", "Heineken UK") == 40
    assert _calculate_supplier_score("Heineken UK", "Heineken UK Limited") == 40
    
    # Partial match
    score = _calculate_supplier_score("Heineken UK", "Heineken")
    assert 0 < score < 40
    
    # No match
    assert _calculate_supplier_score("Heineken UK", "Carlsberg UK") == 0

def test_date_proximity_scoring():
    """Test date proximity scoring"""
    # Same date
    assert _calculate_date_score("2025-01-15", "2025-01-15") == 25
    
    # ±1 day
    assert _calculate_date_score("2025-01-15", "2025-01-16") == 20
    assert _calculate_date_score("2025-01-15", "2025-01-14") == 20
    
    # ±3 days
    assert _calculate_date_score("2025-01-15", "2025-01-18") == 10
    assert _calculate_date_score("2025-01-15", "2025-01-12") == 10
    
    # Far apart
    score = _calculate_date_score("2025-01-15", "2025-02-15")
    assert score < 10

def test_line_items_scoring():
    """Test line items overlap scoring"""
    invoice_items = [
        {"description": "Heineken Lager 24x330ml", "qty": 10},
        {"description": "Corona Extra 24x330ml", "qty": 5}
    ]
    
    delivery_items = [
        {"description": "Heineken Lager 24x330ml", "qty": 10},
        {"description": "Corona Extra 24x330ml", "qty": 5}
    ]
    
    # Perfect match
    score = _calculate_line_items_score(invoice_items, delivery_items)
    assert score == 30
    
    # Partial match
    delivery_items_partial = [
        {"description": "Heineken Lager 24x330ml", "qty": 10},
        {"description": "Budweiser 24x330ml", "qty": 5}
    ]
    
    score = _calculate_line_items_score(invoice_items, delivery_items_partial)
    assert score == 15  # 50% match
    
    # No match
    delivery_items_no_match = [
        {"description": "Carlsberg Pilsner 24x330ml", "qty": 8},
        {"description": "Stella Artois 24x330ml", "qty": 6}
    ]
    
    score = _calculate_line_items_score(invoice_items, delivery_items_no_match)
    assert score == 0

def test_value_scoring():
    """Test value match scoring"""
    # Exact match
    assert _calculate_value_score(38000, 38000) == 5
    
    # ±2%
    assert _calculate_value_score(38000, 38760) == 5  # +2%
    assert _calculate_value_score(38000, 37240) == 5  # -2%
    
    # ±5%
    score = _calculate_value_score(38000, 39900)  # +5%
    assert score == 2.5
    
    # ±10%
    score = _calculate_value_score(38000, 41800)  # +10%
    assert score == 1.25
    
    # Large difference
    score = _calculate_value_score(38000, 20000)
    assert score == 0

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 