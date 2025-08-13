from typing import List, Optional, Dict, Any
from dataclasses import dataclass

@dataclass
class LineItem:
    description: str
    quantity: Optional[float]
    unit: Optional[str]
    unit_price: Optional[float]
    line_total: Optional[float]
    page: Optional[int]
    row_idx: Optional[int]
    confidence: float  # 0.0 - 1.0

@dataclass
class ParsedInvoice:
    supplier_name: Optional[str]
    invoice_number: Optional[str]
    invoice_date: Optional[str]      # ISO "YYYY-MM-DD" if known
    currency: Optional[str]
    subtotal: Optional[float]
    tax: Optional[float]
    total_amount: Optional[float]
    line_items: List[LineItem]
    warnings: List[str]
    field_confidence: Dict[str, float]   # e.g., {"supplier_name":0.93,...}
    raw_extraction: Dict[str, Any]       # model raw output for debug

@dataclass
class InvoiceParsingPayload:
    text: Optional[str]                       # llama-surya path
    tables: Optional[List[Dict[str, Any]]]    # normalized candidate tables
    page_images: Optional[List[Dict[str, Any]]]  # [{"page":1,"image_b64":"..."}]
    hints: Dict[str, Any]                     # {"likely_currency":"GBP", "venue":"Royal Oak"} 