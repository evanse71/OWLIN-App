# -*- coding: utf-8 -*-
"""
Multi-Factor Confidence Calculator

Calculates calibrated confidence scores that reflect financial trustworthiness.
Uses weighted factors (OCR 40%, Extraction 35%, Validation 25%) and classifies
into actionable bands (high/medium/low/critical).
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger("owlin.services.confidence_calculator")


class ConfidenceBand(Enum):
    """Confidence band classification"""
    HIGH = "high"          # 80-100%: Trust financially - Auto-approve ready
    MEDIUM = "medium"      # 60-79%: Review recommended - Quick check needed
    LOW = "low"            # 40-59%: Manual review required - Significant issues
    CRITICAL = "critical"  # <40%: Cannot trust - Major data problems


class ActionRequired(Enum):
    """Action required based on confidence band"""
    NONE = "none"                    # High confidence - no action
    QUICK_REVIEW = "quick_review"    # Medium confidence - quick check
    MANUAL_REVIEW = "manual_review"  # Low confidence - detailed review
    CANNOT_TRUST = "cannot_trust"    # Critical - major issues


@dataclass
class ConfidenceBreakdown:
    """Detailed confidence breakdown by factor"""
    ocr_quality: float          # 0.0-1.0
    extraction_quality: float   # 0.0-1.0
    validation_quality: float   # 0.0-1.0
    overall_confidence: float   # 0.0-1.0 (weighted average)
    band: ConfidenceBand
    action_required: ActionRequired
    primary_issue: Optional[str] = None
    remediation_hints: List[str] = None
    
    def __post_init__(self):
        if self.remediation_hints is None:
            self.remediation_hints = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "ocr_quality": round(self.ocr_quality, 3),
            "extraction_quality": round(self.extraction_quality, 3),
            "validation_quality": round(self.validation_quality, 3),
            "overall_confidence": round(self.overall_confidence, 3),
            "band": self.band.value,
            "action_required": self.action_required.value,
            "primary_issue": self.primary_issue,
            "remediation_hints": self.remediation_hints
        }


class ConfidenceCalculator:
    """
    Multi-factor confidence calculator with calibrated bands.
    
    Weights:
    - OCR Quality: 40%
    - Extraction Quality: 35%
    - Validation Quality: 25%
    """
    
    # Factor weights
    OCR_WEIGHT = 0.40
    EXTRACTION_WEIGHT = 0.35
    VALIDATION_WEIGHT = 0.25
    
    def __init__(self):
        """Initialize the confidence calculator"""
        pass
    
    def calculate_confidence(
        self,
        ocr_result: Dict[str, Any],
        parsed_data: Dict[str, Any],
        line_items: List[Dict[str, Any]],
        ocr_text_length: int = 0
    ) -> ConfidenceBreakdown:
        """
        Calculate multi-factor confidence with band classification.
        
        Args:
            ocr_result: OCR processing result with confidence scores
            parsed_data: Extracted invoice data (supplier, date, total, etc.)
            line_items: List of extracted line items
            ocr_text_length: Total length of OCR text extracted
            
        Returns:
            ConfidenceBreakdown with detailed analysis
        """
        # Calculate individual factor scores
        ocr_quality = self._calculate_ocr_quality(ocr_result, ocr_text_length)
        extraction_quality = self._calculate_extraction_quality(parsed_data, line_items)
        validation_quality = self._calculate_validation_quality(parsed_data, line_items)
        
        # Calculate weighted overall confidence
        overall_confidence = (
            ocr_quality * self.OCR_WEIGHT +
            extraction_quality * self.EXTRACTION_WEIGHT +
            validation_quality * self.VALIDATION_WEIGHT
        )
        
        # Classify band and determine action
        band, action_required, primary_issue, remediation_hints = self._classify_band(
            overall_confidence,
            ocr_quality,
            extraction_quality,
            validation_quality,
            parsed_data,
            line_items
        )
        
        return ConfidenceBreakdown(
            ocr_quality=ocr_quality,
            extraction_quality=extraction_quality,
            validation_quality=validation_quality,
            overall_confidence=overall_confidence,
            band=band,
            action_required=action_required,
            primary_issue=primary_issue,
            remediation_hints=remediation_hints
        )
    
    def _calculate_ocr_quality(
        self,
        ocr_result: Dict[str, Any],
        ocr_text_length: int
    ) -> float:
        """
        Calculate OCR quality score (0.0-1.0).
        
        Factors:
        - OCR confidence from engine
        - Text length (minimum viable threshold)
        - Word count
        """
        # Get OCR confidence (normalize to 0-1 if needed)
        ocr_confidence = ocr_result.get("overall_confidence") or ocr_result.get("confidence", 0.0)
        if ocr_confidence > 1.0:
            ocr_confidence = ocr_confidence / 100.0
        
        # Base score from OCR confidence
        base_score = max(0.0, min(1.0, ocr_confidence))
        
        # Penalize if text is too short (minimum viable threshold)
        if ocr_text_length < 50:
            # Severe penalty for very short text
            text_penalty = 0.5 if ocr_text_length < 20 else 0.3
            base_score = base_score * (1.0 - text_penalty)
        
        # Boost for good word count
        word_count = ocr_text_length // 5  # Rough estimate
        if word_count > 100:
            base_score = min(1.0, base_score * 1.1)
        elif word_count < 20:
            base_score = base_score * 0.8
        
        return max(0.0, min(1.0, base_score))
    
    def _calculate_extraction_quality(
        self,
        parsed_data: Dict[str, Any],
        line_items: List[Dict[str, Any]]
    ) -> float:
        """
        Calculate extraction quality score (0.0-1.0).
        
        Factors:
        - Field completeness (supplier, date, total, invoice_number)
        - Supplier known (not "Unknown")
        - Totals present and > 0
        - Line items present and valid
        """
        score = 0.0
        max_score = 1.0
        
        # Supplier quality (30% of extraction score)
        supplier = parsed_data.get("supplier", "Unknown Supplier")
        if supplier and supplier != "Unknown Supplier" and supplier != "Unknown":
            score += 0.30
        else:
            # Severe penalty for unknown supplier
            pass  # No points
        
        # Date quality (15% of extraction score)
        date = parsed_data.get("date")
        if date and date != "":
            score += 0.15
        
        # Total amount quality (25% of extraction score)
        total = parsed_data.get("total", 0.0)
        if total and total > 0.0:
            score += 0.25
        else:
            # Critical: no total means extraction failed
            pass  # No points
        
        # Invoice number quality (10% of extraction score)
        invoice_number = parsed_data.get("invoice_number")
        if invoice_number and invoice_number != "":
            score += 0.10
        
        # Line items quality (20% of extraction score)
        if line_items and len(line_items) > 0:
            # Check quality of line items
            valid_items = sum(1 for item in line_items if self._is_valid_line_item(item))
            if valid_items > 0:
                item_quality = min(1.0, valid_items / max(1, len(line_items)))
                score += 0.20 * item_quality
        else:
            # No line items - significant penalty
            pass  # No points
        
        # Business rule: If supplier is unknown AND total is 0, cap at 50%
        if (supplier == "Unknown Supplier" or supplier == "Unknown") and total == 0.0:
            score = min(score, 0.50)
        
        return max(0.0, min(1.0, score))
    
    def _is_valid_line_item(self, item: Dict[str, Any]) -> bool:
        """Check if a line item is valid (has description and total)"""
        if not item:
            return False
        
        description = item.get("description") or item.get("desc") or item.get("item")
        total = item.get("total") or item.get("total_price") or 0.0
        
        try:
            total = float(total) if total else 0.0
        except (ValueError, TypeError):
            total = 0.0
        
        return bool(description and len(str(description).strip()) > 2) and total > 0.0
    
    def _calculate_validation_quality(
        self,
        parsed_data: Dict[str, Any],
        line_items: List[Dict[str, Any]]
    ) -> float:
        """
        Calculate validation quality score (0.0-1.0).
        
        Factors:
        - Math consistency (line items sum matches total)
        - VAT calculations
        - Data reasonableness
        """
        score = 1.0  # Start with perfect score, deduct for issues
        
        total = parsed_data.get("total", 0.0)
        
        # CRITICAL: If total exists but no line items, this is suspicious
        # Line-item-driven invoices should have line items
        if total and total > 0.0 and (not line_items or len(line_items) == 0):
            # Cap validation score - we can't validate math without line items
            score = 0.5  # Significant penalty for missing line items when total exists
        
        # Check line items sum vs total
        if line_items and len(line_items) > 0:
            if total and total > 0.0:
                # Calculate sum of line items
                line_items_sum = 0.0
                for item in line_items:
                    item_total = item.get("total") or item.get("total_price") or 0.0
                    try:
                        line_items_sum += float(item_total) if item_total else 0.0
                    except (ValueError, TypeError):
                        pass
                
                if line_items_sum > 0.0:
                    # Check if sum matches total (within 5% tolerance)
                    difference = abs(line_items_sum - total)
                    relative_error = difference / total if total > 0 else 1.0
                    
                    if relative_error > 0.10:  # >10% error
                        score -= 0.5  # Major penalty
                    elif relative_error > 0.05:  # >5% error
                        score -= 0.3  # Moderate penalty
                    elif relative_error > 0.01:  # >1% error
                        score -= 0.1  # Minor penalty
        
        # Check VAT consistency if present
        vat_amount = parsed_data.get("vat") or parsed_data.get("vat_amount") or 0.0
        vat_rate = parsed_data.get("vat_rate") or 0.0
        subtotal = parsed_data.get("subtotal") or (total - vat_amount if total else 0.0)
        
        if vat_rate > 0 and subtotal > 0:
            expected_vat = subtotal * (vat_rate / 100.0) if vat_rate > 1 else subtotal * vat_rate
            if vat_amount > 0:
                vat_error = abs(vat_amount - expected_vat) / expected_vat if expected_vat > 0 else 1.0
                if vat_error > 0.10:  # >10% VAT error
                    score -= 0.2
        
        return max(0.0, min(1.0, score))
    
    def _classify_band(
        self,
        overall_confidence: float,
        ocr_quality: float,
        extraction_quality: float,
        validation_quality: float,
        parsed_data: Dict[str, Any],
        line_items: List[Dict[str, Any]]
    ) -> Tuple[ConfidenceBand, ActionRequired, Optional[str], List[str]]:
        """
        Classify confidence into band and determine action required.
        
        Returns:
            Tuple of (band, action_required, primary_issue, remediation_hints)
        """
        supplier = parsed_data.get("supplier", "Unknown Supplier")
        total = parsed_data.get("total", 0.0)
        line_items_count = len(line_items) if line_items else 0
        
        remediation_hints = []
        primary_issue = None
        
        # Critical band: <40% OR major data problems
        if overall_confidence < 0.40:
            band = ConfidenceBand.CRITICAL
            action_required = ActionRequired.CANNOT_TRUST
            if ocr_quality < 0.30:
                primary_issue = "OCR quality too low"
                remediation_hints.append("OCR confidence is very low - consider re-scanning document")
            elif supplier == "Unknown Supplier" or supplier == "Unknown":
                if total == 0.0 and line_items_count == 0:
                    primary_issue = "No data extracted"
                    remediation_hints.append("Supplier unknown, total is zero, and no line items found")
                else:
                    primary_issue = "Supplier unknown"
                    remediation_hints.append("Supplier name could not be extracted - manual verification needed")
            elif total == 0.0:
                primary_issue = "No total amount"
                remediation_hints.append("Total amount is zero - verify extraction")
            elif line_items_count == 0:
                primary_issue = "No line items"
                remediation_hints.append("No line items extracted - check if document has line items")
        
        # Low band: 40-59% OR significant issues
        elif overall_confidence < 0.60:
            band = ConfidenceBand.LOW
            action_required = ActionRequired.MANUAL_REVIEW
            if ocr_quality < 0.50:
                primary_issue = "OCR quality below threshold"
                remediation_hints.append("OCR confidence is low - review extracted text")
            elif extraction_quality < 0.40:
                primary_issue = "Extraction quality issues"
                remediation_hints.append("Some fields may be missing or incorrect")
            elif validation_quality < 0.70:
                primary_issue = "Validation issues detected"
                remediation_hints.append("Math inconsistencies detected - verify totals")
        
        # Medium band: 60-79% OR minor issues
        elif overall_confidence < 0.80:
            band = ConfidenceBand.MEDIUM
            action_required = ActionRequired.QUICK_REVIEW
            if ocr_quality < 0.60:
                primary_issue = "OCR quality moderate"
                remediation_hints.append("Quick review recommended - OCR confidence is moderate")
            elif extraction_quality < 0.50:
                primary_issue = "Some fields may need verification"
                remediation_hints.append("Verify extracted fields match document")
            elif validation_quality < 0.85:
                primary_issue = "Minor validation issues"
                remediation_hints.append("Check totals and calculations")
        
        # High band: 80-100% - all factors good
        else:
            band = ConfidenceBand.HIGH
            action_required = ActionRequired.NONE
            # Check if all factors are >75%
            if ocr_quality > 0.75 and extraction_quality > 0.75 and validation_quality > 0.75:
                primary_issue = None  # No issues
            else:
                # High overall but one factor is lower
                if ocr_quality <= 0.75:
                    primary_issue = "OCR quality could be better"
                elif extraction_quality <= 0.75:
                    primary_issue = "Some extraction fields could be verified"
                else:
                    primary_issue = "Minor validation note"
        
        return band, action_required, primary_issue, remediation_hints

