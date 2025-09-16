from __future__ import annotations
from typing import Dict, Any, List, Optional
import re
from rapidfuzz import fuzz

DATE_RX = re.compile(r"(20\d{2}?\d{2})")
NUM_RX  = re.compile(r"\d+(?:[.,]\d+)?")

def _parse_date(lines: List[str]) -> Optional[str]:
    for t in lines:
        m = DATE_RX.search(t)
        if m:
            raw = m.group(0).replace('.', '-').replace('/', '-')
            parts = raw.split('-')
            if len(parts[0])==4:
                y, mth, d = parts[0], parts[1].zfill(2), parts[2].zfill(2)
            else:
                d, mth, y = parts[0].zfill(2), parts[1].zfill(2), parts[2]
                if len(y)==2: y = "20"+y
            return f"{y}-{mth}-{d}"
    return None

def parse_invoice_from_ocr(ocr_payload: Dict[str, Any]) -> Dict[str, Any]:
    raw = [l.get("text","") for l in ocr_payload.get("lines", []) if l.get("text")]
    lower = [t.lower() for t in raw]
    supplier = None
    for t in raw[:10]:
        if sum(c.isalpha() for c in t) >= 3:
            supplier = t.strip(); break
    invoice_date = _parse_date(raw)
    reference = None
    for t in lower[:30]:
        if "invoice" in t and ("no" in t or "number" in t or "#" in t):
            reference = raw[lower.index(t)].strip(); break

    items = []
    for t in raw:
        nums = NUM_RX.findall(t)
        nums = [n.replace(",", ".") for n in nums]
        if len(nums) >= 2:
            try:
                qty = float(nums[-2]); unit = float(nums[-1])
                items.append({
                    "description": t[:160], "quantity": qty, "unit_price": unit,
                    "uom": None, "vat_rate": 0
                })
            except: pass

    return {
        "supplier": supplier,
        "invoice_date": invoice_date,
        "reference": reference,
        "currency": "GBP",
        "line_items": items[:120]
    }
