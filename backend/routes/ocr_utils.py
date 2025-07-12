from typing import Literal

def detect_document_type(text: str) -> Literal["invoice", "delivery_note", "unknown"]:
    """
    Detects whether the document is an invoice, delivery note, or unknown based on text heuristics.
    """
    text_l = text.lower()
    invoice_keywords = ["invoice", "total", "vat", "supplier", "invoice number"]
    delivery_keywords = ["delivery", "delivered", "received by", "note", "items delivered"]

    invoice_score = sum(1 for k in invoice_keywords if k in text_l)
    delivery_score = sum(1 for k in delivery_keywords if k in text_l)

    if invoice_score > delivery_score and invoice_score > 0:
        return "invoice"
    elif delivery_score > invoice_score and delivery_score > 0:
        return "delivery_note"
    elif invoice_score == delivery_score and invoice_score > 0:
        return "unknown"
    else:
        return "unknown" 