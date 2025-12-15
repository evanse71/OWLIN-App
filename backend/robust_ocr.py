# Robust OCR + parsing system
import re, logging, statistics, uuid, time
from typing import Dict, List, Any, Union, Optional
from datetime import datetime
import numpy as np
from PIL import Image
import pytesseract
# Optional pdf2image import for PDF processing
try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False
    convert_from_path = None  # type: ignore
import cv2
from difflib import SequenceMatcher

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Strategy tracking
class StrategyTracker:
    def __init__(self):
        self.strategies_used = {}
        self.total_lines = 0
        self.successful_matches = 0
    
    def record_strategy(self, strategy: str, confidence: float, reason: str):
        if strategy not in self.strategies_used:
            self.strategies_used[strategy] = {"count": 0, "confidence": 0, "reasons": []}
        self.strategies_used[strategy]["count"] += 1
        self.strategies_used[strategy]["confidence"] += confidence
        self.strategies_used[strategy]["reasons"].append(reason)
        self.total_lines += 1
        self.successful_matches += 1
    
    def get_summary(self) -> Dict:
        summary = {"strategies": {}, "stats": {"total_lines": self.total_lines, "successful_matches": self.successful_matches}}
        for strategy, data in self.strategies_used.items():
            summary["strategies"][strategy] = {
                "count": data["count"],
                "avg_confidence": data["confidence"] / data["count"] if data["count"] > 0 else 0,
                "reasons": data["reasons"][:5]  # First 5 reasons
            }
        return summary

strategy_tracker = StrategyTracker()

# Enhanced stop patterns for first-totals detection
STOP_PATTERNS = [
    r'\b(SUBTOTAL|TOTAL|TOTAL\s+DUE|AMOUNT\s+DUE|VAT\s+SUMMARY|PAYMENT|BANK|SIGNATURE|BALANCE|OUTSTANDING)\b',
    r'\b(PAYMENT\s+TERMS|DUE\s+DATE|ACCOUNT\s+NUMBER|SORT\s+CODE|IBAN|BIC)\b',
    r'\b(THANK\s+YOU|PLEASE\s+PAY|REMITTANCE|INVOICE\s+SUMMARY)\b',
    r'\b(TAX\s+SUMMARY|VAT\s+REGISTRATION|COMPANY\s+REGISTRATION)\b'
]

STOP_PAT = re.compile('|'.join(STOP_PATTERNS), re.IGNORECASE)

# Item parsing patterns
SKIP_NON_ITEMS = re.compile(r'\b(INVOICE|PAGE|TOTAL|SUBTOTAL|VAT|TAX|AMOUNT|DUE|PAYMENT|BANK|SIGNATURE|THANK|PLEASE)\b', re.I)

ROW_BREWERY = re.compile(r'^(?P<desc>[A-Za-z\s&]+)\s+(?P<qty>\d+)\s+x\s+[£€$]?(?P<unit>\d+\.?\d*)\s+[£€$]?(?P<line>\d+\.?\d*)\s+(?P<vat>\d+)%?$')
ROW_THREE_COL = re.compile(r'^(?P<desc>[A-Za-z\s&]+)\s+(?P<qty>\d+)\s+[£€$]?(?P<rate>\d+\.?\d*)\s+[£€$]?(?P<amount>\d+\.?\d*)\s+(?P<vat>\d+)%?$')
ROW_TWO_COL = re.compile(r'^(?P<desc>[A-Za-z\s&]+)\s+[£€$]?(?P<line>\d+\.?\d*)\s+(?P<vat>\d+)%?$')
ROW_PLAIN_ALIGNED = re.compile(r'^(?P<desc>[A-Za-z\s&]+)\s+(?P<qty>\d+)\s+[£€$]?(?P<unit>\d+\.?\d*)\s+[£€$]?(?P<line>\d+\.?\d*)$')

SUPPRESS_WORDS = re.compile(r"(invoice|number|no\.?|date|tax|vat|total|subtotal|amount|page)", re.I)

