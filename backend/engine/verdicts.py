"""
Verdict System - Strict, Mutually Exclusive
Determine the final verdict for each line item based on priority order.
"""

import hashlib
from typing import Dict, List, Optional, Tuple
from config_units import VERDICT_PRIORITIES, ENGINE_VERSION


class LineVerdict:
    """Represents a verdict for a line item."""
    
    def __init__(self, verdict: str, hypothesis: Optional[str] = None,
                 implied_value: Optional[float] = None,
                 expected_value: Optional[float] = None,
                 residual: Optional[float] = None,
                 ruleset_id: str = "default",
                 line_fingerprint: str = ""):
        self.verdict = verdict
        self.hypothesis = hypothesis
        self.implied_value = implied_value
        self.expected_value = expected_value
        self.residual = residual
        self.ruleset_id = ruleset_id
        self.line_fingerprint = line_fingerprint
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for storage."""
        return {
            'verdict': self.verdict,
            'hypothesis': self.hypothesis,
            'implied_value': self.implied_value,
            'expected_value': self.expected_value,
            'residual': self.residual,
            'ruleset_id': self.ruleset_id,
            'engine_version': ENGINE_VERSION,
            'lf': self.line_fingerprint
        }


def calculate_line_fingerprint(sku_id: str, qty: float, uom_key: str, 
                              unit_price_raw: float, nett_price: float, 
                              nett_value: float, date: str, supplier_id: str,
                              ruleset_id: str) -> str:
    """
    Calculate deterministic line fingerprint for audit trail.
    
    Returns:
        SHA256 hash of concatenated values
    """
    # Create deterministic string representation
    fingerprint_data = f"{sku_id}|{qty}|{uom_key}|{unit_price_raw}|{nett_price}|{nett_value}|{date}|{supplier_id}|{ruleset_id}|{ENGINE_VERSION}"
    
    # Generate SHA256 hash
    return hashlib.sha256(fingerprint_data.encode('utf-8')).hexdigest()


def determine_verdict(math_flags: List[str], reference_conflict: bool,
                     uom_mismatch: bool, off_contract: bool,
                     unusual_history: bool, ocr_error: bool,
                     discount_hypothesis: Optional[Dict] = None,
                     ruleset_id: str = "default") -> str:
    """
    Determine the final verdict based on priority order.
    
    Args:
        math_flags: List of mathematical validation flags
        reference_conflict: Whether reference sources conflict
        uom_mismatch: Whether UOM mismatch is suspected
        off_contract: Whether price is off contract
        unusual_history: Whether price is unusual vs history
        ocr_error: Whether OCR error is suspected
        discount_hypothesis: Best fitting discount hypothesis
        ruleset_id: Ruleset identifier
        
    Returns:
        Verdict string (one of VERDICT_PRIORITIES)
    """
    # Check in priority order
    if "PRICE_INCOHERENT" in math_flags or "PACK_MISMATCH" in math_flags or "VAT_MISMATCH" in math_flags:
        return "math_mismatch"
    
    if reference_conflict:
        return "reference_conflict"
    
    if uom_mismatch:
        return "uom_mismatch_suspected"
    
    if off_contract:
        return "off_contract_discount"
    
    if unusual_history:
        return "unusual_vs_history"
    
    if ocr_error:
        return "ocr_suspected_error"
    
    if discount_hypothesis and discount_hypothesis.get('residual', float('inf')) <= 0.01:
        return "ok_on_contract"
    
    # Check if we need user rule
    if discount_hypothesis and discount_hypothesis.get('hypothesis_type') == 'bundle':
        return "needs_user_rule"
    
    return "pricing_anomaly_unmodelled"


def create_line_verdict(sku_id: str, qty: float, uom_key: str,
                       unit_price_raw: float, nett_price: float,
                       nett_value: float, date: str, supplier_id: str,
                       math_flags: List[str], reference_conflict: bool,
                       uom_mismatch: bool, off_contract: bool,
                       unusual_history: bool, ocr_error: bool,
                       discount_hypothesis: Optional[Dict] = None,
                       ruleset_id: str = "default") -> LineVerdict:
    """
    Create a complete line verdict with fingerprint.
    
    Returns:
        LineVerdict object
    """
    # Calculate line fingerprint
    line_fingerprint = calculate_line_fingerprint(
        sku_id, qty, uom_key, unit_price_raw, nett_price, nett_value,
        date, supplier_id, ruleset_id
    )
    
    # Determine verdict
    verdict = determine_verdict(
        math_flags, reference_conflict, uom_mismatch, off_contract,
        unusual_history, ocr_error, discount_hypothesis, ruleset_id
    )
    
    # Extract hypothesis information
    hypothesis = None
    implied_value = None
    expected_value = None
    residual = None
    
    if discount_hypothesis:
        hypothesis = discount_hypothesis.get('hypothesis_type')
        implied_value = discount_hypothesis.get('implied_discount')
        expected_value = discount_hypothesis.get('expected_value')
        residual = discount_hypothesis.get('residual')
    
    return LineVerdict(
        verdict=verdict,
        hypothesis=hypothesis,
        implied_value=implied_value,
        expected_value=expected_value,
        residual=residual,
        ruleset_id=ruleset_id,
        line_fingerprint=line_fingerprint
    )


def validate_verdict(verdict: str) -> bool:
    """Validate that verdict is in the allowed list."""
    return verdict in VERDICT_PRIORITIES


def get_verdict_priority(verdict: str) -> int:
    """Get priority index of verdict (lower = higher priority)."""
    try:
        return VERDICT_PRIORITIES.index(verdict)
    except ValueError:
        return len(VERDICT_PRIORITIES)  # Lowest priority if not found


def compare_verdicts(verdict1: str, verdict2: str) -> int:
    """
    Compare two verdicts by priority.
    
    Returns:
        -1 if verdict1 has higher priority
         0 if equal priority
        +1 if verdict2 has higher priority
    """
    priority1 = get_verdict_priority(verdict1)
    priority2 = get_verdict_priority(verdict2)
    
    if priority1 < priority2:
        return -1
    elif priority1 > priority2:
        return 1
    else:
        return 0


def get_verdict_description(verdict: str) -> str:
    """Get human-readable description of verdict."""
    descriptions = {
        "math_mismatch": "Mathematical inconsistency detected",
        "reference_conflict": "Conflicting price references",
        "uom_mismatch_suspected": "Unit of measure mismatch suspected",
        "off_contract_discount": "Price differs from contract terms",
        "unusual_vs_history": "Unusual compared to historical prices",
        "ocr_suspected_error": "OCR error suspected",
        "ok_on_contract": "Price is within contract terms",
        "needs_user_rule": "Requires manual review",
        "pricing_anomaly_unmodelled": "Pricing anomaly not explained by models"
    }
    
    return descriptions.get(verdict, "Unknown verdict")


def persist_verdict(verdict: LineVerdict, invoice_id: str, line_id: str, 
                   db_connection) -> None:
    """Persist verdict to database."""
    db_connection.execute("""
        INSERT INTO line_verdicts 
        (id, invoice_id, line_id, verdict, hypothesis, implied_value, 
         expected_value, residual, ruleset_id, engine_version, lf, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
    """, (
        hashlib.sha256(f"{invoice_id}_{line_id}_{verdict.line_fingerprint}".encode()).hexdigest(),
        invoice_id,
        line_id,
        verdict.verdict,
        verdict.hypothesis,
        verdict.implied_value,
        verdict.expected_value,
        verdict.residual,
        verdict.ruleset_id,
        ENGINE_VERSION,
        verdict.line_fingerprint
    )) 