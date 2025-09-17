from __future__ import annotations
from typing import List, Dict, Any, Tuple, DefaultDict
from collections import defaultdict
import re

NUM_RX  = re.compile(r"\d+")
INV_RX  = re.compile(r"(invoice\s*(no|#|number)?\s*[:\-]?\s*[A-Za-z0-9\-\/]+)", re.I)
VAT_RX  = re.compile(r"(gb\d{9})", re.I)

def _norm(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "", (s or "").lower()).strip()

def page_signature(page_parse: Dict[str, Any]) -> Tuple[str,str,str]:
    """Return lightweight signature for grouping: supplier, reference, vat."""
    supplier = _norm(page_parse.get("supplier") or "")
    ref = _norm(page_parse.get("reference") or "")
    vat = ""
    text = " ".join([l.get("text","") for l in page_parse.get("raw_lines", [])])
    m_inv = INV_RX.search(text or "")
    if m_inv and not ref:
        ref = _norm(m_inv.group(0))
    m_vat = VAT_RX.search(text or "")
    if m_vat:
        vat = _norm(m_vat.group(0))
    return supplier, ref, vat

def group_pages(parsed_pages: List[Dict[str, Any]]) -> List[List[int]]:
    """
    Input: list of dicts [{page_index:int, parse:{supplier, reference, raw_lines...}}, ...]
    Output: list of page-index groups → one invoice per group (interleaving allowed)
    Strategy: bucket by (supplier, reference, vat). Unknown pages become singleton groups.
    """
    buckets: DefaultDict[Tuple[str,str,str], List[int]] = defaultdict(list)
    unknown: List[int] = []
    for p in parsed_pages:
        sig = page_signature(p.get("parse") or {})
        if any(sig):
            buckets[sig].append(p["page_index"])
        else:
            unknown.append(p["page_index"])
    groups = [sorted(v) for v in buckets.values()]
    # unknown pages stay independent to avoid accidental merges; can be merged later via UI
    groups.extend([[u] for u in unknown])
    # note: interleaved pages naturally end up in same group if signature matches
    return groups