def _best_supplier_candidate(text: str) -> str:
    """Heuristic: look at top lines; pick longest clean line that isn't a field label."""
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    top = lines[:20]
    candidates = []
    for ln in top:
        if len(ln) < 3:
            continue
        if SUPPRESS_WORDS.search(ln):
            continue
        # prefer lines with letters and limited punctuation
        alpha = sum(ch.isalpha() for ch in ln)
        if alpha >= 3:
            candidates.append(ln)
    # choose the longest candidate
    return max(candidates, key=len) if candidates else ""

def _normalize_supplier(s: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "", (s or "").lower())
    return base

def _alias_match(canonical: str, alias: str) -> float:
    return SequenceMatcher(None, _normalize_supplier(canonical), _normalize_supplier(alias)).ratio()

def extract_header_fields(combined_text: str) -> dict:
    supplier = _best_supplier_candidate(combined_text)
    # invoice number & date (simple patterns; refine as needed)
    inv_no = None
    m = re.search(r"(invoice\s*(no|number|#)\s*[:\-]?\s*([A-Z0-9\-\/]+))", combined_text, re.I)
    if m:
        inv_no = m.group(3)
    inv_date = None
    # accept DD/MM/YYYY, MM/DD/YYYY, or 2024-12-31
    m = re.search(r"\b(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}|\d{4}[\/\-]\d{1,2}[\/\-]\d{1,2})\b", combined_text)
    if m:
        inv_date = m.group(1)

    # per-stage header confidence (cheap heuristic)
    c_header = 0
    if supplier: c_header += 35
    if inv_no:   c_header += 35
    if inv_date: c_header += 30

    return {
        "supplier": supplier or None,
        "invoice_number": inv_no,
        "invoice_date": inv_date,
        "c_header": c_header,  # 0–100
    }

def _score_lines(lines) -> int:
    """Score line items extraction confidence"""
    if not lines: 
        return 0
    n = len(lines)
    numeric_ok = 0
    for li in lines:
        try:
            float(li.get("qty", 0))
            float(li.get("unit_price", 0))
            numeric_ok += 1
        except Exception:
            pass
    # weight count and numeric health
    return min(100, int(50 + 50 * (numeric_ok / max(1, n))))

def _weakest_stage(c_split, c_header, c_lines, c_totals) -> str:
    """Identify the weakest confidence stage"""
    pairs = [("SPLIT_WEAK", c_split), ("HEADER_WEAK", c_header), ("LINES_WEAK", c_lines), ("TOTALS_WEAK", c_totals)]
    return min(pairs, key=lambda x: x[1])[0]

def rasterize(path: str) -> List[Image.Image]:
    """Convert PDF to images or return single image"""
    if path.lower().endswith('.pdf'):
        if PDF2IMAGE_AVAILABLE and convert_from_path:
            return convert_from_path(path, dpi=300)
        else:
            raise ImportError("pdf2image is not installed. PDF processing requires pdf2image. Install with: pip install pdf2image")
    else:
        return [Image.open(path)]

def preprocess(img: Image.Image) -> Image.Image:
    """Enhanced image preprocessing"""
    # Convert to numpy array
    img_array = np.array(img)
    
    # Convert to grayscale if needed
    if len(img_array.shape) == 3:
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_array
    
    # Apply adaptive threshold
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    
    # Denoise
    denoised = cv2.fastNlMeansDenoising(thresh)
    
    return Image.fromarray(denoised)

def ocr_tsv(img: Image.Image) -> List[Dict]:
    """Run OCR and return TSV format with confidence"""
    try:
        # Use PSM 6 for uniform block of text
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT, config='--psm 6')
        
        results = []
        for i in range(len(data['text'])):
            if data['conf'][i] > 0:  # Only include text with confidence > 0
                results.append({
                    'text': data['text'][i].strip(),
                    'conf': data['conf'][i],
                    'left': data['left'][i],
                    'top': data['top'][i],
                    'width': data['width'][i],
                    'height': data['height'][i]
                })
        
        return results
    except Exception as e:
        logger.error(f"OCR failed: {e}")
        return []

