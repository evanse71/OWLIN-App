"""
Confidence Routing and Human-in-the-Loop Flagging System

This module provides comprehensive confidence calculation, routing decisions,
and flagging for the OCR pipeline. It ensures only high-confidence, error-free
records are auto-accepted while routing questionable items for human review.

Features:
- Per-field, per-block, and per-page confidence calculation
- Configurable confidence thresholds
- Auto-accept vs. needs-review routing
- Comprehensive audit logging
- Error case handling
- Review candidate collation
"""

from __future__ import annotations
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
from decimal import Decimal

from .types import (
    NormalizedInvoice, NormalizedLineItem, FieldError, FieldErrorType,
    ParsedDate, ParsedCurrency, ParsedPrice, ParsedVAT, ParsedSupplier, ParsedUnit
)

LOGGER = logging.getLogger("owlin.normalization.confidence_routing")


class RoutingDecision(Enum):
    """Routing decision types."""
    AUTO_ACCEPT = "auto_accept"
    NEEDS_REVIEW = "needs_review"
    ERROR = "error"


class ConfidenceSource(Enum):
    """Sources of confidence metrics."""
    OCR_MODEL = "ocr_model"
    NORMALIZATION_SUCCESS = "normalization_success"
    ERROR_METRICS = "error_metrics"
    CONTEXT_MATCHING = "context_matching"
    CROSS_VALIDATION = "cross_validation"


@dataclass
class ConfidenceMetrics:
    """Comprehensive confidence metrics for a field or item."""
    ocr_confidence: float = 0.0
    normalization_confidence: float = 0.0
    error_penalty: float = 0.0
    context_boost: float = 0.0
    cross_validation_score: float = 0.0
    overall_confidence: float = 0.0
    
    def calculate_overall(self, weights: Optional[Dict[str, float]] = None) -> float:
        """Calculate overall confidence using weighted factors."""
        if weights is None:
            weights = {
                'ocr': 0.3,
                'normalization': 0.4,
                'error': 0.2,
                'context': 0.05,
                'cross_validation': 0.05
            }
        
        # Apply error penalty
        error_adjusted_ocr = max(0.0, self.ocr_confidence - self.error_penalty)
        error_adjusted_norm = max(0.0, self.normalization_confidence - self.error_penalty)
        
        # Calculate weighted average
        overall = (
            error_adjusted_ocr * weights['ocr'] +
            error_adjusted_norm * weights['normalization'] +
            self.context_boost * weights['context'] +
            self.cross_validation_score * weights['cross_validation']
        )
        
        # Apply error penalty to final score
        self.overall_confidence = max(0.0, overall - (self.error_penalty * weights['error']))
        return self.overall_confidence


@dataclass
class RoutingResult:
    """Result of confidence routing for a field or item."""
    field_name: str
    routing_decision: RoutingDecision
    confidence_metrics: ConfidenceMetrics
    threshold_used: float
    error_details: List[str] = field(default_factory=list)
    source_artifact: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    
    def is_auto_acceptable(self) -> bool:
        """Check if this item can be auto-accepted."""
        return (self.routing_decision == RoutingDecision.AUTO_ACCEPT and 
                self.confidence_metrics.overall_confidence >= self.threshold_used)
    
    def needs_human_review(self) -> bool:
        """Check if this item needs human review."""
        return self.routing_decision == RoutingDecision.NEEDS_REVIEW


@dataclass
class ReviewCandidate:
    """A field or item that needs human review."""
    field_name: str
    field_type: str
    raw_value: str
    normalized_value: Optional[Any]
    confidence_metrics: ConfidenceMetrics
    routing_result: RoutingResult
    error_details: List[str]
    suggestions: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "field_name": self.field_name,
            "field_type": self.field_type,
            "raw_value": self.raw_value,
            "normalized_value": str(self.normalized_value) if self.normalized_value is not None else None,
            "confidence": self.confidence_metrics.overall_confidence,
            "routing_decision": self.routing_result.routing_decision.value,
            "error_details": self.error_details,
            "suggestions": self.suggestions,
            "context": self.context
        }


