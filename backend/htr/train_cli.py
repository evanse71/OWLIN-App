# backend/htr/train_cli.py
"""
Command-line interface for HTR training data management.

This module provides CLI tools for exporting training samples, managing
HTR models, and performing training data analysis.
"""

from __future__ import annotations
import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import HTRModelType
from .dataset import HTRSampleStorage

LOGGER = logging.getLogger("owlin.htr.train_cli")


def export_samples_tsv(args) -> int:
    """Export samples to TSV format."""
    try:
        storage = HTRSampleStorage(args.db_path)
        
        # Set filters
        model_used = HTRModelType(args.model) if args.model else None
        min_confidence = args.min_confidence if args.min_confidence else None
        
        # Export samples
        success = storage.export_samples_tsv(
            output_path=args.output,
            model_used=model_used,
            min_confidence=min_confidence
        )
        
        if success:
            print(f"Successfully exported samples to {args.output}")
            return 0
        else:
            print("Failed to export samples", file=sys.stderr)
            return 1
            
    except Exception as e:
        print(f"Error exporting samples: {e}", file=sys.stderr)
        return 1


def show_statistics(args) -> int:
    """Show HTR storage statistics."""
    try:
        storage = HTRSampleStorage(args.db_path)
        stats = storage.get_statistics()
        
        print("HTR Storage Statistics:")
        print(f"  Total samples: {stats.get('total_samples', 0)}")
        print(f"  Average sample confidence: {stats.get('avg_sample_confidence', 0.0):.3f}")
        print(f"  Total predictions: {stats.get('total_predictions', 0)}")
        print(f"  Average prediction confidence: {stats.get('avg_prediction_confidence', 0.0):.3f}")
        
        model_counts = stats.get('model_counts', {})
        if model_counts:
            print("\nSamples by model:")
            for model, count in model_counts.items():
                print(f"  {model}: {count}")
        
        return 0
        
    except Exception as e:
        print(f"Error getting statistics: {e}", file=sys.stderr)
        return 1


def cleanup_old_data(args) -> int:
    """Clean up old HTR data."""
    try:
        storage = HTRSampleStorage(args.db_path)
        deleted_count = storage.cleanup_old_samples(args.days_old)
        
        print(f"Cleaned up {deleted_count} old records")
        return 0
        
    except Exception as e:
        print(f"Error cleaning up data: {e}", file=sys.stderr)
        return 1


def list_samples(args) -> int:
    """List HTR samples with optional filters."""
    try:
        storage = HTRSampleStorage(args.db_path)
        
        # Set filters
        model_used = HTRModelType(args.model) if args.model else None
        min_confidence = args.min_confidence if args.min_confidence else None
        max_confidence = args.max_confidence if args.max_confidence else None
        
        samples = storage.get_samples(
            model_used=model_used,
            min_confidence=min_confidence,
            max_confidence=max_confidence,
            limit=args.limit
        )
        
        print(f"Found {len(samples)} samples:")
        for sample in samples:
            print(f"  {sample.sample_id}: {sample.ground_truth[:50]}... "
                  f"(conf: {sample.confidence:.3f}, model: {sample.model_used.value})")
        
        return 0
        
    except Exception as e:
        print(f"Error listing samples: {e}", file=sys.stderr)
        return 1


def list_predictions(args) -> int:
    """List HTR predictions with optional filters."""
    try:
        storage = HTRSampleStorage(args.db_path)
        
        predictions = storage.get_predictions(
            document_id=args.document_id,
            page_num=args.page_num,
            model_used=HTRModelType(args.model) if args.model else None,
            limit=args.limit
        )
        
        print(f"Found {len(predictions)} predictions:")
        for pred in predictions:
            print(f"  {pred['block_id']}: {pred['text'][:50]}... "
                  f"(conf: {pred['confidence']:.3f}, model: {pred['model_used']})")
        
        return 0
        
    except Exception as e:
        print(f"Error listing predictions: {e}", file=sys.stderr)
        return 1


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="HTR Training Data Management CLI")
    parser.add_argument("--db-path", type=str, default="data/owlin.db",
                       help="Path to SQLite database")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Export command
    export_parser = subparsers.add_parser("export", help="Export samples to TSV")
    export_parser.add_argument("output", help="Output TSV file path")
    export_parser.add_argument("--model", choices=[m.value for m in HTRModelType],
                              help="Filter by model type")
    export_parser.add_argument("--min-confidence", type=float,
                              help="Minimum confidence threshold")
    export_parser.set_defaults(func=export_samples_tsv)
    
    # Statistics command
    stats_parser = subparsers.add_parser("stats", help="Show storage statistics")
    stats_parser.set_defaults(func=show_statistics)
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Clean up old data")
    cleanup_parser.add_argument("--days-old", type=int, default=30,
                               help="Delete records older than N days")
    cleanup_parser.set_defaults(func=cleanup_old_data)
    
    # List samples command
    list_samples_parser = subparsers.add_parser("list-samples", help="List samples")
    list_samples_parser.add_argument("--model", choices=[m.value for m in HTRModelType],
                                    help="Filter by model type")
    list_samples_parser.add_argument("--min-confidence", type=float,
                                    help="Minimum confidence threshold")
    list_samples_parser.add_argument("--max-confidence", type=float,
                                    help="Maximum confidence threshold")
    list_samples_parser.add_argument("--limit", type=int,
                                    help="Limit number of results")
    list_samples_parser.set_defaults(func=list_samples)
    
    # List predictions command
    list_pred_parser = subparsers.add_parser("list-predictions", help="List predictions")
    list_pred_parser.add_argument("--document-id", help="Filter by document ID")
    list_pred_parser.add_argument("--page-num", type=int, help="Filter by page number")
    list_pred_parser.add_argument("--model", choices=[m.value for m in HTRModelType],
                                 help="Filter by model type")
    list_pred_parser.add_argument("--limit", type=int, help="Limit number of results")
    list_pred_parser.set_defaults(func=list_predictions)
    
    args = parser.parse_args()
    
    # Setup logging
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    
    # Execute command
    if hasattr(args, 'func'):
        return args.func(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
