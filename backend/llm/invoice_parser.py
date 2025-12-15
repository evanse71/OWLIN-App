"""
LLM-First Invoice Reconstruction Module

This module provides LLM-based document reconstruction that understands semantic meaning
instead of relying on geometric/regex patterns. It can handle any invoice format, receipts,
multi-page documents, and mixed document types (invoice + delivery note in same PDF).

Key Features:
- Semantic document understanding via Ollama LLM
- Self-verification (math checks: Qty × Unit = Total)
- Bounding box re-alignment for UI visualization
- Multi-page continuation detection
- Multi-document splitting (Invoice + DN separation)
- Graceful failure handling without fallback to geometric methods
"""

from __future__ import annotations
import json
import logging
import re
import time
import requests
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from decimal import Decimal, InvalidOperation

try:
    from rapidfuzz import fuzz
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False
    fuzz = None

LOGGER = logging.getLogger("owlin.llm.invoice_parser")


class DocumentType(Enum):
    """Supported document types."""
    INVOICE = "invoice"
    DELIVERY_NOTE = "delivery_note"
    CREDIT_NOTE = "credit_note"
    RECEIPT = "receipt"
    UNKNOWN = "unknown"


@dataclass
class LLMLineItem:
    """Line item extracted by LLM (matches database schema)."""
    description: str
    qty: float
    unit_price: float
    total: float
    uom: str = ""
    sku: str = ""
    confidence: float = 1.0
    bbox: Optional[List[int]] = None  # [x, y, w, h] for UI visualization
    raw_text: str = ""  # Original text for debugging
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "description": self.description,
            "qty": self.qty,
            "unit_price": self.unit_price,
            "total": self.total,
            "uom": self.uom,
            "sku": self.sku,
            "confidence": self.confidence,
            "raw_text": self.raw_text
        }
        if self.bbox:
            result["bbox"] = self.bbox
        return result


@dataclass
class LLMDocumentResult:
    """Complete document extraction result from LLM."""
    document_type: DocumentType
    supplier_name: str = ""
    invoice_number: str = ""
    invoice_date: str = ""
    currency: str = "GBP"
    line_items: List[LLMLineItem] = field(default_factory=list)
    subtotal: float = 0.0
    vat_amount: float = 0.0
    vat_rate: float = 0.2  # Default 20% UK VAT
    grand_total: float = 0.0
    confidence: float = 1.0
    success: bool = True
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    processing_time: float = 0.0
    page_number: int = 1
    is_continuation: bool = False  # True if this is page 2+ of multi-page doc
    has_more_pages: bool = False  # True if "Page X of Y" detected
    needs_review: bool = False  # True if validation errors exceed threshold
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "document_type": self.document_type.value,
            "supplier_name": self.supplier_name,
            "invoice_number": self.invoice_number,
            "invoice_date": self.invoice_date,
            "currency": self.currency,
            "line_items": [item.to_dict() for item in self.line_items],
            "subtotal": self.subtotal,
            "vat_amount": self.vat_amount,
            "vat_rate": self.vat_rate,
            "grand_total": self.grand_total,
            "confidence": self.confidence,
            "success": self.success,
            "error_message": self.error_message,
            "metadata": self.metadata,
            "processing_time": self.processing_time,
            "page_number": self.page_number,
            "is_continuation": self.is_continuation,
            "has_more_pages": self.has_more_pages,
            "needs_review": self.needs_review
        }


@dataclass
class DocumentGroup:
    """Group of pages representing a single document (for multi-page/multi-doc handling)."""
    document_type: DocumentType
    pages: List[int]
    combined_result: LLMDocumentResult
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "document_type": self.document_type.value,
            "pages": self.pages,
            "combined_result": self.combined_result.to_dict()
        }