def group_lines(tsv_rows: List[Dict]) -> List[Dict]:
    """Group OCR words into lines based on vertical position"""
    if not tsv_rows:
        return []
    
    # Sort by vertical position
    sorted_rows = sorted(tsv_rows, key=lambda x: x['top'])
    
    lines = []
    current_line = []
    current_top = sorted_rows[0]['top']
    
    for row in sorted_rows:
        # If vertical distance is small, it's the same line
        if abs(row['top'] - current_top) < 20:  # 20px tolerance
            current_line.append(row)
        else:
            # New line
            if current_line:
                # Sort words in line by horizontal position
                current_line.sort(key=lambda x: x['left'])
                line_text = ' '.join([r['text'] for r in current_line])
                avg_conf = sum(r['conf'] for r in current_line) / len(current_line)
                lines.append({
                    'text': line_text,
                    'conf': avg_conf,
                    'words': current_line
                })
            current_line = [row]
            current_top = row['top']
    
    # Don't forget the last line
    if current_line:
        current_line.sort(key=lambda x: x['left'])
        line_text = ' '.join([r['text'] for r in current_line])
        avg_conf = sum(r['conf'] for r in current_line) / len(current_line)
        lines.append({
            'text': line_text,
            'conf': avg_conf,
            'words': current_line
        })
    
    return lines

def _slice_items_region(lines: List[Dict]) -> List[Dict]:
    """Find the items section in the invoice"""
    start = 0
    end = len(lines)
    
    # Look for items section markers
    for i, line in enumerate(lines):
        text = line["text"].upper()
        if any(marker in text for marker in ["ITEM", "DESCRIPTION", "QTY", "QUANTITY", "PRICE", "AMOUNT", "TOTAL"]):
            start = i
            break
    
    # Look for end of items section
    for i in range(start, len(lines)):
        text = lines[i]["text"].upper()
        if any(marker in text for marker in ["SUBTOTAL", "TOTAL", "VAT", "AMOUNT DUE", "PAYMENT"]):
            end = i
            break
    
    return lines[start:end]

def _parse_items(lines: List[Dict]) -> List[Dict]:
    """Enhanced item parsing with strategy tracking"""
    out = []
    
    for l in lines:
        t = l["text"].strip()
        if SKIP_NON_ITEMS.search(t):
            continue
        
        # Try each strategy in order of preference
        strategies = [
            ("brewery", ROW_BREWERY, 0.9),
            ("three_col", ROW_THREE_COL, 0.8),
            ("two_col", ROW_TWO_COL, 0.7),
            ("plain_aligned", ROW_PLAIN_ALIGNED, 0.6)
        ]
        
        for strategy_name, pattern, confidence in strategies:
            m = pattern.match(t)
            if m:
                item = {
                    "description": m.group("desc").strip(),
                    "qty": float(m.group("qty")) if "qty" in m.groupdict() else 1.0,
                    "unit_price_str": m.group("unit") if "unit" in m.groupdict() else None,
                    "line_total_str": m.group("line") if "line" in m.groupdict() else None,
                    "vat_rate_str": m.group("vat") if "vat" in m.groupdict() else None,
                    "conf": l["conf"],
                    "strategy": strategy_name
                }
                
                # Handle different column layouts
                if strategy_name == "three_col":
                    item["unit_price_str"] = m.group("rate")
                    item["line_total_str"] = m.group("amount")
                elif strategy_name == "two_col":
                    item["qty"] = 1.0
                    item["unit_price_str"] = None
                    item["line_total_str"] = m.group("line")
                
                out.append(item)
                strategy_tracker.record_strategy(strategy_name, confidence, f"Matched {strategy_name} pattern")
                break
        
        # If no strategy matched, try heuristic extraction
        if not any(pattern.match(t) for _, pattern, _ in strategies):
            # Simple heuristic: look for lines with prices
            price_match = re.search(r'[£€$]?\s*(\d+\.?\d*)', t)
            if price_match and len(t.split()) >= 2:
                # Assume last number is price, rest is description
                parts = t.split()
                price_str = parts[-1].replace('£', '').replace('€', '').replace('$', '')
                try:
                    price = float(price_str)
                    desc = ' '.join(parts[:-1])
                    if desc and len(desc) > 2:
                        out.append({
                            "description": desc,
                            "qty": 1.0,
                            "unit_price_str": None,
                            "line_total_str": price_str,
                            "vat_rate_str": "20",
                            "conf": l["conf"],
                            "strategy": "heuristic"
                        })
                        strategy_tracker.record_strategy("heuristic", 0.3, "Heuristic extraction")
                except ValueError:
                    pass
    
    return out

