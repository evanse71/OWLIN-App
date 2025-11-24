"""
Template Integration

Integrates supplier templates into the post-processing pipeline.
Handles template matching and override application.
"""

from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional

from .loader import get_template_loader
from .matcher import get_template_matcher
from .override import get_template_override

LOGGER = logging.getLogger("owlin.templates.integration")


class TemplateIntegration:
    """Integrates supplier templates into the post-processing pipeline."""
    
    def __init__(self, fuzzy_threshold: float = 0.8):
        """Initialize template integration."""
        self.fuzzy_threshold = fuzzy_threshold
        self.loader = get_template_loader()
        self.matcher = get_template_matcher(fuzzy_threshold)
        self.override = get_template_override()
    
    def apply_template_overrides(self, invoice_card: Dict[str, Any], 
                               header_text: str = "", 
                               raw_line_texts: List[str] = None) -> Dict[str, Any]:
        """
        Apply supplier template overrides to invoice card.
        
        Args:
            invoice_card: Current invoice card data
            header_text: Raw header text from invoice
            raw_line_texts: List of raw line item texts
            
        Returns:
            Updated invoice card with template overrides applied
        """
        if not invoice_card:
            LOGGER.warning("No invoice card provided for template processing")
            return invoice_card
        
        # Get supplier guess from invoice card
        supplier_guess = invoice_card.get('supplier_name') or invoice_card.get('supplier')
        if not supplier_guess:
            LOGGER.info("No supplier name found in invoice card, skipping template processing")
            return invoice_card
        
        # Load all templates
        templates = self.loader.load_all_templates()
        if not templates:
            LOGGER.info("No templates available for processing")
            return invoice_card
        
        # Match template
        matched_template = self.matcher.match_template(
            supplier_guess=supplier_guess,
            header_text=header_text or "",
            vat_id=invoice_card.get('vat_id', ''),
            templates=templates
        )
        
        if not matched_template:
            LOGGER.info(f"No template match found for supplier: {supplier_guess}")
            return invoice_card
        
        # Apply overrides
        updated_card = self.override.apply_overrides(
            invoice_card=invoice_card,
            template=matched_template,
            header_text=header_text or "",
            raw_line_texts=raw_line_texts or []
        )
        
        # Log template application
        if 'template_overrides' in updated_card:
            template_name = matched_template.get('name', 'Unknown')
            fields_applied = updated_card['template_overrides']['fields_applied']
            LOGGER.info(f"Applied template '{template_name}': {fields_applied}")
            
            # Add audit record
            self._add_audit_record(template_name, fields_applied, updated_card)
        
        return updated_card
    
    def _add_audit_record(self, template_name: str, fields_applied: List[str], 
                         invoice_card: Dict[str, Any]) -> None:
        """Add audit record for template application."""
        try:
            # This would integrate with the existing audit system
            # For now, just log the application
            audit_data = {
                'template_name': template_name,
                'fields_applied': fields_applied,
                'supplier': invoice_card.get('supplier_name', 'Unknown'),
                'invoice_id': invoice_card.get('invoice_id', 'Unknown')
            }
            LOGGER.info(f"Template audit: {audit_data}")
        except Exception as e:
            LOGGER.warning(f"Failed to add template audit record: {e}")
    
    def get_template_stats(self) -> Dict[str, Any]:
        """Get template system statistics."""
        try:
            loader_stats = self.loader.get_template_stats()
            return {
                'templates_loaded': loader_stats['total_templates'],
                'template_names': loader_stats['template_names'],
                'suppliers': loader_stats['suppliers'],
                'fuzzy_threshold': self.fuzzy_threshold
            }
        except Exception as e:
            LOGGER.error(f"Failed to get template stats: {e}")
            return {'error': str(e)}


# Global template integration instance
_template_integration: Optional[TemplateIntegration] = None


def get_template_integration(fuzzy_threshold: float = 0.8) -> TemplateIntegration:
    """Get global template integration instance."""
    global _template_integration
    if _template_integration is None:
        _template_integration = TemplateIntegration(fuzzy_threshold)
    return _template_integration


def apply_template_overrides(invoice_card: Dict[str, Any], 
                           header_text: str = "", 
                           raw_line_texts: List[str] = None) -> Dict[str, Any]:
    """Apply template overrides using global integration."""
    integration = get_template_integration()
    return integration.apply_template_overrides(invoice_card, header_text, raw_line_texts)
