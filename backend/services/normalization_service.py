"""
Normalization Service - Pipeline Integration
Compute canonical quantities and validation flags without breaking response shapes.
"""

import json
from typing import Dict, List, Optional
from normalization.units import canonical_quantities, normalize_line_description
from validators.invoice_math import validate_line_item, validate_invoice_totals


class NormalizationService:
    """Service for normalizing invoice data and computing validation flags."""
    
    def __init__(self):
        pass
    
    def normalise_line(self, raw_line: Dict) -> Dict:
        """
        Normalize a single line item.
        
        Args:
            raw_line: Raw line item data
            
        Returns:
            Line item with canonical quantities and flags
        """
        # Extract basic fields
        description = raw_line.get('description', '')
        quantity = float(raw_line.get('quantity', 0))
        unit_price = float(raw_line.get('unit_price', 0))
        line_total = float(raw_line.get('line_total', 0))
        
        # Parse canonical quantities
        canonical = canonical_quantities(quantity, description)
        
        # Normalize description
        normalized_desc = normalize_line_description(description)
        
        # Validate line item
        validation = validate_line_item(
            unit_price=unit_price,
            quantity=quantity,
            line_total=line_total,
            description=description,
            packs=canonical.get('packs'),
            units_per_pack=canonical.get('units_per_pack'),
            unit_size_ml=canonical.get('unit_size_ml'),
            unit_size_g=canonical.get('unit_size_g')
        )
        
        # Merge results
        result = raw_line.copy()
        result.update(canonical)
        result.update(normalized_desc)
        result['line_flags'] = validation['flags']
        result['validation_valid'] = validation['valid']
        
        return result
    
    def normalise_invoice(self, lines: List[Dict], meta: Dict) -> Dict:
        """
        Normalize an entire invoice.
        
        Args:
            lines: List of line items
            meta: Invoice metadata
            
        Returns:
            Invoice with validation flags
        """
        # Normalize each line
        normalized_lines = []
        line_totals = []
        
        for line in lines:
            normalized_line = self.normalise_line(line)
            normalized_lines.append(normalized_line)
            line_totals.append(float(line.get('line_total', 0)))
        
        # Extract invoice totals
        subtotal = float(meta.get('subtotal', 0))
        vat_amount = float(meta.get('vat_amount', 0))
        vat_rate = meta.get('vat_rate')
        invoice_total = float(meta.get('invoice_total', 0))
        
        # Validate invoice totals
        invoice_validation = validate_invoice_totals(
            subtotal=subtotal,
            vat_amount=vat_amount,
            vat_rate=vat_rate,
            invoice_total=invoice_total,
            line_totals=line_totals
        )
        
        # Collect all flags
        all_flags = invoice_validation['flags'].copy()
        for line in normalized_lines:
            all_flags.extend(line.get('line_flags', []))
        
        # Create invoice result
        result = {
            'lines': normalized_lines,
            'validation_flags': all_flags,
            'validation_valid': invoice_validation['valid'],
            'canonical_quantities': [
                {
                    'line_id': line.get('id'),
                    'uom_key': line.get('uom_key'),
                    'packs': line.get('packs'),
                    'units_per_pack': line.get('units_per_pack'),
                    'quantity_each': line.get('quantity_each'),
                    'quantity_ml': line.get('quantity_ml'),
                    'quantity_g': line.get('quantity_g'),
                    'quantity_l': line.get('quantity_l')
                }
                for line in normalized_lines
            ],
            'parsed_metadata': {
                'total_lines': len(normalized_lines),
                'foc_lines': len([l for l in normalized_lines if l.get('uom_key') == 'foc']),
                'categories': list(set(l.get('category') for l in normalized_lines if l.get('category'))),
                'brands': list(set(l.get('brand') for l in normalized_lines if l.get('brand')))
            }
        }
        
        return result
    
    def persist_normalized_data(self, invoice_id: str, normalized_data: Dict, 
                               db_connection) -> None:
        """
        Persist normalized data to database.
        
        Args:
            invoice_id: Invoice identifier
            normalized_data: Normalized invoice data
            db_connection: Database connection
        """
        # Update invoice with validation flags
        validation_flags = json.dumps(normalized_data['validation_flags'])
        canonical_quantities = json.dumps(normalized_data['canonical_quantities'])
        parsed_metadata = json.dumps(normalized_data['parsed_metadata'])
        
        db_connection.execute("""
            UPDATE invoices 
            SET validation_flags = ?, canonical_quantities = ?, parsed_metadata = ?
            WHERE id = ?
        """, (validation_flags, canonical_quantities, parsed_metadata, invoice_id))
        
        # Update line items with normalized fields
        for line in normalized_data['lines']:
            line_id = line.get('id')
            if not line_id:
                continue
            
            db_connection.execute("""
                UPDATE invoice_items 
                SET uom_key = ?, packs = ?, units_per_pack = ?, quantity_each = ?,
                    unit_size_ml = ?, unit_size_g = ?, unit_size_l = ?,
                    quantity_ml = ?, quantity_g = ?, quantity_l = ?,
                    line_flags = ?, sku = ?, brand = ?, category = ?
                WHERE id = ?
            """, (
                line.get('uom_key'),
                line.get('packs'),
                line.get('units_per_pack'),
                line.get('quantity_each'),
                line.get('unit_size_ml'),
                line.get('unit_size_g'),
                line.get('unit_size_l'),
                line.get('quantity_ml'),
                line.get('quantity_g'),
                line.get('quantity_l'),
                json.dumps(line.get('line_flags', [])),
                line.get('sku'),
                line.get('brand'),
                line.get('category'),
                line_id
            ))


# Global service instance
normalization_service = NormalizationService() 