def extract_totals(text: str) -> tuple:
    """Extract subtotal, VAT, and total from text"""
    subtotal = None
    vat_total = None
    total = None
    
    # Look for total patterns
    total_patterns = [
        r'(?:TOTAL|AMOUNT\s+DUE|GRAND\s+TOTAL)[:\s]*[£€$]?\s*(\d+\.?\d*)',
        r'[£€$]\s*(\d+\.?\d*)\s*(?:TOTAL|DUE)',
        r'(?:TOTAL|AMOUNT)[:\s]*[£€$]?\s*(\d+\.?\d*)'
    ]
    
    for pattern in total_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                total = float(match.group(1).replace(',', ''))
                break
            except ValueError:
                continue
    
    # Look for VAT patterns
    vat_patterns = [
        r'(?:VAT|TAX)[:\s]*[£€$]?\s*(\d+\.?\d*)',
        r'[£€$]\s*(\d+\.?\d*)\s*(?:VAT|TAX)',
        r'(?:VAT|TAX)\s+[£€$]?\s*(\d+\.?\d*)'
    ]
    
    for pattern in vat_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                vat_total = float(match.group(1).replace(',', ''))
                break
            except ValueError:
                continue
    
    # Look for subtotal patterns
    subtotal_patterns = [
        r'(?:SUBTOTAL|NET)[:\s]*[£€$]?\s*(\d+\.?\d*)',
        r'[£€$]\s*(\d+\.?\d*)\s*(?:SUBTOTAL|NET)',
        r'(?:SUBTOTAL|NET)\s+[£€$]?\s*(\d+\.?\d*)'
    ]
    
    for pattern in subtotal_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                subtotal = float(match.group(1).replace(',', ''))
                break
            except ValueError:
                continue
    
    return subtotal, vat_total, total

def compute_missing_total(subtotal: float, vat_total: float, total: float) -> tuple:
    """Compute missing totals if possible"""
    if total and subtotal and not vat_total:
        vat_total = total - subtotal
    elif total and vat_total and not subtotal:
        subtotal = total - vat_total
    elif subtotal and vat_total and not total:
        total = subtotal + vat_total
    
    return subtotal, vat_total, total

def normalize_date(s: Union[str, None]) -> Union[str, None]:
    """Normalize date string to ISO format"""
    if not s:
        return None
    
    # Try common date patterns
    patterns = [
        r'(\d{1,2})/(\d{1,2})/(\d{4})',
        r'(\d{1,2})-(\d{1,2})-(\d{4})',
        r'(\d{1,2})/(\d{1,2})/(\d{2})',
        r'(\d{1,2})-(\d{1,2})-(\d{2})'
    ]
    
    for pattern in patterns:
        m = re.search(pattern, s)
        if m:
            try:
                if len(m.group(3)) == 2:
                    year = '20' + m.group(3)
                else:
                    year = m.group(3)
                return f"{year}-{m.group(2).zfill(2)}-{m.group(1).zfill(2)}"
            except ValueError:
                continue
    
    # Try text date patterns
    text_pattern = r'(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})'
    m = re.search(text_pattern, s, re.IGNORECASE)
    if m:
        try:
            return datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3)}", "%d %B %Y").date().isoformat()
        except ValueError:
            pass
    return None

def extract_items_from_pages(lines_by_page: List[List[Dict]]) -> List[Dict]:
    """
    Enhanced multi-page item extraction with first-totals stop.
    
    Args:
        lines_by_page: List of page lines, each page is a list of line dicts
        
    Returns:
        List of extracted items with page_idx added
    """
    all_items = []
    items_started = False
    stop = False
    
    for page_idx, page_lines in enumerate(lines_by_page):
        if stop:
            break
            
        # 1) Pick strategy using FULL page lines (so header is visible)
        strat = pick_strategy(page_lines)
        
        if strat:
            # 2) Extract items region for this page
            page_items = strat.extract(page_lines)
            
            if page_items:
                items_started = True
                for it in page_items:
                    it["page_idx"] = page_idx
                all_items.extend(page_items)
            
            # 3) After items start, if we see a stop token anywhere on the page, stop
            if items_started:
                text_concat = " ".join([ln["text"] for ln in page_lines if ln.get("text")])
                if STOP_PAT.search(text_concat):
                    stop = True
                    logger.info(f"Stopping at page {page_idx + 1} due to totals/payment block")
                    break
    
    return all_items

