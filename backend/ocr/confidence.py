"""
OCR confidence calculation: per-page and per-line confidence scores
"""
from typing import List, Tuple, Dict, Any
import statistics

def page_confidence(words: List[Tuple[str, float]]) -> Tuple[float, float]:
    """Return (avg_conf, min_conf). words = [(text, conf0-100)]."""
    if not words:
        return (0.0, 0.0)
    
    confidences = [conf for _, conf in words]
    avg_conf = statistics.mean(confidences)
    min_conf = min(confidences)
    
    return (avg_conf, min_conf)

def line_confidence(line_words: List[Tuple[str, float]]) -> float:
    """Calculate confidence for a single line of text."""
    if not line_words:
        return 0.0
    
    # Weight by word length (longer words get more weight)
    total_weight = 0
    weighted_sum = 0
    
    for text, conf in line_words:
        weight = len(text.strip())
        total_weight += weight
        weighted_sum += conf * weight
    
    if total_weight == 0:
        return 0.0
    
    return weighted_sum / total_weight

def calculate_invoice_confidence(pages_data: List[Dict[str, Any]]) -> Tuple[float, float]:
    """Calculate overall invoice confidence from page data."""
    if not pages_data:
        return (0.0, 0.0)
    
    page_avgs = [page['avg_conf'] for page in pages_data]
    page_mins = [page['min_conf'] for page in pages_data]
    
    # Invoice average is mean of page averages
    invoice_avg = statistics.mean(page_avgs)
    
    # Invoice minimum is the lowest line confidence across all pages
    invoice_min = min(page_mins) if page_mins else 0.0
    
    return (invoice_avg, invoice_min)

def apply_confidence_gating(avg_conf: float) -> str:
    """Apply confidence gating rules. Return gating decision."""
    if avg_conf < 50.0:
        return "BLOCKED"
    elif avg_conf < 70.0:
        return "WARN"
    else:
        return "PASS" 