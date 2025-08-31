"""
Discount Hypothesis Solver - Choose the Model That Actually Fits
Evaluate four hypotheses per line and pick the best fit.
"""

import math
from typing import Dict, List, Optional, Tuple
from config_units import CATEGORY_TOL, NEW_SKU_TOL_BONUS


class DiscountHypothesis:
    """Represents a discount hypothesis with fit metrics."""
    
    def __init__(self, hypothesis_type: str, implied_discount: float, 
                 expected_value: float, actual_value: float, complexity_penalty: float = 0.0):
        self.hypothesis_type = hypothesis_type
        self.implied_discount = implied_discount
        self.expected_value = expected_value
        self.actual_value = actual_value
        self.complexity_penalty = complexity_penalty
        self.residual = abs(expected_value - actual_value)
        self.total_cost = self.residual + complexity_penalty
    
    def __str__(self):
        return f"{self.hypothesis_type}: discount={self.implied_discount:.2%}, residual={self.residual:.2f}, cost={self.total_cost:.2f}"


def solve_percent_discount(expected_price: float, actual_price: float, 
                          quantity: float) -> Optional[DiscountHypothesis]:
    """Solve for percentage discount hypothesis."""
    if expected_price <= 0 or actual_price < 0:
        return None
    
    # Calculate implied discount percentage
    if expected_price == actual_price:
        implied_discount = 0.0
    else:
        implied_discount = (expected_price - actual_price) / expected_price
    
    # Clamp to reasonable range (-100% to +100%)
    implied_discount = max(-1.0, min(1.0, implied_discount))
    
    expected_value = expected_price * quantity
    actual_value = actual_price * quantity
    
    return DiscountHypothesis(
        hypothesis_type="percent",
        implied_discount=implied_discount,
        expected_value=expected_value,
        actual_value=actual_value,
        complexity_penalty=0.0  # Simple hypothesis
    )


def solve_fixed_per_case_discount(expected_price: float, actual_price: float,
                                 quantity: float, packs: Optional[float] = None) -> Optional[DiscountHypothesis]:
    """Solve for fixed allowance per case hypothesis."""
    if expected_price <= 0 or actual_price < 0:
        return None
    
    # Use packs if available, otherwise assume 1
    effective_packs = packs if packs is not None else 1.0
    if effective_packs <= 0:
        return None
    
    # Calculate implied discount per case
    total_discount = (expected_price - actual_price) * quantity
    implied_discount_per_case = total_discount / effective_packs
    
    expected_value = expected_price * quantity
    actual_value = actual_price * quantity
    
    return DiscountHypothesis(
        hypothesis_type="per_case",
        implied_discount=implied_discount_per_case,
        expected_value=expected_value,
        actual_value=actual_value,
        complexity_penalty=0.1  # Slightly more complex
    )


def solve_fixed_per_litre_discount(expected_price: float, actual_price: float,
                                  quantity: float, quantity_l: Optional[float] = None) -> Optional[DiscountHypothesis]:
    """Solve for fixed allowance per litre hypothesis."""
    if expected_price <= 0 or actual_price < 0:
        return None
    
    # Use quantity_l if available, otherwise skip
    if quantity_l is None or quantity_l <= 0:
        return None
    
    # Calculate implied discount per litre
    total_discount = (expected_price - actual_price) * quantity
    implied_discount_per_litre = total_discount / quantity_l
    
    expected_value = expected_price * quantity
    actual_value = actual_price * quantity
    
    return DiscountHypothesis(
        hypothesis_type="per_litre",
        implied_discount=implied_discount_per_litre,
        expected_value=expected_value,
        actual_value=actual_value,
        complexity_penalty=0.2  # More complex
    )


