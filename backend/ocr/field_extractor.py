"""
field_extractor.py
===================

This module exposes a single function, ``extract_invoice_fields``,
which accepts the OCR output of an invoice and returns a structured
representation of key invoice fields.  It is designed to operate on
offline OCR results without any network calls.  The OCR input is
assumed to be a list of dictionaries where each dictionary
corresponds to a recognised text block on a page.  Each entry looks
like this::

    {
        "text": str,            # the textual content recognised by the OCR engine
        "bbox": [x1, y1, x2, y2],  # bounding box of the text in page coordinates
        "confidence": float,     # OCR engine's confidence (0–100)
        "page_num": int         # 1‑indexed page number
    }

The extractor implements a number of heuristics:

* Supplier names are sought near the top of the page using fuzzy
  keyword matching.  Keywords such as ``Supplier``, ``Vendor``,
  ``From`` and ``Issued By`` are used, and the best candidate from
  the upper quarter of the page is selected.
* Invoice numbers are extracted using a collection of regular
  expressions to match common patterns (e.g. ``INV-12345`` or ``No.
  54321``).  The candidate with the highest OCR confidence is
  returned.
* Dates are detected via regular expressions that cover a range of
  common formats including numeric formats (``dd/mm/yyyy`` or
  ``yyyy-mm-dd``) and longhand formats with ordinal suffixes (``1st
  July 2025``).  The first valid match in reading order is chosen.
* Currency is inferred from the presence of currency symbols (``£``,
  ``€``, ``$``) or ISO codes (``GBP``, ``EUR``, ``USD``) in the text.
  The most frequently observed symbol/code is returned.
* Monetary values for net, VAT and total amounts are obtained by
  locating keywords (``Net``, ``Subtotal``, ``VAT``, ``Sales
  Tax``, ``Total``) and extracting the numeric value following
  each keyword.  When multiple candidates exist, preference is given
  to matches found near the bottom of the page (last 30 %) and
  subsequently by highest confidence.
* Each returned field is accompanied by a confidence score derived
  from the OCR confidence.  If a field cannot be reliably extracted
  (confidence < 50) its value defaults to ``"Unknown"`` and the
  confidence is returned as is.
* The original text snippet that triggered each extraction is
  recorded in the ``field_sources`` dictionary for auditing.
* An optional ``warnings`` entry highlights when the sum of the
  extracted net and VAT amounts deviates from the extracted total by
  more than 2 %.  This aids downstream validation.

Note that this module performs no I/O and may be safely imported into
other components of the OCR pipeline.  Only standard Python modules
and fuzzy string matching from ``fuzzywuzzy`` are used.
"""

from __future__ import annotations

import re
import logging
from typing import Any, Dict, List, Optional, Tuple

try:
    from fuzzywuzzy import fuzz  # type: ignore
    FUZZYWUZZY_AVAILABLE = True
except ImportError:
    FUZZYWUZZY_AVAILABLE = False
    # Fallback fuzzy matching implementation
    def fuzz_partial_ratio(a: str, b: str) -> int:
        """Simple fallback for fuzzy matching when fuzzywuzzy is not available"""
        a_lower = a.lower()
        b_lower = b.lower()
        if a_lower in b_lower or b_lower in a_lower:
            return 80
        # Simple character overlap ratio
        common_chars = set(a_lower) & set(b_lower)
        total_chars = set(a_lower) | set(b_lower)
        if total_chars:
            return int(len(common_chars) / len(total_chars) * 100)
        return 0
    
    class fuzz:
        @staticmethod
        def partial_ratio(a: str, b: str) -> int:
            return fuzz_partial_ratio(a, b)

logger = logging.getLogger(__name__)


