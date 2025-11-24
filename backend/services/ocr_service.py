# MOCK REMOVED: returns only real OCR/DB data
"""
OCR Service - Orchestrates document OCR processing with full lifecycle tracking
"""
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
import json

from backend.app.db import update_document_status, insert_line_items, upsert_invoice, append_audit, clear_last_error
from backend.config import FEATURE_OCR_PIPELINE_V2, env_bool

logger = logging.getLogger("owlin.services.ocr")

# Constants for defensive parsing
MAX_LINE_ITEMS = 500

def _normalize_currency(value: str | float | None) -> float | None:
    """Normalize currency to numeric float, return None if cannot parse"""
    if value is None:
        return None
    
    if isinstance(value, (int, float)):
        return float(value)
    
    if not isinstance(value, str):
        return None
    
    import re
    # Strip currency symbols and commas
    cleaned = re.sub(r'[£€$,\s]', '', str(value)).strip()
    
    try:
        return float(cleaned)
    except ValueError:
        return None

def _normalize_date(date_str: str | None) -> str | None:
    """Normalize to ISO YYYY-MM-DD, return None if cannot parse"""
    if not date_str:
        return None
    
    try:
        from dateutil import parser
        dt = parser.parse(date_str)
        return dt.strftime('%Y-%m-%d')
    except:
        return None

