"""
Verdict System

Enforces exclusive verdict assignment with deterministic priority hierarchy.
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class Verdict(Enum):
    """Exclusive verdict types with priority order"""
    # Highest priority first
    PRICE_INCOHERENT = "price_incoherent"
    VAT_MISMATCH = "vat_mismatch"
    PACK_MISMATCH = "pack_mismatch"
    OCR_LOW_CONF = "ocr_low_conf"
    OFF_CONTRACT_DISCOUNT = "off_contract_discount"
    OK_ON_CONTRACT = "ok_on_contract"

# Priority map (lower number = higher priority)
VERDICT_PRIORITY = {
    Verdict.PRICE_INCOHERENT: 1,
    Verdict.VAT_MISMATCH: 2,
    Verdict.PACK_MISMATCH: 3,
    Verdict.OCR_LOW_CONF: 4,
    Verdict.OFF_CONTRACT_DISCOUNT: 5,
    Verdict.OK_ON_CONTRACT: 6
}

@dataclass
class VerdictContext:
    """Context for verdict assignment"""
    price_incoherent: bool = False
    vat_mismatch: bool = False
    pack_mismatch: bool = False
    ocr_low_conf: bool = False
    off_contract_discount: bool = False
    discount_value: Optional[float] = None
    discount_kind: Optional[str] = None
    residual_pennies: int = 0

class VerdictEngine:
    """Deterministic verdict assignment engine"""
    
    def __init__(self):
        self.engine_version = "1.0"
    
    def assign_verdict(self, context: VerdictContext) -> Verdict:
        """
        Assign exactly one verdict based on context.
        
        Args:
            context: VerdictContext with all flags and data
            
        Returns:
            Single verdict with highest priority
        """
        try:
            # Collect all applicable verdicts
            applicable_verdicts = []
            
            if context.price_incoherent:
                applicable_verdicts.append(Verdict.PRICE_INCOHERENT)
            
            if context.vat_mismatch:
                applicable_verdicts.append(Verdict.VAT_MISMATCH)
            
            if context.pack_mismatch:
                applicable_verdicts.append(Verdict.PACK_MISMATCH)
            
            if context.ocr_low_conf:
                applicable_verdicts.append(Verdict.OCR_LOW_CONF)
            
            if context.off_contract_discount:
                applicable_verdicts.append(Verdict.OFF_CONTRACT_DISCOUNT)
            
            # If no issues found, assign OK_ON_CONTRACT
            if not applicable_verdicts:
                return Verdict.OK_ON_CONTRACT
            
            # Select verdict with highest priority (lowest number)
            selected_verdict = min(applicable_verdicts, 
                                 key=lambda v: VERDICT_PRIORITY[v])
            
            logger.debug(f"Assigned verdict: {selected_verdict.value} "
                        f"(from {len(applicable_verdicts)} candidates)")
            
            return selected_verdict
            
        except Exception as e:
            logger.error(f"❌ Verdict assignment failed: {e}")
            # Fallback to OK_ON_CONTRACT
            return Verdict.OK_ON_CONTRACT
    
    def create_context_from_flags(self, flags: Dict[str, Any], 
                                 discount_data: Optional[Dict[str, Any]] = None) -> VerdictContext:
        """Create VerdictContext from flags and discount data"""
        context = VerdictContext()
        
        # Set flags
        context.price_incoherent = flags.get('PRICE_INCOHERENT', False)
        context.vat_mismatch = flags.get('VAT_MISMATCH', False)
        context.pack_mismatch = flags.get('PACK_MISMATCH', False)
        context.ocr_low_conf = flags.get('OCR_LOW_CONF', False)
        
        # Set discount data
        if discount_data:
            context.off_contract_discount = discount_data.get('is_off_contract', False)
            context.discount_value = discount_data.get('value')
            context.discount_kind = discount_data.get('kind')
            context.residual_pennies = discount_data.get('residual_pennies', 0)
        
        return context
    
    def get_verdict_description(self, verdict: Verdict) -> str:
        """Get human-readable description of verdict"""
        descriptions = {
            Verdict.PRICE_INCOHERENT: "Price calculation mismatch detected",
            Verdict.VAT_MISMATCH: "VAT calculation error",
            Verdict.PACK_MISMATCH: "Pack quantity mismatch",
            Verdict.OCR_LOW_CONF: "Low OCR confidence",
            Verdict.OFF_CONTRACT_DISCOUNT: "Off-contract discount applied",
            Verdict.OK_ON_CONTRACT: "Line item OK on contract"
        }
        return descriptions.get(verdict, "Unknown verdict")
    
    def get_verdict_severity(self, verdict: Verdict) -> str:
        """Get severity level of verdict"""
        severity_map = {
            Verdict.PRICE_INCOHERENT: "critical",
            Verdict.VAT_MISMATCH: "critical",
            Verdict.PACK_MISMATCH: "warning",
            Verdict.OCR_LOW_CONF: "warning",
            Verdict.OFF_CONTRACT_DISCOUNT: "info",
            Verdict.OK_ON_CONTRACT: "info"
        }
        return severity_map.get(verdict, "unknown")

# Global verdict engine instance
_verdict_engine: Optional[VerdictEngine] = None

def get_verdict_engine() -> VerdictEngine:
    """Get global verdict engine instance"""
    global _verdict_engine
    if _verdict_engine is None:
        _verdict_engine = VerdictEngine()
    return _verdict_engine 