def _normalise_amount(amount_str: str) -> Optional[float]:
    """Convert a textual amount into a float.

    This helper removes any thousands separators and currency symbols
    before converting the numeric portion to a float.  If the string
    does not represent a valid float it returns ``None``.

    Parameters
    ----------
    amount_str: str
        The textual representation of the number.

    Returns
    -------
    Optional[float]
        The numeric value or ``None`` if conversion fails.
    """
    if not amount_str:
        return None
    # Remove any currency symbol and whitespace
    cleaned = amount_str.strip()
    cleaned = re.sub(r'[£€$]', '', cleaned)
    # Remove thousand separators (commas or thin spaces)
    cleaned = cleaned.replace(',', '')
    cleaned = cleaned.replace('\u202f', '')  # NBSP/thin space
    # Replace common decimal separators (comma/dot).  If both exist,
    # assume last separator is decimal point.
    if cleaned.count('.') > 1 or cleaned.count(',') > 1:
        # fall back to last occurrence of a separator as decimal point
        last_sep = max(cleaned.rfind('.'), cleaned.rfind(','))
        if last_sep != -1:
            integral = re.sub(r'[.,]', '', cleaned[:last_sep])
            fraction = cleaned[last_sep + 1 :]
            candidate = f"{integral}.{fraction}"
        else:
            candidate = cleaned
    else:
        candidate = cleaned.replace(',', '.')
    try:
        return float(candidate)
    except ValueError:
        return None


def _compute_page_heights(ocr_results: List[Dict[str, Any]]) -> Dict[int, float]:
    """Compute the maximum Y coordinate per page.

    The OCR bounding boxes are specified as ``[x1, y1, x2, y2]``.  We
    treat ``y2`` as the bottom edge of the text block.  The maximum
    across all blocks for a given page is taken as the approximate page
    height.

    Parameters
    ----------
    ocr_results: List[Dict[str, Any]]
        The OCR results.

    Returns
    -------
    Dict[int, float]
        A mapping from page number to the page height (max ``y2``).
    """
    page_heights: Dict[int, float] = {}
    for rec in ocr_results:
        page = rec.get("page_num", 1)
        _, _, _, y2 = rec.get("bbox", [0, 0, 0, 0])
        prev = page_heights.get(page, 0.0)
        if y2 > prev:
            page_heights[page] = y2
    return page_heights


def _extract_supplier(ocr_results: List[Dict[str, Any]]) -> Tuple[str, float, str]:
    """Extract the supplier/vendor name from the OCR results.

    The function looks for lines containing supplier-related keywords
    near the top of the page and uses fuzzy matching to evaluate
    candidates.  The best candidate is chosen based on a combined
    score derived from the fuzzy match score and the OCR confidence.

    Parameters
    ----------
    ocr_results: List[Dict[str, Any]]
        The OCR results to search.

    Returns
    -------
    Tuple[str, float, str]
        A tuple of (supplier_name, confidence, source_text).  If no
        supplier is found, returns ("Unknown", 0.0, "").
    """
    # Keywords indicating supplier
    keywords = ["Supplier", "Vendor", "From", "Issued By"]
    page_heights = _compute_page_heights(ocr_results)
    best_candidate: Tuple[str, float, str] = ("Unknown", 0.0, "")
    for rec in ocr_results:
        text = rec.get("text", "") or ""
        if not text:
            continue
        page = rec.get("page_num", 1)
        y1 = rec.get("bbox", [0, 0, 0, 0])[1]
        # Only consider blocks in the top 25% of the page
        page_height = page_heights.get(page, 0.0) or 1.0
        if page_height <= 0:
            page_height = 1.0
        if y1 > page_height * 0.25:
            continue
        lower = text.lower()
        # Evaluate each keyword using fuzzy matching
        for kw in keywords:
            ratio = fuzz.partial_ratio(kw.lower(), lower)
            if ratio < 60:  # low similarity, skip
                continue
            # Attempt to extract the name after the keyword
            # e.g. "Supplier: ACME Ltd" -> "ACME Ltd"
            pattern = re.compile(re.escape(kw) + r"\s*[:\-]?\s*(.+)", re.IGNORECASE)
            m = pattern.search(text)
            if m:
                candidate_name = m.group(1).strip()
            else:
                # Remove keyword and any punctuation before the rest
                candidate_name = lower.replace(kw.lower(), "").strip(" :-\n\t").strip()
            # Compute combined score: favour high OCR confidence and fuzzy ratio
            conf = float(rec.get("confidence", 0.0))
            combined_score = (conf * (ratio / 100.0))
            # Retain best candidate based on combined score
            if combined_score > best_candidate[1]:
                best_candidate = (candidate_name or "Unknown", conf, text)
    return best_candidate