def _deduplicate_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Deduplicate line items by (description, qty, unit_price, total) hash"""
    seen = set()
    deduped = []
    
    for item in items:
        # Create hash key from normalized fields
        desc = str(item.get('desc', '')).strip().lower()
        qty = item.get('qty', 0)
        unit_price = item.get('unit_price', 0)
        total = item.get('total', 0)
        
        key = (desc, qty, unit_price, total)
        
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    
    return deduped

def _log_lifecycle(stage: str, doc_id: str, **kwargs):
    """Log OCR lifecycle marker with structured key=value format"""
    timestamp = datetime.now().isoformat()
    
    # Build key=value pairs
    pairs = [f"stage={stage}", f"doc_id={doc_id}"]
    for key, value in kwargs.items():
        if value is not None:
            # Format floats with 2 decimals
            if isinstance(value, float):
                pairs.append(f"{key}={value:.2f}")
            else:
                pairs.append(f"{key}={value}")
    
    marker = "[OCR_LIFECYCLE] " + " ".join(pairs)
    logger.info(marker)
    
    # Audit trail
    audit_detail = {"doc_id": doc_id, "stage": stage}
    audit_detail.update(kwargs)
    append_audit(timestamp, "ocr_service", stage, json.dumps(audit_detail))
    
    print(marker)  # Ensure it shows in console logs

def process_document_ocr(doc_id: str, file_path: str) -> Dict[str, Any]:
    """
    Process a document through the complete OCR pipeline.
    
    Args:
        doc_id: Document ID
        file_path: Path to the uploaded file
        
    Returns:
        Dict with status, confidence, extracted data, and line_items
    """
    _log_lifecycle("UPLOAD_SAVED", doc_id, file=file_path)
    
    try:
        # Update status to processing
        update_document_status(doc_id, "processing", "ocr_enqueue")
        _log_lifecycle("OCR_ENQUEUE", doc_id)
        
        # MOCK REMOVED: Force v2 pipeline only - no mock fallback
        use_v2_pipeline = env_bool("FEATURE_OCR_PIPELINE_V2", True)  # Default to True to force real OCR
        
        if not use_v2_pipeline:
            raise Exception("OCR v2 pipeline is required. Mock pipeline has been removed. Set FEATURE_OCR_PIPELINE_V2=true to enable real OCR processing.")
        
        result = _process_with_v2_pipeline(doc_id, file_path)
        return result
        
    except Exception as e:
        error_msg = str(e)
        logger.exception(f"OCR processing failed for doc_id={doc_id}")
        update_document_status(doc_id, "error", "ocr_error", error=error_msg)
        _log_lifecycle("OCR_ERROR", doc_id, error=error_msg)
        
        return {
            "status": "error",
            "doc_id": doc_id,
            "error": error_msg,
            "confidence": 0.0,
            "line_items": []
        }

def _process_with_v2_pipeline(doc_id: str, file_path: str) -> Dict[str, Any]:
    """Process using the full OCR v2 pipeline
    
    Handles both invoices and delivery notes:
    - Performs OCR extraction
    - Classifies document type (invoice vs delivery_note)
    - Creates invoice/delivery note cards for UI
    - Triggers pairing suggestions (via backend.matching.pairing module)
    """
    import os
    from pathlib import Path
    
    # Verify file exists
    if not os.path.exists(file_path):
        error_msg = f"File not found: {file_path}"
        logger.error(f"[OCR_V2] {error_msg} for doc_id={doc_id}")
        raise Exception(error_msg)
    
    _log_lifecycle("OCR_PICK", doc_id, pipeline="v2", file=file_path)
    update_document_status(doc_id, "processing", "ocr_start")
    _log_lifecycle("OCR_START", doc_id)
    
    try:
        from backend.ocr.owlin_scan_pipeline import process_document as process_doc_ocr
    except ImportError as e:
        error_msg = f"Failed to import OCR pipeline: {e}"
        logger.error(f"[OCR_V2] {error_msg} for doc_id={doc_id}")
        raise Exception(error_msg)
    
    # Run OCR pipeline
    try:
        logger.info(f"[OCR_V2] Calling process_document for doc_id={doc_id}, file={file_path}")
        ocr_result = process_doc_ocr(file_path)
        logger.info(f"[OCR_V2] OCR result status: {ocr_result.get('status')}, confidence: {ocr_result.get('confidence', 0)}")
    except Exception as e:
        error_msg = f"OCR pipeline execution failed: {str(e)}"
        logger.exception(f"[OCR_V2] {error_msg} for doc_id={doc_id}")
        raise Exception(error_msg)
    
    if ocr_result.get("status") == "error":
        error_detail = ocr_result.get("error", "OCR processing failed")
        logger.error(f"[OCR_V2] OCR pipeline returned error: {error_detail} for doc_id={doc_id}")
        raise Exception(f"OCR pipeline error: {error_detail}")
    
    confidence = ocr_result.get('confidence', 0.0)
    _log_lifecycle("OCR_DONE", doc_id, confidence=confidence)
    
    # Extract invoice data from OCR result
    pages = ocr_result.get("pages", [])
    
    # DEBUG: Log OCR result structure
    logger.info(f"[OCR_V2] OCR result keys: {list(ocr_result.keys())}")
    logger.info(f"[OCR_V2] Pages count: {len(pages)}")
    logger.info(f"[OCR_V2] Overall confidence: {ocr_result.get('confidence', 'N/A')}")
    
    if not pages:
        # Provide more helpful error - check if PyMuPDF is missing
        import sys
        try:
            import fitz
            fitz_available = True
        except ImportError:
            fitz_available = False
        
        error_msg = "No pages extracted from document. "
        if not fitz_available:
            error_msg += "PyMuPDF (fitz) is not installed - required for PDF processing. Install with: pip install PyMuPDF"
        else:
            error_msg += f"File may be corrupted or unsupported format. File path: {file_path}"
        
        logger.error(f"[OCR_V2] {error_msg} for doc_id={doc_id}")
        logger.error(f"[OCR_V2] OCR result keys: {list(ocr_result.keys())}, pages count: {len(pages)}")
        raise Exception(error_msg)
    
    # Parse first page for now (multi-page handling can be added later)
    page = pages[0]
    
    # DEBUG: Log page structure
    logger.info(f"[OCR_V2] Processing first page. Page type: {type(page)}, is dict: {isinstance(page, dict)}")
    if isinstance(page, dict):
        logger.info(f"[OCR_V2] Page keys: {list(page.keys())}")
        logger.info(f"[OCR_V2] Page has 'blocks': {'blocks' in page}")
        logger.info(f"[OCR_V2] Page has 'text': {'text' in page}")
        logger.info(f"[OCR_V2] Page has 'ocr_text': {'ocr_text' in page}")
        if 'blocks' in page:
            blocks_list = page.get('blocks', [])
            logger.info(f"[OCR_V2] Page blocks count: {len(blocks_list)}")
            # Log details about each block
            for i, b in enumerate(blocks_list[:5]):  # Log first 5 blocks
                if isinstance(b, dict):
                    logger.info(f"[OCR_V2] Block {i}: type='{b.get('type')}', has_table_data={b.get('table_data') is not None}, table_data_type={type(b.get('table_data'))}")
                    if b.get('table_data'):
                        td = b.get('table_data')
                        if isinstance(td, dict):
                            logger.info(f"[OCR_V2] Block {i} table_data keys: {list(td.keys())}, line_items count: {len(td.get('line_items', []))}")
                else:
                    logger.info(f"[OCR_V2] Block {i}: type={type(b)}, has_type_attr={hasattr(b, 'type')}")
    
    parsed_data = _extract_invoice_data_from_page(page)
    
    # DEBUG: Log extracted data
    logger.info(f"[OCR_V2] Extracted data: supplier='{parsed_data.get('supplier')}', date='{parsed_data.get('date')}', total={parsed_data.get('total')}")
    
    # Classify document type based on OCR text
    from backend.matching.pairing import classify_doc
    # Re-extract full_text for classification (handle both dict and object formats)
    if hasattr(page, 'blocks'):
        classify_blocks = list(page.blocks) if hasattr(page, 'blocks') and page.blocks else []
        classify_text_parts = []
        for block in classify_blocks:
            if hasattr(block, 'ocr_text'):
                text = getattr(block, 'ocr_text', '') or getattr(block, 'text', '')
            else:
                text = block.get("ocr_text", block.get("text", ""))
            if text:
                classify_text_parts.append(text)
        classify_full_text = "\n".join(classify_text_parts)
    else:
        classify_full_text = "\n".join([block.get("ocr_text", block.get("text", "")) 
                                      for block in page.get("blocks", []) 
                                      if block.get("ocr_text") or block.get("text")])
    doc_type = classify_doc(classify_full_text) if classify_full_text else "invoice"
    
    # Store document type for potential pairing
    parsed_data["doc_type"] = doc_type
    
    _log_lifecycle("PARSE_START", doc_id, doc_type=doc_type)
    
    # Extract and normalize line items (pass parsed_data so STORI items can be reused)
    logger.info(f"[LINE_ITEMS] Starting line item extraction for doc_id={doc_id}")
    line_items = _extract_line_items_from_page(page, parsed_data)
    logger.info(f"[LINE_ITEMS] Extracted {len(line_items)} line items before deduplication")
    
    line_items = _deduplicate_items(line_items)
    logger.info(f"[LINE_ITEMS] After deduplication: {len(line_items)} line items")
    
    # Truncate if exceeds limit
    original_count = len(line_items)
    if original_count > MAX_LINE_ITEMS:
        logger.warning(f"[ITEMS_TRUNCATED] doc_id={doc_id} count={original_count} limit={MAX_LINE_ITEMS}")
        line_items = line_items[:MAX_LINE_ITEMS]
    
    _log_lifecycle("PARSE_DONE", doc_id, items=len(line_items), original_count=original_count)
    
    # DEBUG: Log sample line items
    if line_items:
        logger.info(f"[LINE_ITEMS] Sample first item: {line_items[0]}")
    
    # Store invoice in database
    invoice_id = doc_id  # Use doc_id as invoice_id
    confidence = ocr_result.get("confidence", parsed_data.get("confidence", 0.9))
    
    # DEBUG: Log what we're storing
    supplier = parsed_data.get("supplier", "Unknown Supplier")
    date = parsed_data.get("date", datetime.now().strftime("%Y-%m-%d"))
    total = parsed_data.get("total", 0.0)
    
    logger.info(f"[STORE] Storing invoice: supplier='{supplier}', date='{date}', total={total}, confidence={confidence}")
    
    upsert_invoice(
        doc_id=doc_id,
        supplier=supplier,
        date=date,
        value=total
    )
    
    # Verify invoice was stored
    import sqlite3
    conn = sqlite3.connect("data/owlin.db")
    cur = conn.cursor()
    cur.execute("SELECT supplier, date, value FROM invoices WHERE id = ?", (doc_id,))
    stored = cur.fetchone()
    conn.close()
    if stored:
        logger.info(f"[STORE] Verified invoice stored: supplier='{stored[0]}', date='{stored[1]}', value={stored[2]}")
    else:
        logger.error(f"[STORE] FAILED to store invoice for doc_id={doc_id}")
    
    # Store line items
    if line_items:
        logger.info(f"[STORE] Storing {len(line_items)} line items for doc_id={doc_id}, invoice_id={invoice_id}")
        insert_line_items(doc_id, invoice_id, line_items)
        
        # Verify line items were stored
        import sqlite3
        conn = sqlite3.connect("data/owlin.db")
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM invoice_line_items WHERE doc_id = ?", (doc_id,))
        stored_count = cur.fetchone()[0]
        conn.close()
        if stored_count > 0:
            logger.info(f"[STORE] Verified {stored_count} line items stored in database")
        else:
            logger.error(f"[STORE] FAILED to store line items for doc_id={doc_id}")
    else:
        logger.warning(f"[STORE] No line items to store for doc_id={doc_id}")
    
    # Update document status to ready
    update_document_status(doc_id, "ready", "doc_ready", confidence=confidence)
    doc_type = parsed_data.get("doc_type", "invoice")
    _log_lifecycle("DOC_READY", doc_id, 
                  supplier=parsed_data.get('supplier'), 
                  total=parsed_data.get('total'), 
                  items=len(line_items), 
                  confidence=confidence,
                  doc_type=doc_type)
    
    # Clear any previous errors since processing succeeded
    clear_last_error()
    
    # Note: For full delivery note/invoice pairing support, the migrations/0003_pairs.sql
    # schema should be used with backend.matching.pairing.maybe_create_pair_suggestions()
    # This current implementation stores all documents in the invoices table.
    # Both invoices and delivery notes will appear as invoice cards in the UI.
    
    return {
        "status": "ok",
        "doc_id": doc_id,
        "confidence": confidence,
        "supplier": parsed_data.get("supplier"),
        "date": parsed_data.get("date"),
        "total": parsed_data.get("total"),
        "line_items": line_items,
        "doc_type": doc_type
    }


def _extract_invoice_data_from_page(page: Dict[str, Any]) -> Dict[str, Any]:
    """Extract invoice header data from OCR page result"""
    # Handle both dict and PageResult object formats
    if hasattr(page, 'blocks'):
        # PageResult object - convert to dict-like access
        blocks = list(page.blocks) if hasattr(page, 'blocks') and page.blocks else []
        page_dict = {
            "blocks": blocks,
            "text": getattr(page, 'text', getattr(page, 'ocr_text', '')),
            "ocr_text": getattr(page, 'ocr_text', getattr(page, 'text', '')),
            "confidence": getattr(page, 'confidence', 0.9)
        }
    else:
        # Dict format
        blocks = page.get("blocks", [])
        page_dict = page
    
    # DEBUG: Log block structure to diagnose empty data
    logger.info(f"[EXTRACT] Processing page with {len(blocks)} blocks")
    if blocks:
        first_block = blocks[0]
        if hasattr(first_block, '__dict__'):
            # Block is an object
            block_keys = list(first_block.__dict__.keys())
            has_ocr_text = hasattr(first_block, 'ocr_text')
            has_text = hasattr(first_block, 'text')
        else:
            # Block is a dict
            block_keys = list(first_block.keys()) if isinstance(first_block, dict) else []
            has_ocr_text = isinstance(first_block, dict) and 'ocr_text' in first_block
            has_text = isinstance(first_block, dict) and 'text' in first_block
        
        logger.info(f"[EXTRACT] First block keys: {block_keys}")
        logger.info(f"[EXTRACT] First block has ocr_text: {has_ocr_text}")
        logger.info(f"[EXTRACT] First block has text: {has_text}")
    
    # Build full text from all blocks for vendor template matching
    # Handle both dict and object block formats
    full_text_parts = []
    for block in blocks:
        if hasattr(block, 'ocr_text'):
            # Block is an object
            text = getattr(block, 'ocr_text', '') or getattr(block, 'text', '')
        else:
            # Block is a dict
            text = block.get("ocr_text", block.get("text", ""))
        if text:
            full_text_parts.append(text)
    
    full_text = "\n".join(full_text_parts)
    
    # DEBUG: Log extracted text length
    logger.info(f"[EXTRACT] Extracted {len(full_text)} characters of text from {len(blocks)} blocks")
    
    # If no text extracted, log warning but continue with defaults
    if not full_text or len(full_text.strip()) < 10:
        logger.warning(f"[EXTRACT] Very little or no text extracted from page. Blocks: {len(blocks)}, Text length: {len(full_text)}")
        # Try to get text from page-level fields if blocks are empty
        page_text = page_dict.get("text", page_dict.get("ocr_text", ""))
        if page_text and len(page_text.strip()) > 10:
            logger.info(f"[EXTRACT] Using page-level text (length: {len(page_text)})")
            full_text = page_text
    
    # Try STORI extractor first if detected
    from backend.ocr.vendors.stori_extractor import extract as extract_stori
    
    # Detect STORI: look for "Stori Beer & Wine" or STORI cues
    vendor_hint = None
    if "Stori Beer & Wine" in full_text or ("VAT Invoice" in full_text and "Bala" in full_text):
        vendor_hint = "stori"
        stori_result = extract_stori(full_text)
        
        if stori_result.get("items"):
            # STORI extraction succeeded - use its data
            supplier = "Stori Beer & Wine CYF"
            if "date" in stori_result:
                date = stori_result["date"]
            else:
                date = datetime.now().strftime("%Y-%m-%d")
            
            # Store total in pounds (database value field stores pounds as REAL)
            if "total_pence" in stori_result:
                total = stori_result["total_pence"] / 100.0
            elif "subtotal_pence" in stori_result:
                total = stori_result["subtotal_pence"] / 100.0
            else:
                total = 0.0
            
            confidence = page.get("confidence", 0.9)
            
            return {
                "supplier": supplier,
                "date": date,
                "total": total,
                "confidence": confidence,
                "_stori_data": stori_result  # Store for line item extraction
            }
    
    # Fallback to generic extraction
    supplier = "Unknown Supplier"
    date = datetime.now().strftime("%Y-%m-%d")
    total = 0.0
    
    # Get confidence from page (handle both dict and object)
    if hasattr(page, 'confidence'):
        confidence = page.confidence
    else:
        confidence = page_dict.get("confidence", 0.9)
    
    # Try to find supplier and total from blocks
    for block in blocks:
        # Handle both dict and object block formats
        if hasattr(block, 'ocr_text'):
            # Block is an object
            block_text = getattr(block, 'ocr_text', '') or getattr(block, 'text', '')
        else:
            # Block is a dict
            block_text = block.get("ocr_text", block.get("text", ""))
        
        text = block_text.lower() if block_text else ""
        if "supplier" in text or "ltd" in text or "limited" in text:
            supplier = block_text if block_text else "Unknown Supplier"
        if "total" in text or "£" in text:
            # Try to extract amount
            import re
            amounts = re.findall(r'£?(\d+\.?\d*)', block_text)
            if amounts:
                total = max(float(a) for a in amounts)
    
    return {
        "supplier": supplier,
        "date": date,
        "total": total,
        "confidence": confidence
    }

def _parse_quantity(qty_str: str) -> float:
    """Parse quantity string to float"""
    if not qty_str:
        return 0.0
    try:
        return float(str(qty_str).replace(',', ''))
    except (ValueError, AttributeError):
        return 0.0

def _parse_price(price_str: str) -> float:
    """Parse price string to float, handling currency symbols"""
    if not price_str:
        return 0.0
    try:
        # Remove currency symbols and whitespace
        cleaned = str(price_str).replace('£', '').replace('€', '').replace('$', '').replace(',', '').strip()
        return float(cleaned)
    except (ValueError, AttributeError):
        return 0.0

def _extract_line_items_from_page(page: Dict[str, Any], parsed_data: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """Extract line items from OCR page result"""
    # Handle both dict and PageResult object formats
    if hasattr(page, 'blocks'):
        # PageResult object - convert to list
        blocks = list(page.blocks) if hasattr(page, 'blocks') and page.blocks else []
    else:
        # Dict format
        blocks = page.get("blocks", [])
    
    line_items = []
    
    # DEBUG: Log block structure
    logger.info(f"[LINE_ITEMS] Processing {len(blocks)} blocks for line item extraction")
    
    # Check if STORI data was extracted (stored in parsed_data)
    if parsed_data and "_stori_data" in parsed_data:
        stori_data = parsed_data["_stori_data"]
        stori_items = stori_data.get("items", [])
        
        logger.info(f"[LINE_ITEMS] Found STORI data with {len(stori_items)} items")
        
        # Convert STORI format to our format
        for item in stori_items:
            # STORI returns: name, qty, unit_price_pence, line_total_pence
            # We need: desc, qty, unit_price, total, uom, confidence
            line_items.append({
                "desc": item.get("name", ""),
                "qty": item.get("qty", 0),
                "unit_price": item.get("unit_price_pence", 0) / 100.0,  # Convert pence to pounds
                "total": item.get("line_total_pence", 0) / 100.0,  # Convert pence to pounds
                "uom": "",
                "confidence": 0.9  # High confidence for template-matched data
            })
        
        if line_items:
            logger.info(f"[LINE_ITEMS] Returning {len(line_items)} STORI line items")
            return line_items
    
    # Build full text for vendor template matching if not already done
    # Handle both dict and object block formats
    full_text_parts = []
    for block in blocks:
        if hasattr(block, 'ocr_text'):
            # Block is an object
            text = getattr(block, 'ocr_text', '') or getattr(block, 'text', '')
        else:
            # Block is a dict
            text = block.get("ocr_text", block.get("text", ""))
        if text:
            full_text_parts.append(text)
    
    full_text = "\n".join(full_text_parts)
    
    # Try STORI extractor if detected
    if "Stori Beer & Wine" in full_text or ("VAT Invoice" in full_text and "Bala" in full_text):
        from backend.ocr.vendors.stori_extractor import extract as extract_stori
        stori_result = extract_stori(full_text)
        
        if stori_result.get("items"):
            logger.info(f"[LINE_ITEMS] STORI extractor found {len(stori_result['items'])} items")
            # Convert STORI format to our format
            for item in stori_result["items"]:
                line_items.append({
                    "desc": item.get("name", ""),
                    "qty": item.get("qty", 0),
                    "unit_price": item.get("unit_price_pence", 0) / 100.0,
                    "total": item.get("line_total_pence", 0) / 100.0,
                    "uom": "",
                    "confidence": 0.9
                })
            
            if line_items:
                logger.info(f"[LINE_ITEMS] Returning {len(line_items)} STORI line items")
                return line_items
    
    # Look for table blocks - FIX: Check table_data.line_items
    table_count = 0
    for idx, block in enumerate(blocks):
        # Handle both dict and object block formats
        if hasattr(block, 'type'):
            block_type = block.type
            table_data = getattr(block, 'table_data', None)
            block_ocr_text = getattr(block, 'ocr_text', '')
        else:
            block_type = block.get("type", "")
            table_data = block.get("table_data")
            block_ocr_text = block.get("ocr_text", block.get("text", ""))
        
        # DEBUG: Log all blocks to see what we have
        logger.info(f"[LINE_ITEMS] Block {idx}: type='{block_type}', has_table_data={table_data is not None}, ocr_text_len={len(block_ocr_text)}")
        
        if block_type == "table":
            table_count += 1
            logger.info(f"[LINE_ITEMS] Found table block #{table_count}, table_data type: {type(table_data)}, table_data value: {table_data}")
            
            # FIX: Check table_data.line_items instead of block.line_items
            if table_data:
                if isinstance(table_data, dict):
                    table_line_items = table_data.get("line_items", [])
                    logger.info(f"[LINE_ITEMS] table_data is dict, keys: {list(table_data.keys())}, line_items count: {len(table_line_items)}")
                elif isinstance(table_data, list):
                    # table_data might be a list (List[List[str]] format from type hint)
                    logger.warning(f"[LINE_ITEMS] table_data is a list, not dict. Length: {len(table_data)}")
                    table_line_items = []
                else:
                    # table_data might be an object
                    table_line_items = getattr(table_data, 'line_items', [])
                    logger.info(f"[LINE_ITEMS] table_data is object, line_items count: {len(table_line_items)}")
                
                logger.info(f"[LINE_ITEMS] Table block has {len(table_line_items)} line items")
                
                # Convert TableResult format to our format
                for item_idx, item in enumerate(table_line_items):
                    if isinstance(item, dict):
                        # TableResult.to_dict() format
                        logger.debug(f"[LINE_ITEMS] Processing table item {item_idx}: {item}")
                        line_items.append({
                            "desc": item.get("description", ""),
                            "qty": _parse_quantity(item.get("quantity", "")),
                            "unit_price": _parse_price(item.get("unit_price", "")),
                            "total": _parse_price(item.get("total_price", "")),
                            "uom": "",
                            "confidence": item.get("confidence", 0.7)
                        })
                    else:
                        # LineItem object
                        line_items.append({
                            "desc": getattr(item, 'description', ''),
                            "qty": _parse_quantity(getattr(item, 'quantity', '')),
                            "unit_price": _parse_price(getattr(item, 'unit_price', '')),
                            "total": _parse_price(getattr(item, 'total_price', '')),
                            "uom": "",
                            "confidence": getattr(item, 'confidence', 0.7)
                        })
            else:
                logger.warning(f"[LINE_ITEMS] Table block found but table_data is None or empty. Block OCR text length: {len(block_ocr_text)}")
    
    logger.info(f"[LINE_ITEMS] Found {table_count} table blocks, extracted {len(line_items)} line items")
    
    # If no line items found in tables, try to parse from text blocks
    if not line_items:
        logger.info(f"[LINE_ITEMS] No table items found, trying fallback extraction")
        # Convert blocks to dict format for fallback
        blocks_dict = []
        for block in blocks:
            if hasattr(block, '__dict__'):
                blocks_dict.append({
                    "ocr_text": getattr(block, 'ocr_text', ''),
                    "text": getattr(block, 'text', ''),
                    "type": getattr(block, 'type', '')
                })
            else:
                blocks_dict.append(block)
        line_items = _fallback_line_item_extraction(blocks_dict)
        logger.info(f"[LINE_ITEMS] Fallback extraction found {len(line_items)} line items")
    
    return line_items

def _fallback_line_item_extraction(blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Fallback line item extraction from text blocks with normalization"""
    import re
    line_items = []
    
    for block in blocks:
        # Blocks use "ocr_text" field from the OCR pipeline
        text = block.get("ocr_text", block.get("text", ""))
        # Look for patterns like "Description 10 x £2.50 = £25.00"
        pattern = r'(.+?)\s+(\d+\.?\d*)\s*x?\s*[£€$]?(\d+\.?\d*)\s*=?\s*[£€$]?(\d+\.?\d*)'
        matches = re.finditer(pattern, text, re.IGNORECASE)
        
        for match in matches:
            desc, qty_str, price_str, total_str = match.groups()
            
            # Normalize values
            qty = _normalize_currency(qty_str)
            unit_price = _normalize_currency(price_str)
            total = _normalize_currency(total_str)
            
            # Only add if we have valid numeric values
            if qty is not None and unit_price is not None and total is not None:
                line_items.append({
                    "desc": desc.strip(),
                    "qty": qty,
                    "unit_price": unit_price,
                    "total": total,
                    "uom": "",
                    "confidence": 0.75
                })
    
    return line_items

