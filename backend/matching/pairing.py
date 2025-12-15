"""
Invoice â†” Delivery-Note pairing logic
"""
import re
import sqlite3
from typing import Dict, List, Tuple
from backend.db.pairs import (
    db_get_document, db_recent_docs, db_upsert_pair_suggest, date_from
)
from backend.services.quantity_validator import calculate_quantity_match_score
from backend.app.db import get_line_items_for_invoice, get_line_items_for_doc, DB_PATH

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
        
        # Quantity match validation (if line items available)
        quantity_match_score = 1.0
        has_quantity_mismatch = False
        try:
            if d["doc_type"] == "invoice":
                # d is invoice, c is delivery note
                invoice_doc_id = d["id"]
                delivery_doc_id = c["id"]
                
                # Get invoice_id from invoices table
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM invoices WHERE doc_id = ?", (str(invoice_doc_id),))
                invoice_row = cursor.fetchone()
                conn.close()
                
                if invoice_row:
                    invoice_id = invoice_row[0]
                    invoice_items = get_line_items_for_invoice(invoice_id)
                    delivery_items = get_line_items_for_doc(str(delivery_doc_id), invoice_id=None)
                    
                    if invoice_items and delivery_items:
                        qty_score = calculate_quantity_match_score(invoice_items, delivery_items)
                        quantity_match_score = qty_score
                        
                        # Check for quantity mismatches
                        if qty_score < 0.95:  # Less than 95% match indicates mismatches
                            has_quantity_mismatch = True
                        
                        # Adjust confidence based on quantity match:
                        # Perfect match (>= 0.95): +0.05 to confidence
                        # Good match (>= 0.85): no change
                        # Poor match (< 0.85): -0.10 to confidence
                        if qty_score >= 0.95:
                            score += 0.05
                        elif qty_score < 0.85:
                            score -= 0.10
            else:
                # d is delivery note, c is invoice
                delivery_doc_id = d["id"]
                invoice_doc_id = c["id"]
                
                # Get invoice_id from invoices table
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM invoices WHERE doc_id = ?", (str(invoice_doc_id),))
                invoice_row = cursor.fetchone()
                conn.close()
                
                if invoice_row:
                    invoice_id = invoice_row[0]
                    invoice_items = get_line_items_for_invoice(invoice_id)
                    delivery_items = get_line_items_for_doc(str(delivery_doc_id), invoice_id=None)
                    
                    if invoice_items and delivery_items:
                        qty_score = calculate_quantity_match_score(invoice_items, delivery_items)
                        quantity_match_score = qty_score
                        
                        # Check for quantity mismatches
                        if qty_score < 0.95:  # Less than 95% match indicates mismatches
                            has_quantity_mismatch = True
                        
                        # Adjust confidence based on quantity match
                        if qty_score >= 0.95:
                            score += 0.05
                        elif qty_score < 0.85:
                            score -= 0.10
        except Exception:
            # If quantity validation fails, continue without it
            pass
        
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