def _extract_invoice_number(ocr_results: List[Dict[str, Any]]) -> Tuple[str, float, str]:
    """Extract the invoice number from the OCR results.

    Recognises a variety of patterns such as ``INV-12345``, ``#12345``,
    ``No. 12345`` or ``Invoice No.``.  If multiple matches are
    encountered, the one coming from the text block with the highest
    OCR confidence is selected.  Duplicate matches for the same
    invoice number are deduplicated.

    Parameters
    ----------
    ocr_results: List[Dict[str, Any]]
        The OCR results to search.

    Returns
    -------
    Tuple[str, float, str]
        A tuple of (invoice_number, confidence, source_text).  If no
        invoice number is found, returns ("Unknown", 0.0, "").
    """
    # Compile patterns for invoice numbers
    patterns = [
        re.compile(r"\bINV[-\s]?\d+\b", re.IGNORECASE),
        re.compile(r"#\s?\d+\b"),
        re.compile(r"\b(?:No\.|Number)\s*[:#]?\s*\d+\b", re.IGNORECASE),
        re.compile(r"\bInvoice\s*(?:No\.|Number)?\s*[:#]?\s*\d+\b", re.IGNORECASE),
    ]
    best_candidate: Tuple[str, float, str] = ("Unknown", 0.0, "")
    seen_values: Dict[str, float] = {}
    for rec in ocr_results:
        text = rec.get("text", "") or ""
        if not text:
            continue
        for pat in patterns:
            for match in pat.finditer(text):
                raw_candidate = match.group().strip()
                # Clean the invoice number to remove common prefixes and punctuation.
                # We keep the INV- prefix intact but strip other labels such as
                # "Invoice", "No.", "Number" and leading symbols like '#'.
                cleaned_candidate = raw_candidate
                if not raw_candidate.lower().startswith("inv"):
                    cleaned_candidate = re.sub(
                        r"^(?:Invoice\s*(?:No\.|Number)?\s*[:#-]?\s*|(?:No\.|Number)\s*[:#-]?\s*|#\s*)",
                        "",
                        raw_candidate,
                        flags=re.IGNORECASE,
                    ).strip()
                candidate = cleaned_candidate or raw_candidate
                conf = float(rec.get("confidence", 0.0))
                # Deduplicate: if we already saw this value with higher confidence, skip
                prev_conf = seen_values.get(candidate)
                if prev_conf is not None and prev_conf >= conf:
                    continue
                seen_values[candidate] = conf
                # Keep the highest confidence candidate overall
                if conf > best_candidate[1]:
                    best_candidate = (candidate, conf, text)
    return best_candidate


