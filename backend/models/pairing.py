from typing import Dict, List, Literal, Optional

from pydantic import BaseModel


class FeatureSummary(BaseModel):
    amount_diff_pct: float
    date_diff_days: Optional[float]
    proportion_invoice_value_explained: float
    supplier_name_similarity: float
    ocr_confidence_total: float


class PairingCandidate(BaseModel):
    delivery_note_id: str
    probability: float
    features: Dict[str, float]
    features_summary: FeatureSummary
    delivery_date: Optional[str] = None
    delivery_total: Optional[float] = None
    venue: Optional[str] = None
    supplier: Optional[str] = None
    model_version: Optional[str] = None


class PairingResult(BaseModel):
    invoice_id: str
    status: Literal["auto_paired", "suggested", "unpaired"]
    pairing_confidence: Optional[float]
    pairing_model_version: Optional[str]
    best_candidate: Optional[PairingCandidate]
    candidates: List[PairingCandidate]
    llm_explanation: Optional[str] = None


# Alias for backward compatibility - CandidateFeatureSummary is the same as FeatureSummary
CandidateFeatureSummary = FeatureSummary
