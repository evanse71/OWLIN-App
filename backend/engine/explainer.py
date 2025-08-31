"""
Explainer - LLM Leashed with Deterministic Fallback
Generate explanations for anomalies with strict output schema.
"""

import json
import hashlib
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from config_units import ENGINE_VERSION


class ExplainerResponse:
    """Strict Pydantic-like schema for explainer output."""
    
    def __init__(self, headline: str, explanation: str, 
                 suggested_actions: List[Dict[str, str]],
                 engine_verdict: str, engine_facts_hash: str,
                 model_id: str = "deterministic", prompt_hash: str = "",
                 response_hash: str = ""):
        self.headline = headline
        self.explanation = explanation
        self.suggested_actions = suggested_actions
        self.engine_verdict = engine_verdict
        self.engine_facts_hash = engine_facts_hash
        self.model_id = model_id
        self.prompt_hash = prompt_hash
        self.response_hash = response_hash
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "headline": self.headline,
            "explanation": self.explanation,
            "suggested_actions": self.suggested_actions,
            "engine_verdict": self.engine_verdict,
            "engine_facts_hash": self.engine_facts_hash,
            "model_id": self.model_id,
            "prompt_hash": self.prompt_hash,
            "response_hash": self.response_hash
        }
    
    def validate(self) -> bool:
        """Validate the response meets schema requirements."""
        if not self.headline or len(self.headline) > 100:
            return False
        
        if not self.explanation or len(self.explanation) > 500:
            return False
        
        if not self.suggested_actions or len(self.suggested_actions) > 3:
            return False
        
        for action in self.suggested_actions:
            if not isinstance(action, dict) or 'label' not in action or 'reason' not in action:
                return False
        
        if not self.engine_verdict:
            return False
        
        return True


def create_engine_facts_hash(verdict: str, hypothesis: Optional[str],
                           implied_value: Optional[float], residual: Optional[float],
                           sku_id: str, supplier_id: str) -> str:
    """Create deterministic hash of engine facts."""
    # Convert hypothesis to string if it's a DiscountHypothesis object
    if hasattr(hypothesis, 'hypothesis_type'):
        hypothesis_str = hypothesis.hypothesis_type
    else:
        hypothesis_str = hypothesis
    
    facts = {
        "verdict": verdict,
        "hypothesis": hypothesis_str,
        "implied_value": implied_value,
        "residual": residual,
        "sku_id": sku_id,
        "supplier_id": supplier_id,
        "engine_version": ENGINE_VERSION
    }
    
    facts_str = json.dumps(facts, sort_keys=True)
    return hashlib.sha256(facts_str.encode()).hexdigest()


def get_deterministic_explanation(verdict: str, hypothesis: Optional[str],
                                implied_value: Optional[float], residual: Optional[float],
                                sku_id: str, supplier_id: str) -> ExplainerResponse:
    """Generate deterministic explanation template."""
    
    # Create engine facts hash
    engine_facts_hash = create_engine_facts_hash(
        verdict, hypothesis, implied_value, residual, sku_id, supplier_id
    )
    
    # Generate headline and explanation based on verdict
    if verdict == "math_mismatch":
        headline = "Mathematical inconsistency detected"
        explanation = f"Line total does not match unit price × quantity calculation. Difference: £{residual:.2f}."
        actions = [
            {"label": "Review OCR accuracy", "reason": "Check if numbers were misread"},
            {"label": "Verify line totals", "reason": "Confirm manual calculations"}
        ]
    
    elif verdict == "reference_conflict":
        headline = "Conflicting price references"
        explanation = f"Different price sources disagree for {sku_id}. Manual review required."
        actions = [
            {"label": "Check contract terms", "reason": "Verify current pricing agreement"},
            {"label": "Contact supplier", "reason": "Clarify pricing discrepancy"}
        ]
    
    elif verdict == "uom_mismatch_suspected":
        headline = "Unit of measure confusion suspected"
        explanation = f"Price difference may be due to pack size confusion for {sku_id}."
        actions = [
            {"label": "Verify pack sizes", "reason": "Check if case vs unit pricing"},
            {"label": "Update UOM mapping", "reason": "Correct unit definitions"}
        ]
    
    elif verdict == "off_contract_discount":
        discount_pct = abs(implied_value * 100) if implied_value else 0
        headline = f"Off-contract discount detected ({discount_pct:.1f}%)"
        explanation = f"Price is {discount_pct:.1f}% different from contract terms for {sku_id}."
        actions = [
            {"label": "Verify discount approval", "reason": "Check if discount is authorised"},
            {"label": "Update contract", "reason": "Record new pricing terms"}
        ]
    
    elif verdict == "unusual_vs_history":
        headline = "Unusual pricing vs history"
        explanation = f"Price for {sku_id} differs significantly from historical patterns."
        actions = [
            {"label": "Review price change", "reason": "Check if change is expected"},
            {"label": "Update price history", "reason": "Record new baseline"}
        ]
    
    elif verdict == "ocr_suspected_error":
        headline = "OCR error suspected"
        explanation = f"Numbers may have been misread during OCR processing for {sku_id}."
        actions = [
            {"label": "Review original document", "reason": "Check image quality and clarity"},
            {"label": "Re-process with OCR", "reason": "Try alternative OCR settings"}
        ]
    
    elif verdict == "ok_on_contract":
        headline = "Price within contract terms"
        explanation = f"Price for {sku_id} matches expected contract pricing."
        actions = [
            {"label": "No action required", "reason": "Price is acceptable"}
        ]
    
    elif verdict == "needs_user_rule":
        headline = "Requires manual review"
        explanation = f"Complex pricing scenario for {sku_id} needs human judgement."
        actions = [
            {"label": "Review pricing logic", "reason": "Apply business rules manually"},
            {"label": "Create pricing rule", "reason": "Add rule for future automation"}
        ]
    
    else:  # pricing_anomaly_unmodelled
        headline = "Pricing anomaly not explained"
        explanation = f"Price difference for {sku_id} cannot be explained by current models."
        actions = [
            {"label": "Investigate manually", "reason": "Review supplier communication"},
            {"label": "Add new model", "reason": "Consider new discount type"}
        ]
    
    return ExplainerResponse(
        headline=headline,
        explanation=explanation,
        suggested_actions=actions,
        engine_verdict=verdict,
        engine_facts_hash=engine_facts_hash,
        model_id="deterministic"
    )