def _extract_invoice_date(ocr_results: List[Dict[str, Any]]) -> Tuple[str, float, str]:
    """Extract the invoice date from the OCR results.

    Supports several date formats, including numeric (``dd/mm/yyyy`` or
    ``yyyy-mm-dd``) and textual (``1st July 2025``).  The first
    occurrence in reading order is returned.  Dates are not normalised
    here; the raw matched string is returned.

    Parameters
    ----------
    ocr_results: List[Dict[str, Any]]
        The OCR results to search.

    Returns
    -------
    Tuple[str, float, str]
        A tuple of (date_string, confidence, source_text).  If no
        date is found, returns ("Unknown", 0.0, "").
    """
    # Compile date patterns
    # Numeric: dd/mm/yyyy or d/m/yy
    numeric_pattern1 = re.compile(
        r"\b(?:0?[1-9]|[12][0-9]|3[01])[-/](?:0?[1-9]|1[0-2])[-/](?:\d{2,4})\b"
    )
    # Numeric: yyyy-mm-dd
    numeric_pattern2 = re.compile(
        r"\b(?:\d{4})[-/](?:0?[1-9]|1[0-2])[-/](?:0?[1-9]|[12][0-9]|3[01])\b"
    )
    # Textual with ordinal suffix and month name
    month_names = (
        r"Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|"
        r"Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?"
    )
    textual_pattern = re.compile(
        rf"\b\d{{1,2}}(?:st|nd|rd|th)\s+({month_names})\s+\d{{4}}\b",
        re.IGNORECASE,
    )
    patterns = [numeric_pattern1, numeric_pattern2, textual_pattern]
    # Sort the OCR results by page and y coordinate to approximate reading order
    ordered_results = sorted(
        ocr_results,
        key=lambda rec: (rec.get("page_num", 1), rec.get("bbox", [0, 0, 0, 0])[1], rec.get("bbox", [0, 0, 0, 0])[0]),
    )
    for rec in ordered_results:
        text = rec.get("text", "") or ""
        if not text:
            continue
        for pattern in patterns:
            m = pattern.search(text)
            if m:
                date_str = m.group().strip()
                return (date_str, float(rec.get("confidence", 0.0)), text)
    return ("Unknown", 0.0, "")


def _extract_currency(ocr_results: List[Dict[str, Any]]) -> Tuple[str, float, str]:
    """Infer the currency used in the invoice.

    Examines all text blocks for currency symbols or ISO currency codes
    and returns the most frequently occurring currency.  If no
    currency can be detected, returns ("Unknown", 0.0, "").

    Parameters
    ----------
    ocr_results: List[Dict[str, Any]]
        The OCR results to analyse.

    Returns
    -------
    Tuple[str, float, str]
        A tuple of (currency_code, confidence, source_text).  The
        confidence for currency detection is heuristic and set to 100
        for detected currencies and 0 otherwise.
    """
    currency_counts: Dict[str, int] = {}
    currency_sources: Dict[str, str] = {}
    symbol_to_code = {
        '£': 'GBP',
        '€': 'EUR',
        '$': 'USD',
    }
    code_patterns = {
        'GBP': re.compile(r'\bGBP\b', re.IGNORECASE),
        'EUR': re.compile(r'\bEUR\b', re.IGNORECASE),
        'USD': re.compile(r'\bUSD\b', re.IGNORECASE),
    }
    for rec in ocr_results:
        text = rec.get("text", "") or ""
        if not text:
            continue
        # Check currency symbols
        for symbol, code in symbol_to_code.items():
            if symbol in text:
                currency_counts[code] = currency_counts.get(code, 0) + text.count(symbol)
                # Record the first occurrence as source
                currency_sources.setdefault(code, text)
        # Check currency codes
        for code, pat in code_patterns.items():
            if pat.search(text):
                currency_counts[code] = currency_counts.get(code, 0) + 1
                currency_sources.setdefault(code, text)
    if not currency_counts:
        return ("Unknown", 0.0, "")
    # Choose the currency with highest count
    chosen_code = max(currency_counts.items(), key=lambda item: item[1])[0]
    return (chosen_code, 100.0, currency_sources[chosen_code])


def _find_amount_after_keyword(text: str, keyword: str) -> Optional[str]:
    """Find a monetary amount appearing after a keyword within a line.

    This helper searches for numeric patterns in ``text`` and returns
    the first occurrence that comes after ``keyword``.  If none are
    found after the keyword, it falls back to the first occurrence in
    the line.

    Parameters
    ----------
    text: str
        The line of text to search.
    keyword: str
        The keyword that should precede the amount.

    Returns
    -------
    Optional[str]
        The matched amount string (including currency symbol) or
        ``None`` if no amount can be found.
    """
    # Normalise for case‑insensitive search
    lower_text = text.lower()
    key_index = lower_text.find(keyword.lower())
    # Regex to capture an optional currency symbol followed by a number
    amount_pattern = re.compile(r'([£€$]?\s*[+-]?\d{1,3}(?:,\d{3})*(?:\.\d+)?|[+-]?\d+(?:\.\d+)?)(?=\b)', re.IGNORECASE)
    matches = list(amount_pattern.finditer(text))
    if not matches:
        return None
    if key_index >= 0:
        # Look for the first match whose start position is after the keyword
        for m in matches:
            if m.start() > key_index:
                return m.group().strip()
    # Fallback: return the first numeric match anywhere in the line
    return matches[0].group().strip()


