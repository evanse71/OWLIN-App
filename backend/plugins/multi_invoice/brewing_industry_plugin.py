"""
Brewing Industry Multi-Invoice Detection Plugin

This plugin provides specialized detection logic for brewing industry invoices,
including specific supplier patterns, invoice formats, and industry-specific rules.
"""

import re
from typing import Dict, Any, List
from . import MultiInvoicePlugin

class BrewingIndustryPlugin(MultiInvoicePlugin):
    """Plugin for brewing industry multi-invoice detection"""
    
    def __init__(self):
        super().__init__("brewing_industry", "1.0.0")
        self.brewing_suppliers = [
            "WILD HORSE BREWING CO LTD",
            "RED DRAGON DISPENSE LIMITED",
            "SNOWDONIA HOSPITALITY",
            "BREWERY SUPPLIES LTD",
            "DISPENSE SOLUTIONS LIMITED",
            "BREWING EQUIPMENT CO",
            "FERMENTATION SUPPLIES",
            "HOP MERCHANTS LTD",
            "MALT SUPPLIERS",
            "YEAST CULTURES CO"
        ]
        
        self.brewing_keywords = [
            "brewing", "brewery", "fermentation", "hops", "malt", "yeast",
            "dispense", "keg", "cask", "barrel", "pint", "ale", "lager",
            "stout", "porter", "ipa", "bitter", "mild", "wheat beer"
        ]
        
        self.invoice_patterns = [
            r'\b(?:BREW|BRW|DISP|KEG)[0-9\-_/]{3,15}\b',
            r'\b(?:INV|BILL)[0-9\-_/]{3,15}\b',
            r'\b(?:FERR|HOP|MALT)[0-9\-_/]{3,15}\b'
        ]
    
    def detect(self, text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Detect brewing industry multi-invoice content"""
        result = {
            "is_brewing_industry": False,
            "suppliers_detected": [],
            "invoice_numbers": [],
            "brewing_keywords": [],
            "confidence": 0.0
        }
        
        text_upper = text.upper()
        
        # Check for brewing suppliers
        detected_suppliers = []
        for supplier in self.brewing_suppliers:
            if supplier.upper() in text_upper:
                detected_suppliers.append(supplier)
        
        result["suppliers_detected"] = detected_suppliers
        
        # Check for brewing keywords
        detected_keywords = []
        for keyword in self.brewing_keywords:
            if keyword.lower() in text.lower():
                detected_keywords.append(keyword)
        
        result["brewing_keywords"] = detected_keywords
        
        # Check for brewing-specific invoice patterns
        detected_invoices = []
        for pattern in self.invoice_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            detected_invoices.extend(matches)
        
        result["invoice_numbers"] = detected_invoices
        
        # Determine if this is brewing industry
        result["is_brewing_industry"] = (
            len(detected_suppliers) > 0 or 
            len(detected_keywords) > 2 or 
            len(detected_invoices) > 0
        )
        
        return result
    
    def get_confidence(self, text: str, context: Dict[str, Any]) -> float:
        """Get confidence score for brewing industry detection"""
        result = self.detect(text, context)
        confidence = 0.0
        
        # Supplier confidence
        if len(result["suppliers_detected"]) > 0:
            confidence += 0.4
        
        # Keyword confidence
        keyword_count = len(result["brewing_keywords"])
        if keyword_count > 5:
            confidence += 0.3
        elif keyword_count > 2:
            confidence += 0.2
        elif keyword_count > 0:
            confidence += 0.1
        
        # Invoice pattern confidence
        if len(result["invoice_numbers"]) > 0:
            confidence += 0.2
        
        # Context confidence
        if context.get("document_type") == "invoice":
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def validate(self, text: str) -> bool:
        """Validate if this plugin can process the text"""
        # Check if text contains any brewing-related content
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in self.brewing_keywords) or \
               any(supplier.lower() in text_lower for supplier in self.brewing_suppliers) 