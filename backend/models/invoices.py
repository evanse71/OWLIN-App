from pydantic import BaseModel, Field, condecimal, conint
from typing import List, Optional
from datetime import date
from decimal import Decimal

class LineItemIn(BaseModel):
    description: str = Field(min_length=1)
    quantity: conint(ge=0) = 1
    unit_price: condecimal(ge=0) = Decimal("0")
    bbox: Optional[List[int]] = None  # [x, y, w, h] for visual verification

class InvoiceCreate(BaseModel):
    supplier_id: int
    invoice_number: Optional[str] = None  # Extracted invoice number from OCR
    invoice_date: date
    currency: str = Field(min_length=3, max_length=3)  # "GBP"
    total_value: condecimal(ge=0)
    notes: Optional[str] = None
    line_items: List[LineItemIn] = []

class InvoiceOut(BaseModel):
    id: int
    supplier_id: int
    invoice_number: Optional[str] = None  # Extracted invoice number from OCR
    invoice_date: date
    currency: str
    total_value: Decimal
    notes: Optional[str] = None
