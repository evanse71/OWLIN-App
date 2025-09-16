from pydantic import BaseModel
from typing import Optional, List
from .invoice_line_items import InvoiceLineItemIn, InvoiceLineItem

class InvoiceManualIn(BaseModel):
    supplier: str
    invoice_date: Optional[str] = None
    reference: Optional[str] = None
    currency: Optional[str] = "GBP"
    line_items: Optional[List[InvoiceLineItemIn]] = None

class InvoiceOut(BaseModel):
    id: str
    supplier: Optional[str] = None
    invoice_date: Optional[str] = None
    status: str
    total_value: Optional[float] = None
    currency: Optional[str] = "GBP"
