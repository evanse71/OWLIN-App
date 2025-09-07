"""
Matching Configuration Service

Provides configurable thresholds and parameters for the matching engine.
Reads from environment variables with sensible defaults.
"""

import os
from typing import Dict, Any
from contracts import MatchingConfig

def get_matching_config() -> MatchingConfig:
    """Get current matching configuration from environment or defaults."""
    return MatchingConfig(
        date_window_days=int(os.getenv("DATE_WINDOW_DAYS", "3")),
        amount_proximity_pct=float(os.getenv("AMOUNT_PROXIMITY_PCT", "0.10")),
        qty_tol_rel=float(os.getenv("QTY_TOL_REL", "0.025")),
        qty_tol_abs=float(os.getenv("QTY_TOL_ABS", "0.25")),
        price_tol_rel=float(os.getenv("PRICE_TOL_REL", "0.05")),
        fuzzy_desc_threshold=float(os.getenv("FUZZY_DESC_THRESHOLD", "0.90"))
    )

def get_uom_map() -> Dict[str, list]:
    """Get unit of measure mapping for normalization."""
    return {
        'kg': ['kg', 'kilo', 'kilogram'],
        'l': ['l', 'litre', 'liter'],
        'each': ['ea', 'unit', 'pcs', 'piece'],
        'case': ['case', 'cs'],
        'box': ['box', 'bx'],
        'pack': ['pack', 'pk'],
        'bottle': ['bottle', 'btl'],
        'can': ['can', 'tin'],
        'bag': ['bag', 'sack']
    }

def get_conversions() -> Dict[str, Dict[str, float]]:
    """Get unit conversion factors."""
    return {
        'case': {'each': 24.0},
        'box': {'each': 12.0},
        'pack': {'each': 6.0},
        'kg': {'g': 1000.0},
        'l': {'ml': 1000.0}
    }

def normalize_uom(uom: str) -> str:
    """Normalize unit of measure to canonical form."""
    if not uom:
        return 'each'
    
    uom_lower = uom.lower().strip()
    uom_map = get_uom_map()
    
    for canonical, variants in uom_map.items():
        if uom_lower in variants or uom_lower == canonical:
            return canonical
    
    return uom_lower

def convert_quantity(qty: float, from_uom: str, to_uom: str) -> float:
    """Convert quantity between units if conversion is known."""
    if from_uom == to_uom:
        return qty
    
    conversions = get_conversions()
    
    # Direct conversion
    if from_uom in conversions and to_uom in conversions[from_uom]:
        return qty * conversions[from_uom][to_uom]
    
    # Reverse conversion
    if to_uom in conversions and from_uom in conversions[to_uom]:
        return qty / conversions[to_uom][from_uom]
    
    # No conversion available
    return qty 