def pick_strategy(page_lines: List[Dict]) -> Optional[Any]:
    """
    Pick the best strategy for extracting items from this page.
    This is a simplified version - you can enhance this with more sophisticated logic.
    """
    # For now, return a simple strategy object
    class SimpleStrategy:
        def extract(self, lines):
            return _parse_items(_slice_items_region(lines))
    
    return SimpleStrategy()

def process_multipage_invoice(path: str) -> Dict:
    """Enhanced multi-page processing with first-totals stop"""
    pages = rasterize(path)
    if not pages:
        return {
            "supplier_name": "",
            "invoice_date_raw": "",
            "confidence": 0,
            "total_amount": 0,
            "subtotal": None,
            "vat_total": None,
            "items_raw": [],
            "strategy_summary": strategy_tracker.get_summary()
        }
    
    all_lines = []
    page_confidences = []
    
    # Process each page to get lines
    for page_idx, page_img in enumerate(pages):
        tsv_rows = ocr_tsv(preprocess(page_img))
        for row in tsv_rows:
            row["page"] = page_idx
        
        page_lines = group_lines(tsv_rows)
        all_lines.extend(page_lines)
        
        # Track confidence
        page_confs = [l["conf"] for l in page_lines if l["text"].strip()]
        if page_confs:
            page_confidences.extend(page_confs)
    
    # Group lines by page for multi-page processing
    lines_by_page = []
    current_page_lines = []
    current_page = 0
    
    for line in all_lines:
        page = line.get("page", 0)
        if page != current_page:
            if current_page_lines:
                lines_by_page.append(current_page_lines)
            current_page_lines = [line]
            current_page = page
        else:
            current_page_lines.append(line)
    
    if current_page_lines:
        lines_by_page.append(current_page_lines)
    
    # Extract items using enhanced multi-page logic
    all_items = extract_items_from_pages(lines_by_page)
    
    # Parse totals and metadata from all lines
    text = "\n".join([l["text"] for l in all_lines])
    subtotal_raw, vat_total_raw, total_raw = extract_totals(text)
    subtotal_raw, vat_total_raw, total_raw = compute_missing_total(subtotal_raw, vat_total_raw, total_raw)
    
    # Extract supplier and date
    supplier = None
    invoice_date = None
    
    for line in all_lines[:20]:
        text = line.get("text", "")
        if not supplier and re.search(r"[A-Za-z]{3,}", text) and not re.search(r"\d{2,}", text):
            supplier = text
        
        if not invoice_date:
            date_match = re.search(r"(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})", text)
            if date_match:
                invoice_date = date_match.group(1)
    
    # Overall confidence
    overall_conf = int(statistics.median(page_confidences)) if page_confidences else 0
    
    logger.info(f"Multi-page processing complete: {len(all_items)} total items from {len(pages)} pages")
    
    return {
        "items_raw": all_items,
        "subtotal_raw": subtotal_raw,
        "vat_total_raw": vat_total_raw,
        "total_raw": total_raw,
        "confidence": overall_conf,
        "supplier_name": supplier,
        "invoice_date_raw": invoice_date,
        "strategy_summary": strategy_tracker.get_summary()
    }

def _is_footer_line(text: str) -> bool:
    """Check if a line is likely a footer line"""
    text = text.upper().strip()
    
    # Common footer patterns
    footer_patterns = [
        r'PAGE\s+\d+',
        r'INVOICE\s+\d+',
        r'THANK\s+YOU',
        r'PLEASE\s+PAY',
        r'PAYMENT\s+TERMS',
        r'BANK\s+DETAILS',
        r'ACCOUNT\s+NUMBER',
        r'VAT\s+REGISTRATION',
        r'COMPANY\s+REGISTRATION',
        r'WWW\.',
        r'HTTP://',
        r'HTTPS://',
        r'EMAIL:',
        r'PHONE:',
        r'TEL:',
        r'FAX:'
    ]
    
    for pattern in footer_patterns:
        if re.search(pattern, text, re.I):
            return True
    
    return False

