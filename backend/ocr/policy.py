#!/usr/bin/env python3
"""
Document Policy Engine - Phase-C Enhanced

Evaluates documents and determines routing based on classification, validation, and confidence.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import datetime

from .config import get_ocr_config
from .classifier import ClassificationResult
from .validate import ValidationResult

logger = logging.getLogger(__name__)

class PolicyAction(Enum):
    ACCEPT = "ACCEPT"
    ACCEPT_WITH_WARNINGS = "ACCEPT_WITH_WARNINGS"
    QUARANTINE = "QUARANTINE"
    REJECT = "REJECT"

class PolicyReason(Enum):
    DOC_OTHER = "doc_other"
    LOW_CONFIDENCE = "low_confidence"
    CRITICAL_VALIDATION_FAIL = "critical_validation_fail"
    FUTURE_DATE = "future_date"
    ARITHMETIC_MISMATCH = "arithmetic_mismatch"
    CURRENCY_INCONSISTENT = "currency_inconsistent"
    HEIC_NOT_SUPPORTED = "heic_not_supported"
    AUTO_RETRY_USED = "auto_retry_used"
    TEMPLATE_HINT_USED = "template_hint_used"
    LLM_ASSIST_DTYPE = "llm_assist_dtype"
    LLM_ASSIST_IGNORED = "llm_assist_ignored"

@dataclass
class PolicyDecision:
    action: PolicyAction
    reasons: List[PolicyReason]
    confidence_threshold_met: bool
    validation_passed: bool
    auto_retry_used: bool = False
    retry_metrics: Optional[Dict[str, Any]] = None

class DocumentPolicy:
    """Document policy evaluator with configuration-driven thresholds"""
    
    def __init__(self):
        self.config = get_ocr_config()
        self.critical_issues = self.config.get_policy("critical_issues")
    
    def evaluate_document(self, 
                         classification: ClassificationResult, 
                         validation: ValidationResult, 
                         extracted_data: Dict[str, Any], 
                         ocr_confidence: float,
                         auto_retry_used: bool = False,
                         retry_metrics: Optional[Dict[str, Any]] = None) -> PolicyDecision:
        """
        Evaluate document and determine policy action
        
        Args:
            classification: Document classification result
            validation: Document validation result
            extracted_data: Extracted document data
            ocr_confidence: Overall OCR confidence (0-100)
            auto_retry_used: Whether auto-retry was used
            retry_metrics: Metrics from auto-retry if used
            
        Returns:
            PolicyDecision with action and reasons
        """
        logger.info(f"🔍 Evaluating document policy: doc_type={classification.doc_type}, confidence={ocr_confidence:.1f}")
        
        reasons = []
        confidence_threshold_met = True
        validation_passed = True
        
        # Get thresholds from config
        accept_min = self.config.get_threshold("accept_min_confidence")
        warning_min = self.config.get_threshold("warning_min_confidence")
        reject_max = self.config.get_threshold("reject_max_confidence")
        
        # Check for immediate rejection conditions
        if classification.doc_type == 'other':
            logger.info("❌ Document classified as 'other' - REJECT")
            return PolicyDecision(
                action=PolicyAction.REJECT,
                reasons=[PolicyReason.DOC_OTHER],
                confidence_threshold_met=False,
                validation_passed=False,
                auto_retry_used=auto_retry_used,
                retry_metrics=retry_metrics
            )
        
        if ocr_confidence < reject_max:
            logger.info(f"❌ OCR confidence {ocr_confidence:.1f} below reject threshold {reject_max} - REJECT")
            return PolicyDecision(
                action=PolicyAction.REJECT,
                reasons=[PolicyReason.LOW_CONFIDENCE],
                confidence_threshold_met=False,
                validation_passed=False,
                auto_retry_used=auto_retry_used,
                retry_metrics=retry_metrics
            )
        
        # Check validation results
        if validation and validation.issues:
            critical_validation_failures = [
                issue for issue in validation.issues 
                if issue.issue_type in self.critical_issues
            ]
            
            if critical_validation_failures:
                validation_passed = False
                reasons.append(PolicyReason.CRITICAL_VALIDATION_FAIL)
                
                # Add specific validation reasons
                for issue in critical_validation_failures:
                    if issue.issue_type == "FUTURE_DATE":
                        reasons.append(PolicyReason.FUTURE_DATE)
                    elif issue.issue_type == "ARITHMETIC_MISMATCH":
                        reasons.append(PolicyReason.ARITHMETIC_MISMATCH)
                    elif issue.issue_type == "CURRENCY_INCONSISTENT":
                        reasons.append(PolicyReason.CURRENCY_INCONSISTENT)
        
        # Determine action based on confidence and validation
        if not validation_passed:
            if ocr_confidence < (accept_min + warning_min) / 2:  # Use midpoint as quarantine threshold
                action = PolicyAction.QUARANTINE
                logger.info(f"⚠️ Critical validation failures + low confidence - QUARANTINE")
            else:
                action = PolicyAction.ACCEPT_WITH_WARNINGS
                logger.info(f"⚠️ Critical validation failures but good confidence - ACCEPT_WITH_WARNINGS")
        elif ocr_confidence >= accept_min:
            action = PolicyAction.ACCEPT
            logger.info(f"✅ High confidence and validation passed - ACCEPT")
        elif ocr_confidence >= warning_min:
            action = PolicyAction.ACCEPT_WITH_WARNINGS
            logger.info(f"⚠️ Medium confidence - ACCEPT_WITH_WARNINGS")
        else:
            action = PolicyAction.QUARANTINE
            confidence_threshold_met = False
            logger.info(f"⚠️ Low confidence - QUARANTINE")
        
        # Add auto-retry reason if used
        if auto_retry_used:
            reasons.append(PolicyReason.AUTO_RETRY_USED)
        
        decision = PolicyDecision(
            action=action,
            reasons=reasons,
            confidence_threshold_met=confidence_threshold_met,
            validation_passed=validation_passed,
            auto_retry_used=auto_retry_used,
            retry_metrics=retry_metrics
        )
        
        logger.info(f"📋 Policy decision: {action.value}, reasons: {[r.value for r in reasons]}")
        return decision

# Global policy instance
_policy_instance: Optional[DocumentPolicy] = None

def get_document_policy() -> DocumentPolicy:
    """Get global document policy instance"""
    global _policy_instance
    if _policy_instance is None:
        _policy_instance = DocumentPolicy()
    return _policy_instance

def evaluate_document_policy(classification: ClassificationResult,
                           validation: ValidationResult,
                           extracted_data: Dict[str, Any],
                           ocr_confidence: float,
                           auto_retry_used: bool = False,
                           retry_metrics: Optional[Dict[str, Any]] = None) -> PolicyDecision:
    """Convenience function to evaluate document policy"""
    policy = get_document_policy()
    return policy.evaluate_document(classification, validation, extracted_data, ocr_confidence, auto_retry_used, retry_metrics) 