@dataclass
class ConfidenceRoutingResult:
    """Complete result of confidence routing for an invoice."""
    invoice_id: str
    overall_confidence: float
    auto_accepted_fields: List[str]
    review_candidates: List[ReviewCandidate]
    routing_log: List[RoutingResult]
    processing_time: float
    error_count: int
    warning_count: int
    
    def is_fully_auto_acceptable(self) -> bool:
        """Check if the entire invoice can be auto-accepted."""
        return len(self.review_candidates) == 0 and self.overall_confidence >= 0.7
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the routing result."""
        return {
            "invoice_id": self.invoice_id,
            "overall_confidence": self.overall_confidence,
            "auto_accepted_count": len(self.auto_accepted_fields),
            "review_candidates_count": len(self.review_candidates),
            "is_fully_auto_acceptable": self.is_fully_auto_acceptable(),
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "processing_time": self.processing_time
        }


class ConfidenceCalculator:
    """Calculates confidence metrics for fields and items."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the confidence calculator with configuration."""
        self.config = config or {}
        self.default_weights = {
            'ocr': 0.3,
            'normalization': 0.4,
            'error': 0.2,
            'context': 0.05,
            'cross_validation': 0.05
        }
        
    def calculate_field_confidence(self, field_name: str, parsed_result: Any, 
                                 context: Optional[Dict[str, Any]] = None) -> ConfidenceMetrics:
        """Calculate confidence metrics for a parsed field."""
        metrics = ConfidenceMetrics()
        
        # OCR confidence (from parsed result)
        if hasattr(parsed_result, 'confidence'):
            metrics.ocr_confidence = parsed_result.confidence
        else:
            metrics.ocr_confidence = 0.5  # Default if not available
        
        # Normalization confidence
        if hasattr(parsed_result, 'is_valid') and parsed_result.is_valid():
            metrics.normalization_confidence = 0.9
        else:
            metrics.normalization_confidence = 0.3
        
        # Error penalty
        if hasattr(parsed_result, 'errors') and parsed_result.errors:
            error_penalty = min(0.5, len(parsed_result.errors) * 0.1)
            metrics.error_penalty = error_penalty
        
        # Context boost
        metrics.context_boost = self._calculate_context_boost(field_name, parsed_result, context)
        
        # Cross-validation score
        metrics.cross_validation_score = self._calculate_cross_validation_score(field_name, parsed_result, context)
        
        # Calculate overall confidence
        weights = self.config.get('confidence_weights', self.default_weights)
        metrics.calculate_overall(weights)
        
        return metrics
    
    def calculate_line_item_confidence(self, line_item: NormalizedLineItem, 
                                    context: Optional[Dict[str, Any]] = None) -> ConfidenceMetrics:
        """Calculate confidence metrics for a line item."""
        metrics = ConfidenceMetrics()
        
        # OCR confidence (from line item)
        metrics.ocr_confidence = line_item.confidence
        
        # Normalization confidence
        if line_item.is_valid():
            metrics.normalization_confidence = 0.9
        else:
            metrics.normalization_confidence = 0.3
        
        # Error penalty
        if line_item.errors:
            error_penalty = min(0.5, len(line_item.errors) * 0.1)
            metrics.error_penalty = error_penalty
        
        # Context boost
        metrics.context_boost = self._calculate_line_item_context_boost(line_item, context)
        
        # Cross-validation score
        metrics.cross_validation_score = self._calculate_line_item_cross_validation(line_item, context)
        
        # Calculate overall confidence
        weights = self.config.get('confidence_weights', self.default_weights)
        metrics.calculate_overall(weights)
        
        return metrics
    
    def calculate_invoice_confidence(self, normalized_invoice: NormalizedInvoice, 
                                   context: Optional[Dict[str, Any]] = None) -> ConfidenceMetrics:
        """Calculate overall confidence metrics for an invoice."""
        metrics = ConfidenceMetrics()
        
        # OCR confidence (from invoice)
        metrics.ocr_confidence = normalized_invoice.overall_confidence
        
        # Normalization confidence
        if normalized_invoice.is_valid():
            metrics.normalization_confidence = 0.9
        else:
            metrics.normalization_confidence = 0.3
        
        # Error penalty
        if normalized_invoice.errors:
            error_penalty = min(0.5, len(normalized_invoice.errors) * 0.05)
            metrics.error_penalty = error_penalty
        
        # Context boost
        metrics.context_boost = self._calculate_invoice_context_boost(normalized_invoice, context)
        
        # Cross-validation score
        metrics.cross_validation_score = self._calculate_invoice_cross_validation(normalized_invoice, context)
        
        # Calculate overall confidence
        weights = self.config.get('confidence_weights', self.default_weights)
        metrics.calculate_overall(weights)
        
        return metrics
    
    def _calculate_context_boost(self, field_name: str, parsed_result: Any, 
                                context: Optional[Dict[str, Any]]) -> float:
        """Calculate context-based confidence boost."""
        if not context:
            return 0.0
        
        boost = 0.0
        
        # Known suppliers boost
        if field_name == 'supplier' and hasattr(parsed_result, 'name'):
            known_suppliers = context.get('known_suppliers', [])
            if parsed_result.name in known_suppliers:
                boost += 0.1
        
        # Document region matching
        if field_name == 'currency' and hasattr(parsed_result, 'currency_code'):
            region = context.get('region', '').lower()
            currency = parsed_result.currency_code
            if (region in ['uk', 'gb'] and currency == 'GBP') or \
               (region in ['eu', 'europe'] and currency == 'EUR') or \
               (region in ['us', 'usa'] and currency == 'USD'):
                boost += 0.05
        
        # Date reasonableness
        if field_name == 'date' and hasattr(parsed_result, 'date'):
            if parsed_result.date:
                from datetime import date
                today = date.today()
                days_diff = abs((parsed_result.date - today).days)
                if days_diff < 365:  # Within a year
                    boost += 0.05
        
        return min(boost, 0.2)  # Cap at 0.2
    
    def _calculate_line_item_context_boost(self, line_item: NormalizedLineItem, 
                                         context: Optional[Dict[str, Any]]) -> float:
        """Calculate context boost for line items."""
        if not context:
            return 0.0
        
        boost = 0.0
        
        # Price reasonableness
        if line_item.unit_price and line_item.quantity and line_item.line_total:
            calculated_total = line_item.unit_price * line_item.quantity
            if abs(calculated_total - line_item.line_total) < 0.01:  # Within 1 cent
                boost += 0.1
        
        # Unit consistency
        if line_item.unit and line_item.quantity:
            if line_item.unit in ['pcs', 'each', 'units'] and line_item.quantity > 0:
                boost += 0.05
        
        return min(boost, 0.2)
    
    def _calculate_invoice_context_boost(self, invoice: NormalizedInvoice, 
                                        context: Optional[Dict[str, Any]]) -> float:
        """Calculate context boost for invoices."""
        if not context:
            return 0.0
        
        boost = 0.0
        
        # Total calculation consistency
        if invoice.subtotal and invoice.tax_amount and invoice.total_amount:
            calculated_total = invoice.subtotal + invoice.tax_amount
            if abs(calculated_total - invoice.total_amount) < 0.01:
                boost += 0.1
        
        # Line items consistency
        if invoice.line_items:
            line_totals = [item.line_total for item in invoice.line_items if item.line_total]
            if line_totals and invoice.subtotal:
                calculated_subtotal = sum(line_totals)
                if abs(calculated_subtotal - invoice.subtotal) < 0.01:
                    boost += 0.05
        
        return min(boost, 0.2)
    
    def _calculate_cross_validation_score(self, field_name: str, parsed_result: Any, 
                                        context: Optional[Dict[str, Any]]) -> float:
        """Calculate cross-validation score for a field."""
        if not context:
            return 0.0
        
        score = 0.0
        
        # Cross-reference with other fields
        if field_name == 'currency' and hasattr(parsed_result, 'currency_code'):
            # Check if currency matches other price fields
            other_currencies = context.get('other_currencies', [])
            if parsed_result.currency_code in other_currencies:
                score += 0.1
        
        # Format consistency
        if field_name == 'date' and hasattr(parsed_result, 'format_detected'):
            if parsed_result.format_detected:
                score += 0.05
        
        return min(score, 0.1)
    
    def _calculate_line_item_cross_validation(self, line_item: NormalizedLineItem, 
                                            context: Optional[Dict[str, Any]]) -> float:
        """Calculate cross-validation score for line items."""
        score = 0.0
        
        # Mathematical consistency
        if line_item.unit_price and line_item.quantity and line_item.line_total:
            calculated = line_item.unit_price * line_item.quantity
            if abs(calculated - line_item.line_total) < 0.01:
                score += 0.1
        
        return min(score, 0.1)
    
    def _calculate_invoice_cross_validation(self, invoice: NormalizedInvoice, 
                                          context: Optional[Dict[str, Any]]) -> float:
        """Calculate cross-validation score for invoices."""
        score = 0.0
        
        # Mathematical consistency
        if invoice.subtotal and invoice.tax_amount and invoice.total_amount:
            calculated = invoice.subtotal + invoice.tax_amount
            if abs(calculated - invoice.total_amount) < 0.01:
                score += 0.1
        
        return min(score, 0.1)


