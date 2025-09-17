from __future__ import annotations
from typing import Dict, Any, List, Optional
import re
from rapidfuzz import fuzz

DATE_RX = re.compile(r"(20\d{2}?\d{2})")
NUM_RX  = re.compile(r"\d+(?:[.,]\d+)?")
CURRENCY_RX = re.compile(r"£|€|\$|GBP|EUR|USD")
TOTAL_RX = re.compile(r"(?:total|amount due|balance|net total|grand total)[\s:]*([£€$]?\s*\d+(?:[.,]\d+)?)", re.IGNORECASE)

# Supplier lexicon for better matching
SUPPLIER_LEXICON = [
    "Brakes", "Bidfood", "Booker", "Tesco", "Makro", "JJ Foodservice", "Sysco",
    "Nisbets", "Caterlink", "Aramark", "Compass", "Sodexo", "Elior", "Mitie",
    "Bidvest", "Fresh Direct", "Ocado", "Waitrose", "Sainsbury's", "Morrisons",
    "Asda", "Lidl", "Aldi", "Iceland", "Co-op", "Marks & Spencer", "M&S"
]

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

def _parse_supplier_lexicon(lines: List[str]) -> Optional[str]:
    """Match supplier using lexicon with fuzzy matching (score >= 88)."""
    for line in lines:
        for supplier in SUPPLIER_LEXICON:
            score = fuzz.ratio(line.lower(), supplier.lower())
            if score >= 88:
                return supplier
    return None

def _parse_total(lines: List[str]) -> Optional[float]:
    """Extract total using regex patterns for common total labels."""
    for line in lines:
        # Look for total patterns
        match = TOTAL_RX.search(line)
        if match:
            total_str = match.group(1).replace("£", "").replace("€", "").replace("$", "").replace(",", ".").strip()
            try:
                return float(total_str)
            except ValueError:
                continue
        
        # Fallback: look for currency symbol followed by number
        if CURRENCY_RX.search(line):
            nums = NUM_RX.findall(line)
            if nums:
                try:
                    return float(nums[-1].replace(",", "."))
                except ValueError:
                    continue
    return None

def parse_invoice_from_ocr(ocr_payload: Dict[str, Any]) -> Dict[str, Any]:
    raw = [l.get("text","") for l in ocr_payload.get("lines", []) if l.get("text")]
    lower = [t.lower() for t in raw]
    
    # Enhanced supplier detection with lexicon
    supplier = _parse_supplier_lexicon(raw)
    if not supplier:
        # Fallback to original method
        for t in raw[:10]:
            if sum(c.isalpha() for c in t) >= 3:
                supplier = t.strip(); break
    
    invoice_date = _parse_date(raw)
    
    # Enhanced total extraction
    total_value = _parse_total(raw)
    
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
        "total_value": total_value,
        "line_items": items[:120]
    }
