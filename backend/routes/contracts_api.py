from __future__ import annotations
from fastapi import APIRouter
from typing import List
from uuid import uuid4
from datetime import date, datetime
from backend.contracts import Invoice, LineItem, DeliveryNote, Supplier, User, FlaggedIssue

router = APIRouter(prefix="/api/contracts", tags=["contracts"])

# Marked logically deprecated for future cutover. FastAPI does not have direct @deprecated, but we can set in OpenAPI via include_in_schema flags if needed per-route metadata.


def _sample_line_item(idx: int) -> LineItem:
	return LineItem(
		id=uuid4(),
		description=f"Item {idx}",
		qty=1 + (idx % 3),
		unit_price_pennies=199,
		total_pennies=(1 + (idx % 3)) * 199,
		uom=None,
		sku=None,
	)


def _sample_invoice(n: int) -> Invoice:
	items = [_sample_line_item(i) for i in range(1, 4)]
	return Invoice(
		id=uuid4(),
		supplier_name=f"Supplier {n}",
		invoice_number=f"INV-{2024+n:04d}-{n:03d}",
		invoice_date=date(2024, 5, min(28, n)),
		total_amount_pennies=sum(i.total_pennies for i in items),
		vat_amount_pennies=0,
		currency="GBP",
		status="scanned",
		confidence=86,
		line_items=items,
		delivery_note_id=None,
	)


@router.get("/invoices", response_model=List[Invoice])
async def list_invoices_contracts():
	return [_sample_invoice(i) for i in range(1, 6)]


@router.get("/delivery-notes", response_model=List[DeliveryNote])
async def list_delivery_notes_contracts():
	return []


@router.get("/flagged-issues", response_model=List[FlaggedIssue])
async def list_flagged_issues_contracts():
	return []


@router.get("/suppliers", response_model=List[Supplier])
async def list_suppliers_contracts():
	return [Supplier(id=uuid4(), name="Acme Foods")]


@router.get("/users", response_model=List[User])
async def list_users_contracts():
	return [User(id=uuid4(), name="Demo User", role="GM")] 