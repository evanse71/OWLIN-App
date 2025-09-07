# backend/normalization/units.py
from __future__ import annotations
from typing import Optional, Tuple, TypedDict, cast, Dict, Any, List
import re
from config_core import (
    VOLUME_SYNONYMS, WEIGHT_SYNONYMS, DOZEN_ALIASES, KEG_LITRES, ML_PER_L
)

# ---- Strong types -----------------------------------------------------------

class SizeParse(TypedDict):
    unit_size_ml: Optional[float]
    unit_size_g: Optional[float]
    unit_size_l: Optional[float]

class CanonicalQuantities(TypedDict, total=False):
    # totals & descriptors
    packs: Optional[float]
    units_per_pack: Optional[float]
    quantity_each: float
    quantity_ml: Optional[float]
    quantity_g: Optional[float]
    quantity_l: Optional[float]
    # echo back size fields so callers don't look in two places
    unit_size_ml: Optional[float]
    unit_size_g: Optional[float]
    unit_size_l: Optional[float]

# ---- Regexes ----------------------------------------------------------------

SIZE_RE = re.compile(r'(?P<count>\d+(?:[.,]\d+)?)\s*[x×]\s*(?P<size>\d+(?:[.,]\d+)?)\s*(?P<u>ml|cl|l|g|kg)\b', re.I)
SIMPLE_SIZE_RE = re.compile(r'(?P<size>\d+(?:[.,]\d+)?)\s*(?P<u>ml|cl|l|g|kg)\b', re.I)
PACK_PAIR_RE = re.compile(r'\b(\d+(?:[.,]\d+)?)\s*[x×]\s*(\d+(?:[.,]\d+)?)\b', re.I)
DOZEN_RE = re.compile(r'\bdozen\b', re.I)
KEG_RE = re.compile(r'\b(?P<kind>keg|cask|pin)\b', re.I)

def _num(x: str) -> float:
    return float(x.replace(',', '.'))

# ---- Parsers ----------------------------------------------------------------

def parse_pack_descriptor(text: str) -> Tuple[Optional[float], Optional[float]]:
    t = text.lower()
    m = PACK_PAIR_RE.search(t)
    if m:
        return _num(m.group(2)), _num(m.group(1))  # units_per_pack, packs
    if DOZEN_RE.search(t):
        m2 = re.search(r'(\d+)\s+dozen', t)
        packs = float(m2.group(1)) if m2 else 1.0
        return float(DOZEN_ALIASES["dozen"]), packs
    m3 = re.search(r'\b(?:case|pack|crate|tray)\s*(?:of)?\s*(\d+)\b', t)
    if m3:
        return float(_num(m3.group(1))), 1.0
    return None, None

def parse_size(text: str) -> SizeParse:
    t = text.lower()
    keg = KEG_RE.search(t)
    if keg:
        litres = KEG_LITRES.get(keg.group('kind'))
        return {
            "unit_size_ml": float(litres * ML_PER_L) if litres else None,
            "unit_size_g": None,
            "unit_size_l": float(litres) if litres else None,
        }
    m = SIZE_RE.search(t) or SIMPLE_SIZE_RE.search(t)
    if not m:
        return {"unit_size_ml": None, "unit_size_g": None, "unit_size_l": None}
    size = _num(m.group('size'))
    u = m.group('u').lower()
    if u in ('ml', 'cl', 'l'):
        ml = size * VOLUME_SYNONYMS[u]
        return {"unit_size_ml": float(ml), "unit_size_l": float(ml / ML_PER_L), "unit_size_g": None}
    g = size * WEIGHT_SYNONYMS[u]
    return {"unit_size_ml": None, "unit_size_g": float(g), "unit_size_l": None}

