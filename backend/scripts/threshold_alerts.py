#!/usr/bin/env python3
"""
Threshold Alerts for OCR Pipeline
Monitors pipeline health and warns about potential issues
"""

import os
import json
import sqlite3
import sys
from datetime import datetime

DB_PATH = os.environ.get("OWLIN_DB", "data/owlin.db")

def check_thresholds():
    """Check various thresholds and return alerts"""
    alerts = []
    
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        
        # Check high confidence but zero line items
        hi_conf_zero_lines = conn.execute("""
            SELECT COUNT(*) 
            FROM invoices 
            WHERE confidence >= 80 
            AND (line_items IS NULL OR line_items = '[]' OR line_items = '')
        """).fetchone()[0]
        
        if hi_conf_zero_lines > 0:
            alerts.append({
                "type": "warning",
                "message": f"High confidence but zero line items: {hi_conf_zero_lines} invoices",
                "threshold": "> 0",
                "current": hi_conf_zero_lines
            })
        
        # Check total mismatch percentage
        total_invoices = conn.execute("SELECT COUNT(*) FROM invoices").fetchone()[0]
        if total_invoices > 0:
            # Simple check for potential mismatches (subtotal = 0 but has line items)
            total_mismatch = conn.execute("""
                SELECT COUNT(*) 
                FROM invoices 
                WHERE (subtotal = 0 OR subtotal IS NULL)
                AND (line_items IS NOT NULL AND line_items != '[]' AND line_items != '')
            """).fetchone()[0]
            
            mismatch_percentage = (total_mismatch / total_invoices) * 100
            if mismatch_percentage > 3:
                alerts.append({
                    "type": "warning",
                    "message": f"Total mismatch percentage: {mismatch_percentage:.1f}%",
                    "threshold": "> 3%",
                    "current": f"{mismatch_percentage:.1f}%"
                })
        
        # Check multi-invoice uploads (if we have any)
        multi_invoice_uploads = conn.execute("""
            SELECT COUNT(DISTINCT parent_pdf_filename) 
            FROM (
                SELECT parent_pdf_filename, COUNT(*) as cnt 
                FROM invoices 
                WHERE parent_pdf_filename IS NOT NULL
                GROUP BY parent_pdf_filename 
                HAVING cnt > 1
            )
        """).fetchone()[0]
        
        # This is more of a monitoring metric than an alert
        print(f"📊 Multi-invoice uploads: {multi_invoice_uploads}")
        
        conn.close()
        
    except Exception as e:
        alerts.append({
            "type": "error",
            "message": f"Error checking thresholds: {e}",
            "threshold": "N/A",
            "current": "ERROR"
        })
    
    return alerts

def main():
    print(f"🔍 Checking thresholds at {datetime.now()}")
    
    alerts = check_thresholds()
    
    if alerts:
        print("\n⚠️  ALERTS:")
        for alert in alerts:
            print(f"  {alert['type'].upper()}: {alert['message']}")
            print(f"    Threshold: {alert['threshold']}, Current: {alert['current']}")
        sys.exit(1)
    else:
        print("✅ All thresholds within acceptable ranges")
        sys.exit(0)

if __name__ == "__main__":
    main() 