import pytest
import tempfile
import base64
from pathlib import Path
from backend.types.parsed_invoice import InvoiceParsingPayload, ParsedInvoice, LineItem
from backend.ocr.validators import validate_invoice

def test_validate_invoice_clean():
    """Test validation with clean invoice data"""
    invoice = ParsedInvoice(
        supplier_name="Test Supplier",
        invoice_number="INV-001",
        invoice_date="2024-01-01",
        currency="GBP",
        subtotal=100.0,
        tax=20.0,
        total_amount=120.0,
        line_items=[
            LineItem(
                description="Item 1",
                quantity=2.0,
                unit="pcs",
                unit_price=50.0,
                line_total=100.0,
                page=1,
                row_idx=1,
                confidence=0.95
            )
        ],
        warnings=[],
        field_confidence={"supplier_name": 0.93},
        raw_extraction={}
    )
    
    validated = validate_invoice(invoice)
    assert len(validated.warnings) == 0

def test_validate_invoice_totals_mismatch():
    """Test validation with totals mismatch"""
    invoice = ParsedInvoice(
        supplier_name="Test Supplier",
        invoice_number="INV-001",
        invoice_date="2024-01-01",
        currency="GBP",
        subtotal=100.0,
        tax=20.0,
        total_amount=150.0,  # Should be 120.0
        line_items=[
            LineItem(
                description="Item 1",
                quantity=2.0,
                unit="pcs",
                unit_price=50.0,
                line_total=100.0,
                page=1,
                row_idx=1,
                confidence=0.95
            )
        ],
        warnings=[],
        field_confidence={"supplier_name": 0.93},
        raw_extraction={}
    )
    
    validated = validate_invoice(invoice)
    assert len(validated.warnings) > 0
    assert any("Totals mismatch" in warning for warning in validated.warnings)

def test_validate_invoice_suspicious_quantity():
    """Test validation with suspicious quantity"""
    invoice = ParsedInvoice(
        supplier_name="Test Supplier",
        invoice_number="INV-001",
        invoice_date="2024-01-01",
        currency="GBP",
        subtotal=1000000.0,
        tax=0.0,
        total_amount=1000000.0,
        line_items=[
            LineItem(
                description="Item 1",
                quantity=1000000.0,
                unit="pcs",
                unit_price=1.0,
                line_total=1000000.0,
                page=1,
                row_idx=1,
                confidence=0.95
            )
        ],
        warnings=[],
        field_confidence={"supplier_name": 0.93},
        raw_extraction={}
    )
    
    validated = validate_invoice(invoice)
    assert len(validated.warnings) > 0
    assert any("Suspicious quantity" in warning for warning in validated.warnings)

def test_line_item_structure():
    """Test LineItem structure"""
    item = LineItem(
        description="Test Item",
        quantity=2.0,
        unit="kg",
        unit_price=10.0,
        line_total=20.0,
        page=1,
        row_idx=1,
        confidence=0.9
    )
    
    assert item.description == "Test Item"
    assert item.quantity == 2.0
    assert item.unit == "kg"
    assert item.unit_price == 10.0
    assert item.line_total == 20.0
    assert item.page == 1
    assert item.row_idx == 1
    assert item.confidence == 0.9 