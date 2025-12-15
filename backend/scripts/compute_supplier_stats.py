"""
Compute supplier statistics from historical delivery notes.

This script analyzes delivery note patterns to compute:
- Typical delivery weekdays (most common days of week)
- Average days between deliveries
- Standard deviation of days between deliveries

Run periodically (e.g., weekly) to update supplier patterns for improved pairing accuracy.
"""
import argparse
import sqlite3
import sys
import os
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import statistics

# Force path so imports always work
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_PROJECT_ROOT = _BACKEND_DIR.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.app.db import DB_PATH, upsert_supplier_stats
from backend.services.pairing_service import normalize_supplier_name


def parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """Parse a date string to datetime object."""
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except ValueError:
        try:
            return datetime.strptime(date_str.split("T")[0], "%Y-%m-%d")
        except Exception:
            return None


def compute_weekday_distribution(dates: List[datetime]) -> List[int]:
    """
    Compute typical delivery weekdays.
    Returns list of weekday numbers (0=Monday, 6=Sunday) that occur most frequently.
    """
    if not dates:
        return []
    
    weekday_counts = Counter(d.weekday() for d in dates)
    
    # Get weekdays that occur at least 20% as often as the most common weekday
    if not weekday_counts:
        return []
    
    max_count = max(weekday_counts.values())
    threshold = max(1, int(max_count * 0.2))  # At least 20% of max frequency
    
    typical_weekdays = [
        weekday for weekday, count in weekday_counts.items()
        if count >= threshold
    ]
    
    return sorted(typical_weekdays)


def compute_delivery_intervals(dates: List[datetime]) -> Tuple[Optional[float], Optional[float]]:
    """
    Compute average and standard deviation of days between consecutive deliveries.
    Returns (avg_days, std_days) or (None, None) if insufficient data.
    """
    if len(dates) < 2:
        return None, None
    
    # Sort dates chronologically
    sorted_dates = sorted(dates)
    
    # Calculate intervals between consecutive deliveries
    intervals = []
    for i in range(1, len(sorted_dates)):
        delta = (sorted_dates[i] - sorted_dates[i-1]).days
        if delta > 0:  # Only positive intervals
            intervals.append(float(delta))
    
    if not intervals:
        return None, None
    
    avg = statistics.mean(intervals)
    std = statistics.stdev(intervals) if len(intervals) > 1 else 0.0
    
    return avg, std


def compute_supplier_stats(
    supplier_id: Optional[str] = None,
    venue_id: Optional[str] = None,
    min_deliveries: int = 3,
    dry_run: bool = False
) -> Dict[str, int]:
    """
    Compute statistics for suppliers from historical delivery notes.
    
    Args:
        supplier_id: If provided, only compute for this supplier
        venue_id: If provided, filter by venue
        min_deliveries: Minimum number of deliveries required (default: 3)
        dry_run: If True, show what would be computed without saving
    
    Returns:
        Dictionary with counts of suppliers processed, updated, skipped
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Build query to get delivery notes
    where_parts = ["doc_type = 'delivery_note'", "doc_date IS NOT NULL"]
    params = []
    
    if supplier_id:
        # Normalize supplier name for matching
        normalized_supplier = normalize_supplier_name(supplier_id)
        where_parts.append("LOWER(TRIM(supplier)) = LOWER(TRIM(?))")
        params.append(supplier_id)
    
    if venue_id:
        where_parts.append("venue = ?")
        params.append(venue_id)
    
    query = f"""
        SELECT 
            supplier,
            venue,
            doc_date,
            uploaded_at
        FROM documents
        WHERE {' AND '.join(where_parts)}
        ORDER BY supplier, venue, doc_date
    """
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    # Group by normalized supplier name and venue
    supplier_data: Dict[Tuple[str, Optional[str]], List[datetime]] = defaultdict(list)
    
    for row in rows:
        supplier = row["supplier"]
        venue = row["venue"] if row["venue"] else None
        doc_date = parse_date(row["doc_date"])
        
        if not supplier or not doc_date:
            continue
        
        normalized_supplier = normalize_supplier_name(supplier)
        key = (normalized_supplier, venue)
        supplier_data[key].append(doc_date)
    
    # Compute statistics for each supplier/venue combination
    stats_updated = 0
    stats_skipped = 0
    stats_processed = 0
    
    print(f"\n{'='*80}")
    print(f"Computing Supplier Statistics")
    print(f"{'='*80}")
    if supplier_id:
        print(f"Supplier filter: {supplier_id}")
    if venue_id:
        print(f"Venue filter: {venue_id}")
    print(f"Minimum deliveries required: {min_deliveries}")
    print(f"Mode: {'DRY RUN' if dry_run else 'UPDATE'}")
    print(f"{'='*80}\n")
    
    for (norm_supplier, venue), dates in supplier_data.items():
        stats_processed += 1
        
        if len(dates) < min_deliveries:
            print(f"⏭️  SKIP: {norm_supplier} ({venue or 'all venues'}) - Only {len(dates)} delivery(ies), need {min_deliveries}")
            stats_skipped += 1
            continue
        
        # Compute statistics
        typical_weekdays = compute_weekday_distribution(dates)
        avg_days, std_days = compute_delivery_intervals(dates)
        
        # Format weekday names for display
        weekday_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        typical_weekday_names = [weekday_names[wd] for wd in typical_weekdays] if typical_weekdays else []
        
        print(f"✓ {norm_supplier} ({venue or 'all venues'}):")
        print(f"  - Deliveries: {len(dates)}")
        print(f"  - Typical weekdays: {', '.join(typical_weekday_names) if typical_weekday_names else 'None'}")
        print(f"  - Avg days between: {avg_days:.1f}" if avg_days else "  - Avg days between: N/A")
        print(f"  - Std dev: {std_days:.1f}" if std_days else "  - Std dev: N/A")
        
        if not dry_run:
            upsert_supplier_stats(
                supplier_id=norm_supplier,
                venue_id=venue,
                typical_delivery_weekdays=typical_weekdays if typical_weekdays else None,
                avg_days_between_deliveries=avg_days,
                std_days_between_deliveries=std_days,
            )
            print(f"  → Updated in database")
            stats_updated += 1
        else:
            print(f"  → [DRY RUN] Would update in database")
            stats_updated += 1
        
        print()
    
    print(f"{'='*80}")
    print(f"Summary:")
    print(f"  Processed: {stats_processed}")
    print(f"  Updated: {stats_updated}")
    print(f"  Skipped: {stats_skipped}")
    print(f"{'='*80}\n")
    
    return {
        "processed": stats_processed,
        "updated": stats_updated,
        "skipped": stats_skipped,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Compute supplier statistics from historical delivery notes"
    )
    parser.add_argument(
        "--supplier-id",
        type=str,
        help="Compute stats for specific supplier only"
    )
    parser.add_argument(
        "--venue-id",
        type=str,
        help="Filter by venue"
    )
    parser.add_argument(
        "--min-deliveries",
        type=int,
        default=3,
        help="Minimum number of deliveries required (default: 3)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be computed without saving"
    )
    
    args = parser.parse_args()
    
    try:
        results = compute_supplier_stats(
            supplier_id=args.supplier_id,
            venue_id=args.venue_id,
            min_deliveries=args.min_deliveries,
            dry_run=args.dry_run
        )
        
        if args.dry_run:
            print("\n⚠️  DRY RUN MODE - No changes were saved to the database")
            print("   Run without --dry-run to update supplier statistics")
        
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

