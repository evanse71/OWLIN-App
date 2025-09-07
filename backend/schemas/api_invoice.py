from __future__ import annotations
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

class Line(BaseModel):
    desc: str
    qty: float
    unit_price: float
    line_total: float
    flags: List[str] = []

class MatchSuggestion(BaseModel):
    invoice_line_idx: int
    dn_line_idx: int
    score: float

class DNCandidate(BaseModel):
    id: str
    supplier_name: Optional[str] = None
    date: Optional[str] = None
    score: float

class InvoiceBundle(BaseModel):
    id: str
    meta: Dict[str, Any]
    lines: List[Line]
    dn_candidates: List[DNCandidate]
    suggestions: List[MatchSuggestion]
    doc_flags: List[str] = [] 