class ConfidenceRouter:
    """Routes fields and items based on confidence scores."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the confidence router with configuration."""
        self.config = config or {}
        self.default_threshold = self.config.get('confidence_threshold', 0.7)
        self.calculator = ConfidenceCalculator(config)
        
    def route_field(self, field_name: str, parsed_result: Any, 
                   context: Optional[Dict[str, Any]] = None) -> RoutingResult:
        """Route a single field based on confidence."""
        try:
            # Calculate confidence metrics
            metrics = self.calculator.calculate_field_confidence(field_name, parsed_result, context)
            
            # Get threshold for this field
            threshold = self._get_field_threshold(field_name)
            
            # Determine routing decision
            if metrics.overall_confidence >= threshold and not self._has_critical_errors(parsed_result):
                decision = RoutingDecision.AUTO_ACCEPT
            else:
                decision = RoutingDecision.NEEDS_REVIEW
            
            # Collect error details
            error_details = []
            if hasattr(parsed_result, 'errors') and parsed_result.errors:
                error_details = [error.message for error in parsed_result.errors]
            
            # Create routing result
            result = RoutingResult(
                field_name=field_name,
                routing_decision=decision,
                confidence_metrics=metrics,
                threshold_used=threshold,
                error_details=error_details,
                source_artifact=f"field_{field_name}"
            )
            
            # Log routing decision
            self._log_routing_decision(result)
            
            return result
            
        except Exception as e:
            LOGGER.error("Error routing field %s: %s", field_name, e)
            return RoutingResult(
                field_name=field_name,
                routing_decision=RoutingDecision.ERROR,
                confidence_metrics=ConfidenceMetrics(),
                threshold_used=self.default_threshold,
                error_details=[f"Routing error: {e}"],
                source_artifact=f"field_{field_name}"
            )
    
    def route_line_item(self, line_item: NormalizedLineItem, 
                       context: Optional[Dict[str, Any]] = None) -> RoutingResult:
        """Route a line item based on confidence."""
        try:
            # Calculate confidence metrics
            metrics = self.calculator.calculate_line_item_confidence(line_item, context)
            
            # Get threshold for line items
            threshold = self._get_field_threshold('line_item')
            
            # Determine routing decision
            if metrics.overall_confidence >= threshold and not self._has_critical_errors(line_item):
                decision = RoutingDecision.AUTO_ACCEPT
            else:
                decision = RoutingDecision.NEEDS_REVIEW
            
            # Collect error details
            error_details = [error.message for error in line_item.errors]
            
            # Create routing result
            result = RoutingResult(
                field_name="line_item",
                routing_decision=decision,
                confidence_metrics=metrics,
                threshold_used=threshold,
                error_details=error_details,
                source_artifact=f"line_item_{id(line_item)}"
            )
            
            # Log routing decision
            self._log_routing_decision(result)
            
            return result
            
        except Exception as e:
            LOGGER.error("Error routing line item: %s", e)
            return RoutingResult(
                field_name="line_item",
                routing_decision=RoutingDecision.ERROR,
                confidence_metrics=ConfidenceMetrics(),
                threshold_used=self.default_threshold,
                error_details=[f"Routing error: {e}"],
                source_artifact="line_item"
            )
    
    def route_invoice(self, normalized_invoice: NormalizedInvoice, 
                     context: Optional[Dict[str, Any]] = None) -> ConfidenceRoutingResult:
        """Route an entire invoice based on confidence."""
        start_time = time.time()
        
        try:
            # Calculate overall confidence
            overall_metrics = self.calculator.calculate_invoice_confidence(normalized_invoice, context)
            
            # Route all fields
            routing_log = []
            auto_accepted_fields = []
            review_candidates = []
            
            # Route main fields
            main_fields = [
                ('supplier_name', normalized_invoice.supplier_name),
                ('invoice_number', normalized_invoice.invoice_number),
                ('invoice_date', normalized_invoice.invoice_date),
                ('currency', normalized_invoice.currency),
                ('subtotal', normalized_invoice.subtotal),
                ('tax_amount', normalized_invoice.tax_amount),
                ('total_amount', normalized_invoice.total_amount)
            ]
            
            for field_name, field_value in main_fields:
                if field_value is not None:
                    # Create a mock parsed result for routing
                    mock_result = self._create_mock_parsed_result(field_name, field_value)
                    routing_result = self.route_field(field_name, mock_result, context)
                    routing_log.append(routing_result)
                    
                    if routing_result.is_auto_acceptable():
                        auto_accepted_fields.append(field_name)
                    else:
                        review_candidates.append(self._create_review_candidate(
                            field_name, field_value, routing_result, context
                        ))
            
            # Route line items
            for i, line_item in enumerate(normalized_invoice.line_items):
                routing_result = self.route_line_item(line_item, context)
                routing_log.append(routing_result)
                
                if routing_result.is_auto_acceptable():
                    auto_accepted_fields.append(f"line_item_{i}")
                else:
                    review_candidates.append(self._create_line_item_review_candidate(
                        line_item, routing_result, context
                    ))
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Count errors and warnings
            error_count = sum(1 for result in routing_log if result.routing_decision == RoutingDecision.ERROR)
            warning_count = sum(1 for result in routing_log if result.routing_decision == RoutingDecision.NEEDS_REVIEW)
            
            # Create final result
            result = ConfidenceRoutingResult(
                invoice_id=context.get('invoice_id', 'unknown') if context else 'unknown',
                overall_confidence=overall_metrics.overall_confidence,
                auto_accepted_fields=auto_accepted_fields,
                review_candidates=review_candidates,
                routing_log=routing_log,
                processing_time=processing_time,
                error_count=error_count,
                warning_count=warning_count
            )
            
            # Log overall result
            self._log_invoice_routing_result(result)
            
            return result
            
        except Exception as e:
            LOGGER.error("Error routing invoice: %s", e)
            return ConfidenceRoutingResult(
                invoice_id=context.get('invoice_id', 'unknown') if context else 'unknown',
                overall_confidence=0.0,
                auto_accepted_fields=[],
                review_candidates=[],
                routing_log=[],
                processing_time=time.time() - start_time,
                error_count=1,
                warning_count=0
            )
    
    def _get_field_threshold(self, field_name: str) -> float:
        """Get confidence threshold for a specific field."""
        field_thresholds = self.config.get('field_thresholds', {})
        return field_thresholds.get(field_name, self.default_threshold)
    
    def _has_critical_errors(self, parsed_result: Any) -> bool:
        """Check if parsed result has critical errors that require review."""
        if not hasattr(parsed_result, 'errors'):
            return False
        
        critical_error_types = [FieldErrorType.PARSE_ERROR, FieldErrorType.INVALID_FORMAT]
        return any(error.error_type in critical_error_types for error in parsed_result.errors)
    
    def _create_mock_parsed_result(self, field_name: str, field_value: Any) -> Any:
        """Create a mock parsed result for routing."""
        class MockParsedResult:
            def __init__(self, value, confidence=0.8):
                self.value = value
                self.confidence = confidence
                self.errors = []
                self.raw_value = str(value) if value is not None else ""
            
            def is_valid(self):
                return self.value is not None and self.confidence >= 0.7
        
        return MockParsedResult(field_value)
    
    def _create_review_candidate(self, field_name: str, field_value: Any, 
                               routing_result: RoutingResult, context: Optional[Dict[str, Any]]) -> ReviewCandidate:
        """Create a review candidate for a field."""
        return ReviewCandidate(
            field_name=field_name,
            field_type=type(field_value).__name__,
            raw_value=str(field_value) if field_value is not None else "",
            normalized_value=field_value,
            confidence_metrics=routing_result.confidence_metrics,
            routing_result=routing_result,
            error_details=routing_result.error_details,
            context=context or {}
        )
    
    def _create_line_item_review_candidate(self, line_item: NormalizedLineItem, 
                                          routing_result: RoutingResult, 
                                          context: Optional[Dict[str, Any]]) -> ReviewCandidate:
        """Create a review candidate for a line item."""
        return ReviewCandidate(
            field_name="line_item",
            field_type="NormalizedLineItem",
            raw_value=str(line_item.raw_data),
            normalized_value=line_item,
            confidence_metrics=routing_result.confidence_metrics,
            routing_result=routing_result,
            error_details=routing_result.error_details,
            context=context or {}
        )
    
    def _log_routing_decision(self, result: RoutingResult):
        """Log a routing decision."""
        LOGGER.info(
            "Field %s routed as %s (confidence: %.3f, threshold: %.3f)",
            result.field_name,
            result.routing_decision.value,
            result.confidence_metrics.overall_confidence,
            result.threshold_used
        )
        
        if result.error_details:
            LOGGER.warning("Field %s has errors: %s", result.field_name, result.error_details)
    
    def _log_invoice_routing_result(self, result: ConfidenceRoutingResult):
        """Log overall invoice routing result."""
        LOGGER.info(
            "Invoice %s routing completed: %d auto-accepted, %d review candidates, "
            "overall confidence: %.3f",
            result.invoice_id,
            len(result.auto_accepted_fields),
            len(result.review_candidates),
            result.overall_confidence
        )
