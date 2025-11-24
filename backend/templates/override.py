"""
Template Override Engine

Applies supplier template overrides to invoice cards.
Only fills missing fields, never overwrites existing values.
"""

from __future__ import annotations
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

LOGGER = logging.getLogger("owlin.templates.override")


class TemplateOverride:
    """Applies template overrides to invoice cards."""
    
    def __init__(self):
        """Initialize template override engine."""
        pass
    
    def apply_overrides(self, invoice_card: Dict[str, Any], template: Dict[str, Any], 
                       header_text: str = "", raw_line_texts: List[str] = None) -> Dict[str, Any]:
        """
        Apply template overrides to invoice card.
        
        Args:
            invoice_card: Current invoice card data
            template: Matched template data
            header_text: Raw header text from invoice
            raw_line_texts: List of raw line item texts
            
        Returns:
            Updated invoice card with overrides applied
        """
        if not template:
            LOGGER.warning("No template provided for overrides")
            return invoice_card
        
        if not invoice_card:
            LOGGER.warning("No invoice card provided for overrides")
            return invoice_card
        
        # Create copy to avoid modifying original
        updated_card = invoice_card.copy()
        overrides_applied = []
        
        # Apply field overrides
        field_overrides = template.get('field_overrides', {})
        
        # Override total amount
        if 'total' in field_overrides and not updated_card.get('total_amount'):
            total_value = self._extract_total(field_overrides['total'], header_text)
            if total_value is not None:
                updated_card['total_amount'] = total_value
                overrides_applied.append('total_amount')
                LOGGER.debug(f"Applied total override: {total_value}")
        
        # Override VAT total
        if 'vat_total' in field_overrides and not updated_card.get('vat_total'):
            vat_value = self._extract_vat_total(field_overrides['vat_total'], header_text)
            if vat_value is not None:
                updated_card['vat_total'] = vat_value
                overrides_applied.append('vat_total')
                LOGGER.debug(f"Applied VAT total override: {vat_value}")
        
        # Override date
        if 'date' in field_overrides and not updated_card.get('date'):
            date_value = self._extract_date(field_overrides['date'], header_text)
            if date_value is not None:
                updated_card['date'] = date_value
                overrides_applied.append('date')
                LOGGER.debug(f"Applied date override: {date_value}")
        
        # Override line items
        if 'line_items' in field_overrides and raw_line_texts:
            line_items_updated = self._apply_line_item_overrides(
                updated_card.get('line_items', []), 
                field_overrides['line_items'], 
                raw_line_texts
            )
            if line_items_updated:
                updated_card['line_items'] = line_items_updated
                overrides_applied.append('line_items')
                LOGGER.debug(f"Applied line items overrides: {len(line_items_updated)} items")
        
        # Add override metadata
        if overrides_applied:
            updated_card['template_overrides'] = {
                'template_name': template.get('name', 'Unknown'),
                'template_version': template.get('version', '1.0'),
                'fields_applied': overrides_applied,
                'applied_at': self._get_current_timestamp()
            }
            LOGGER.info(f"Applied {len(overrides_applied)} template overrides: {overrides_applied}")
        
        return updated_card
    
    def _extract_total(self, total_config: Dict[str, Any], header_text: str) -> Optional[float]:
        """Extract total amount using template patterns."""
        patterns = total_config.get('patterns', [])
        currency_symbols = total_config.get('currency_symbols', ['£', 'GBP'])
        
        if not patterns or not header_text:
            return None
        
        for pattern in patterns:
            try:
                matches = re.findall(pattern, header_text, re.IGNORECASE)
                if matches:
                    # Take the first match
                    value_str = matches[0]
                    # Remove currency symbols and commas
                    for symbol in currency_symbols:
                        value_str = value_str.replace(symbol, '')
                    value_str = value_str.replace(',', '')
                    
                    try:
                        return float(value_str)
                    except ValueError:
                        continue
            except re.error:
                LOGGER.warning(f"Invalid regex pattern: {pattern}")
                continue
        
        return None
    
    def _extract_vat_total(self, vat_config: Dict[str, Any], header_text: str) -> Optional[float]:
        """Extract VAT total using template patterns."""
        patterns = vat_config.get('patterns', [])
        currency_symbols = vat_config.get('currency_symbols', ['£', 'GBP'])
        
        if not patterns or not header_text:
            return None
        
        for pattern in patterns:
            try:
                matches = re.findall(pattern, header_text, re.IGNORECASE)
                if matches:
                    # Take the first match
                    value_str = matches[0]
                    # Remove currency symbols and commas
                    for symbol in currency_symbols:
                        value_str = value_str.replace(symbol, '')
                    value_str = value_str.replace(',', '')
                    
                    try:
                        return float(value_str)
                    except ValueError:
                        continue
            except re.error:
                LOGGER.warning(f"Invalid regex pattern: {pattern}")
                continue
        
        return None
    
    def _extract_date(self, date_config: Dict[str, Any], header_text: str) -> Optional[str]:
        """Extract date using template patterns."""
        patterns = date_config.get('patterns', [])
        date_format = date_config.get('format', 'DD/MM/YYYY')
        
        if not patterns or not header_text:
            return None
        
        for pattern in patterns:
            try:
                matches = re.findall(pattern, header_text, re.IGNORECASE)
                if matches:
                    # Take the first match
                    date_str = matches[0]
                    # Validate date format
                    if self._validate_date_format(date_str, date_format):
                        return date_str
            except re.error:
                LOGGER.warning(f"Invalid regex pattern: {pattern}")
                continue
        
        return None
    
    def _apply_line_item_overrides(self, line_items: List[Dict[str, Any]], 
                                 line_config: Dict[str, Any], 
                                 raw_line_texts: List[str]) -> List[Dict[str, Any]]:
        """Apply line item overrides."""
        if not line_items or not raw_line_texts:
            return line_items
        
        updated_items = []
        
        for i, item in enumerate(line_items):
            updated_item = item.copy()
            
            # Apply quantity override
            if not updated_item.get('quantity') and i < len(raw_line_texts):
                quantity = self._extract_quantity(line_config, raw_line_texts[i])
                if quantity is not None:
                    updated_item['quantity'] = quantity
            
            # Apply unit price override
            if not updated_item.get('unit_price') and i < len(raw_line_texts):
                unit_price = self._extract_unit_price(line_config, raw_line_texts[i])
                if unit_price is not None:
                    updated_item['unit_price'] = unit_price
            
            # Apply line total override
            if not updated_item.get('line_total') and i < len(raw_line_texts):
                line_total = self._extract_line_total(line_config, raw_line_texts[i])
                if line_total is not None:
                    updated_item['line_total'] = line_total
            
            updated_items.append(updated_item)
        
        return updated_items
    
    def _extract_quantity(self, line_config: Dict[str, Any], line_text: str) -> Optional[float]:
        """Extract quantity from line text."""
        patterns = line_config.get('quantity_patterns', [])
        
        for pattern in patterns:
            try:
                matches = re.findall(pattern, line_text, re.IGNORECASE)
                if matches:
                    try:
                        return float(matches[0])
                    except ValueError:
                        continue
            except re.error:
                LOGGER.warning(f"Invalid regex pattern: {pattern}")
                continue
        
        return None
    
    def _extract_unit_price(self, line_config: Dict[str, Any], line_text: str) -> Optional[float]:
        """Extract unit price from line text."""
        patterns = line_config.get('unit_price_patterns', [])
        
        for pattern in patterns:
            try:
                matches = re.findall(pattern, line_text, re.IGNORECASE)
                if matches:
                    # Remove currency symbols
                    value_str = matches[0]
                    value_str = value_str.replace('£', '').replace(',', '')
                    try:
                        return float(value_str)
                    except ValueError:
                        continue
            except re.error:
                LOGGER.warning(f"Invalid regex pattern: {pattern}")
                continue
        
        return None
    
    def _extract_line_total(self, line_config: Dict[str, Any], line_text: str) -> Optional[float]:
        """Extract line total from line text."""
        patterns = line_config.get('total_patterns', [])
        
        for pattern in patterns:
            try:
                matches = re.findall(pattern, line_text, re.IGNORECASE)
                if matches:
                    # Remove currency symbols
                    value_str = matches[0]
                    value_str = value_str.replace('£', '').replace(',', '')
                    try:
                        return float(value_str)
                    except ValueError:
                        continue
            except re.error:
                LOGGER.warning(f"Invalid regex pattern: {pattern}")
                continue
        
        return None
    
    def _validate_date_format(self, date_str: str, date_format: str) -> bool:
        """Validate date format."""
        # Simple validation for DD/MM/YYYY format
        if date_format == "DD/MM/YYYY":
            pattern = r'^\d{1,2}/\d{1,2}/\d{4}$'
            return bool(re.match(pattern, date_str))
        
        # Add more format validations as needed
        return True
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp string."""
        from datetime import datetime
        return datetime.now().isoformat()


# Global template override instance
_template_override: Optional[TemplateOverride] = None


def get_template_override() -> TemplateOverride:
    """Get global template override instance."""
    global _template_override
    if _template_override is None:
        _template_override = TemplateOverride()
    return _template_override


def apply_overrides(invoice_card: Dict[str, Any], template: Dict[str, Any], 
                   header_text: str = "", raw_line_texts: List[str] = None) -> Dict[str, Any]:
    """Apply template overrides using global override engine."""
    override_engine = get_template_override()
    return override_engine.apply_overrides(invoice_card, template, header_text, raw_line_texts)
