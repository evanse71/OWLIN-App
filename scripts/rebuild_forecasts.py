#!/usr/bin/env python3
"""
Rebuild Forecasts Script

This script rebuilds all item-level price forecasts in the system.
It can be run headlessly for batch processing and maintenance.

Usage:
    python scripts/rebuild_forecasts.py [--all] [--item-id ITEM_ID] [--supplier-id SUPPLIER_ID] [--force]

Options:
    --all           Rebuild all forecasts (default)
    --item-id       Rebuild forecasts for specific item ID
    --supplier-id   Rebuild forecasts for specific supplier
    --force         Force rebuild even if recent forecasts exist
    --dry-run       Show what would be rebuilt without actually doing it
    --verbose       Show detailed progress information
"""

import argparse
import sys
import os
import time
from datetime import datetime, timedelta
from typing import List, Optional

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from services.forecast_service import ForecastService
from db.connection import get_conn
from contracts import ForecastSeries


def get_items_to_rebuild(
    item_id: Optional[int] = None,
    supplier_id: Optional[int] = None,
    force: bool = False
) -> List[dict]:
    """Get list of items that need forecast rebuilding."""
    conn = get_conn()
    cursor = conn.cursor()
    
    # Base query
    query = """
        SELECT DISTINCT 
            i.id as item_id,
            i.name as item_name,
            i.supplier_id,
            s.name as supplier_name,
            COUNT(ili.id) as invoice_count,
            MIN(ili.unit_price) as min_price,
            MAX(ili.unit_price) as max_price,
            AVG(ili.unit_price) as avg_price,
            MAX(f.created_at) as last_forecast
        FROM invoice_line_items ili
        JOIN items i ON ili.item_id = i.id
        JOIN suppliers s ON i.supplier_id = s.id
        LEFT JOIN forecasts f ON i.id = f.item_id
        WHERE ili.unit_price > 0
    """
    
    params = []
    
    if item_id:
        query += " AND i.id = ?"
        params.append(item_id)
    
    if supplier_id:
        query += " AND i.supplier_id = ?"
        params.append(supplier_id)
    
    query += """
        GROUP BY i.id, i.name, i.supplier_id, s.name
        HAVING COUNT(ili.id) >= 6  -- Minimum 6 data points
        ORDER BY i.name
    """
    
    cursor.execute(query, params)
    items = []
    
    for row in cursor.fetchall():
        item = {
            'item_id': row[0],
            'item_name': row[1],
            'supplier_id': row[2],
            'supplier_name': row[3],
            'invoice_count': row[4],
            'min_price': row[5],
            'max_price': row[6],
            'avg_price': row[7],
            'last_forecast': row[8]
        }
        
        # Check if rebuild is needed
        needs_rebuild = True
        if not force and item['last_forecast']:
            last_forecast_date = datetime.fromisoformat(item['last_forecast'].replace('Z', '+00:00'))
            if datetime.now(last_forecast_date.tzinfo) - last_forecast_date < timedelta(days=7):
                needs_rebuild = False
        
        item['needs_rebuild'] = needs_rebuild
        items.append(item)
    
    conn.close()
    return items


