"""
Template Matcher

Provides fuzzy matching between invoice data and supplier templates.
Uses supplier names, header tokens, and VAT IDs for matching.
"""

from __future__ import annotations
import logging
import re
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple

LOGGER = logging.getLogger("owlin.templates.matcher")


class TemplateMatcher:
    """Fuzzy matching between invoice data and supplier templates."""
    
    def __init__(self, fuzzy_threshold: float = 0.8):
        """Initialize template matcher with fuzzy threshold."""
        self.fuzzy_threshold = fuzzy_threshold
    
    def match_template(self, supplier_guess: str, header_text: str = "", 
                      vat_id: str = "", templates: Dict[str, Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Match a template based on supplier guess, header text, and VAT ID.
        
        Args:
            supplier_guess: Supplier name from invoice processing
            header_text: Raw header text from invoice
            vat_id: VAT registration number (if available)
            templates: Dictionary of available templates
            
        Returns:
            Best matching template or None if no match found
        """
        if not templates:
            LOGGER.warning("No templates provided for matching")
            return None
        
        if not supplier_guess:
            LOGGER.warning("No supplier guess provided for matching")
            return None
        
        best_match = None
        best_score = 0.0
        
        for template_name, template_data in templates.items():
            score = self._calculate_match_score(
                supplier_guess, header_text, vat_id, template_data
            )
            
            if score > best_score and score >= self.fuzzy_threshold:
                best_score = score
                best_match = template_data
                LOGGER.debug(f"Template {template_name} scored {score:.3f}")
        
        if best_match:
            LOGGER.info(f"Matched template: {best_match.get('name', 'Unknown')} (score: {best_score:.3f})")
        else:
            LOGGER.info(f"No template match found for supplier: {supplier_guess}")
        
        return best_match
    
    def _calculate_match_score(self, supplier_guess: str, header_text: str, 
                             vat_id: str, template_data: Dict[str, Any]) -> float:
        """Calculate match score for a template."""
        scores = []
        
        # Supplier name matching
        supplier_score = self._match_supplier_name(supplier_guess, template_data)
        if supplier_score > 0:
            scores.append(supplier_score)
        
        # Header token matching
        if header_text:
            header_score = self._match_header_tokens(header_text, template_data)
            if header_score > 0:
                scores.append(header_score)
        
        # VAT ID matching
        if vat_id:
            vat_score = self._match_vat_id(vat_id, template_data)
            if vat_score > 0:
                scores.append(vat_score)
        
        if not scores:
            return 0.0
        
        # Return weighted average (supplier name gets higher weight)
        if len(scores) == 1:
            return scores[0]
        elif len(scores) == 2:
            return (scores[0] * 0.7 + scores[1] * 0.3)
        else:
            return (scores[0] * 0.5 + scores[1] * 0.3 + scores[2] * 0.2)
    
    def _match_supplier_name(self, supplier_guess: str, template_data: Dict[str, Any]) -> float:
        """Match supplier name against template."""
        supplier_info = template_data.get('supplier', {})
        supplier_name = supplier_info.get('name', '')
        aliases = supplier_info.get('aliases', [])
        
        # Normalize supplier guess
        supplier_guess_norm = self._normalize_text(supplier_guess)
        
        # Check exact match with primary name
        if supplier_name:
            supplier_name_norm = self._normalize_text(supplier_name)
            if supplier_guess_norm == supplier_name_norm:
                return 1.0
        
        # Check fuzzy match with primary name
        if supplier_name:
            similarity = self._calculate_similarity(supplier_guess_norm, self._normalize_text(supplier_name))
            if similarity > 0.8:
                return similarity
        
        # Check aliases
        best_alias_score = 0.0
        for alias in aliases:
            alias_norm = self._normalize_text(alias)
            if supplier_guess_norm == alias_norm:
                return 1.0
            
            similarity = self._calculate_similarity(supplier_guess_norm, alias_norm)
            if similarity > best_alias_score:
                best_alias_score = similarity
        
        return best_alias_score
    
    def _match_header_tokens(self, header_text: str, template_data: Dict[str, Any]) -> float:
        """Match header text against template tokens."""
        supplier_info = template_data.get('supplier', {})
        header_tokens = supplier_info.get('header_tokens', [])
        
        if not header_tokens:
            return 0.0
        
        header_text_norm = self._normalize_text(header_text)
        matches = 0
        
        for token in header_tokens:
            token_norm = self._normalize_text(token)
            if token_norm in header_text_norm:
                matches += 1
        
        return matches / len(header_tokens) if header_tokens else 0.0
    
    def _match_vat_id(self, vat_id: str, template_data: Dict[str, Any]) -> float:
        """Match VAT ID against template VAT IDs."""
        supplier_info = template_data.get('supplier', {})
        template_vat_ids = supplier_info.get('vat_ids', [])
        
        if not template_vat_ids:
            return 0.0
        
        vat_id_norm = self._normalize_text(vat_id)
        
        for template_vat_id in template_vat_ids:
            template_vat_id_norm = self._normalize_text(template_vat_id)
            if vat_id_norm == template_vat_id_norm:
                return 1.0
        
        return 0.0
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        if not text:
            return ""
        
        # Convert to lowercase and strip whitespace
        normalized = text.lower().strip()
        
        # Remove common punctuation
        normalized = re.sub(r'[^\w\s]', '', normalized)
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized)
        
        return normalized
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts using SequenceMatcher."""
        if not text1 or not text2:
            return 0.0
        
        return SequenceMatcher(None, text1, text2).ratio()


# Global template matcher instance
_template_matcher: Optional[TemplateMatcher] = None


def get_template_matcher(fuzzy_threshold: float = 0.8) -> TemplateMatcher:
    """Get global template matcher instance."""
    global _template_matcher
    if _template_matcher is None:
        _template_matcher = TemplateMatcher(fuzzy_threshold)
    return _template_matcher


def match_template(supplier_guess: str, header_text: str = "", 
                  vat_id: str = "", templates: Dict[str, Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """Match a template using global matcher."""
    matcher = get_template_matcher()
    return matcher.match_template(supplier_guess, header_text, vat_id, templates)
