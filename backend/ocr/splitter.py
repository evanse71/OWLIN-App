#!/usr/bin/env python3
"""
Multi-invoice PDF splitter
Detects invoice boundaries and splits multi-invoice PDFs into separate invoice objects
"""

import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# Header anchors that indicate a new invoice
HEADER_ANCHORS = [
    r"\bInvoice\s*(No|#|Number)\b",
    r"\bTax\s*Invoice\b",
    r"\bVAT\s*Invoice\b",
    r"\bBill\s*(No|#|Number)\b",
    r"\bStatement\s*(No|#|Number)\b",
    r"\bINVOICE\s*PAGE\s*\d+\b",  # Add pattern for "INVOICE PAGE X"
]

HEADER_RE = re.compile("|".join(HEADER_ANCHORS), re.IGNORECASE)

MIN_TOKENS_PER_CHUNK = 80
FOOTER_LINE_FRACTION = 0.80  # ignore anchors below this fraction (footer area)

def _has_valid_header_anchor(page_text: str) -> bool:
    """Check if page has a valid header anchor (not in footer area)"""
    if not page_text:
        return False
    lines = [ln.strip() for ln in page_text.splitlines() if ln.strip()]
    if not lines:
        return False
    n = len(lines)
    for i, ln in enumerate(lines):
        if HEADER_RE.search(ln):
            # footer guard: ignore anchors in bottom 20% of lines
            if (i / max(1, n-1)) >= FOOTER_LINE_FRACTION:
                continue
            return True
    return False

def _chunk_token_count(chunk_pages: List[Dict[str, Any]]) -> int:
    """Count total tokens across all pages in a chunk"""
    tok = 0
    for p in chunk_pages:
        t = (p.get("text") or "")
        tok += len(t.split())
    return tok

def split_pages_into_invoices(pages: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    """
    Split pages into invoice chunks based on header detection with false-split guards
    
    Args:
        pages: List of page dictionaries with 'text' and 'page_index' keys
        
    Returns:
        List of chunks; each chunk is a list of pages belonging to one invoice
    """
    if not pages:
        return []
    
    chunks: List[List[Dict[str, Any]]] = []
    current: List[Dict[str, Any]] = []
    
    for p in pages:
        text = p.get("text", "") or ""
        
        # Check if this page contains a new invoice header
        if _has_valid_header_anchor(text) and current:
            # start a new invoice
            # validate previous chunk token count; if too small, merge it forward
            if _chunk_token_count(current) < MIN_TOKENS_PER_CHUNK and chunks:
                # merge tiny chunk into previous instead of starting new
                logger.info(f"Merging tiny chunk ({_chunk_token_count(current)} tokens) into previous")
                chunks[-1].extend(current)
            else:
                chunks.append(current)
            current = [p]
        else:
            current.append(p)
    
    # Add the last chunk
    if current:
        if _chunk_token_count(current) < MIN_TOKENS_PER_CHUNK and chunks:
            logger.info(f"Merging final tiny chunk ({_chunk_token_count(current)} tokens) into previous")
            chunks[-1].extend(current)
        else:
            chunks.append(current)
    
    # If we detected nothing (single invoice), return [pages]
    if not chunks:
        logger.info("No invoice boundaries detected, treating as single invoice")
        return [pages]
    
    logger.info(f"Split {len(pages)} pages into {len(chunks)} invoice chunks")
    for i, chunk in enumerate(chunks):
        page_indices = [p.get("page_index", "unknown") for p in chunk]
        token_count = _chunk_token_count(chunk)
        logger.info(f"  Invoice {i+1}: pages {page_indices}, {token_count} tokens")
    
    return chunks

def extract_invoice_metadata_from_chunk(chunk: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Extract invoice metadata from a chunk of pages
    
    Args:
        chunk: List of pages belonging to one invoice
        
    Returns:
        Dictionary with extracted metadata
    """
    combined_text = "\n".join([p.get("text", "") for p in chunk])
    
    # Extract invoice number
    invoice_number_match = re.search(r"Invoice\s*(?:No|#|Number)[:\s]*([A-Z0-9\-]+)", combined_text, re.IGNORECASE)
    invoice_number = invoice_number_match.group(1) if invoice_number_match else ""
    
    # Extract supplier name (basic heuristic - look for company patterns)
    supplier_match = re.search(r"^([A-Z][A-Z\s&]+(?:LTD|LLC|INC|CORP|CO|COMPANY))", combined_text, re.MULTILINE | re.IGNORECASE)
    supplier_name = supplier_match.group(1) if supplier_match else "Unknown Supplier"
    
    # Extract date (basic pattern)
    date_match = re.search(r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", combined_text)
    invoice_date = date_match.group(1) if date_match else ""
    
    return {
        "supplier_name": supplier_name.strip(),
        "invoice_number": invoice_number.strip(),
        "invoice_date": invoice_date,
        "page_range": (chunk[0].get("page_index", 0), chunk[-1].get("page_index", 0)),
        "confidence": 75  # Default confidence for split invoices
    } 