def solve_promo_bundle_discount(expected_price: float, actual_price: float,
                               quantity: float, line_items: List[Dict]) -> Optional[DiscountHypothesis]:
    """Solve for promo/bundle hypothesis (only if multiple lines show FOC/free)."""
    if expected_price <= 0 or actual_price < 0:
        return None
    
    # Check if this looks like a bundle (multiple lines with FOC/free)
    foc_lines = [item for item in line_items if item.get('line_total', 0) == 0]
    if len(foc_lines) < 2:
        return None
    
    # Calculate implied bundle discount
    total_expected = sum(item.get('expected_price', 0) * item.get('quantity', 0) for item in line_items)
    total_actual = sum(item.get('line_total', 0) for item in line_items)
    
    if total_expected <= 0:
        return None
    
    implied_discount = (total_expected - total_actual) / total_expected
    
    expected_value = expected_price * quantity
    actual_value = actual_price * quantity
    
    return DiscountHypothesis(
        hypothesis_type="bundle",
        implied_discount=implied_discount,
        expected_value=expected_value,
        actual_value=actual_value,
        complexity_penalty=0.5  # Most complex
    )


def evaluate_discount_hypotheses(expected_price: float, actual_price: float,
                                quantity: float, category: str = "default",
                                is_new_sku: bool = False, packs: Optional[float] = None,
                                quantity_l: Optional[float] = None,
                                line_items: List[Dict] = None) -> Tuple[str, Optional[DiscountHypothesis]]:
    """
    Evaluate all discount hypotheses and pick the best fit.
    
    Returns:
        (verdict, best_hypothesis)
    """
    if line_items is None:
        line_items = []
    
    # Calculate tolerance for this category
    base_tolerance = CATEGORY_TOL.get(category, CATEGORY_TOL["default"])
    if is_new_sku:
        tolerance = base_tolerance + NEW_SKU_TOL_BONUS
    else:
        tolerance = base_tolerance
    
    # Generate all hypotheses
    hypotheses = []
    
    # H1: Percent discount
    h1 = solve_percent_discount(expected_price, actual_price, quantity)
    if h1:
        hypotheses.append(h1)
    
    # H2: Fixed per case
    h2 = solve_fixed_per_case_discount(expected_price, actual_price, quantity, packs)
    if h2:
        hypotheses.append(h2)
    
    # H3: Fixed per litre
    h3 = solve_fixed_per_litre_discount(expected_price, actual_price, quantity, quantity_l)
    if h3:
        hypotheses.append(h3)
    
    # H4: Promo/bundle (only if multiple FOC lines)
    h4 = solve_promo_bundle_discount(expected_price, actual_price, quantity, line_items)
    if h4:
        hypotheses.append(h4)
    
    if not hypotheses:
        return "pricing_anomaly_unmodelled", None
    
    # Pick the hypothesis with minimum total cost
    best_hypothesis = min(hypotheses, key=lambda h: h.total_cost)
    
    # Check if the best hypothesis fits within tolerance
    # For large discounts (>30%), accept them as valid
    if best_hypothesis.hypothesis_type == "percent" and abs(best_hypothesis.implied_discount) > 0.30:
        return "off_contract_discount", best_hypothesis.hypothesis_type
    elif best_hypothesis.residual <= tolerance:
        return "ok_on_contract", best_hypothesis.hypothesis_type
    else:
        return "pricing_anomaly_unmodelled", best_hypothesis.hypothesis_type


def calculate_line_residual(expected_price: float, actual_price: float, 
                           quantity: float) -> float:
    """Calculate residual for a line item."""
    expected_value = expected_price * quantity
    actual_value = actual_price * quantity
    return abs(expected_value - actual_value)


def detect_uom_mismatch(expected_price: float, actual_price: float,
                       quantity: float, packs: Optional[float] = None,
                       units_per_pack: Optional[float] = None) -> bool:
    """
    Detect potential UOM mismatch by checking if pack sizes explain price difference.
    """
    if packs is None or units_per_pack is None:
        return False
    
    # If packs and units_per_pack are available, check for UOM confusion
    if packs > 0 and units_per_pack > 0:
        # Check if the price difference could be explained by pack size confusion
        # e.g., case price vs unit price
        pack_ratio = packs / units_per_pack
        if pack_ratio != 1.0:
            # Calculate what the price would be if UOM was confused
            confused_price = actual_price * pack_ratio
            price_diff_ratio = abs(confused_price - expected_price) / expected_price
            
            # If the confused price is much closer to expected, flag as UOM mismatch
            if price_diff_ratio < 0.1:  # Within 10%
                return True
    
    return False 