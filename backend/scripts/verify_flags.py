#!/usr/bin/env python3
"""
Verify Flags Script
Emit counts for critical flags; exit non-zero if thresholds exceeded.
"""

import sys
import os
import json
from typing import Dict, List

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db_manager_unified import get_db_manager


# Critical flag thresholds
CRITICAL_FLAG_THRESHOLDS = {
    "math_mismatch": 0.01,      # Max 1% of lines
    "reference_conflict": 0.05,  # Max 5% of lines
    "uom_mismatch_suspected": 0.02,  # Max 2% of lines
    "ocr_suspected_error": 0.03,     # Max 3% of lines
    "pricing_anomaly_unmodelled": 0.10  # Max 10% of lines
}


def get_flag_counts(db_connection) -> Dict[str, int]:
    """Get counts of all flags in the system."""
    flag_counts = {}
    
    # Count flags from invoice_items
    line_flag_rows = db_connection.execute("""
        SELECT line_flags FROM invoice_items WHERE line_flags IS NOT NULL
    """).fetchall()
    
    for row in line_flag_rows:
        try:
            flags = json.loads(row['line_flags'])
            for flag in flags:
                flag_counts[flag] = flag_counts.get(flag, 0) + 1
        except (json.JSONDecodeError, TypeError):
            continue
    
    # Count flags from invoices
    invoice_flag_rows = db_connection.execute("""
        SELECT validation_flags FROM invoices WHERE validation_flags IS NOT NULL
    """).fetchall()
    
    for row in invoice_flag_rows:
        try:
            flags = json.loads(row['validation_flags'])
            for flag in flags:
                flag_counts[flag] = flag_counts.get(flag, 0) + 1
        except (json.JSONDecodeError, TypeError):
            continue
    
    return flag_counts


def get_total_line_count(db_connection) -> int:
    """Get total number of line items."""
    result = db_connection.execute("SELECT COUNT(*) as count FROM invoice_items").fetchone()
    return result['count'] if result else 0


def check_thresholds(flag_counts: Dict[str, int], total_lines: int) -> List[str]:
    """Check if any flags exceed thresholds."""
    violations = []
    
    for flag, count in flag_counts.items():
        if flag in CRITICAL_FLAG_THRESHOLDS:
            threshold = CRITICAL_FLAG_THRESHOLDS[flag]
            percentage = count / total_lines if total_lines > 0 else 0
            
            if percentage > threshold:
                violations.append(f"{flag}: {count}/{total_lines} ({percentage:.1%}) > {threshold:.1%}")
    
    return violations


def main():
    """Main verification function."""
    print("Verifying flag thresholds...")
    
    # Get database connection
    db_manager = get_db_manager()
    
    with db_manager.get_connection() as conn:
        # Get flag counts
        flag_counts = get_flag_counts(conn)
        total_lines = get_total_line_count(conn)
        
        print(f"Total line items: {total_lines}")
        print("\nFlag counts:")
        
        for flag, count in sorted(flag_counts.items()):
            percentage = count / total_lines if total_lines > 0 else 0
            print(f"  {flag}: {count} ({percentage:.1%})")
        
        # Check thresholds
        violations = check_thresholds(flag_counts, total_lines)
        
        if violations:
            print(f"\n❌ THRESHOLD VIOLATIONS DETECTED:")
            for violation in violations:
                print(f"  - {violation}")
            return False
        else:
            print(f"\n✅ All thresholds within limits")
            return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 