# backend/ocr/vendors/stori_extractor.py
# Vendor template: STORI Beer & Wine CYF
# Parses lines under the PRODUCT/QTY/RATE/VAT/AMOUNT table.
# Input: raw OCR text (single string) + optional lines list
# Output: dict with items[], header fields (date, total, vat, subtotal) when found.

import re
from typing import Dict, List, Any, Optional

_MONEY = r"(?:£\s*)?([0-9]+(?:\.[0-9]{1,2})?)"
_INT = r"([0-9]+)"

# Table header cue and line matcher (robust to variable spacing)
_HDR_CUE = re.compile(r"\bPRODUCT\b.*\bQTY\b.*\bRATE\b.*\bVAT\b.*\bAMOUNT\b", re.IGNORECASE)
_ROW = re.compile(
    rf"^(?P<name>.+?)\s+{_INT}\s+{_MONEY}\s+(?P<vat>\d+\.?\d*%[A-Za-z]?)\s+{_MONEY}\s*$"
)

# Totals block
_SUBTOTAL = re.compile(r"\bSUBTOTAL\b\s+" + _MONEY, re.IGNORECASE)
_VAT_TOTAL = re.compile(r"\bVAT\s+TOTAL\b\s+" + _MONEY, re.IGNORECASE)
_TOTAL = re.compile(r"\bTOTAL\b\s+" + _MONEY, re.IGNORECASE)
_DATE = re.compile(r"\bDATE\b\s*[:]?\s*([0-9]{2}/[0-9]{2}/[0-9]{4}|[0-9]{2}-[0-9]{2}-[0-9]{4}|[0-9]{4}-[0-9]{2}-[0-9]{2})", re.IGNORECASE)

def _to_pence(val: str) -> int:
    return int(round(float(val) * 100))

def _norm_date(val: str) -> str:
    # Accepts 21/08/2025, 21-08-2025, 2025-08-21 -> returns ISO
    parts = re.split(r"[/-]", val)
    if len(parts) == 3:
        if len(parts[0]) == 4:
            y, m, d = parts
        else:
            d, m, y = parts
        return f"{y.zfill(4)}-{m.zfill(2)}-{d.zfill(2)}"
    return val

def extract(text: str) -> Dict[str, Any]:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    out: Dict[str, Any] = {"items": []}

    # Date
    mdate = _DATE.search(text)
    if mdate:
        out["date"] = _norm_date(mdate.group(1))

    # Totals
    msub = _SUBTOTAL.search(text)
    mvat = _VAT_TOTAL.search(text)
    mtot = _TOTAL.search(text)
    if msub: out["subtotal_pence"] = _to_pence(msub.group(1))
    if mvat: out["vat_pence"] = _to_pence(mvat.group(1))
    if mtot: out["total_pence"] = _to_pence(mtot.group(1))

    # Find table start
    start_idx: Optional[int] = None
    for i, l in enumerate(lines):
        if _HDR_CUE.search(l):
            start_idx = i + 1
            break
    if start_idx is None:
        return out

    # Consume rows until a totals cue line
    for l in lines[start_idx:]:
        if re.search(r"\bSUBTOTAL\b|\bTOTAL\b|VAT\s+SUMMARY", l, re.IGNORECASE):
            break
        m = _ROW.match(l)
        if not m:
            continue
        name = m.group("name").strip()
        qty = int(m.group(1))
        unit_price = _to_pence(m.group(2))
        amount = _to_pence(m.group(4))
        out["items"].append({
            "sku": None,
            "name": name,
            "qty": qty,
            "unit_price_pence": unit_price,
            "line_total_pence": amount
        })
    return out

