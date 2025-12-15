"""
LLM-powered explanations for pairing suggestions.

This module generates human-readable explanations for why invoice-delivery note
pairings were suggested, with fallback to template-based explanations when
LLM is unavailable.
"""
import logging
from typing import Optional
from backend.models.pairing import PairingCandidate, CandidateFeatureSummary

LOGGER = logging.getLogger("owlin.services.pairing_explainer")

# Try to import LLM, but make it optional
try:
    from backend.llm.local_llm import LocalLLMInterface, LLMConfig, LLMProvider, LLMDevice
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    LocalLLMInterface = None
    LLMConfig = None
    LLMProvider = None
    LLMDevice = None

# Global LLM instance (lazy-loaded)
_LLM_INSTANCE = None


def _get_llm_instance() -> Optional[LocalLLMInterface]:
    """Get or create LLM instance (lazy initialization)."""
    global _LLM_INSTANCE
    
    if not LLM_AVAILABLE:
        return None
    
    if _LLM_INSTANCE is not None:
        return _LLM_INSTANCE
    
    try:
        # Try to load LLM config from environment or use defaults
        # For now, we'll use a simple approach - try to create a mock instance
        # In production, this would read from config
        config = LLMConfig(
            model_path="mock",  # Will use mock provider
            provider=LLMProvider.MOCK,
            device=LLMDevice.CPU
        )
        _LLM_INSTANCE = LocalLLMInterface(config)
        if _LLM_INSTANCE.is_available():
            LOGGER.debug("LLM instance initialized for pairing explanations")
            return _LLM_INSTANCE
    except Exception as e:
        LOGGER.debug("Failed to initialize LLM for pairing explanations: %s", e)
    
    return None


def generate_pairing_explanation(
    invoice_id: str,
    candidate: PairingCandidate,
    features_summary: Optional[CandidateFeatureSummary] = None
) -> str:
    """
    Generate human-readable explanation for why this pairing was suggested.
    
    Args:
        invoice_id: Invoice ID
        candidate: Pairing candidate with probability and features
        features_summary: Optional feature summary (uses candidate's if not provided)
    
    Returns:
        Human-readable explanation string
    """
    if not features_summary:
        features_summary = candidate.features_summary
    
    # Always generate template-based explanation first
    explanation = _template_explanation(candidate, features_summary)
    
    # Try LLM enhancement if available
    try:
        llm = _get_llm_instance()
        if llm and llm.is_available():
            enhanced = _llm_enhance_explanation(invoice_id, candidate, features_summary, explanation)
            if enhanced and enhanced.strip():
                return enhanced
    except Exception as e:
        LOGGER.debug("LLM explanation unavailable, using template: %s", e)
    
    return explanation


def _template_explanation(
    candidate: PairingCandidate,
    features: Optional[CandidateFeatureSummary]
) -> str:
    """Generate template-based explanation from features."""
    if not features:
        return f"Suggested delivery note with {candidate.probability:.0%} confidence."
    
    reasons = []
    
    # Amount matching
    if features.amount_diff_pct is not None:
        if abs(features.amount_diff_pct) < 0.01:
            reasons.append("exact total match")
        elif abs(features.amount_diff_pct) < 0.05:
            reasons.append(f"very close total ({abs(features.amount_diff_pct)*100:.1f}% difference)")
        elif abs(features.amount_diff_pct) < 0.10:
            reasons.append(f"close total ({abs(features.amount_diff_pct)*100:.1f}% difference)")
    
    # Date matching
    if features.date_diff_days is not None:
        days_diff = abs(features.date_diff_days)
        if days_diff == 0:
            reasons.append("same day delivery")
        elif days_diff == 1:
            reasons.append("delivery 1 day apart")
        elif days_diff <= 3:
            reasons.append(f"delivery within {int(days_diff)} days")
        elif days_diff <= 7:
            reasons.append(f"delivery within {int(days_diff)} days")
    
    # Supplier matching
    if features.supplier_name_similarity is not None:
        if features.supplier_name_similarity > 0.95:
            reasons.append("exact supplier match")
        elif features.supplier_name_similarity > 0.9:
            reasons.append("matching supplier")
        elif features.supplier_name_similarity > 0.8:
            reasons.append("similar supplier name")
    
    # Line item coverage
    if features.proportion_invoice_value_explained is not None:
        if features.proportion_invoice_value_explained > 0.9:
            reasons.append("excellent line-item coverage")
        elif features.proportion_invoice_value_explained > 0.8:
            reasons.append("high line-item coverage")
        elif features.proportion_invoice_value_explained > 0.6:
            reasons.append("good line-item coverage")
    
    # OCR confidence
    if features.ocr_confidence_total is not None and features.ocr_confidence_total > 0.9:
        reasons.append("high OCR confidence")
    
    # Build explanation
    if reasons:
        confidence_str = f"{candidate.probability:.0%}"
        if candidate.probability >= 0.9:
            confidence_str = f"high confidence ({confidence_str})"
        elif candidate.probability >= 0.7:
            confidence_str = f"moderate confidence ({confidence_str})"
        
        return f"Suggested match ({confidence_str}) because: {', '.join(reasons)}."
    else:
        return f"Suggested match with {candidate.probability:.0%} confidence based on supplier and date proximity."


def _llm_enhance_explanation(
    invoice_id: str,
    candidate: PairingCandidate,
    features: Optional[CandidateFeatureSummary],
    template: str
) -> Optional[str]:
    """Use LLM to generate more natural explanation."""
    if not LLM_AVAILABLE:
        return None
    
    llm = _get_llm_instance()
    if not llm or not llm.is_available():
        return None
    
    # Build feature description
    feature_desc = []
    if features:
        if features.amount_diff_pct is not None:
            feature_desc.append(f"Amount difference: {abs(features.amount_diff_pct)*100:.1f}%")
        if features.date_diff_days is not None:
            feature_desc.append(f"Date difference: {abs(features.date_diff_days):.0f} days")
        if features.supplier_name_similarity is not None:
            feature_desc.append(f"Supplier similarity: {features.supplier_name_similarity*100:.0f}%")
        if features.proportion_invoice_value_explained is not None:
            feature_desc.append(f"Line item coverage: {features.proportion_invoice_value_explained*100:.0f}%")
    
    prompt = f"""You are an assistant explaining why an invoice should be paired with a delivery note.

Invoice ID: {invoice_id}
Delivery Note ID: {candidate.delivery_note_id}
Confidence: {candidate.probability:.1%}

Key Features:
{chr(10).join(f'- {f}' for f in feature_desc) if feature_desc else '- No detailed features available'}

Generate a concise, natural explanation (1-2 sentences) for why this pairing was suggested.
Focus on the strongest matching signals. Be specific about numbers when relevant.
Do not include the confidence percentage in your response - it will be shown separately.

Explanation:"""
    
    try:
        result = llm.generate(prompt, max_tokens=150, temperature=0.3)
        if result.success and result.text.strip():
            # Clean up the response
            text = result.text.strip()
            # Remove any trailing punctuation that might be duplicated
            if text.endswith('..'):
                text = text[:-1]
            return text
    except Exception as e:
        LOGGER.debug("LLM enhancement failed: %s", e)
    
    return None

