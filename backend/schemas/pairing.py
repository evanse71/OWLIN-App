from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class CandidateLine:
    sku: Optional[str]
    description: str
    quantity_each: float
    unit_price_pennies: int
    quantity_l: float  # 0.0 if N/A

@dataclass(frozen=True)
class LineScore:
    desc_score: float
    qty_score: float
    price_score: float
    uom_score: float
    total: float 