def rebuild_forecasts(
    items: List[dict],
    dry_run: bool = False,
    verbose: bool = False
) -> dict:
    """Rebuild forecasts for the given items."""
    forecast_service = ForecastService()
    results = {
        'total': len(items),
        'success': 0,
        'failed': 0,
        'skipped': 0,
        'errors': []
    }
    
    start_time = time.time()
    
    for i, item in enumerate(items, 1):
        if verbose:
            print(f"[{i}/{len(items)}] Processing {item['item_name']} (ID: {item['item_id']})")
        
        if not item['needs_rebuild']:
            if verbose:
                print(f"  Skipping - recent forecast exists")
            results['skipped'] += 1
            continue
        
        try:
            if not dry_run:
                # Generate forecasts for different horizons
                for horizon in [1, 3, 12]:
                    forecast = forecast_service.generate_forecast(item['item_id'], horizon)
                    if verbose:
                        print(f"  Generated {horizon}-month forecast")
                
                # Update quality metrics
                quality = forecast_service.update_quality_metrics(item['item_id'])
                if verbose:
                    print(f"  Updated quality metrics")
            
            results['success'] += 1
            
        except Exception as e:
            error_msg = f"Failed to rebuild forecast for item {item['item_id']}: {str(e)}"
            results['errors'].append(error_msg)
            results['failed'] += 1
            
            if verbose:
                print(f"  ERROR: {error_msg}")
        
        # Progress indicator
        if i % 10 == 0 and verbose:
            elapsed = time.time() - start_time
            rate = i / elapsed
            remaining = (len(items) - i) / rate if rate > 0 else 0
            print(f"  Progress: {i}/{len(items)} ({i/len(items)*100:.1f}%) - ETA: {remaining/60:.1f}min")
    
    return results


def main():
    parser = argparse.ArgumentParser(description='Rebuild item-level price forecasts')
    parser.add_argument('--all', action='store_true', help='Rebuild all forecasts (default)')
    parser.add_argument('--item-id', type=int, help='Rebuild forecasts for specific item ID')
    parser.add_argument('--supplier-id', type=int, help='Rebuild forecasts for specific supplier')
    parser.add_argument('--force', action='store_true', help='Force rebuild even if recent forecasts exist')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be rebuilt without actually doing it')
    parser.add_argument('--verbose', action='store_true', help='Show detailed progress information')
    
    args = parser.parse_args()
    
    print("=== Forecast Rebuild Script ===")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Get items to rebuild
    print("Scanning for items that need forecast rebuilding...")
    items = get_items_to_rebuild(
        item_id=args.item_id,
        supplier_id=args.supplier_id,
        force=args.force
    )
    
    if not items:
        print("No items found that need forecast rebuilding.")
        return
    
    print(f"Found {len(items)} items to process")
    
    if args.dry_run:
        print("\n=== DRY RUN - No changes will be made ===")
        for item in items:
            status = "REBUILD" if item['needs_rebuild'] else "SKIP"
            print(f"[{status}] {item['item_name']} (ID: {item['item_id']}) - {item['supplier_name']}")
        return
    
    # Filter items that need rebuilding
    items_to_rebuild = [item for item in items if item['needs_rebuild']]
    items_to_skip = [item for item in items if not item['needs_rebuild']]
    
    print(f"Items to rebuild: {len(items_to_rebuild)}")
    print(f"Items to skip: {len(items_to_skip)}")
    print()
    
    if not items_to_rebuild:
        print("All items have recent forecasts. Use --force to rebuild anyway.")
        return
    
    # Confirm before proceeding
    if not args.verbose:
        response = input(f"Proceed with rebuilding {len(items_to_rebuild)} forecasts? (y/N): ")
        if response.lower() != 'y':
            print("Cancelled.")
            return
    
    # Rebuild forecasts
    print("Starting forecast rebuild...")
    start_time = time.time()
    
    results = rebuild_forecasts(
        items_to_rebuild,
        dry_run=args.dry_run,
        verbose=args.verbose
    )
    
    elapsed_time = time.time() - start_time
    
    # Print results
    print()
    print("=== Rebuild Results ===")
    print(f"Total items processed: {results['total']}")
    print(f"Successful rebuilds: {results['success']}")
    print(f"Failed rebuilds: {results['failed']}")
    print(f"Skipped (recent): {results['skipped']}")
    print(f"Elapsed time: {elapsed_time/60:.1f} minutes")
    print(f"Average time per item: {elapsed_time/results['total']:.2f} seconds")
    
    if results['errors']:
        print("\n=== Errors ===")
        for error in results['errors']:
            print(f"  {error}")
    
    print()
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == '__main__':
    main() 