def _extract_monetary_field(
    ocr_results: List[Dict[str, Any]],
    keywords: List[str],
    page_heights: Dict[int, float],
) -> Tuple[Optional[float], float, str]:
    """Extract a monetary field (net, VAT or total) based on keywords.

    The function scans the OCR results for lines containing any of the
    supplied ``keywords``.  It then attempts to extract a numeric
    amount appearing after the keyword.  Candidates are prioritised
    according to their page position (prefer bottom 30 %) and OCR
    confidence.

    Parameters
    ----------
    ocr_results: List[Dict[str, Any]]
        The OCR results to search.
    keywords: List[str]
        A list of case-insensitive keywords associated with the field.
    page_heights: Dict[int, float]
        Mapping from page numbers to their heights, used to determine
        the bottom part of the page.

    Returns
    -------
    Tuple[Optional[float], float, str]
        A tuple of (amount, confidence, source_text).  ``amount`` is
        ``None`` if no suitable candidate is found.
    """
    candidates: List[Tuple[float, float, str]] = []  # (y_position_ratio, confidence, amount_str, source_text)
    for rec in ocr_results:
        text = rec.get("text", "") or ""
        if not text:
            continue
        lower_text = text.lower()
        for kw in keywords:
            if kw.lower() in lower_text:
                amount_str = _find_amount_after_keyword(text, kw)
                if amount_str:
                    # Determine relative vertical position on page
                    page = rec.get("page_num", 1)
                    y1 = rec.get("bbox", [0, 0, 0, 0])[1]
                    page_height = page_heights.get(page, 0.0) or 1.0
                    # Ratio: 0 at top, 1 at bottom
                    y_ratio = y1 / page_height if page_height else 0.0
                    conf = float(rec.get("confidence", 0.0))
                    candidates.append((y_ratio, conf, amount_str, text))
                break  # avoid matching same line multiple times for this field
    # Prefer candidates in bottom 30 % of page (y_ratio >= 0.7).  Among
    # them, choose the one with highest confidence.  If none in the
    # bottom, choose the overall highest confidence candidate.
    chosen: Optional[Tuple[float, float, str]] = None  # (confidence, amount_str, source_text)
    # Filter bottom candidates
    bottom_candidates = [(conf, amt, src) for (y_ratio, conf, amt, src) in candidates if y_ratio >= 0.7]
    if bottom_candidates:
        # Pick by highest confidence
        chosen = max(bottom_candidates, key=lambda tup: tup[0])
    else:
        # No bottom candidates, choose highest confidence overall
        if candidates:
            chosen = max([(conf, amt, src) for (_, conf, amt, src) in candidates], key=lambda tup: tup[0])
    if chosen:
        conf, amt_str, src = chosen
        amount = _normalise_amount(amt_str)
        return (amount, conf, src)
    return (None, 0.0, "")


