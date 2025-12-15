import sqlite3
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from backend.app.db import DB_PATH
from backend.main import app


@pytest.fixture
def test_db():
    """Set up test database with sample data."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    now = datetime.now().isoformat()

    cursor.execute(
        """
        INSERT INTO documents (id, filename, stored_path, size_bytes, uploaded_at, status, ocr_stage, ocr_confidence, sha256)
        VALUES ('test-doc-1', 'Test Invoice.pdf', NULL, 0, ?, 'completed', 'manual', 1.0, 'test-hash-1')
        """,
        (now,),
    )

    cursor.execute(
        """
        INSERT INTO invoices (id, doc_id, supplier, date, value, confidence, status, venue, issues_count, paired, created_at)
        VALUES ('test-inv-1', 'test-doc-1', 'Test Supplier', '2025-01-15', 100.0, 1.0, 'ready', 'Waterloo', 0, 0, ?)
        """,
        (now,),
    )

    cursor.execute(
        """
        INSERT INTO documents (id, filename, stored_path, size_bytes, uploaded_at, status, ocr_stage, ocr_confidence, sha256, supplier, delivery_no, doc_date, total, doc_type)
        VALUES ('test-dn-1', 'Test DN.pdf', NULL, 0, ?, 'completed', 'manual', 1.0, 'test-hash-2', 'Test Supplier', 'DN-001', '2025-01-15', 100.0, 'delivery_note')
        """,
        (now,),
    )

    cursor.execute(
        """
        INSERT INTO invoice_line_items (doc_id, invoice_id, line_number, description, qty, unit_price, total, uom, confidence, created_at)
        VALUES ('test-doc-1', 'test-inv-1', 1, 'Apples', 10, 2.5, 25.0, 'kg', 0.95, ?)
        """,
        (now,),
    )

    cursor.execute(
        """
        INSERT INTO invoice_line_items (doc_id, invoice_id, line_number, description, qty, unit_price, total, uom, confidence, created_at)
        VALUES ('test-dn-1', NULL, 1, 'Apples', 10, 2.5, 25.0, 'kg', 0.95, ?)
        """,
        (now,),
    )

    conn.commit()
    yield conn

    cursor.execute("DELETE FROM pairing_events WHERE invoice_id = 'test-inv-1'")
    cursor.execute("DELETE FROM invoice_line_items WHERE doc_id IN ('test-doc-1', 'test-dn-1')")
    cursor.execute("DELETE FROM invoices WHERE id = 'test-inv-1'")
    cursor.execute("DELETE FROM documents WHERE id IN ('test-doc-1', 'test-dn-1', 'test-dn-2')")
    conn.commit()
    conn.close()


def test_pairing_review_mode_returns_candidates(test_db):
    client = TestClient(app)
    response = client.get("/api/pairing/invoice/test-inv-1", params={"mode": "review"})
    assert response.status_code == 200
    data = response.json()
    assert data["invoice_id"] == "test-inv-1"
    assert isinstance(data["candidates"], list)
    assert data["candidates"], "Expected at least one candidate"
    assert data["candidates"][0]["delivery_note_id"] == "test-dn-1"


def test_evaluate_normal_mode_can_auto_pair(test_db):
    client = TestClient(app)
    response = client.get("/api/pairing/invoice/test-inv-1")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in {"auto_paired", "suggested", "unpaired"}
    if data["status"] == "auto_paired":
        # ensure DB updated
        cursor = test_db.cursor()
        cursor.execute("SELECT delivery_note_id FROM invoices WHERE id = 'test-inv-1'")
        assert cursor.fetchone()[0] == "test-dn-1"
    else:
        # even if not auto-paired, we should have stored confidence
        assert data["pairing_confidence"] is not None


def test_confirm_and_unpair_flow(test_db):
    client = TestClient(app)

    confirm_resp = client.post(
        "/api/pairing/invoice/test-inv-1/confirm",
        json={"delivery_note_id": "test-dn-1"},
    )
    assert confirm_resp.status_code == 200
    confirm_data = confirm_resp.json()
    assert confirm_data["pairing_status"] == "manual_paired"
    assert confirm_data["delivery_note_id"] == "test-dn-1"

    # verify DB link
    cursor = test_db.cursor()
    cursor.execute("SELECT invoice_id FROM documents WHERE id = 'test-dn-1'")
    assert cursor.fetchone()[0] == "test-inv-1"

    unpair_resp = client.post(
        "/api/pairing/invoice/test-inv-1/unpair",
        json={"actor_type": "user"},
    )
    assert unpair_resp.status_code == 200
    unpair_data = unpair_resp.json()
    assert unpair_data["delivery_note_id"] is None
    cursor.execute("SELECT invoice_id FROM documents WHERE id = 'test-dn-1'")
    assert cursor.fetchone()[0] is None


def test_reassign_pairing_flow(test_db):
    client = TestClient(app)
    # Insert a second delivery note
    now = datetime.now().isoformat()
    cursor = test_db.cursor()
    cursor.execute(
        """
        INSERT INTO documents (id, filename, stored_path, size_bytes, uploaded_at, status, ocr_stage, ocr_confidence, sha256, supplier, delivery_no, doc_date, total, doc_type)
        VALUES ('test-dn-2', 'Test DN 2.pdf', NULL, 0, ?, 'completed', 'manual', 0.9, 'test-hash-3', 'Test Supplier', 'DN-002', '2025-01-16', 100.0, 'delivery_note')
        """,
        (now,),
    )
    test_db.commit()

    client.post(
        "/api/pairing/invoice/test-inv-1/confirm",
        json={"delivery_note_id": "test-dn-1"},
    )

    reassign_resp = client.post(
        "/api/pairing/invoice/test-inv-1/reassign",
        json={"new_delivery_note_id": "test-dn-2"},
    )
    assert reassign_resp.status_code == 200
    reassign_data = reassign_resp.json()
    assert reassign_data["delivery_note_id"] == "test-dn-2"

    cursor.execute("SELECT invoice_id FROM documents WHERE id = 'test-dn-2'")
    assert cursor.fetchone()[0] == "test-inv-1"


def test_reject_endpoint_sets_status_unpaired(test_db):
    client = TestClient(app)
    resp = client.post(
        "/api/pairing/invoice/test-inv-1/reject",
        json={"delivery_note_id": "test-dn-1"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["pairing_status"] == "unpaired"
    assert data["pairing_confidence"] is None