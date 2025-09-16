from pydantic import BaseModel, Field
from typing import Optional, List

class InvoiceLineItemIn(BaseModel):
    description: Optional[str] = None
    quantity: float = 0
    unit_price: float = 0
    uom: Optional[str] = None
    vat_rate: float = 0

class InvoiceLineItem(InvoiceLineItemIn):
    id: str
    total: float = Field(0, description="quantity * unit_price")
