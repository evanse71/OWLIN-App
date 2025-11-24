"""
Invoice â†” Delivery-Note pairing logic
"""
import re
from typing import Dict, List, Tuple
from backend.db.pairs import (
    db_get_document, db_recent_docs, db_upsert_pair_suggest, date_from
)

def classify_doc(text: str) -> str:
    """Classify document type based on text content"""
    t = text.lower()
    
    # Delivery note indicators
    if any(indicator in t for indicator in [
        "delivery note", "goods received", " grn ", "delivery receipt"
    ]):
        return "delivery_note"
    
    # Check for DN number patterns
    if re.search(r"\bdn[- ]?\d", t):
        return "delivery_note"
    
    # Invoice indicators
    if "invoice" in t:
        return "invoice"
    
    # Check for invoice number patterns
    if re.search(r"\binv[- ]?\d", t):
        return "invoice"
    
    return "unknown"

def maybe_create_pair_suggestions(doc_id: int):
    """Create pairing suggestions for a document"""
    d = db_get_document(doc_id)
    if not d or d["doc_type"] not in ("invoice", "delivery_note"):
        return
    
    # Find counter-type documents
    counter_type = "delivery_note" if d["doc_type"] == "invoice" else "invoice"
    candidates = db_recent_docs(counter_type, supplier=d["supplier"], days=14)
    
    best = []
    for c in candidates:
        score = 0.0
        
        # Exact number link (highest confidence)
        if d["doc_type"] == "invoice" and d["delivery_no"] and c["delivery_no"] == d["delivery_no"]:
            score = 0.98
        elif d["doc_type"] == "delivery_note" and d["invoice_no"] and c["invoice_no"] == d["invoice_no"]:
            score = 0.98
        
        # Supplier + date proximity
        if d["supplier"] and c["supplier"] and d["supplier"].lower() == c["supplier"].lower():
            if d["doc_date"] and c["doc_date"]:
                try:
                    d_date = date_from(d["doc_date"])
                    c_date = date_from(c["doc_date"])
                    if d_date and c_date:
                        delta = abs((d_date - c_date).days)
                        if delta <= 3:
                            score = max(score, 0.90 - delta * 0.02)
                except:
                    pass
        
        # Amount sanity check
        if d["total"] and c["total"]:
            total_diff = abs(d["total"] - c["total"])
            max_total = max(d["total"], c["total"])
            if total_diff <= 0.02 * max_total:
                score += 0.03
        
        # Filename hints
        if d["filename"] and c["filename"]:
            d_lower = d["filename"].lower()
            c_lower = c["filename"].lower()
            if ("inv" in d_lower and "dn" in c_lower) or ("dn" in d_lower and "inv" in c_lower):
                score += 0.02
        
        # Only suggest high-confidence pairs
        if score >= 0.85:
            best.append((c["id"], round(min(score, 0.99), 2)))
    
    # Create suggestions for top candidates
    for cid, conf in best[:3]:  # Limit to top 3 suggestions
        db_upsert_pair_suggest(d, cid, conf)

def extract_doc_metadata(parsed: Dict, filename: str) -> Dict:
    """Extract metadata for document storage"""
    # Classify document type
    text_content = ""
    if parsed:
        # Combine all text fields for classification
        text_fields = [
            parsed.get("supplier", ""),
            parsed.get("invoice_number", ""),
            parsed.get("delivery_note_number", ""),
            parsed.get("description", ""),
            parsed.get("line_items", [])
        ]
        text_content = " ".join(str(field) for field in text_fields if field)
    
    doc_type = classify_doc(text_content) if text_content else "unknown"
    
    return {
        "supplier": parsed.get("supplier") if parsed else None,
        "invoice_no": parsed.get("invoice_number") if parsed else None,
        "delivery_no": parsed.get("delivery_note_number") if parsed else None,
        "doc_date": parsed.get("date") if parsed else None,
        "total": parsed.get("total") if parsed else None,
        "currency": parsed.get("currency") if parsed else None,
        "doc_type": doc_type
    }