def canonical_quantities(base_qty: float, description: str) -> Dict[str, Any]:
    """
    Parse quantity description into canonical format.
    
    Args:
        base_qty: Base quantity (e.g., number of cases)
        description: Description string (e.g., "24×275ml", "C6", "11g")
    
    Returns:
        Dict with canonical quantities and flags
    """
    if not description:
        return {
            'quantity_each': base_qty,
            'packs': 1.0,
            'units_per_pack': base_qty,
            'quantity_ml': None,
            'quantity_l': None,
            'quantity_g': None,
            'flags': []
        }
    
    description = description.strip()
    flags = []
    
    # Initialize result
    result = {
        'quantity_each': base_qty,
        'packs': 1.0,
        'units_per_pack': base_qty,
        'quantity_ml': None,
        'quantity_l': None,
        'quantity_g': None,
        'unit_size_ml': None,
        'unit_size_l': None,
        'unit_size_g': None,
        'flags': flags
    }
    
    # Case notation (C6, C12, C24)
    case_match = re.match(r'^C(\d+)$', description, re.IGNORECASE)
    if case_match:
        case_size = int(case_match.group(1))
        result['quantity_each'] = base_qty * case_size
        result['units_per_pack'] = case_size
        return result
    
    # Check for special units first (before simple unit patterns)
    special_patterns = [
        # Gallon notation (11g = 11 gallon = 50L keg) - use exact value from config
        (r'(\d+)g', lambda m: {'quantity_l': 50.0, 'quantity_ml': 50000}),
        # Cask (standard 72 pints = 40.9L)
        (r'cask', lambda m: {'quantity_l': 40.9, 'quantity_ml': 40900}),
        # Pin (standard 36 pints = 20.5L)
        (r'pin', lambda m: {'quantity_l': 20.45, 'quantity_ml': 20450}),
        # Dozen
        (r'dozen', lambda m: {'quantity_each': base_qty * 12, 'units_per_pack': 12}),
    ]
    
    # Check for special units first
    for pattern, converter in special_patterns:
        match = re.search(pattern, description, re.IGNORECASE)
        if match:
            special_result = converter(match)
            result.update(special_result)
            return result
    
    # Pack notation (24×275ml, 12x1L, etc.)
    pack_patterns = [
        # Unicode × and regular x
        r'(\d+)[×x](\d+(?:\.\d+)?)(ml|cl|l|g|kg)',
        # Case notation with size
        r'(\d+)[×x](\d+(?:\.\d+)?)(ml|cl|l|g|kg)\s*([A-Z]+)?',
        # Comma decimal (European format)
        r'(\d+)[×x](\d+(?:,\d+)?)(ml|cl|l|g|kg)',
        # Complex: 2×(12×330ml)
        r'(\d+)[×x]\((\d+)[×x](\d+(?:\.\d+)?)(ml|cl|l|g|kg)',
    ]
    
    # Check for partial pack notation (24× without size) - must be more specific
    partial_pack_pattern = r'^(\d+)[×x]\s*\(?([^mlclgkg\d])*\)?$'
    partial_match = re.search(partial_pack_pattern, description, re.IGNORECASE)
    if partial_match:
        mult = int(partial_match.group(1))
        result['quantity_each'] = base_qty * mult
        result['units_per_pack'] = mult
        result['packs'] = 1.0
        flags.append('SIZE_AMBIGUOUS')
        result['flags'] = flags
        return result
    
    # Simple unit notation (70cl, 1L, etc.)
    simple_unit_pattern = r'^(\d+(?:[.,]\d+)?)(ml|cl|l|g|kg)$'
    simple_match = re.search(simple_unit_pattern, description, re.IGNORECASE)
    if simple_match:
        size = float(simple_match.group(1).replace(',', '.'))
        unit = simple_match.group(2).lower()
        
        # Convert to canonical units
        if unit == 'ml':
            result['quantity_ml'] = round(base_qty * size, 2)
            result['quantity_l'] = round(result['quantity_ml'] / 1000.0, 2)
            result['unit_size_ml'] = size
            result['unit_size_l'] = round(size / 1000.0, 2)
        elif unit == 'cl':
            result['quantity_ml'] = round(base_qty * size * 10, 2)
            result['quantity_l'] = round(result['quantity_ml'] / 1000.0, 2)
            result['unit_size_ml'] = size * 10
            result['unit_size_l'] = round(size / 100.0, 2)
        elif unit == 'l':
            result['quantity_l'] = round(base_qty * size, 2)
            result['quantity_ml'] = round(result['quantity_l'] * 1000.0, 2)
            result['unit_size_l'] = size
            result['unit_size_ml'] = size * 1000.0
        elif unit == 'g':
            result['quantity_g'] = round(base_qty * size, 2)
            result['unit_size_g'] = size
        elif unit == 'kg':
            result['quantity_g'] = round(base_qty * size * 1000.0, 2)
            result['unit_size_g'] = size * 1000.0
        
        return result
    
    # Handle "330 ML" pattern (with space)
    space_unit_pattern = r'^(\d+(?:[.,]\d+)?)\s+(ml|cl|l|g|kg)$'
    space_match = re.search(space_unit_pattern, description, re.IGNORECASE)
    if space_match:
        size = float(space_match.group(1).replace(',', '.'))
        unit = space_match.group(2).lower()
        
        # Convert to canonical units (same logic as above)
        if unit == 'ml':
            result['quantity_ml'] = round(base_qty * size, 2)
            result['quantity_l'] = round(result['quantity_ml'] / 1000.0, 2)
            result['unit_size_ml'] = size
            result['unit_size_l'] = round(size / 1000.0, 2)
        elif unit == 'cl':
            result['quantity_ml'] = round(base_qty * size * 10, 2)
            result['quantity_l'] = round(result['quantity_ml'] / 1000.0, 2)
            result['unit_size_ml'] = size * 10
            result['unit_size_l'] = round(size / 100.0, 2)
        elif unit == 'l':
            result['quantity_l'] = round(base_qty * size, 2)
            result['quantity_ml'] = round(result['quantity_l'] * 1000.0, 2)
            result['unit_size_l'] = size
            result['unit_size_ml'] = size * 1000.0
        elif unit == 'g':
            result['quantity_g'] = round(base_qty * size, 2)
            result['unit_size_g'] = size
        elif unit == 'kg':
            result['quantity_g'] = round(base_qty * size * 1000.0, 2)
            result['unit_size_g'] = size * 1000.0
        
        return result
    
    for pattern in pack_patterns:
        match = re.search(pattern, description, re.IGNORECASE)
        if match:
            if len(match.groups()) == 4:  # Complex pattern
                outer_mult = int(match.group(1))
                inner_mult = int(match.group(2))
                size = float(match.group(3).replace(',', '.'))
                unit = match.group(4).lower()
                
                total_mult = outer_mult * inner_mult
                result['quantity_each'] = base_qty * total_mult
                result['packs'] = outer_mult
                result['units_per_pack'] = inner_mult
            else:  # Simple pattern
                mult = int(match.group(1))
                size = float(match.group(2).replace(',', '.'))
                unit = match.group(3).lower()
                
                result['quantity_each'] = base_qty * mult
                result['packs'] = base_qty  # Number of cases/packs
                result['units_per_pack'] = mult  # Number of units in each pack
            
            # Convert to canonical units
            if unit == 'ml':
                result['quantity_ml'] = round(result['quantity_each'] * size, 2)
                result['quantity_l'] = round(result['quantity_ml'] / 1000.0, 2)
                result['unit_size_ml'] = size
                result['unit_size_l'] = round(size / 1000.0, 2)
            elif unit == 'cl':
                result['quantity_ml'] = round(result['quantity_each'] * size * 10, 2)
                result['quantity_l'] = round(result['quantity_ml'] / 1000.0, 2)
                result['unit_size_ml'] = size * 10
                result['unit_size_l'] = round(size / 100.0, 2)
            elif unit == 'l':
                result['quantity_l'] = round(result['quantity_each'] * size, 2)
                result['quantity_ml'] = round(result['quantity_l'] * 1000.0, 2)
                result['unit_size_l'] = size
                result['unit_size_ml'] = size * 1000.0
            elif unit == 'g':
                result['quantity_g'] = round(result['quantity_each'] * size, 2)
                result['unit_size_g'] = size
            elif unit == 'kg':
                result['quantity_g'] = round(result['quantity_each'] * size * 1000.0, 2)
                result['unit_size_g'] = size * 1000.0
            
            return result
    
    # Check for keg/cask/pin with size (50L Keg, etc.)
    keg_size_pattern = r'(\d+(?:[.,]\d+)?)(ml|cl|l|g|kg)\s+(keg|cask|pin)'
    keg_match = re.search(keg_size_pattern, description, re.IGNORECASE)
    if keg_match:
        size = float(keg_match.group(1).replace(',', '.'))
        unit = keg_match.group(2).lower()
        keg_type = keg_match.group(3).lower()
        
        # Convert to litres
        if unit == 'ml':
            litres = size / 1000.0
        elif unit == 'cl':
            litres = size / 100.0
        elif unit == 'l':
            litres = size
        elif unit == 'g':
            litres = size * 4.546 / 1000.0  # Convert gallons to litres
        else:
            litres = size
        
        result['quantity_l'] = litres
        result['quantity_ml'] = litres * 1000.0
        result['unit_size_l'] = litres
        result['unit_size_ml'] = litres * 1000.0
        return result
    
    # Check for generic keg/cask/pin (without size)
    generic_patterns = [
        (r'\bkeg\b', lambda m: {'quantity_l': 50.0, 'quantity_ml': 50000, 'unit_size_l': 50.0}),
        (r'\bcask\b', lambda m: {'quantity_l': 40.9, 'quantity_ml': 40900, 'unit_size_l': 40.9}),
        (r'\bpin\b', lambda m: {'quantity_l': 20.45, 'quantity_ml': 20450, 'unit_size_l': 20.45}),
    ]
    
    for pattern, converter in generic_patterns:
        match = re.search(pattern, description, re.IGNORECASE)
        if match:
            generic_result = converter(match)
            result.update(generic_result)
            return result
    
    # Check for "Pack of X" and "Case of X" patterns
    pack_case_patterns = [
        (r'pack\s+of\s+(\d+)', lambda m: {'quantity_each': base_qty * int(m.group(1)), 'units_per_pack': int(m.group(1))}),
        (r'case\s+of\s+(\d+)', lambda m: {'quantity_each': base_qty * int(m.group(1)), 'units_per_pack': int(m.group(1))}),
    ]
    
    for pattern, converter in pack_case_patterns:
        match = re.search(pattern, description, re.IGNORECASE)
        if match:
            pack_result = converter(match)
            result.update(pack_result)
            return result
    
    # FOC detection
    if re.search(r'\bFOC\b', description, re.IGNORECASE):
        flags.append('FOC_LINE')
    
    # Pack mismatch detection
    if 'packs' in description.lower() and result['packs'] == 1.0:
        flags.append('PACK_MISMATCH')
    
    # Size ambiguity detection
    if not any([result['quantity_ml'], result['quantity_l'], result['quantity_g']]):
        flags.append('SIZE_AMBIGUOUS')
    
    result['flags'] = flags
    return result 