from __future__ import annotations
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Path, Body
from pydantic import BaseModel, Field

try:
    # relative (installed as package)
    from ..db import fetch_all, fetch_one, execute, uuid_str
    from ..services.recompute import recompute_invoice_totals
except ImportError:
    try:
        # fallback if run from repo root
        from backend.db import fetch_all, fetch_one, execute, uuid_str
        from backend.services.recompute import recompute_invoice_totals
    except ImportError:
        # fallback if run from backend directory
        from db import fetch_all, fetch_one, execute, uuid_str
        from services.recompute import recompute_invoice_totals

router = APIRouter(prefix="/api/invoices", tags=["invoices"])


# ---------- Pydantic Schemas (v1 style) ----------
class LineItemDTO(BaseModel):
    id: str
    description: Optional[str] = None
    quantity: float = 0
    unit_price: float = 0
    total: float = 0
    uom: Optional[str] = None
    vat_rate: float = 0
    source: Optional[str] = None


class InvoiceDTO(BaseModel):
    id: str
    supplier: Optional[str] = None
    invoice_date: Optional[str] = None  # ISO date string
    status: str = "scanned"
    currency: Optional[str] = "GBP"
    total_value: Optional[float] = None
    pages: Optional[List[int]] = []
    page_count: Optional[int] = 0


class ApiListResponse(BaseModel):
    items: List[Any]
    total: Optional[int] = None


class CreateInvoiceRequest(BaseModel):
    supplier: str = Field(..., min_length=1)
    invoice_date: Optional[str] = None
    reference: Optional[str] = None
    currency: Optional[str] = "GBP"
    line_items: Optional[List["CreateLineItemRequest"]] = None  # forward ref


class CreateLineItemRequest(BaseModel):
    description: Optional[str] = None
    quantity: float = 0
    unit_price: float = 0
    uom: Optional[str] = None
    vat_rate: float = 0


class UpdateLineItemRequest(BaseModel):
    description: Optional[str] = None
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    uom: Optional[str] = None
    vat_rate: Optional[float] = None


CreateInvoiceRequest.update_forward_refs()


# ---------- Helpers ----------
def _row_to_invoice(row: Dict[str, Any]) -> InvoiceDTO:
    return InvoiceDTO(
        id=row["id"],
        supplier=row.get("supplier"),
        invoice_date=row.get("invoice_date"),
        status=row.get("status", "scanned"),
        currency=row.get("currency", "GBP"),
        total_value=row.get("total_value"),
        pages=[],
        page_count=row.get("page_count", 0),
    )


def _row_to_line_item(row: Dict[str, Any]) -> LineItemDTO:
    return LineItemDTO(
        id=row["id"],
        description=row.get("description"),
        quantity=row.get("quantity", 0) or 0,
        unit_price=row.get("unit_price", 0) or 0,
        total=row.get("total", 0) or 0,
        uom=row.get("uom"),
        vat_rate=row.get("vat_rate", 0) or 0,
        source=row.get("source"),
    )


# ---------- Endpoints ----------
@router.get("", response_model=ApiListResponse)
def list_invoices() -> ApiListResponse:
    rows = fetch_all("SELECT * FROM invoices ORDER BY created_at DESC")
    items = [_row_to_invoice(r) for r in rows]
    return ApiListResponse(items=items, total=len(items))


@router.get("/{invoice_id}", response_model=InvoiceDTO)
def get_invoice(invoice_id: str = Path(...)) -> InvoiceDTO:
    row = fetch_one("SELECT * FROM invoices WHERE id = ?", (invoice_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return _row_to_invoice(row)


@router.get("/{invoice_id}/line-items", response_model=ApiListResponse)
def get_invoice_line_items(invoice_id: str = Path(...)) -> ApiListResponse:
    inv = fetch_one("SELECT id FROM invoices WHERE id = ?", (invoice_id,))
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    rows = fetch_all("SELECT * FROM invoice_line_items WHERE invoice_id = ? ORDER BY row_no ASC", (invoice_id,))
    items = [_row_to_line_item(r) for r in rows]
    return ApiListResponse(items=items, total=len(items))


@router.post("/{invoice_id}/line-items", response_model=ApiListResponse)
def add_line_items(
    invoice_id: str,
    body: List[CreateLineItemRequest] = Body(...),
) -> ApiListResponse:
    inv = fetch_one("SELECT id FROM invoices WHERE id = ?", (invoice_id,))
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")

    for li in body:
        line_id = uuid_str()
        execute(
            """
            INSERT INTO invoice_line_items (id, invoice_id, description, quantity, unit_price, uom, vat_rate, total, source, row_no)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE((SELECT MAX(row_no)+1 FROM invoice_line_items WHERE invoice_id = ?), 1))
            """,
            (
                line_id,
                invoice_id,
                li.description,
                li.quantity,
                li.unit_price,
                li.uom,
                li.vat_rate,
                (li.quantity or 0) * (li.unit_price or 0),  # naive total
                "manual",
                invoice_id,
            ),
        )

    # recompute totals
    recompute_invoice_totals(invoice_id)

    rows = fetch_all("SELECT * FROM invoice_line_items WHERE invoice_id = ? ORDER BY row_no ASC", (invoice_id,))
    items = [_row_to_line_item(r) for r in rows]
    return ApiListResponse(items=items, total=len(items))


@router.put("/{invoice_id}/line-items/{line_id}", response_model=LineItemDTO)
def update_line_item(
    invoice_id: str,
    line_id: str,
    body: UpdateLineItemRequest = Body(...),
) -> LineItemDTO:
    exists = fetch_one("SELECT id FROM invoice_line_items WHERE id = ? AND invoice_id = ?", (line_id, invoice_id))
    if not exists:
        raise HTTPException(status_code=404, detail="Line item not found")

    # Build dynamic update
    fields = []
    params: list = []
    for k in ["description", "quantity", "unit_price", "uom", "vat_rate"]:
        v = getattr(body, k)
        if v is not None:
            fields.append(f"{k} = ?")
            params.append(v)
    if fields:
        params.extend([line_id, invoice_id])
        execute(f"UPDATE invoice_line_items SET {', '.join(fields)} WHERE id = ? AND invoice_id = ?", tuple(params))

    # recompute per-line total & invoice totals
    execute(
        "UPDATE invoice_line_items SET total = COALESCE(quantity,0)*COALESCE(unit_price,0) WHERE id = ?",
        (line_id,),
    )
    recompute_invoice_totals(invoice_id)

    row = fetch_one("SELECT * FROM invoice_line_items WHERE id = ?", (line_id,))
    return _row_to_line_item(row)


@router.delete("/{invoice_id}/line-items/{line_id}")
def delete_line_item(invoice_id: str, line_id: str) -> Dict[str, Any]:
    exists = fetch_one("SELECT id FROM invoice_line_items WHERE id = ? AND invoice_id = ?", (line_id, invoice_id))
    if not exists:
        raise HTTPException(status_code=404, detail="Line item not found")
    execute("DELETE FROM invoice_line_items WHERE id = ? AND invoice_id = ?", (line_id, invoice_id))
    recompute_invoice_totals(invoice_id)
    return {"ok": True}


@router.post("/{invoice_id}/rescan")
def rescan_invoice(invoice_id: str) -> Dict[str, Any]:
    # Minimal no-op stub to keep UI happy; wire to real OCR job if present
    inv = fetch_one("SELECT id FROM invoices WHERE id = ?", (invoice_id,))
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    # mark status for UI
    execute("UPDATE invoices SET status = 'ocr' WHERE id = ?", (invoice_id,))
    return {"ok": True, "status": "ocr"}