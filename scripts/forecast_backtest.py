#!/usr/bin/env python3
"""
Forecast Backtest Script

This script performs rolling backtests on forecast models to evaluate their performance.
It can be run headlessly for model evaluation and comparison.

Usage:
    python scripts/forecast_backtest.py [--item-id ITEM_ID] [--window-days DAYS] [--models MODEL1,MODEL2]

Options:
    --item-id       Backtest specific item ID (default: all items)
    --window-days   Rolling window size in days (default: 90)
    --models        Comma-separated list of models to test (default: all)
    --output        Output file for results (default: backtest_results.json)
    --verbose       Show detailed progress information
"""

import argparse
import sys
import os
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from services.forecast_service import ForecastService
from db.connection import get_conn
from contracts import ForecastQuality


def get_items_for_backtest(item_id: Optional[int] = None) -> List[dict]:
    """Get list of items suitable for backtesting."""
    conn = get_conn()
    cursor = conn.cursor()
    
    query = """
        SELECT DISTINCT 
            i.id as item_id,
            i.name as item_name,
            i.supplier_id,
            s.name as supplier_name,
            COUNT(ili.id) as data_points,
            MIN(ili.invoice_date) as first_date,
            MAX(ili.invoice_date) as last_date,
            AVG(ili.unit_price) as avg_price
        FROM invoice_line_items ili
        JOIN items i ON ili.item_id = i.id
        JOIN suppliers s ON i.supplier_id = s.id
        WHERE ili.unit_price > 0
    """
    
    params = []
    if item_id:
        query += " AND i.id = ?"
        params.append(item_id)
    
    query += """
        GROUP BY i.id, i.name, i.supplier_id, s.name
        HAVING COUNT(ili.id) >= 12  -- Minimum 12 data points for backtesting
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
            'data_points': row[4],
            'first_date': row[5],
            'last_date': row[6],
            'avg_price': row[7]
        }
        items.append(item)
    
    conn.close()
    return items


def run_backtest(
    forecast_service: ForecastService,
    item: dict,
    window_days: int,
    models: List[str],
    verbose: bool = False
) -> Dict[str, Any]:
    """Run backtest for a single item."""
    if verbose:
        print(f"  Backtesting {item['item_name']} (ID: {item['item_id']})")
    
    results = {
        'item_id': item['item_id'],
        'item_name': item['item_name'],
        'supplier_name': item['supplier_name'],
        'window_days': window_days,
        'models': {},
        'summary': {}
    }
    
    try:
        # Run rolling backtest
        backtest_results = forecast_service.rolling_backtest(
            item['item_id'], 
            window_days,
            models=models
        )
        
        # Process results by model
        for model_result in backtest_results:
            model_name = model_result['model']
            results['models'][model_name] = {
                'smape': model_result['smape'],
                'mape': model_result['mape'],
                'wape': model_result['wape'],
                'bias_pct': model_result['bias_pct'],
                'forecast_count': model_result.get('forecast_count', 0)
            }
        
        # Find best model
        if results['models']:
            best_model = min(results['models'].keys(), 
                           key=lambda m: results['models'][m]['smape'])
            results['summary'] = {
                'best_model': best_model,
                'best_smape': results['models'][best_model]['smape'],
                'model_count': len(results['models']),
                'avg_smape': sum(r['smape'] for r in results['models'].values()) / len(results['models'])
            }
        
        if verbose:
            if results['summary']:
                print(f"    Best model: {results['summary']['best_model']} (SMAPE: {results['summary']['best_smape']:.1f}%)")
            else:
                print(f"    No valid backtest results")
    
    except Exception as e:
        if verbose:
            print(f"    ERROR: {str(e)}")
        results['error'] = str(e)
    
    return results


def analyze_backtest_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze overall backtest results."""
    analysis = {
        'total_items': len(results),
        'successful_items': len([r for r in results if 'error' not in r]),
        'failed_items': len([r for r in results if 'error' in r]),
        'model_performance': {},
        'best_models': {},
        'summary_stats': {}
    }
    
    # Model performance analysis
    model_stats = {}
    for result in results:
        if 'error' in result:
            continue
        
        for model_name, metrics in result['models'].items():
            if model_name not in model_stats:
                model_stats[model_name] = {
                    'smape_values': [],
                    'mape_values': [],
                    'wape_values': [],
                    'bias_values': [],
                    'usage_count': 0
                }
            
            model_stats[model_name]['smape_values'].append(metrics['smape'])
            model_stats[model_name]['mape_values'].append(metrics['mape'])
            model_stats[model_name]['wape_values'].append(metrics['wape'])
            model_stats[model_name]['bias_values'].append(metrics['bias_pct'])
            model_stats[model_name]['usage_count'] += 1
    
    # Calculate summary statistics for each model
    for model_name, stats in model_stats.items():
        analysis['model_performance'][model_name] = {
            'usage_count': stats['usage_count'],
            'avg_smape': sum(stats['smape_values']) / len(stats['smape_values']),
            'avg_mape': sum(stats['mape_values']) / len(stats['mape_values']),
            'avg_wape': sum(stats['wape_values']) / len(stats['wape_values']),
            'avg_bias': sum(stats['bias_values']) / len(stats['bias_values']),
            'min_smape': min(stats['smape_values']),
            'max_smape': max(stats['smape_values']),
            'std_smape': (sum((x - sum(stats['smape_values'])/len(stats['smape_values']))**2 
                         for x in stats['smape_values']) / len(stats['smape_values']))**0.5
        }
    
    # Best model analysis
    best_models = [r['summary']['best_model'] for r in results 
                  if 'error' not in r and 'summary' in r and 'best_model' in r['summary']]
    for model in set(best_models):
        analysis['best_models'][model] = best_models.count(model)
    
    # Overall summary statistics
    all_smape = [r['summary']['best_smape'] for r in results 
                if 'error' not in r and 'summary' in r and 'best_smape' in r['summary']]
    
    if all_smape:
        analysis['summary_stats'] = {
            'avg_best_smape': sum(all_smape) / len(all_smape),
            'min_best_smape': min(all_smape),
            'max_best_smape': max(all_smape),
            'items_with_good_forecasts': len([s for s in all_smape if s < 20]),
            'items_with_poor_forecasts': len([s for s in all_smape if s >= 20])
        }
    
    return analysis