def parse_invoice_file(path: str) -> Dict:
    """Main parsing function with enhanced error handling and strategy tracking"""
    try:
        # Delay injector for testing timeouts
        import os
        delay_ms = int(os.environ.get("OWLIN_OCR_DELAY_MS", "0"))
        if delay_ms > 0:
            import time
            time.sleep(delay_ms / 1000.0)
            logger.info(f"TIMING DELAY_INJECTED {delay_ms}ms")
        
        # Reset strategy tracker for new file
        global strategy_tracker
        strategy_tracker = StrategyTracker()
        
        # Check if multi-invoice splitting is available
        try:
            from ocr.splitter import split_pages_into_invoices, extract_invoice_metadata_from_chunk
            SPLITTER_AVAILABLE = True
        except ImportError:
            SPLITTER_AVAILABLE = False
            logger.warning("Multi-invoice splitter not available, using single-invoice processing")
        
        if SPLITTER_AVAILABLE:
            # Multi-invoice processing path
            pages = rasterize(path)
            if not pages:
                return {"items_raw": [], "confidence": 0, "supplier_name": "", "invoice_date_raw": ""}
            
            # Convert pages to OCR text format
            ocr_pages = []
            for i, img in enumerate(pages):
                tsv_rows = ocr_tsv(preprocess(img))
                text = "\n".join([row["text"] for row in tsv_rows if row["text"].strip()])
                ocr_pages.append({
                    "page_index": i,
                    "text": text,
                    "blocks": tsv_rows
                })
            
            # Split into invoice chunks
            chunks = split_pages_into_invoices(ocr_pages)
            
            if len(chunks) > 1:
                # Multiple invoices detected
                logger.info(f"Detected {len(chunks)} invoices in {path}")
                invoices = []
                
                for chunk in chunks:
                    # Extract metadata from chunk
                    metadata = extract_invoice_metadata_from_chunk(chunk)
                    
                    # Combine all blocks from chunk pages
                    all_blocks = []
                    for page in chunk:
                        all_blocks.extend(page.get("blocks", []))
                    
                    # Parse items and totals
                    lines = group_lines(all_blocks)
                    items_region = _slice_items_region(lines)
                    items = _parse_items(items_region)
                    
                    combined_text = "\n".join([page.get("text", "") for page in chunk])
                    subtotal, vat_total, total = extract_totals(combined_text)
                    
                    # Calculate per-stage confidence
                    c_split = 80  # base heuristic; bump if header anchor found at valid spot
                    c_header = metadata.get("c_header", 0)
                    c_lines = _score_lines(items)
                    
                    # Prepare invoice dict with confidence scores
                    inv = {
                        "supplier_name": metadata["supplier_name"],
                        "invoice_number": metadata["invoice_number"],
                        "invoice_date_raw": metadata["invoice_date"],
                        "items_raw": items,
                        "subtotal_raw": subtotal,
                        "vat_total_raw": vat_total,
                        "total_raw": total,
                        "c_split": c_split,
                        "c_header": c_header,
                        "c_lines": c_lines,
                        "page_range": metadata["page_range"]
                    }
                    
                    # Enrich with totals validation (import from services)
                    try:
                        from services import enrich_totals_and_flags
                        inv = enrich_totals_and_flags(inv)
                    except ImportError:
                        # Fallback if services not available
                        inv["c_totals"] = 75
                        inv["validation_flags"] = []
                    
                    # Set overall confidence and reason
                    overall_conf = min(c_split, c_header, c_lines, inv.get("c_totals", 75))
                    inv["confidence"] = overall_conf
                    inv["reason"] = _weakest_stage(c_split, c_header, c_lines, inv.get("c_totals", 75))
                    
                    invoices.append(inv)
                
                return {"invoices": invoices}
            else:
                # Single invoice, use existing processing
                logger.info(f"Single invoice detected in {path}")
                result = process_multipage_invoice(path)
                return result
        else:
            # Fallback to existing processing
            result = process_multipage_invoice(path)
            return result
            
    except Exception as e:
        logger.error(f"Error in multi-page processing: {e}")
        # Fallback to single-page processing
        return _fallback_single_page_processing(path)

