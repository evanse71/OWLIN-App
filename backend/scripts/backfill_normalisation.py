#!/usr/bin/env python3
"""
Backfill Normalisation Script
Walk all invoices, normalise lines, persist canonical fields/flags.
"""

import sys
import os
import json
from typing import List, Dict

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db_manager_unified import get_db_manager
from services.normalization_service import normalization_service


def get_all_invoices(db_connection) -> List[Dict]:
    """Get all invoices with their line items."""
    invoices = []
    
    # Get all invoices with correct column names
    invoice_rows = db_connection.execute("""
        SELECT id, supplier_name, invoice_date, subtotal_pennies, vat_total_pennies, vat_rate, total_amount_pennies
        FROM invoices
        ORDER BY created_at DESC
    """).fetchall()
    
    for invoice_row in invoice_rows:
        invoice_id = invoice_row['id']
        
        # Get line items for this invoice with correct column names
        line_rows = db_connection.execute("""
            SELECT id, description, quantity, unit_price_pennies, line_total_pennies
            FROM invoice_line_items
            WHERE invoice_id = ?
        """, (invoice_id,)).fetchall()
        
        # Convert to standard format
        lines = []
        for line_row in line_rows:
            lines.append({
                'id': line_row['id'],
                'description': line_row['description'],
                'quantity': float(line_row['quantity']),
                'unit_price': float(line_row['unit_price_pennies']) / 100,  # Convert from pennies
                'line_total': float(line_row['line_total_pennies']) / 100   # Convert from pennies
            })
        
        # Create invoice metadata with correct column names
        meta = {
            'subtotal': float(invoice_row['subtotal_pennies'] or 0) / 100,  # Convert from pennies
            'vat_amount': float(invoice_row['vat_total_pennies'] or 0) / 100,  # Convert from pennies
            'vat_rate': invoice_row['vat_rate'],
            'invoice_total': float(invoice_row['total_amount_pennies']) / 100  # Convert from pennies
        }
        
        invoices.append({
            'id': invoice_id,
            'lines': lines,
            'meta': meta
        })
    
    return invoices


def backfill_invoice(invoice_data: Dict, db_connection) -> Dict:
    """Backfill a single invoice."""
    invoice_id = invoice_data['id']
    lines = invoice_data['lines']
    meta = invoice_data['meta']
    
    print(f"Processing invoice {invoice_id} with {len(lines)} lines...")
    
    try:
        # Normalize the invoice
        normalized_data = normalization_service.normalise_invoice(lines, meta)
        
        # Persist the normalized data
        normalization_service.persist_normalized_data(invoice_id, normalized_data, db_connection)
        
        # Count flags
        total_flags = len(normalized_data['validation_flags'])
        invalid_lines = len([l for l in normalized_data['lines'] if not l.get('validation_valid', True)])
        
        print(f"  ✓ Normalized {len(lines)} lines, {total_flags} flags, {invalid_lines} invalid lines")
        
        return {
            'invoice_id': invoice_id,
            'lines_processed': len(lines),
            'flags_found': total_flags,
            'invalid_lines': invalid_lines,
            'success': True
        }
        
    except Exception as e:
        print(f"  ✗ Error processing invoice {invoice_id}: {e}")
        return {
            'invoice_id': invoice_id,
            'error': str(e),
            'success': False
        }


def main():
    """Main backfill function."""
    print("Starting normalisation backfill...")
    
    # Get database connection
    db_manager = get_db_manager()
    
    with db_manager.get_connection() as conn:
        # Get all invoices
        print("Fetching invoices...")
        invoices = get_all_invoices(conn)
        print(f"Found {len(invoices)} invoices to process")
        
        # Process each invoice
        results = []
        for i, invoice_data in enumerate(invoices, 1):
            print(f"\n[{i}/{len(invoices)}] ", end="")
            result = backfill_invoice(invoice_data, conn)
            results.append(result)
        
        # Summary
        successful = len([r for r in results if r['success']])
        failed = len([r for r in results if not r['success']])
        total_lines = sum(r.get('lines_processed', 0) for r in results if r['success'])
        total_flags = sum(r.get('flags_found', 0) for r in results if r['success'])
        
        print(f"\n{'='*50}")
        print(f"Backfill complete!")
        print(f"  Invoices processed: {successful}")
        print(f"  Invoices failed: {failed}")
        print(f"  Total lines processed: {total_lines}")
        print(f"  Total flags found: {total_flags}")
        print(f"{'='*50}")
        
        if failed > 0:
            print("\nFailed invoices:")
            for result in results:
                if not result['success']:
                    print(f"  - {result['invoice_id']}: {result['error']}")
        
        return successful == len(invoices)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 