def save_results(results: List[Dict[str, Any]], analysis: Dict[str, Any], output_file: str):
    """Save backtest results to file."""
    output_data = {
        'timestamp': datetime.now().isoformat(),
        'results': results,
        'analysis': analysis
    }
    
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)
    
    print(f"Results saved to: {output_file}")


def main():
    parser = argparse.ArgumentParser(description='Run forecast model backtests')
    parser.add_argument('--item-id', type=int, help='Backtest specific item ID')
    parser.add_argument('--window-days', type=int, default=90, help='Rolling window size in days')
    parser.add_argument('--models', help='Comma-separated list of models to test')
    parser.add_argument('--output', default='backtest_results.json', help='Output file for results')
    parser.add_argument('--verbose', action='store_true', help='Show detailed progress information')
    
    args = parser.parse_args()
    
    print("=== Forecast Backtest Script ===")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Parse models
    models = None
    if args.models:
        models = [m.strip() for m in args.models.split(',')]
        print(f"Testing models: {', '.join(models)}")
    else:
        print("Testing all available models")
    
    print(f"Rolling window: {args.window_days} days")
    print()
    
    # Get items for backtesting
    print("Scanning for items suitable for backtesting...")
    items = get_items_for_backtest(item_id=args.item_id)
    
    if not items:
        print("No items found suitable for backtesting.")
        print("Items need at least 12 data points for meaningful backtesting.")
        return
    
    print(f"Found {len(items)} items for backtesting")
    
    # Initialize forecast service
    forecast_service = ForecastService()
    
    # Run backtests
    print("Starting backtests...")
    start_time = time.time()
    
    results = []
    for i, item in enumerate(items, 1):
        if args.verbose:
            print(f"[{i}/{len(items)}] Processing {item['item_name']}")
        
        result = run_backtest(
            forecast_service,
            item,
            args.window_days,
            models,
            verbose=args.verbose
        )
        results.append(result)
        
        # Progress indicator
        if i % 10 == 0 and args.verbose:
            elapsed = time.time() - start_time
            rate = i / elapsed
            remaining = (len(items) - i) / rate if rate > 0 else 0
            print(f"  Progress: {i}/{len(items)} ({i/len(items)*100:.1f}%) - ETA: {remaining/60:.1f}min")
    
    elapsed_time = time.time() - start_time
    
    # Analyze results
    print("\nAnalyzing results...")
    analysis = analyze_backtest_results(results)
    
    # Print summary
    print("\n=== Backtest Summary ===")
    print(f"Total items: {analysis['total_items']}")
    print(f"Successful backtests: {analysis['successful_items']}")
    print(f"Failed backtests: {analysis['failed_items']}")
    print(f"Elapsed time: {elapsed_time/60:.1f} minutes")
    
    if analysis['summary_stats']:
        print(f"\nOverall Performance:")
        print(f"  Average best SMAPE: {analysis['summary_stats']['avg_best_smape']:.1f}%")
        print(f"  Range: {analysis['summary_stats']['min_best_smape']:.1f}% - {analysis['summary_stats']['max_best_smape']:.1f}%")
        print(f"  Good forecasts (<20%): {analysis['summary_stats']['items_with_good_forecasts']}")
        print(f"  Poor forecasts (≥20%): {analysis['summary_stats']['items_with_poor_forecasts']}")
    
    if analysis['model_performance']:
        print(f"\nModel Performance:")
        for model, stats in analysis['model_performance'].items():
            print(f"  {model}:")
            print(f"    Usage: {stats['usage_count']} items")
            print(f"    Avg SMAPE: {stats['avg_smape']:.1f}%")
            print(f"    Range: {stats['min_smape']:.1f}% - {stats['max_smape']:.1f}%")
    
    if analysis['best_models']:
        print(f"\nBest Model Distribution:")
        for model, count in analysis['best_models'].items():
            percentage = (count / analysis['successful_items']) * 100
            print(f"  {model}: {count} items ({percentage:.1f}%)")
    
    # Save results
    print(f"\nSaving results...")
    save_results(results, analysis, args.output)
    
    print()
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == '__main__':
    main() 