def call_llm_explainer(engine_facts: Dict, cache_key: str) -> Optional[ExplainerResponse]:
    """
    Call LLM explainer with strict guardrails.
    
    Returns:
        ExplainerResponse if successful, None if failed
    """
    # TODO: Implement LLM call with strict output validation
    # This would call the LLM service with a carefully crafted prompt
    # and validate the response against the schema
    
    # For now, return None to use deterministic fallback
    return None


def get_explanation(verdict: str, hypothesis: Optional[str],
                   implied_value: Optional[float], residual: Optional[float],
                   sku_id: str, supplier_id: str, line_fingerprint: str,
                   max_llm_calls: int = 10, cache_duration_days: int = 30) -> ExplainerResponse:
    """
    Get explanation for anomaly with LLM leashed.
    
    Args:
        verdict: Engine verdict
        hypothesis: Discount hypothesis type
        implied_value: Implied discount value
        residual: Residual error
        sku_id: SKU identifier
        supplier_id: Supplier identifier
        line_fingerprint: Line fingerprint for caching
        max_llm_calls: Maximum LLM calls per invoice
        cache_duration_days: Cache duration in days
        
    Returns:
        ExplainerResponse
    """
    # Only call LLM for anomalies
    if verdict in ["ok_on_contract"]:
        return get_deterministic_explanation(
            verdict, hypothesis, implied_value, residual, sku_id, supplier_id
        )
    
    # TODO: Check cache for existing explanation
    # This would query a cache table for existing explanations
    
    # TODO: Check LLM call limits
    # This would track LLM calls per invoice and respect limits
    
    # Try LLM first
    engine_facts = {
        "verdict": verdict,
        "hypothesis": hypothesis,
        "implied_value": implied_value,
        "residual": residual,
        "sku_id": sku_id,
        "supplier_id": supplier_id
    }
    
    llm_response = call_llm_explainer(engine_facts, line_fingerprint)
    
    if llm_response and llm_response.validate():
        # Validate that LLM response matches engine verdict
        if llm_response.engine_verdict == verdict:
            return llm_response
        else:
            # LLM contradicted engine - discard and use deterministic
            pass
    
    # Fall back to deterministic explanation
    return get_deterministic_explanation(
        verdict, hypothesis, implied_value, residual, sku_id, supplier_id
    )


def cache_explanation(explanation: ExplainerResponse, line_fingerprint: str,
                     db_connection) -> None:
    """Cache explanation for reuse."""
    # TODO: Implement explanation caching
    # This would store explanations in a cache table with expiry
    pass


def get_cached_explanation(line_fingerprint: str, db_connection) -> Optional[ExplainerResponse]:
    """Get cached explanation if available and not expired."""
    # TODO: Implement cache retrieval
    # This would query cache table and check expiry
    return None 