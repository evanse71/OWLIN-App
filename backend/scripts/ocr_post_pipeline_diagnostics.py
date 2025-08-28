#!/usr/bin/env python3
"""
OCR Post-Pipeline Diagnostics
Analyzes invoice processing results and exports detailed CSV data
"""

import os, json, sqlite3, csv, sys
from datetime import datetime

# Use same environment variable as backend
DB_PATH = os.environ.get("OWLIN_DB", "data/owlin.db")
OUT_DIR = os.environ.get("OWLIN_DIAG_DIR", "backups/diagnostics")
os.makedirs(OUT_DIR, exist_ok=True)
CSV_PATH = os.path.join(OUT_DIR, f"ocr_post_pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")

def fetch_invoices(conn):
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
        SELECT
          i.id, i.invoice_number, i.invoice_date, i.supplier_name,
          i.confidence, i.subtotal, i.vat, i.total_incl_vat,
          i.parent_pdf_filename, i.page_range, i.status,
          i.line_items, i.upload_timestamp
        FROM invoices i
        ORDER BY i.upload_timestamp DESC
        LIMIT 500
    """)
    return cur.fetchall()

def count_line_items(line_items_json):
    """Count line items from JSON string"""
    if not line_items_json:
        return 0
    try:
        items = json.loads(line_items_json)
        return len(items) if isinstance(items, list) else 0
    except:
        return 0

def extract_page_range(filename):
    """Extract page range from filename if present"""
    if not filename:
        return ""
    if "_pages_" in filename:
        try:
            parts = filename.split("_pages_")
            if len(parts) > 1:
                return parts[1]
        except:
            pass
    return ""

def main():
    if not os.path.exists(DB_PATH):
        print(f"[ERR] DB not found at {DB_PATH}", file=sys.stderr)
        sys.exit(2)

    conn = sqlite3.connect(DB_PATH)
    rows = fetch_invoices(conn)

    fieldnames = [
        "invoice_id","filename","page_range",
        "supplier","invoice_number","invoice_date",
        "confidence","status","line_items",
        "subtotal","vat","total_incl_vat"
    ]
    out = []
    for r in rows:
        page_range = extract_page_range(r["parent_pdf_filename"])
        line_items_count = count_line_items(r["line_items"])
        
        out.append({
            "invoice_id": r["id"],
            "filename": r["parent_pdf_filename"],
            "page_range": page_range,
            "supplier": r["supplier_name"],
            "invoice_number": r["invoice_number"],
            "invoice_date": r["invoice_date"],
            "confidence": r["confidence"],
            "status": r["status"],
            "line_items": line_items_count,
            "subtotal": r["subtotal"],
            "vat": r["vat"],
            "total_incl_vat": r["total_incl_vat"],
        })

    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(out)

    # Pretty summary
    total = len(out)
    
    # Group by filename to detect multi-invoice uploads
    multi_by_filename = {}
    for r in out:
        if r["filename"]:
            multi_by_filename.setdefault(r["filename"], 0)
            multi_by_filename[r["filename"]] += 1
    multi_uploads = {k:v for k,v in multi_by_filename.items() if v>1}

    hi_conf_zero_lines = [r for r in out if (r["confidence"] or 0) >= 80 and (r["line_items"] or 0) == 0]
    
    # Check for potential total mismatches
    total_mismatch = []
    for r in out:
        if r["line_items"] and r["subtotal"]:
            # Simple check: if line items exist but subtotal is 0 or very different
            if r["subtotal"] == 0 and r["line_items"] > 0:
                total_mismatch.append(r)

    print("\n=== OCR Post-Pipeline Diagnostics ===")
    print(f"Invoices scanned: {total}")
    print(f"Uploads with >1 invoices (split success): {len(multi_uploads)}")
    print(f"High confidence but 0 line items: {len(hi_conf_zero_lines)}")
    print(f"Potential total mismatches: {len(total_mismatch)}")
    print(f"CSV written: {CSV_PATH}\n")

    # Optional: list top 5 risky invoices
    def head(lst): return lst[:5]
    if hi_conf_zero_lines:
        print("- Top high-conf no-lines (5):", [ (r['invoice_id'], r['filename'], r['confidence']) for r in head(hi_conf_zero_lines) ])
    if total_mismatch:
        print("- Top potential mismatches (5):", [ (r['invoice_id'], r['filename']) for r in head(total_mismatch) ])
    if multi_uploads:
        print("- Multi-invoice files:", list(multi_uploads.keys())[:3])

if __name__ == "__main__":
    main() 