class BBoxAligner:
    """
    Re-aligns LLM extraction results to PaddleOCR bounding boxes.
    
    Uses fuzzy text matching to find OCR words corresponding to LLM descriptions,
    then calculates union bounding boxes for UI visualization.
    """
    
    def __init__(self, match_threshold: float = 0.7):
        """
        Initialize bbox aligner.
        
        Args:
            match_threshold: Minimum fuzzy match score (0.0-1.0) to consider a match
        """
        self.match_threshold = match_threshold
        if not RAPIDFUZZ_AVAILABLE:
            LOGGER.warning("rapidfuzz not available, bbox alignment will be less accurate")
    
    def align_llm_to_ocr(
        self, 
        llm_items: List[LLMLineItem], 
        ocr_raw_blocks: List[Dict[str, Any]]
    ) -> List[LLMLineItem]:
        """
        Align LLM line items to OCR bounding boxes.
        
        Args:
            llm_items: Line items extracted by LLM
            ocr_raw_blocks: Raw OCR results with text and bbox
            
        Returns:
            Line items with bbox fields populated
        """
        if not ocr_raw_blocks:
            LOGGER.warning("No OCR blocks provided for bbox alignment")
            return llm_items
        
        aligned_items = []
        
        for item in llm_items:
            # Find matching OCR blocks for this item's description
            matching_blocks = self._find_matching_blocks(
                item.description, 
                ocr_raw_blocks
            )
            
            if matching_blocks:
                # Calculate union bounding box
                union_bbox = self._calculate_union_bbox(matching_blocks)
                item.bbox = union_bbox
                LOGGER.debug(f"Aligned '{item.description[:30]}...' to bbox {union_bbox}")
            else:
                LOGGER.warning(f"Could not find bbox for '{item.description[:30]}...'")
                # No bbox - will be handled gracefully in UI
                item.confidence *= 0.9  # Slight confidence penalty
            
            aligned_items.append(item)
        
        return aligned_items
    
    def _find_matching_blocks(
        self, 
        target_text: str, 
        ocr_blocks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Find OCR blocks that match the target text using fuzzy matching.
        
        Args:
            target_text: Text to search for (e.g., "Crate of Beer")
            ocr_blocks: List of OCR blocks with 'text' and 'bbox' fields
            
        Returns:
            List of matching OCR blocks
        """
        if not RAPIDFUZZ_AVAILABLE:
            # Fallback to simple substring matching
            return [
                block for block in ocr_blocks
                if 'text' in block and target_text.lower() in block['text'].lower()
            ]
        
        # Tokenize target text
        target_tokens = target_text.lower().split()
        matching_blocks = []
        
        for block in ocr_blocks:
            if 'text' not in block or not block['text']:
                continue
            
            block_text = block['text'].lower()
            
            # Check if any target token fuzzy matches this block
            for token in target_tokens:
                if len(token) < 3:  # Skip very short tokens
                    continue
                
                # Use partial ratio for substring matching
                score = fuzz.partial_ratio(token, block_text) / 100.0
                
                if score >= self.match_threshold:
                    matching_blocks.append(block)
                    break  # Don't add same block twice
        
        return matching_blocks
    
    def _calculate_union_bbox(self, blocks: List[Dict[str, Any]]) -> List[int]:
        """
        Calculate union bounding box from multiple blocks.
        
        Args:
            blocks: List of blocks with 'bbox' field [x, y, w, h]
            
        Returns:
            Union bbox [x, y, w, h]
        """
        if not blocks:
            return [0, 0, 0, 0]
        
        # Extract all bboxes
        bboxes = []
        for block in blocks:
            if 'bbox' in block and block['bbox']:
                bbox = block['bbox']
                if len(bbox) >= 4:
                    bboxes.append(bbox)
        
        if not bboxes:
            return [0, 0, 0, 0]
        
        # Calculate union: min x, min y, max (x+w), max (y+h)
        min_x = min(bbox[0] for bbox in bboxes)
        min_y = min(bbox[1] for bbox in bboxes)
        max_x = max(bbox[0] + bbox[2] for bbox in bboxes)
        max_y = max(bbox[1] + bbox[3] for bbox in bboxes)
        
        return [min_x, min_y, max_x - min_x, max_y - min_y]


class LLMInvoiceParser:
    """
    LLM-based invoice parser using Ollama for semantic document understanding.
    
    This parser replaces geometric/regex approaches with LLM reconstruction,
    enabling "any format" invoice processing with self-verification.
    """
    
    def __init__(
        self, 
        ollama_url: str = "http://localhost:11434",
        model_name: str = "qwen2.5-coder:7b",
        timeout: int = 120,  # INCREASED: 120s for first-time model loading
        max_retries: int = 3
    ):
        """
        Initialize LLM invoice parser.
        
        Args:
            ollama_url: Ollama API base URL
            model_name: Model to use for extraction
            timeout: Request timeout in seconds (default 120s for slow local models)
            max_retries: Maximum retry attempts
        """
        self.ollama_url = ollama_url
        self.model_name = model_name
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Note: System prompt is now generated by _get_extraction_prompt() method
        # Old prompt kept for reference but not used
        # self.system_prompt = """... (old prompt removed, see _get_extraction_prompt method)"""
    
    def _get_extraction_prompt(self, ocr_text: str) -> str:
        """
        Construct the prompt for the LLM with strict extraction rules.
        """
        system_prompt = """You are an expert Data Extraction AI specialized in Invoices and Receipts.

You are a JSON generation engine. Do not output conversational text.
Ensure all strings are properly escaped.
Output raw JSON only. Do not wrap in markdown code blocks.

Your goal is to extract structured data from OCR text into valid JSON.

### EXTRACTION RULES:

1. **LINE ITEMS (CRITICAL):**

   - Extract `description`, `qty`, `unit_price`, `total`, and `vat_rate` (if available).

   - **Merged Columns Rule (CRITICAL):** When you see patterns like "6 12 LITRE PEPSI", split immediately:
     * The FIRST number is ALWAYS the QUANTITY: Qty = 6
     * The rest is the DESCRIPTION: Description = "12 LITRE PEPSI"
     * Example: "6 12 LITRE PEPSI" → qty=6, description="12 LITRE PEPSI"
     * Example: "12 500ML COKE" → qty=12, description="500ML COKE"
     * If a line starts with a number followed by another number, the first is ALWAYS the quantity.

   - **Unit of Measure Extraction:** Extract UOM from descriptions when present:
     * Patterns like "12x1L", "6x2.5kg", "1x3kg" → Extract qty and unit separately
     * Example: "12x1L" → qty=12, uom="1L" or description="12x1L" (preserve full format)
     * Example: "6x2.5kg" → qty=6, uom="2.5kg"
     * Handle formats: "12x1L", "6x2.5kg", "1x3kg", "30x340g"

   - **Product Code Extraction:** If a separate CODE column exists, extract it:
     * Harlech format: CODE | DESCRIPTION | QTY | UNIT | PRICE | VALUE | VAT
     * M Hughes format: Prod Code | Description | Origin | Quantity | Price
     * Extract code as `sku` field if present

   - **Various Table Formats:**
     * **Harlech Format:** CODE | DESCRIPTION | RSP | QTY | UNIT | PRICE | VALUE | VAT
       - CODE → sku
       - DESCRIPTION → description
       - QTY → qty
       - UNIT → uom
       - PRICE → unit_price
       - VALUE → total
       - VAT → vat_rate
     * **M Hughes Format:** Prod Code | Description | Origin | Quantity | Price
       - Prod Code → sku (optional)
       - Description → description
       - Quantity → qty
       - Price → unit_price (calculate total = qty × unit_price if total column missing)
     * **Generic Format:** Description | Qty | Unit Price | Total | VAT
       - Extract all fields as available

   - **Splits Section Handling:** When you see "*** Splits ***" or similar markers:
     * These are continuation/partial quantities - extract as separate line items
     * Example: "28001K | aa Peeled Potatoes Sagita | 15.069 K | 1.60 | 24.11"
       → Extract as line item with qty=15.069, uom="K", unit_price=1.60, total=24.11

   - **Math Derivation Rule:** If `qty` is missing or 0, but you have `total` and `unit_price`, CALCULATE it: `qty = total / unit_price`.

   - **Default Rule:** If Quantity is totally missing and cannot be calculated, default to **1**.

   - **Sanity Check:** `qty * unit_price` should roughly equal `total`. Trust the explicit `total` over the `unit_price` if they conflict.

2. **NOISE FILTERING (CRITICAL - DO NOT EXTRACT THESE AS LINE ITEMS):**

   - **Header Information (IGNORE COMPLETELY):**
     * DO NOT extract "VAT Registration No: GB123456789" as a line item
     * DO NOT extract "VAT Reg: GB123456789" as a line item
     * DO NOT extract "Reg No: 12345678" as a line item
     * DO NOT extract "Company No: 12345678" as a line item
     * If a line contains "VAT Registration", "VAT Reg", "Reg No", "Company No", IGNORE it completely.

   - **Contact Information (IGNORE COMPLETELY):**
     * DO NOT extract addresses, phone numbers, emails as line items
     * If a line contains "Address:", "Phone:", "Tel:", "Email:", "Bank:", "Account:", "Sort Code:", IGNORE it completely
     * Only extract actual product/service descriptions, quantities, and prices

   - **Container Lists (IGNORE COMPLETELY - CRITICAL FOR BREWERY INVOICES):**
     * DO NOT extract container IDs, container numbers, or container lists as line items
     * If a line contains "Container", "Containers", "Delivered in containers", "Containers outstanding", "Container ID", "Container No", IGNORE it completely
     * Examples to IGNORE: "CONTAINER ABC123", "Delivered in containers: XYZ789", "Containers outstanding: 5"
     * These are logistics metadata, NOT products

   - **Return Policy / Terms (IGNORE COMPLETELY):**
     * DO NOT extract return policy text, terms and conditions, or legal disclaimers as line items
     * If a line is ALL CAPS and contains "RETURN", "POLICY", "TERMS", "CONDITIONS", "ACCEPT", "UNSOLD", IGNORE it completely
     * Examples to IGNORE: "WE DO NOT ACCEPT RETURNS OF UNSOLD BEER", "RETURN POLICY: NO RETURNS ACCEPTED"
     * These are legal text, NOT products

   - **Table Headers (IGNORE):**
     * DO NOT extract column headers like "CODE", "DESCRIPTION", "QTY", "UNIT", "PRICE", "VALUE", "VAT" as line items
     * DO NOT extract "Prod Code", "Description", "Origin", "Quantity", "Price" as line items

   - **Other Noise (IGNORE):**
     * IGNORE lines that look like: Addresses, Phone Numbers, Bank Account info, or "Page x of y"
     * Do NOT extract "Subtotal", "VAT Total", or "Grand Total" as line items. Put them in the root fields.
     * IGNORE "C/F:" (carried forward) lines - these are accounting references, not products

3. **TOTAL EXTRACTION (CRITICAL - AVOID 100× ERRORS):**

   - **Decimal Point Handling:** When extracting totals, preserve the decimal point EXACTLY as shown
   - If you see "891.54", extract it as 891.54 (NOT 89154.00 or 89,154.00)
   - If you see "£891.54", extract it as 891.54 (NOT 89154.00)
   - **DO NOT multiply totals by 100** - the decimal point is already correct
   - **DO NOT remove decimal points** - if the invoice shows "891.54", that is the correct total
   - If the total appears as "891,54" (comma), convert it to "891.54" (decimal point) for UK invoices
   - Verify: The sum of line item totals should approximately equal the grand_total (within 1-2%)

4. **INVOICE BOUNDARY DETECTION (CRITICAL FOR MULTI-INVOICE PDFs):**

   - **New Invoice Indicators:** A new invoice starts when you see:
     * A different supplier name in the header
     * A different invoice number
     * A complete header block with supplier name + invoice number + date (all together)
     * A page break with a new document type (invoice vs delivery note)
     * The words "Invoice" or "INVOICE" with a new invoice number

   - **Same Invoice Continuation:** Pages belong to the same invoice if:
     * Same invoice number appears
     * Same supplier name appears
     * "Page X of Y" indicator shows continuation
     * Line items continue from previous page without a new header

   - **Multi-Invoice PDF Handling:** If you detect multiple invoices in the same document:
     * Extract each invoice separately with its own supplier_name, invoice_number, and line_items
     * Each invoice should have its own totals (subtotal, vat_amount, grand_total)
     * If processing a single page, extract only the invoice visible on that page

5. **MULTI-PAGE DOCUMENT HANDLING:**

   - **Delivery Note Detection (CRITICAL):**
     * If the OCR text contains the words "Delivery Note" or "DELIVERY NOTE" anywhere on the page, DO NOT extract any line items from that page
     * If you see "Delivery Note" in the text, return an empty `line_items` array: `"line_items": []`
     * Set `document_type` to `"delivery_note"` if "Delivery Note" is detected
     * Only process pages that are clearly invoices or receipts, not delivery notes
     * Example: If text contains "DELIVERY NOTE" or "Delivery Note", return: `{"document_type": "delivery_note", "line_items": [], ...}`

   - **Page Continuation:** If you see "Page 1 of 2" or similar, mark `has_more_pages: true` in metadata
   - **Continuation Pages:** If this is page 2+ and has same invoice number, mark `is_continuation: true`

6. **DOCUMENT INFO:**

   - Extract `supplier_name`, `invoice_date` (YYYY-MM-DD), `invoice_number`, `currency` (e.g., "GBP"), `subtotal`, `vat_amount`, `grand_total`.

   - **Invoice Date:** If multiple dates exist, the "Invoice Date" is usually near the top right. Do not confuse with "Due Date" or "Order Date".
     * Common formats: "10/12/25", "10-12-2025", "10 Dec 2025" → Convert to "2025-12-10"
     * UK format: DD/MM/YYYY or DD-MM-YYYY

   - **Invoice Number:** Extract from header area. May be labeled as "Invoice No", "INV", "Order No", or just a number near the date.
     * Examples: "375424", "INV-2025-001", "By Telephone" (if no number, use empty string)

   - **Supplier Name:** Extract the main supplier name from the header/top of the document. Do NOT use distributor names, payment processor names, or footer text as the supplier name.
     * Examples: "HARLECH", "M Hughes & Sons Llandudno Ltd" - extract the main business name

   - **VAT Rate Extraction:** Extract VAT rate from line items or VAT column:
     * Common UK rates: "20%", "5%", "0%" (zero-rated)
     * May appear as "1", "2", "5", "20" in VAT code column (where 1=20%, 2=5%, etc.)
     * If VAT code is numeric: 1→20%, 2→5%, 0→0%

### OUTPUT FORMAT:

Return ONLY raw JSON. No markdown formatting, no explanation.

{
  "document_type": "invoice",
  "supplier_name": "...",
  "invoice_number": "...",
  "invoice_date": "YYYY-MM-DD",
  "currency": "GBP",
  "line_items": [
    {
      "description": "...",
      "qty": 1.0,
      "unit_price": 0.00,
      "total": 0.00,
      "uom": "",
      "sku": "",
      "vat_rate": "20%"
    }
  ],
  "subtotal": 0.00,
  "vat_amount": 0.00,
  "grand_total": 0.00
}
"""
        user_prompt = f"Here is the OCR text from the document:\n\n{ocr_text}"
        
        return f"{system_prompt}\n\n{user_prompt}"
    
    def parse_document(
        self, 
        ocr_text: str,
        page_number: int = 1,
        context: Optional[Dict[str, Any]] = None
    ) -> LLMDocumentResult:
        """
        Parse document using LLM reconstruction.
        
        Args:
            ocr_text: Raw OCR text from PaddleOCR
            page_number: Page number for multi-page handling
            context: Optional context (previous page results, etc.)
            
        Returns:
            LLMDocumentResult with extracted data
        """
        start_time = time.time()
        
        try:
            # Call Ollama with retry logic
            llm_response = self._call_ollama_with_retry(ocr_text, context)
            
            if not llm_response:
                return self._create_error_result(
                    "LLM returned empty response",
                    start_time,
                    page_number
                )
            
            # Parse LLM JSON response
            result = self._parse_llm_response(llm_response, page_number)
            
            # Store OCR text length in metadata for debugging
            result.metadata['ocr_text_length'] = len(ocr_text)
            
            # Apply Python self-healing repair logic
            # Repair line items (fix quantities and totals)
            result.line_items = self._repair_line_items(result.line_items)
            
            # Filter footer/container text from line items
            result.line_items = self._filter_footer_lines(result.line_items)
            
            # Repair invoice number (extract from OCR if missing)
            # Repair invoice number, but prioritize printed numbers over internal IDs
            repaired_invoice_number = self._repair_invoice_number(result.invoice_number, ocr_text)
            
            # If repaired number looks like an internal ID (INV-xxx) and we have a printed number, prefer printed
            if repaired_invoice_number and repaired_invoice_number.startswith("INV-") and len(repaired_invoice_number) > 10:
                # Look for printed invoice number patterns in OCR text
                import re
                printed_patterns = [
                    r'invoice\s*[#:]?\s*([A-Za-z0-9\-\/]+)',
                    r'#\s*([0-9]{4,})',
                    r'Invoice\s+(?:No|Number|#)[:.\s]+([A-Z0-9_-]+)',
                ]
                
                for pattern in printed_patterns:
                    match = re.search(pattern, ocr_text[:2000], re.IGNORECASE)  # Check first 2000 chars (header zone)
                    if match:
                        candidate = match.group(1).strip().lstrip('#')
                        # Prefer numeric invoice numbers (e.g., 77212) over alphanumeric
                        if candidate and (candidate.isdigit() or len(candidate) < 15):
                            repaired_invoice_number = candidate
                            LOGGER.info(f"[REPAIR] Preferring printed invoice number '{candidate}' over internal ID")
                            break
            
            result.invoice_number = repaired_invoice_number
            
            # Clean supplier name (remove payment terms and noise)
            result.supplier_name = self._clean_supplier_name(result.supplier_name)
            
            # Verify math and calculate confidence
            result = self._verify_and_score(result)
            
            result.processing_time = time.time() - start_time
            
            LOGGER.info(
                f"LLM extraction complete: type={result.document_type.value}, "
                f"items={len(result.line_items)}, confidence={result.confidence:.3f}, "
                f"needs_review={getattr(result, 'needs_review', False)}, "
                f"time={result.processing_time:.2f}s"
            )
            
            return result
            
        except Exception as e:
            LOGGER.error(f"LLM parsing failed: {e}", exc_info=True)
            return self._create_error_result(str(e), start_time, page_number)
    
    def _call_ollama_with_retry(
        self, 
        ocr_text: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Call Ollama API with exponential backoff retry.
        
        Args:
            ocr_text: Raw OCR text
            context: Optional context
            
        Returns:
            LLM response text or None on failure
        """
        # Build prompt using the new extraction prompt method
        prompt_text = self._get_extraction_prompt(ocr_text)
        
        if context and context.get("previous_page_result"):
            prompt_text += f"\n\nContext: This may be a continuation of a previous page."
        
        # Prepare Ollama request
        payload = {
            "model": self.model_name,
            "prompt": prompt_text,
            "stream": False,
            "options": {
                "temperature": 0.0,  # Deterministic output
                "num_predict": 2048
            }
        }
        
        # Retry with exponential backoff
        for attempt in range(self.max_retries):
            try:
                LOGGER.info(f"[LLM_PARSER] Calling Ollama (attempt {attempt + 1}/{self.max_retries})...")
                LOGGER.info(f"[LLM_PARSER] Model: {self.model_name}, Timeout: {self.timeout}s")
                
                response = requests.post(
                    f"{self.ollama_url}/api/generate",
                    json=payload,
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    result = response.json()
                    llm_text = result.get("response", "")
                    # CRITICAL DEBUG: Log raw LLM response immediately after receiving it
                    LOGGER.info(f"[LLM_DEBUG] Raw Response (first 1000 chars): {llm_text[:1000]}")
                    LOGGER.info(f"[LLM_PARSER] SUCCESS - Response length: {len(llm_text)} chars")
                    # #region agent log
                    import json
                    log_path = Path(__file__).parent.parent.parent.parent / ".cursor" / "debug.log"
                    try:
                        with open(log_path, "a", encoding="utf-8") as f:
                            f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "B", "location": "invoice_parser.py:570", "message": "Ollama response success", "data": {"response_length": len(llm_text), "has_json": "{" in llm_text}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
                    except: pass
                    # #endregion
                    return llm_text
                else:
                    error_msg = f"Ollama returned HTTP {response.status_code}: {response.text[:200]}"
                    LOGGER.error(f"[LLM_PARSER] FAILED - {error_msg}")
                    # #region agent log
                    try:
                        with open(log_path, "a", encoding="utf-8") as f:
                            f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "B", "location": "invoice_parser.py:573", "message": "Ollama HTTP error", "data": {"status_code": response.status_code, "error": error_msg}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
                    except: pass
                    # #endregion
                    
            except requests.exceptions.Timeout as e:
                LOGGER.error(f"[LLM_PARSER] TIMEOUT after {self.timeout}s (attempt {attempt + 1}/{self.max_retries})")
                LOGGER.error(f"[LLM_PARSER] Timeout details: {str(e)}")
            except requests.exceptions.ConnectionError as e:
                LOGGER.error(f"[LLM_PARSER] CONNECTION ERROR (attempt {attempt + 1}/{self.max_retries})")
                LOGGER.error(f"[LLM_PARSER] Cannot reach Ollama at {self.ollama_url}")
                LOGGER.error(f"[LLM_PARSER] Error details: {str(e)}", exc_info=True)
                # #region agent log
                import json
                log_path = Path(__file__).parent.parent.parent.parent / ".cursor" / "debug.log"
                try:
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "B", "location": "invoice_parser.py:579", "message": "Ollama connection error", "data": {"ollama_url": self.ollama_url, "attempt": attempt + 1, "error": str(e)}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
                except: pass
                # #endregion
            except Exception as e:
                LOGGER.error(f"[LLM_PARSER] UNEXPECTED ERROR: {str(e)}", exc_info=True)
            
            # Exponential backoff
            if attempt < self.max_retries - 1:
                wait_time = 2 ** attempt
                LOGGER.warning(f"[LLM_PARSER] Retrying in {wait_time}s...")
                time.sleep(wait_time)
        
        LOGGER.error(f"[LLM_PARSER] FAILED after {self.max_retries} attempts - returning None")
        return None
    
    def _parse_llm_response(
        self, 
        llm_text: str, 
        page_number: int
    ) -> LLMDocumentResult:
        """
        Parse LLM JSON response into structured result.
        
        Robust JSON extraction that handles:
        - Markdown code blocks (```json ... ```)
        - Conversational text ("Here is the JSON: {...}")
        - Empty responses
        - Malformed JSON
        
        Args:
            llm_text: Raw LLM response text
            page_number: Page number
            
        Returns:
            LLMDocumentResult
        """
        import re
        
        try:
            # Step 1: Check for empty response
            if not llm_text or not llm_text.strip():
                error_msg = "LLM returned empty response"
                LOGGER.error(f"[LLM_PARSER] ✗ {error_msg}")
                LOGGER.error(f"[LLM_PARSER] Raw output sample: (empty)")
                raise ValueError(error_msg)
            
            # Step 2: Remove markdown code blocks
            cleaned_text = llm_text.strip()
            
            # Remove ```json ... ``` or ``` ... ```
            markdown_pattern = r'```(?:json)?\s*(.*?)\s*```'
            markdown_match = re.search(markdown_pattern, cleaned_text, re.DOTALL)
            if markdown_match:
                cleaned_text = markdown_match.group(1).strip()
                LOGGER.debug("[LLM_PARSER] Removed markdown code block")
            
            # Step 3: Find JSON object by locating first { and last }
            # This ignores conversational fluff like "Here is the JSON:" or "Sure! Here you go:"
            first_brace = cleaned_text.find('{')
            last_brace = cleaned_text.rfind('}')
            
            if first_brace == -1 or last_brace == -1 or first_brace >= last_brace:
                # No JSON object found - log the raw output for debugging
                error_msg = "No JSON object found in LLM response"
                LOGGER.error(f"[LLM_PARSER] ✗ JSON DECODE ERROR: {error_msg}")
                LOGGER.error(f"[LLM_PARSER] Raw output sample: {llm_text[:500]}")
                raise ValueError(f"{error_msg}. Response may be purely conversational or empty.")
            
            # Extract just the JSON portion
            json_text = cleaned_text[first_brace:last_brace + 1]
            LOGGER.debug(f"[LLM_PARSER] Extracted JSON from position {first_brace} to {last_brace}")
            
            # Step 4: Try to parse JSON
            try:
                data = json.loads(json_text)
            except json.JSONDecodeError as json_err:
                # Log detailed error with context - FULL raw text for debugging
                LOGGER.error(f"[LLM_PARSER] ✗ JSON DECODE ERROR: {json_err}")
                LOGGER.error(f"[LLM_DEBUG] FULL Raw Response: {llm_text}")
                LOGGER.error(f"[LLM_PARSER] Raw output sample: {llm_text[:500]}")
                LOGGER.error(f"[LLM_PARSER] Extracted JSON text: {json_text[:500]}")
                
                # Try to repair common issues
                repaired_json = self._repair_json(json_text)
                if repaired_json:
                    try:
                        data = json.loads(repaired_json)
                        LOGGER.info("[LLM_PARSER] ✓ JSON repair successful")
                    except json.JSONDecodeError:
                        raise ValueError(f"LLM returned invalid JSON (even after repair attempt): {json_err}")
                else:
                    raise ValueError(f"LLM returned invalid JSON: {json_err}")
            
            # Extract document type
            doc_type_str = data.get("document_type", "invoice").lower()
            try:
                doc_type = DocumentType(doc_type_str)
            except ValueError:
                doc_type = DocumentType.INVOICE
            
            # Extract line items
            line_items = []
            for idx, item_data in enumerate(data.get("line_items", [])):
                try:
                    line_item = LLMLineItem(
                        description=str(item_data.get("description", "Unknown item")),
                        qty=float(item_data.get("qty", 0)),
                        unit_price=float(item_data.get("unit_price", 0)),
                        total=float(item_data.get("total", 0)),
                        uom=str(item_data.get("uom", "")),
                        sku=str(item_data.get("sku", "")),
                        raw_text=json.dumps(item_data)
                    )
                    line_items.append(line_item)
                except (ValueError, KeyError) as e:
                    LOGGER.warning(f"Skipping invalid line item {idx}: {e}")
                    continue
            
            # Create result
            result = LLMDocumentResult(
                document_type=doc_type,
                supplier_name=str(data.get("supplier_name", "")),
                invoice_number=str(data.get("invoice_number", "")),
                invoice_date=str(data.get("invoice_date", "")),
                currency=str(data.get("currency", "GBP")),
                line_items=line_items,
                subtotal=float(data.get("subtotal", 0)),
                vat_amount=float(data.get("vat_amount", 0)),
                vat_rate=float(data.get("vat_rate", 0.2)),
                grand_total=float(data.get("grand_total", 0)),
                page_number=page_number,
                success=True
            )
            
            return result
            
        except json.JSONDecodeError as e:
            # This should be caught above, but just in case
            LOGGER.error(f"[LLM_PARSER] ✗ JSON DECODE ERROR: {e}")
            LOGGER.error(f"[LLM_PARSER] Raw output sample: {llm_text[:500]}")
            raise ValueError(f"LLM returned invalid JSON: {e}")
        except Exception as e:
            LOGGER.error(f"[LLM_PARSER] ✗ Failed to parse LLM response: {e}", exc_info=True)
            raise
    
    def _repair_json(self, json_text: str) -> Optional[str]:
        """
        Attempt to repair common JSON issues.
        
        Args:
            json_text: Potentially malformed JSON string
            
        Returns:
            Repaired JSON string or None if repair not possible
        """
        try:
            # Strip markdown code fences (coder models often wrap JSON in markdown)
            repaired = json_text.strip()
            markdown_pattern = r'```(?:json)?\s*(.*?)\s*```'
            markdown_match = re.search(markdown_pattern, repaired, re.DOTALL)
            if markdown_match:
                repaired = markdown_match.group(1).strip()
            
            # Remove trailing commas before closing braces/brackets
            repaired = re.sub(r',(\s*[}\]])', r'\1', repaired)
            
            # Fix single quotes to double quotes (basic attempt)
            # This is risky, so only do it if we detect single quotes
            if "'" in repaired and '"' not in repaired:
                repaired = repaired.replace("'", '"')
            
            # Try to parse to verify it's valid
            json.loads(repaired)
            return repaired
            
        except Exception:
            # Repair failed
            return None
    
    def _filter_footer_lines(self, items: List[LLMLineItem]) -> List[LLMLineItem]:
        """
        Filter out footer/container/policy text that was incorrectly extracted as line items.
        
        This post-processing step removes common noise patterns that the LLM might miss:
        - Container IDs and container lists
        - Return policy text (all caps)
        - Legal disclaimers
        
        Args:
            items: List of line items from LLM extraction
            
        Returns:
            Filtered list with footer/container text removed
        """
        filtered = []
        
        for item in items:
            desc_lower = item.description.lower()
            desc_upper = item.description.upper()
            
            # Skip container-related lines
            container_keywords = [
                "container",
                "containers",
                "delivered in containers",
                "containers outstanding",
                "container id",
                "container no",
                "container number",
                "container:",
            ]
            if any(keyword in desc_lower for keyword in container_keywords):
                LOGGER.info(f"[FILTER] Removed container line: '{item.description[:50]}...'")
                continue
            
            # Skip all-caps policy/legal text
            if desc_upper == item.description and len(item.description) > 20:
                policy_keywords = [
                    "RETURN",
                    "POLICY",
                    "TERMS",
                    "CONDITIONS",
                    "ACCEPT",
                    "UNSOLD",
                    "DO NOT",
                    "NO RETURNS",
                    "RETURNS NOT ACCEPTED",
                ]
                if any(keyword in desc_upper for keyword in policy_keywords):
                    LOGGER.info(f"[FILTER] Removed policy text: '{item.description[:50]}...'")
                    continue
            
            # Skip lines that are just numbers/IDs (likely container IDs)
            # Pattern: All caps alphanumeric, 6+ chars, no spaces or very few
            if (item.description.isupper() and 
                len(item.description.replace(" ", "")) >= 6 and
                item.description.replace(" ", "").isalnum() and
                item.qty == 0 and item.unit_price == 0 and item.total == 0):
                LOGGER.info(f"[FILTER] Removed ID-only line: '{item.description[:50]}...'")
                continue
            
            # Keep the item
            filtered.append(item)
        
        removed_count = len(items) - len(filtered)
        if removed_count > 0:
            LOGGER.info(f"[FILTER] Filtered {removed_count} footer/container lines, kept {len(filtered)} valid items")
        
        return filtered
    
    def _repair_line_items(self, items: List[LLMLineItem]) -> List[LLMLineItem]:
        """
        Repair line items by fixing quantities and totals using aggressive Python math.
        
        Aggressive Rules (in priority order):
        - PRIORITY 1: If Qty == 0 AND Unit Price > 0: Force Qty = 1, recalculate Total = Qty * Unit Price
        - If total is 0 but unit_price > 0: Force Qty = 1, Total = Unit Price
        - If qty is 0/None but total > 0 and unit_price > 0: calculate qty = total / unit_price
        - If qty is 0 after all attempts: Force Qty = 1, recalculate Total = Qty * Unit Price
        
        Args:
            items: List of line items to repair
            
        Returns:
            Repaired list of line items
        """
        repaired_items = []
        
        for item in items:
            original_qty = item.qty
            original_total = item.total
            
            # PRIORITY 1: Fix for Stori invoice - Qty=0 but Unit Price exists
            # Force Qty=1 when Qty=0 but Unit Price exists, then recalculate Total
            if (item.qty <= 0 or item.qty is None) and item.unit_price > 0:
                item.qty = 1.0
                item.total = round(item.qty * item.unit_price, 2)
                LOGGER.info(
                    f"[REPAIR] Fixed Zero Quantity (Stori fix): Set Qty=1, Total={item.total} for '{item.description[:50]}...' "
                    f"(unit_price={item.unit_price}, original_qty={original_qty}, original_total={original_total})"
                )
                repaired_items.append(item)
                continue
            
            # AGGRESSIVE FIX #1: Total is 0 but Unit Price exists
            # This handles the "Garbage In" case where LLM returns Total=0 but Unit Price is valid
            if (item.total <= 0 or item.total is None) and item.unit_price > 0:
                # Force Quantity = 1
                item.qty = 1.0
                # Force Total = Unit Price
                item.total = round(item.unit_price, 2)
                LOGGER.info(
                    f"[REPAIR] Fixed Zero Total: Set Qty=1, Total={item.total} for '{item.description[:50]}...' "
                    f"(unit_price={item.unit_price}, original_qty={original_qty}, original_total={original_total})"
                )
                repaired_items.append(item)
                continue
            
            # Fix quantity: if qty is 0/None but we have total and unit_price
            if (item.qty <= 0 or item.qty is None) and item.total > 0 and item.unit_price > 0:
                try:
                    calculated_qty = item.total / item.unit_price
                    item.qty = round(calculated_qty, 2)
                    LOGGER.info(
                        f"[REPAIR] Fixed qty for '{item.description[:50]}...': "
                        f"{original_qty} -> {item.qty} (calculated from total={item.total} / unit_price={item.unit_price})"
                    )
                except (ZeroDivisionError, ValueError) as e:
                    LOGGER.warning(f"[REPAIR] Failed to calculate qty for '{item.description[:50]}...': {e}")
            
            # Fix total: if total is 0 but we have qty and unit_price
            if (item.total <= 0 or item.total is None) and item.qty > 0 and item.unit_price > 0:
                try:
                    calculated_total = item.qty * item.unit_price
                    item.total = round(calculated_total, 2)
                    LOGGER.info(
                        f"[REPAIR] Fixed total for '{item.description[:50]}...': "
                        f"{original_total} -> {item.total} (calculated from qty={item.qty} * unit_price={item.unit_price})"
                    )
                except (ValueError, TypeError) as e:
                    LOGGER.warning(f"[REPAIR] Failed to calculate total for '{item.description[:50]}...': {e}")
            
            # AGGRESSIVE FIX #2: Quantity is still 0 after all attempts
            if (item.qty <= 0 or item.qty is None):
                item.qty = 1.0
                # Recalculate total if we have unit_price
                if item.unit_price > 0:
                    item.total = round(item.qty * item.unit_price, 2)
                    LOGGER.info(
                        f"[REPAIR] Defaulted qty to 1.0 and recalculated total={item.total} for '{item.description[:50]}...' "
                        f"(original_qty={original_qty}, original_total={original_total}, unit_price={item.unit_price})"
                    )
                else:
                    LOGGER.info(
                        f"[REPAIR] Defaulted qty to 1.0 for '{item.description[:50]}...' "
                        f"(original_qty={original_qty}, original_total={original_total}, unit_price={item.unit_price})"
                    )
            
            repaired_items.append(item)
        
        return repaired_items
    
    def _repair_invoice_number(self, extracted_num: str, ocr_text: str) -> str:
        """
        Extract invoice number from OCR text if LLM missed it.
        
        Args:
            extracted_num: Invoice number from LLM (may be empty)
            ocr_text: Raw OCR text to search
            
        Returns:
            Invoice number (extracted or original)
        """
        # If LLM already extracted a valid invoice number, use it
        if extracted_num and extracted_num.strip() and extracted_num.lower() not in ['null', 'none', 'n/a', '']:
            return extracted_num.strip()
        
        # Search OCR text with multiple regex patterns
        patterns = [
            r'\bVAT\s+Invoice\s+([A-Za-z0-9\-\/]+)',  # VAT Invoice 99471 (high priority)
            r'Invoice\s*#\s*([A-Za-z0-9\-\/]+)',  # Invoice #77212
            r'Invoice\s*(?:No|Number|#)?\s*[:.]?\s*([A-Z0-9-]{3,})',
            r'INV[-\s]?([A-Z0-9-]{3,})',
            r'Invoice\s*([A-Z]{2,}\d{4,})',
            r'Invoice\s*#?\s*([A-Z0-9]{4,})',
            r'INV[-\s]?([A-Z0-9]{4,})',
            r'Invoice\s*(?:Number|No\.?)\s*:?\s*([A-Z0-9-]+)',
        ]
        
        for pattern in patterns:
            try:
                match = re.search(pattern, ocr_text, re.IGNORECASE)
                if match:
                    invoice_num = match.group(1).strip()
                    if invoice_num and len(invoice_num) >= 3:
                        LOGGER.info(f"[REPAIR] Extracted invoice number from OCR: '{invoice_num}' (pattern: {pattern})")
                        return invoice_num
            except Exception as e:
                LOGGER.debug(f"[REPAIR] Pattern {pattern} failed: {e}")
                continue
        
        # Fallback: Look for INV-\w+ or \d{4,} near the top of the text (first 2000 chars)
        # Invoice numbers are typically near the top of the document
        top_text = ocr_text[:2000] if len(ocr_text) > 2000 else ocr_text
        
        # Try INV-\w+ pattern (e.g., INV-1f0ad2f8)
        try:
            inv_pattern = r'INV-(\w+)'
            match = re.search(inv_pattern, top_text, re.IGNORECASE)
            if match:
                invoice_num = f"INV-{match.group(1)}"
                LOGGER.info(f"[REPAIR] Extracted invoice number from OCR (fallback INV-): '{invoice_num}'")
                return invoice_num
        except Exception as e:
            LOGGER.debug(f"[REPAIR] Fallback INV- pattern failed: {e}")
        
        # Try \d{4,} pattern (4+ digit numbers, often invoice numbers)
        try:
            digit_pattern = r'\b(\d{4,})\b'
            match = re.search(digit_pattern, top_text)
            if match:
                invoice_num = match.group(1)
                LOGGER.info(f"[REPAIR] Extracted invoice number from OCR (fallback digits): '{invoice_num}'")
                return invoice_num
        except Exception as e:
            LOGGER.debug(f"[REPAIR] Fallback digit pattern failed: {e}")
        
        # No invoice number found
        LOGGER.debug(f"[REPAIR] Could not extract invoice number from OCR text")
        return extracted_num if extracted_num else ""
    
    def _clean_supplier_name(self, name: str) -> str:
        """
        Clean supplier name by removing payment terms and other noise.
        
        Args:
            name: Raw supplier name from LLM
            
        Returns:
            Cleaned supplier name
        """
        if not name or not name.strip():
            return name
        
        original_name = name.strip()
        cleaned = original_name
        
        # Keywords that indicate we should split and keep only the part before
        # Case-insensitive matching - order matters (longer patterns first)
        split_keywords = [
            "& PAYMENT TERMS",
            "PAYMENT TERMS &",
            "& PAYMENT",
            "PAYMENT &",
            "& TERMS",
            "TERMS &",
            "PAYMENT TERMS",
            "Payment Terms",
            "TERMS",
            "Terms",
            "PAYMENT",
            "Payment",
            "Due Date",
            "DUE DATE",
            "Due date",
        ]
        
        # Check if name contains any split keywords (case-insensitive)
        cleaned_lower = cleaned.lower()
        for keyword in split_keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in cleaned_lower:
                # Find the position in the original string (case-insensitive)
                idx = cleaned_lower.find(keyword_lower)
                if idx > 0:
                    # Split on the keyword and keep only the part before it
                    cleaned = cleaned[:idx].strip()
                    LOGGER.info(f"[REPAIR] Cleaned supplier name: '{original_name}' -> '{cleaned}' (removed '{keyword}' and following text)")
                    break
        
        # Regex fallback for complex patterns (e.g., "Snowdonia Hospitality & TERMS & PAYMENT")
        # This handles cases where multiple keywords appear or patterns are more complex
        if cleaned == original_name:
            # Try regex patterns for more flexible matching
            regex_patterns = [
                r'(.+?)\s*[&]\s*(?:TERMS|PAYMENT|PAYMENT\s+TERMS).*$',  # "Name & TERMS" or "Name & PAYMENT"
                r'(.+?)\s+(?:TERMS|PAYMENT|PAYMENT\s+TERMS)\s*[&].*$',  # "Name TERMS &" or "Name PAYMENT &"
                r'(.+?)\s+(?:DUE\s+)?DATE.*$',  # "Name DUE DATE" or "Name DATE"
            ]
            
            for pattern in regex_patterns:
                try:
                    match = re.search(pattern, cleaned, re.IGNORECASE)
                    if match:
                        potential_cleaned = match.group(1).strip()
                        # Only use if it's shorter and seems reasonable (at least 3 chars)
                        if len(potential_cleaned) >= 3 and len(potential_cleaned) < len(cleaned):
                            cleaned = potential_cleaned
                            LOGGER.info(f"[REPAIR] Cleaned supplier name (regex): '{original_name}' -> '{cleaned}' (pattern: {pattern})")
                            break
                except Exception as e:
                    LOGGER.debug(f"[REPAIR] Regex pattern {pattern} failed: {e}")
                    continue
        
        # Remove trailing punctuation and clean up
        cleaned = cleaned.rstrip('.,;:')
        cleaned = cleaned.strip()
        
        # If we made changes, log it
        if cleaned != original_name:
            LOGGER.info(f"[REPAIR] Final cleaned supplier name: '{original_name}' -> '{cleaned}'")
        
        return cleaned
    
    def _verify_and_score(self, result: LLMDocumentResult) -> LLMDocumentResult:
        """
        Verify math and calculate confidence score.
        
        NEW: Implements hard validation gate - if relative error between calculated
        and extracted totals exceeds LLM_VALIDATION_ERROR_THRESHOLD (default 10%),
        the invoice is marked as needs_review=True and confidence is capped at 0.5.
        
        Args:
            result: Parsed LLM result
            
        Returns:
            Result with verified data, confidence score, and needs_review flag
        """
        from backend.config import LLM_VALIDATION_ERROR_THRESHOLD
        
        # Start with perfect confidence
        confidence = 1.0
        
        # Verify line item math
        math_errors = 0
        for item in result.line_items:
            expected_total = item.qty * item.unit_price
            actual_total = item.total
            
            # Allow 1 penny tolerance for rounding
            if abs(expected_total - actual_total) > 0.01:
                LOGGER.warning(
                    f"Math error in '{item.description[:30]}...': "
                    f"expected {expected_total:.2f}, got {actual_total:.2f}"
                )
                math_errors += 1
                # Auto-fix the total
                item.total = expected_total
                item.confidence *= 0.9
        
        # Penalize for math errors
        if result.line_items:
            math_penalty = (math_errors / len(result.line_items)) * 0.3
            confidence -= math_penalty
        
        # Verify totals - HARD VALIDATION GATE
        validation_errors = []
        needs_review = False
        
        if result.line_items:
            calculated_subtotal = sum(item.total for item in result.line_items)
            
            # Check subtotal
            if result.subtotal > 0:
                subtotal_error = abs(calculated_subtotal - result.subtotal) / result.subtotal
                if subtotal_error > LLM_VALIDATION_ERROR_THRESHOLD:
                    validation_errors.append(
                        f"Subtotal error: {subtotal_error*100:.1f}% "
                        f"(calculated {calculated_subtotal:.2f} vs extracted {result.subtotal:.2f})"
                    )
                    needs_review = True
                    LOGGER.error(
                        f"[VALIDATION] HARD GATE TRIGGERED: Subtotal error {subtotal_error*100:.1f}% "
                        f"exceeds threshold {LLM_VALIDATION_ERROR_THRESHOLD*100:.1f}%"
                    )
                elif abs(calculated_subtotal - result.subtotal) > 0.01:
                    # Smaller error - auto-fix but log warning
                    LOGGER.warning(
                        f"Subtotal mismatch: calculated {calculated_subtotal:.2f}, "
                        f"extracted {result.subtotal:.2f}"
                    )
                    result.subtotal = calculated_subtotal
                    confidence -= 0.1
            else:
                # No subtotal extracted - use calculated
                result.subtotal = calculated_subtotal
            
            # Check grand total (most critical)
            calculated_grand = result.subtotal + result.vat_amount
            if result.grand_total > 0:
                grand_error = abs(calculated_grand - result.grand_total) / result.grand_total
                if grand_error > LLM_VALIDATION_ERROR_THRESHOLD:
                    validation_errors.append(
                        f"Grand total error: {grand_error*100:.1f}% "
                        f"(calculated {calculated_grand:.2f} vs extracted {result.grand_total:.2f})"
                    )
                    needs_review = True
                    LOGGER.error(
                        f"[VALIDATION] HARD GATE TRIGGERED: Grand total error {grand_error*100:.1f}% "
                        f"exceeds threshold {LLM_VALIDATION_ERROR_THRESHOLD*100:.1f}%"
                    )
                    LOGGER.error(
                        f"[VALIDATION] This invoice will be marked as needs_review=True "
                        f"(confidence capped at 0.5)"
                    )
                elif abs(calculated_grand - result.grand_total) > 0.01:
                    # Smaller error - auto-fix but log warning
                    LOGGER.warning(
                        f"Grand total mismatch: calculated {calculated_grand:.2f}, "
                        f"extracted {result.grand_total:.2f}"
                    )
                    result.grand_total = calculated_grand
                    confidence -= 0.1
            else:
                # No grand total extracted - use calculated
                result.grand_total = calculated_grand
        
        # Penalize for missing critical fields
        if not result.supplier_name:
            confidence -= 0.05
        if not result.invoice_number:
            confidence -= 0.05
        if not result.invoice_date:
            confidence -= 0.05
        if not result.line_items:
            confidence -= 0.3
        
        # Ensure confidence is in valid range
        confidence = max(0.0, min(1.0, confidence))
        
        # HARD GATE: If validation errors exceed threshold, cap confidence and mark for review
        if needs_review:
            confidence = min(confidence, 0.5)  # Cap at 0.5 for review items
            result.metadata["needs_review"] = True
            result.metadata["review_reason"] = "; ".join(validation_errors)
            result.metadata["validation_errors"] = validation_errors
            LOGGER.warning(
                f"[VALIDATION] Invoice marked for review: {len(validation_errors)} validation error(s), "
                f"confidence capped at {confidence:.3f}"
            )
        elif confidence < 0.6:
            # Low confidence but within math tolerance - still mark for review
            result.metadata["needs_review"] = True
            result.metadata["review_reason"] = "Low confidence after verification"
        
        # Add needs_review as a direct attribute for easier access
        result.needs_review = needs_review or (confidence < 0.6)
        
        result.confidence = confidence
        
        return result
    
    def _create_error_result(
        self, 
        error_message: str, 
        start_time: float,
        page_number: int
    ) -> LLMDocumentResult:
        """Create error result."""
        return LLMDocumentResult(
            document_type=DocumentType.UNKNOWN,
            success=False,
            error_message=error_message,
            confidence=0.0,
            processing_time=time.time() - start_time,
            page_number=page_number
        )
    
    def is_continuation(
        self, 
        page1_result: LLMDocumentResult, 
        page2_result: LLMDocumentResult
    ) -> bool:
        """
        Determine if page2 is a continuation of page1.
        
        Args:
            page1_result: Result from page 1
            page2_result: Result from page 2
            
        Returns:
            True if page2 continues page1
        """
        # If page2 has no header fields but has line items, likely continuation
        if (not page2_result.supplier_name and 
            not page2_result.invoice_number and
            page2_result.line_items):
            LOGGER.info("Page 2 has line items but no header - likely continuation")
            return True
        
        # If page2 has no totals but page1 does, likely continuation
        if page1_result.grand_total > 0 and page2_result.grand_total == 0:
            if page2_result.line_items:
                LOGGER.info("Page 2 has no totals - likely continuation")
                return True
        
        # If same invoice number, likely continuation
        if (page1_result.invoice_number and 
            page2_result.invoice_number and
            page1_result.invoice_number == page2_result.invoice_number):
            LOGGER.info(f"Same invoice number {page1_result.invoice_number} - likely continuation")
            return True
        
        return False
    
    def merge_pages(
        self, 
        pages: List[LLMDocumentResult]
    ) -> LLMDocumentResult:
        """
        Merge multiple page results into single document.
        
        Args:
            pages: List of page results to merge
            
        Returns:
            Combined document result
        """
        if not pages:
            return self._create_error_result("No pages to merge", 0, 1)
        
        if len(pages) == 1:
            return pages[0]
        
        # Use first page as base
        merged = pages[0]
        
        # Append line items from subsequent pages
        for page in pages[1:]:
            merged.line_items.extend(page.line_items)
            # Use last page's totals (they're usually on the final page)
            if page.grand_total > 0:
                merged.subtotal = page.subtotal
                merged.vat_amount = page.vat_amount
                merged.grand_total = page.grand_total
        
        # Re-verify merged result
        merged = self._verify_and_score(merged)
        merged.metadata["merged_from_pages"] = len(pages)
        
        LOGGER.info(f"Merged {len(pages)} pages into single document with {len(merged.line_items)} items")
        
        return merged
    
    def split_documents(
        self, 
        page_results: List[LLMDocumentResult]
    ) -> List[DocumentGroup]:
        """
        Split multi-document PDF into separate document groups.
        
        Example: Page 1 = Invoice, Page 2 = Delivery Note → Split into 2 groups
        
        Args:
            page_results: List of parsed page results
            
        Returns:
            List of DocumentGroup objects
        """
        if not page_results:
            return []
        
        groups: List[DocumentGroup] = []
        current_group_pages: List[int] = []
        current_group_results: List[LLMDocumentResult] = []
        
        for idx, page_result in enumerate(page_results):
            page_num = idx + 1
            
            # Check if this starts a new document
            is_new_document = False
            
            if idx == 0:
                # First page always starts a document
                is_new_document = True
            else:
                prev_result = page_results[idx - 1]
                
                # Different document type = new document
                if page_result.document_type != prev_result.document_type:
                    LOGGER.info(
                        f"Page {page_num} has different type "
                        f"({page_result.document_type.value} vs {prev_result.document_type.value}) "
                        f"- splitting documents"
                    )
                    is_new_document = True
                
                # Different supplier name = new document (strong indicator)
                elif (page_result.supplier_name and 
                      prev_result.supplier_name and
                      page_result.supplier_name.strip().upper() != prev_result.supplier_name.strip().upper()):
                    LOGGER.info(
                        f"Page {page_num} has different supplier "
                        f"('{page_result.supplier_name}' vs '{prev_result.supplier_name}') "
                        f"- splitting documents"
                    )
                    is_new_document = True
                
                # Different invoice number = new document (when both present)
                elif (page_result.invoice_number and 
                      prev_result.invoice_number and
                      page_result.invoice_number.strip() != prev_result.invoice_number.strip()):
                    LOGGER.info(
                        f"Page {page_num} has different invoice number "
                        f"('{page_result.invoice_number}' vs '{prev_result.invoice_number}') "
                        f"- splitting documents"
                    )
                    is_new_document = True
                
                # New invoice number appears (previous had none) = new document
                elif (page_result.invoice_number and 
                      not prev_result.invoice_number and
                      page_result.supplier_name):
                    # Only if this page has both supplier and invoice number (complete header)
                    LOGGER.info(
                        f"Page {page_num} has new invoice number '{page_result.invoice_number}' "
                        f"(previous had none) - splitting documents"
                    )
                    is_new_document = True
                
                # Check for continuation indicators
                elif self.is_continuation(prev_result, page_result):
                    # This is a continuation - keep in same group
                    is_new_document = False
                    LOGGER.debug(
                        f"Page {page_num} is continuation of page {idx} "
                        f"(same invoice '{prev_result.invoice_number or 'N/A'}')"
                    )
                
                # Has full header but previous page had different header = new document
                elif (page_result.supplier_name and page_result.invoice_number and
                      prev_result.supplier_name and prev_result.invoice_number):
                    # Both have headers - check if they match
                    if (page_result.supplier_name.strip().upper() != prev_result.supplier_name.strip().upper() or
                        page_result.invoice_number.strip() != prev_result.invoice_number.strip()):
                        LOGGER.info(
                            f"Page {page_num} has different header than previous page - splitting documents"
                        )
                        is_new_document = True
                    # Otherwise, same header = continuation (multi-page invoice)
                
                # Has full header but previous page had no header = likely new document
                elif (page_result.supplier_name and page_result.invoice_number and
                      (not prev_result.supplier_name or not prev_result.invoice_number)):
                    # Previous page was incomplete, this has full header = new document
                    LOGGER.info(
                        f"Page {page_num} has full header (previous incomplete) - splitting documents"
                    )
                    is_new_document = True
            
            if is_new_document and current_group_pages:
                # Save previous group
                combined = self.merge_pages(current_group_results)
                groups.append(DocumentGroup(
                    document_type=combined.document_type,
                    pages=current_group_pages.copy(),
                    combined_result=combined
                ))
                current_group_pages = []
                current_group_results = []
            
            # Add to current group
            current_group_pages.append(page_num)
            current_group_results.append(page_result)
        
        # Save final group
        if current_group_pages:
            combined = self.merge_pages(current_group_results)
            groups.append(DocumentGroup(
                document_type=combined.document_type,
                pages=current_group_pages,
                combined_result=combined
            ))
        
        LOGGER.info(f"Split {len(page_results)} pages into {len(groups)} document groups")
        
        return groups


def _auto_detect_model(ollama_url: str) -> Optional[str]:
    """
    Auto-detect best available model from Ollama.
    
    Args:
        ollama_url: Ollama API URL
        
    Returns:
        Model name or None if no models available
    """
    try:
        import requests
        
        response = requests.get(f"{ollama_url}/api/tags", timeout=5)
        if response.status_code == 200:
            data = response.json()
            available_models = [m.get("name", "") for m in data.get("models", [])]
            
            if not available_models:
                LOGGER.warning("No Ollama models available")
                return None
            
            # Try to import fallback list from config
            try:
                from backend.config import LLM_MODEL_FALLBACK_LIST
                fallback_list = LLM_MODEL_FALLBACK_LIST
            except ImportError:
                fallback_list = [
                    "qwen2.5-coder:7b",
                    "llama3:8b",
                    "llama3:latest",
                    "mistral:latest"
                ]
            
            # Find first match from fallback list
            for preferred in fallback_list:
                if preferred in available_models:
                    LOGGER.info(f"Auto-detected model: {preferred}")
                    return preferred
            
            # Use first available model
            first_model = available_models[0]
            LOGGER.info(f"Using first available model: {first_model}")
            return first_model
            
        else:
            LOGGER.warning(f"Failed to query Ollama models: HTTP {response.status_code}")
            return None
            
    except Exception as e:
        LOGGER.warning(f"Model auto-detection failed: {e}")
        return None


# Factory function for easy instantiation
def create_invoice_parser(
    ollama_url: Optional[str] = None,
    model_name: Optional[str] = None,
    timeout: Optional[int] = None,
    max_retries: Optional[int] = None
) -> LLMInvoiceParser:
    """
    Create LLM invoice parser with config from backend.config.
    Auto-detects best available model if not specified.
    
    Args:
        ollama_url: Override default Ollama URL
        model_name: Override default model name
        timeout: Override default timeout
        max_retries: Override default max retries
        
    Returns:
        Configured LLMInvoiceParser instance
    """
    try:
        from backend.config import (
            env_str, env_int,
            LLM_OLLAMA_URL, LLM_MODEL_NAME, 
            LLM_TIMEOUT_SECONDS, LLM_MAX_RETRIES
        )
        
        url = ollama_url or LLM_OLLAMA_URL
        model = model_name or LLM_MODEL_NAME
        
        # Auto-detect model if not specified or empty
        if not model or model == "":
            LOGGER.info("No model specified, auto-detecting...")
            detected_model = _auto_detect_model(url)
            if detected_model:
                model = detected_model
            else:
                # Ultimate fallback
                model = "qwen2.5-coder:7b"
                LOGGER.warning(f"Auto-detection failed, using fallback: {model}")
        
        return LLMInvoiceParser(
            ollama_url=url,
            model_name=model,
            timeout=timeout or LLM_TIMEOUT_SECONDS,
            max_retries=max_retries or LLM_MAX_RETRIES
        )
    except ImportError:
        # Fallback if config not available
        url = ollama_url or "http://localhost:11434"
        model = model_name
        
        if not model:
            detected_model = _auto_detect_model(url)
            model = detected_model or "qwen2.5-coder:7b"
        
        return LLMInvoiceParser(
            ollama_url=url,
            model_name=model,
            timeout=timeout or 30,
            max_retries=max_retries or 3
        )