def extract_invoice_fields(ocr_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Extract key invoice metadata from OCR results.

    This is the public entry point for the module.  It orchestrates
    calls to the various helper functions to obtain a dictionary
    containing the supplier name, invoice number, date, monetary
    amounts and currency.  Each field is accompanied by a confidence
    score and the original text snippet that produced the match.

    Parameters
    ----------
    ocr_results: List[Dict[str, Any]]
        The OCR results as specified in the module docstring.

    Returns
    -------
    Dict[str, Any]
        A dictionary with the extracted fields and associated
    metadata.
    """
    logger.info("🔄 Starting field extraction from OCR results")
    
    # Check if fuzzywuzzy is available
    if not FUZZYWUZZY_AVAILABLE:
        logger.warning("⚠️ fuzzywuzzy not available, using fallback fuzzy matching")
    
    # Prepare page heights for positional heuristics
    page_heights = _compute_page_heights(ocr_results)

    # Extract fields
    supplier_name, supplier_conf, supplier_src = _extract_supplier(ocr_results)
    invoice_number, invnum_conf, invnum_src = _extract_invoice_number(ocr_results)
    invoice_date, date_conf, date_src = _extract_invoice_date(ocr_results)
    currency_code, currency_conf, currency_src = _extract_currency(ocr_results)

    # Monetary fields
    net_keywords = ["net", "subtotal", "sub total", "sub-total"]
    vat_keywords = ["vat", "sales tax", "tax"]
    total_keywords = ["total", "grand total"]

    net_amount, net_conf, net_src = _extract_monetary_field(ocr_results, net_keywords, page_heights)
    vat_amount, vat_conf, vat_src = _extract_monetary_field(ocr_results, vat_keywords, page_heights)
    total_amount, total_conf, total_src = _extract_monetary_field(ocr_results, total_keywords, page_heights)

    # Prepare confidence scores dictionary
    confidence_scores: Dict[str, float] = {
        "supplier_name": supplier_conf,
        "invoice_number": invnum_conf,
        "invoice_date": date_conf,
        "net_amount": net_conf,
        "vat_amount": vat_conf,
        "total_amount": total_conf,
        "currency": currency_conf,
    }
    # Prepare field sources dictionary (raw text lines)
    field_sources: Dict[str, str] = {
        "supplier_name": supplier_src,
        "invoice_number": invnum_src,
        "invoice_date": date_src,
        "net_amount": net_src,
        "vat_amount": vat_src,
        "total_amount": total_src,
        "currency": currency_src,
    }

    # Replace values with Unknown if confidence < 50
    supplier_out = supplier_name if supplier_conf >= 50 else "Unknown"
    invnum_out = invoice_number if invnum_conf >= 50 else "Unknown"
    date_out = invoice_date if date_conf >= 50 else "Unknown"
    # For numeric fields, assign "Unknown" when confidence < 50 or value could not be parsed
    net_out: Any = net_amount if net_conf >= 50 and net_amount is not None else "Unknown"
    vat_out: Any = vat_amount if vat_conf >= 50 and vat_amount is not None else "Unknown"
    total_out: Any = total_amount if total_conf >= 50 and total_amount is not None else "Unknown"
    # Currency out: keep Unknown if confidence < 50 or currency code unknown
    currency_out = currency_code if currency_conf >= 50 else "Unknown"

    result: Dict[str, Any] = {
        "supplier_name": supplier_out,
        "invoice_number": invnum_out,
        "invoice_date": date_out,
        "net_amount": net_out,
        "vat_amount": vat_out,
        "total_amount": total_out,
        "currency": currency_out,
        "confidence_scores": confidence_scores,
        "field_sources": field_sources,
    }

    # Validation: check if net + VAT matches total within a tolerance of 2 %
    warnings: List[str] = []
    if (
        isinstance(net_out, (int, float))
        and isinstance(vat_out, (int, float))
        and isinstance(total_out, (int, float))
    ):
        computed_total = net_out + vat_out
        if total_out != 0:
            diff_ratio = abs(computed_total - total_out) / abs(total_out)
            if diff_ratio > 0.02:
                warnings.append(
                    f"Net ({net_out}) + VAT ({vat_out}) does not equal Total ({total_out}); deviation {diff_ratio*100:.1f}%"
                )
    # Append warnings if present
    if warnings:
        result["warnings"] = warnings
        logger.warning(f"⚠️ Field extraction warnings: {warnings}")
    
    logger.info(f"✅ Field extraction completed: {supplier_out}, {invnum_out}, {date_out}")
    return result

# Legacy compatibility alias
extract_invoice_metadata = extract_invoice_fields 