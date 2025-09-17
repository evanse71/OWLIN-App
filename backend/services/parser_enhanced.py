"""
Enhanced parser with supplier lexicon and robust extraction
"""
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

@dataclass
class ParsedAmount:
    """Represents a parsed monetary amount"""
    value: float
    currency: str
    confidence: float
    raw_text: str

@dataclass
class ParsedSupplier:
    """Represents a parsed supplier name"""
    name: str
    normalized: str
    confidence: float
    aliases: List[str]

class EnhancedParser:
    """Enhanced parser with supplier lexicon and robust extraction"""
    
    def __init__(self):
        self.supplier_lexicon = self._build_supplier_lexicon()
        self.currency_patterns = self._build_currency_patterns()
        self.amount_patterns = self._build_amount_patterns()
    
    def _build_supplier_lexicon(self) -> Dict[str, Dict[str, Any]]:
        """Build supplier lexicon with aliases and normalization rules"""
        return {
            "acme_corp": {
                "primary": "ACME Corporation",
                "aliases": ["ACME Corp", "ACME Ltd", "Acme Corp", "acme"],
                "normalized": "acme corporation"
            },
            "tech_solutions": {
                "primary": "Tech Solutions Ltd",
                "aliases": ["Tech Solutions", "Tech Sol", "TSL", "tech-solutions"],
                "normalized": "tech solutions ltd"
            },
            "global_supplies": {
                "primary": "Global Supplies Inc",
                "aliases": ["Global Supplies", "GSI", "Global Supply", "global-supplies"],
                "normalized": "global supplies inc"
            },
            "metro_services": {
                "primary": "Metro Services PLC",
                "aliases": ["Metro Services", "Metro", "Metro PLC", "metro-services"],
                "normalized": "metro services plc"
            }
        }
    
    def _build_currency_patterns(self) -> List[Tuple[str, str]]:
        """Build currency detection patterns"""
        return [
            (r'£\s*(\d+(?:,\d{3})*(?:\.\d{2})?)', 'GBP'),
            (r'€\s*(\d+(?:,\d{3})*(?:\.\d{2})?)', 'EUR'),
            (r'\$\s*(\d+(?:,\d{3})*(?:\.\d{2})?)', 'USD'),
            (r'(\d+(?:,\d{3})*(?:\.\d{2})?)\s*GBP', 'GBP'),
            (r'(\d+(?:,\d{3})*(?:\.\d{2})?)\s*EUR', 'EUR'),
            (r'(\d+(?:,\d{3})*(?:\.\d{2})?)\s*USD', 'USD'),
            (r'(\d+(?:,\d{3})*(?:\.\d{2})?)\s*£', 'GBP'),
            (r'(\d+(?:,\d{3})*(?:\.\d{2})?)\s*€', 'EUR'),
            (r'(\d+(?:,\d{3})*(?:\.\d{2})?)\s*\$', 'USD'),
        ]
    
    def _build_amount_patterns(self) -> List[str]:
        """Build amount extraction patterns"""
        return [
            r'(\d+(?:,\d{3})*(?:\.\d{2})?)',  # Standard number with optional commas and decimals
            r'(\d+\.\d{2})',  # Decimal with exactly 2 places
            r'(\d+)',  # Integer
        ]
    
    def parse_supplier(self, text: str) -> Optional[ParsedSupplier]:
        """
        Parse supplier name from text using lexicon
        
        Args:
            text: Raw text to parse
            
        Returns:
            ParsedSupplier or None if no match
        """
        if not text:
            return None
        
        text_lower = text.lower().strip()
        
        # Try exact matches first
        for supplier_id, supplier_data in self.supplier_lexicon.items():
            for alias in supplier_data["aliases"]:
                if alias.lower() in text_lower:
                    return ParsedSupplier(
                        name=supplier_data["primary"],
                        normalized=supplier_data["normalized"],
                        confidence=0.9,
                        aliases=supplier_data["aliases"]
                    )
        
        # Try fuzzy matching
        best_match = None
        best_score = 0.0
        
        for supplier_id, supplier_data in self.supplier_lexicon.items():
            score = self._calculate_supplier_similarity(text, supplier_data["normalized"])
            if score > best_score and score > 0.6:
                best_score = score
                best_match = ParsedSupplier(
                    name=supplier_data["primary"],
                    normalized=supplier_data["normalized"],
                    confidence=score,
                    aliases=supplier_data["aliases"]
                )
        
        return best_match
    
    def parse_amounts(self, text: str) -> List[ParsedAmount]:
        """
        Parse monetary amounts from text
        
        Args:
            text: Raw text to parse
            
        Returns:
            List of ParsedAmount objects
        """
        amounts = []
        
        if not text:
            return amounts
        
        # Try currency-specific patterns first
        for pattern, currency in self.currency_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    value_str = match.group(1).replace(',', '')
                    value = float(value_str)
                    
                    amounts.append(ParsedAmount(
                        value=value,
                        currency=currency,
                        confidence=0.9,
                        raw_text=match.group(0)
                    ))
                except ValueError:
                    continue
        
        # If no currency-specific matches, try generic patterns
        if not amounts:
            for pattern in self.amount_patterns:
                matches = re.finditer(pattern, text)
                for match in matches:
                    try:
                        value_str = match.group(1).replace(',', '')
                        value = float(value_str)
                        
                        # Only include reasonable amounts (not page numbers, etc.)
                        if 0.01 <= value <= 1000000:
                            amounts.append(ParsedAmount(
                                value=value,
                                currency='GBP',  # Default currency
                                confidence=0.6,
                                raw_text=match.group(0)
                            ))
                    except ValueError:
                        continue
        
        # Remove duplicates and sort by confidence
        unique_amounts = []
        seen_values = set()
        
        for amount in sorted(amounts, key=lambda x: x.confidence, reverse=True):
            if amount.value not in seen_values:
                unique_amounts.append(amount)
                seen_values.add(amount.value)
        
        return unique_amounts
    
    def extract_total_value(self, text: str) -> Optional[ParsedAmount]:
        """
        Extract the most likely total value from text
        
        Args:
            text: Raw text to parse
            
        Returns:
            ParsedAmount representing the total, or None
        """
        amounts = self.parse_amounts(text)
        
        if not amounts:
            return None
        
        # Look for keywords that indicate total
        total_keywords = ['total', 'amount due', 'net total', 'grand total', 'sum', 'subtotal']
        
        for amount in amounts:
            # Check if amount appears near total keywords
            amount_start = text.lower().find(amount.raw_text.lower())
            if amount_start != -1:
                # Look in surrounding text for total keywords
                context_start = max(0, amount_start - 50)
                context_end = min(len(text), amount_start + len(amount.raw_text) + 50)
                context = text[context_start:context_end].lower()
                
                for keyword in total_keywords:
                    if keyword in context:
                        amount.confidence += 0.2  # Boost confidence
                        break
        
        # Return the amount with highest confidence
        return max(amounts, key=lambda x: x.confidence) if amounts else None
    
    def extract_vat_rate(self, text: str) -> Optional[float]:
        """
        Extract VAT rate from text
        
        Args:
            text: Raw text to parse
            
        Returns:
            VAT rate as float (e.g., 20.0 for 20%), or None
        """
        if not text:
            return None
        
        # Common VAT rate patterns
        vat_patterns = [
            r'VAT\s*@?\s*(\d+(?:\.\d+)?)\s*%',
            r'(\d+(?:\.\d+)?)\s*%\s*VAT',
            r'VAT\s*(\d+(?:\.\d+)?)',
            r'(\d+(?:\.\d+)?)\s*%',
        ]
        
        for pattern in vat_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    rate = float(match.group(1))
                    # Validate reasonable VAT rate
                    if 0 <= rate <= 50:
                        return rate
                except ValueError:
                    continue
        
        return None
    
    def _calculate_supplier_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two supplier names"""
        if not text1 or not text2:
            return 0.0
        
        # Normalize text
        t1 = re.sub(r'[^\w\s]', '', text1.lower()).strip()
        t2 = re.sub(r'[^\w\s]', '', text2.lower()).strip()
        
        if t1 == t2:
            return 1.0
        
        # Simple word overlap
        words1 = set(t1.split())
        words2 = set(t2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    def normalize_supplier_name(self, name: str) -> str:
        """
        Normalize supplier name for consistent matching
        
        Args:
            name: Raw supplier name
            
        Returns:
            Normalized supplier name
        """
        if not name:
            return ""
        
        # Remove common business suffixes
        normalized = name.strip()
        suffixes = ['ltd', 'limited', 'inc', 'corp', 'llc', 'plc', 'co', 'company']
        
        for suffix in suffixes:
            if normalized.lower().endswith(f' {suffix}'):
                normalized = normalized[:-len(f' {suffix}')]
        
        # Remove extra whitespace and special characters
        normalized = re.sub(r'[^\w\s]', ' ', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized.lower()

# Global instance
_parser = None

def get_enhanced_parser() -> EnhancedParser:
    """Get singleton instance of enhanced parser"""
    global _parser
    if _parser is None:
        _parser = EnhancedParser()
    return _parser