def _fallback_single_page_processing(path: str) -> Dict:
    """Fallback single-page processing"""
    try:
        pages = rasterize(path)
        if not pages:
            return {"items_raw": [], "confidence": 0, "supplier_name": "", "invoice_date_raw": ""}
        
        img = pages[0]
        tsv_rows = ocr_tsv(preprocess(img))
        lines = group_lines(tsv_rows)
        
        return _parse(lines)
    except Exception as e:
        logger.error(f"Fallback processing failed: {e}")
        return {"items_raw": [], "confidence": 0, "supplier_name": "", "invoice_date_raw": ""}

def _parse(lines: List[Dict]) -> Dict:
    """Parse single page"""
    items_region = _slice_items_region(lines)
    items = _parse_items(items_region)
    
    text = "\n".join([l["text"] for l in lines])
    subtotal, vat_total, total = extract_totals(text)
    
    return {
        "items_raw": items,
        "subtotal_raw": subtotal,
        "vat_total_raw": vat_total,
        "total_raw": total,
        "confidence": int(statistics.mean([l["conf"] for l in lines if l["text"].strip()])) if lines else 0,
        "supplier_name": "",
        "invoice_date_raw": ""
    }

def run_ocr(path: str) -> Dict[str, Any]:
    """Main OCR function - returns structured data"""
    try:
        result = parse_invoice_file(path)
        
        # Debug logging with null-safe formatting
        subtotal = result.get('subtotal_raw') or 0
        vat_total = result.get('vat_total_raw') or 0
        total_amount = result.get('total_raw') or 0
        
        print(f"OCR Result for {path}:")
        print(f"  Supplier: {result['supplier_name']}")
        print(f"  Date: {result['invoice_date_raw']}")
        print(f"  Subtotal: {subtotal} pence (£{subtotal/100:.2f})")
        print(f"  VAT: {vat_total} pence (£{vat_total/100:.2f})")
        print(f"  Total: {total_amount} pence (£{total_amount/100:.2f})")
        print(f"  Confidence: {result['confidence']}%")
        print(f"  Items: {len(result['items_raw'])}")
        for i, item in enumerate(result['items_raw'][:3]):  # First 3 items
            unit_price = item.get('unit_price_str', 0) or 0
            total = item.get('line_total_str', 0) or 0
            print(f"    {i+1}. {item['description']} x{item['qty']} @ £{unit_price/100:.2f} = £{total/100:.2f} ({item['vat_rate_str']}% VAT)")
        
        return {
            "confidence": result["confidence"],
            "items": result["items_raw"],
            "supplier_name": result["supplier_name"],
            "invoice_date_raw": result["invoice_date_raw"],
            "total_amount": total_amount,
            "subtotal": subtotal,
            "vat_total": vat_total
        }
    except Exception as e:
        print(f"OCR error for {path}: {str(e)}")
        # Always return a dictionary
        return {
            "confidence": 0, 
            "items": [],
            "supplier_name": "",
            "invoice_date_raw": "",
            "total_amount": 0,
            "subtotal": 0,
            "vat_total": 0
        } 

def _score_lines(lines) -> int:
    """Score line items extraction confidence"""
    if not lines: 
        return 0
    n = len(lines)
    numeric_ok = 0
    for li in lines:
        try:
            float(li.get("qty", 0))
            float(li.get("unit_price", 0))
            numeric_ok += 1
        except Exception:
            pass
    # weight count and numeric health
    return min(100, int(50 + 50 * (numeric_ok / max(1, n))))

def _weakest_stage(c_split, c_header, c_lines, c_totals) -> str:
    """Identify the weakest confidence stage"""
    pairs = [("SPLIT_WEAK", c_split), ("HEADER_WEAK", c_header), ("LINES_WEAK", c_lines), ("TOTALS_WEAK", c_totals)]
    return min(pairs, key=lambda x: x[1])[0] 