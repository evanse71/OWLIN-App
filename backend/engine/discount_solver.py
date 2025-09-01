"""
Discount Solver Engine

Evaluates different discount hypotheses and selects the best fit.
"""

import math
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from backend.config_units import ML_PER_L

logger = logging.getLogger(__name__)

@dataclass
class DiscountHypothesis:
    kind: str  # 'percent', 'per_case', 'per_litre'
    value: float
    residual_pennies: int
    confidence: float

@dataclass
class DiscountResult:
    kind: str
    value: float
    residual_pennies: int
    confidence: float
    hypothesis: DiscountHypothesis

class DiscountSolver:
    """Solves for the most likely discount type and value"""
    
    def __init__(self):
        # Tolerance for accepting a hypothesis (in pennies)
        self.RESIDUAL_TOL = 50  # 50p tolerance
        # Minimum confidence threshold
        self.MIN_CONFIDENCE = 0.8
    
    def solve_discount(self, qty: float, unit_price: float, nett_value: float,
                      canonical_quantities: Optional[Dict[str, Any]] = None) -> Optional[DiscountResult]:
        """
        Solve for the most likely discount type and value.
        
        Args:
            qty: Raw quantity
            unit_price: Unit price in pounds
            nett_value: Net value in pounds
            canonical_quantities: Parsed quantities from units.py
            
        Returns:
            DiscountResult or None if no good fit found
        """
        try:
            # Calculate expected value without discount
            expected_value = qty * unit_price
            
            # If values are very close, no discount
            if abs(expected_value - nett_value) < 0.01:
                return None
            
            # Generate hypotheses
            hypotheses = self._generate_hypotheses(qty, unit_price, nett_value, canonical_quantities)
            
            if not hypotheses:
                return None
            
            # Select best hypothesis
            best_hypothesis = self._select_best_hypothesis(hypotheses)
            
            if best_hypothesis.confidence < self.MIN_CONFIDENCE:
                return None
            
            return DiscountResult(
                kind=best_hypothesis.kind,
                value=best_hypothesis.value,
                residual_pennies=best_hypothesis.residual_pennies,
                confidence=best_hypothesis.confidence,
                hypothesis=best_hypothesis
            )
            
        except Exception as e:
            logger.error(f"❌ Discount solver failed: {e}")
            return None
    
    def _generate_hypotheses(self, qty: float, unit_price: float, nett_value: float,
                           canonical_quantities: Optional[Dict[str, Any]]) -> List[DiscountHypothesis]:
        """Generate discount hypotheses"""
        hypotheses = []
        
        # Hypothesis 1: Percent discount
        percent_hypothesis = self._solve_percent_discount(qty, unit_price, nett_value)
        if percent_hypothesis:
            hypotheses.append(percent_hypothesis)
        
        # Hypothesis 2: Per-case discount
        per_case_hypothesis = self._solve_per_case_discount(qty, unit_price, nett_value, canonical_quantities)
        if per_case_hypothesis:
            hypotheses.append(per_case_hypothesis)
        
        # Hypothesis 3: Per-litre discount
        per_litre_hypothesis = self._solve_per_litre_discount(qty, unit_price, nett_value, canonical_quantities)
        if per_litre_hypothesis:
            hypotheses.append(per_litre_hypothesis)
        
        return hypotheses
    
    def _solve_percent_discount(self, qty: float, unit_price: float, nett_value: float) -> Optional[DiscountHypothesis]:
        """Solve for percent discount"""
        try:
            expected_value = qty * unit_price
            
            if expected_value <= 0 or nett_value <= 0:
                return None
            
            # Calculate percent discount
            discount_percent = ((expected_value - nett_value) / expected_value) * 100
            
            # Validate reasonable range (0-80%)
            if discount_percent < 0 or discount_percent > 80:
                return None
            
            # Calculate residual
            implied_value = expected_value * (1 - discount_percent / 100)
            residual_pennies = abs(implied_value - nett_value) * 100
            
            # Calculate confidence (inverse of residual)
            confidence = max(0, 1 - (residual_pennies / 100))
            
            return DiscountHypothesis(
                kind="percent",
                value=discount_percent,
                residual_pennies=int(residual_pennies),
                confidence=confidence
            )
            
        except Exception as e:
            logger.error(f"❌ Percent discount solve failed: {e}")
            return None
    
    def _solve_per_case_discount(self, qty: float, unit_price: float, nett_value: float,
                                canonical_quantities: Optional[Dict[str, Any]]) -> Optional[DiscountHypothesis]:
        """Solve for per-case discount"""
        try:
            expected_value = qty * unit_price
            
            # Get pack information
            packs = canonical_quantities.get('packs', 1.0) if canonical_quantities else 1.0
            
            if packs <= 0:
                return None
            
            # Calculate per-case discount
            total_discount = expected_value - nett_value
            per_case_discount = total_discount / packs
            
            # Validate reasonable range (£0-£50 per case)
            if per_case_discount < 0 or per_case_discount > 50:
                return None
            
            # Calculate residual
            implied_value = expected_value - (packs * per_case_discount)
            residual_pennies = abs(implied_value - nett_value) * 100
            
            # Calculate confidence
            confidence = max(0, 1 - (residual_pennies / 100))
            
            return DiscountHypothesis(
                kind="per_case",
                value=per_case_discount,
                residual_pennies=int(residual_pennies),
                confidence=confidence
            )
            
        except Exception as e:
            logger.error(f"❌ Per-case discount solve failed: {e}")
            return None
    
    def _solve_per_litre_discount(self, qty: float, unit_price: float, nett_value: float,
                                 canonical_quantities: Optional[Dict[str, Any]]) -> Optional[DiscountHypothesis]:
        """Solve for per-litre discount"""
        try:
            expected_value = qty * unit_price
            
            # Get quantity in litres
            quantity_l = canonical_quantities.get('quantity_l', 0) if canonical_quantities else 0
            
            if quantity_l <= 0:
                return None
            
            # Calculate per-litre discount
            total_discount = expected_value - nett_value
            per_litre_discount = total_discount / quantity_l
            
            # Validate reasonable range (£0-£10 per litre)
            if per_litre_discount < 0 or per_litre_discount > 10:
                return None
            
            # Calculate residual
            implied_value = expected_value - (quantity_l * per_litre_discount)
            residual_pennies = abs(implied_value - nett_value) * 100
            
            # Calculate confidence
            confidence = max(0, 1 - (residual_pennies / 100))
            
            return DiscountHypothesis(
                kind="per_litre",
                value=per_litre_discount,
                residual_pennies=int(residual_pennies),
                confidence=confidence
            )
            
        except Exception as e:
            logger.error(f"❌ Per-litre discount solve failed: {e}")
            return None
    
    def _select_best_hypothesis(self, hypotheses: List[DiscountHypothesis]) -> DiscountHypothesis:
        """Select the best hypothesis based on residual and confidence"""
        if not hypotheses:
            raise ValueError("No hypotheses provided")
        
        # Sort by residual (ascending) and confidence (descending)
        sorted_hypotheses = sorted(hypotheses, 
                                 key=lambda h: (h.residual_pennies, -h.confidence))
        
        return sorted_hypotheses[0]

# Global solver instance
_discount_solver: Optional[DiscountSolver] = None

def get_discount_solver() -> DiscountSolver:
    """Get global discount solver instance"""
    global _discount_solver
    if _discount_solver is None:
        _discount_solver = DiscountSolver()
    return _discount_solver 