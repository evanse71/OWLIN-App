#!/usr/bin/env python3
"""
Pipeline Truth Table Generator

Generates a truth table showing the end-to-end pipeline status for documents.
Shows where data is lost or where processing fails.

Usage:
    python scripts/pipeline_truth_table.py [doc_id1] [doc_id2] ...
    
    If no doc_ids provided, analyzes all recent documents (last 24 hours).
"""
import json
import sqlite3
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# Database path
DB_PATH = Path("data/owlin.db")
if not DB_PATH.exists():
    DB_PATH = Path("backend/data/owlin.db")

def get_document_data(doc_id: str) -> Dict[str, Any]:
    """Get all data for a document from database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    result = {
        "doc_id": doc_id,
        "upload_ok": False,
        "ocr_text_length": 0,
        "extraction_ok": False,
        "supplier_extracted": "Unknown Supplier",
        "totals_extracted": 0.0,
        "line_items_count": 0,
        "db_invoice_row_exists": False,
        "api_invoice_returned": False,  # Will be set by API check
        "frontend_card_rendered": False,  # Will be set by frontend check
        "first_failure_stage": None,
        "proposed_fix": None
    }
    
    # Check documents table (use uploaded_at, not created_at)
    cur.execute("""
        SELECT id, filename, stored_path, size_bytes, status, ocr_error, 
               doc_type, ocr_confidence, uploaded_at
        FROM documents
        WHERE id = ?
    """, (doc_id,))
    doc_row = cur.fetchone()
    
    if doc_row:
        result["upload_ok"] = True
        result["doc_status"] = doc_row["status"]
        result["doc_error"] = doc_row["ocr_error"]
        result["doc_type"] = doc_row["doc_type"]
        result["doc_confidence"] = doc_row["ocr_confidence"]
    else:
        result["first_failure_stage"] = "upload"
        result["proposed_fix"] = "Document not found in database - upload may have failed"
        conn.close()
        return result
    
    # Check invoices table
    cur.execute("""
        SELECT id, supplier, date, value, invoice_number, confidence, status
        FROM invoices
        WHERE id = ?
    """, (doc_id,))
    inv_row = cur.fetchone()
    
    if inv_row:
        result["db_invoice_row_exists"] = True
        result["supplier_extracted"] = inv_row["supplier"] or "Unknown Supplier"
        result["totals_extracted"] = float(inv_row["value"]) if inv_row["value"] else 0.0
        result["invoice_status"] = inv_row["status"]
        result["invoice_confidence"] = inv_row["confidence"]
    else:
        if not result["first_failure_stage"]:
            result["first_failure_stage"] = "db_write"
            result["proposed_fix"] = "Invoice row not found in database - extraction may have failed or DB write failed"
    
    # Check line_items table
    cur.execute("""
        SELECT COUNT(*) as count
        FROM invoice_line_items
        WHERE doc_id = ?
    """, (doc_id,))
    line_items_row = cur.fetchone()
    if line_items_row:
        result["line_items_count"] = line_items_row["count"] or 0
    
    # Check audit trail for OCR text length (if table exists)
    try:
        cur.execute("""
            SELECT detail
            FROM audit_trail
            WHERE entity = 'ocr_service' AND action = 'OCR_DONE' AND detail LIKE ?
            ORDER BY timestamp DESC
            LIMIT 1
        """, (f'%"doc_id": "{doc_id}"%',))
        audit_row = cur.fetchone()
        if audit_row:
            try:
                audit_detail = json.loads(audit_row["detail"])
                result["ocr_text_length"] = audit_detail.get("ocr_text_length", 0)
            except:
                pass
    except sqlite3.OperationalError:
        # audit_trail table doesn't exist - skip
        pass
    
    # Check for extraction data in audit trail (if table exists)
    try:
        cur.execute("""
            SELECT detail
            FROM audit_trail
            WHERE entity = 'ocr_service' AND action = 'EXTRACTION_DONE' AND detail LIKE ?
            ORDER BY timestamp DESC
            LIMIT 1
        """, (f'%"doc_id": "{doc_id}"%',))
        extraction_row = cur.fetchone()
        if extraction_row:
            try:
                extraction_detail = json.loads(extraction_row["detail"])
                if extraction_detail.get("supplier") and extraction_detail.get("supplier") != "Unknown Supplier":
                    result["extraction_ok"] = True
                elif extraction_detail.get("line_items_count", 0) > 0:
                    result["extraction_ok"] = True
                elif extraction_detail.get("total", 0) > 0 or extraction_detail.get("totals_extracted", 0) > 0:
                    result["extraction_ok"] = True
            except:
                pass
    except sqlite3.OperationalError:
        # audit_trail table doesn't exist - skip
        pass
    
    # Determine first failure stage based on DB data
    if not result["first_failure_stage"]:
        # Check document status for OCR errors
        if doc_row and doc_row["status"] == "error" and doc_row["ocr_error"]:
            if "insufficient text" in str(doc_row["ocr_error"]).lower() or "0 chars" in str(doc_row["ocr_error"]):
                result["first_failure_stage"] = "ocr"
                result["proposed_fix"] = f"OCR produced insufficient text. Error: {doc_row['ocr_error']}"
            else:
                result["first_failure_stage"] = "ocr"
                result["proposed_fix"] = f"OCR failed: {doc_row['ocr_error']}"
        elif result["supplier_extracted"] == "Unknown Supplier" and result["totals_extracted"] == 0.0 and result["line_items_count"] == 0:
            result["first_failure_stage"] = "extraction"
            result["proposed_fix"] = "Extraction produced empty data - supplier=Unknown, total=0, line_items=0. Check extraction heuristics and LLM integration."
            # Also check if document is incorrectly marked as "ready"
            if doc_row and doc_row["status"] == "ready":
                result["proposed_fix"] += " BUG: Document marked as 'ready' despite empty data - should be 'error' or 'needs_review'."
        elif not result["db_invoice_row_exists"]:
            result["first_failure_stage"] = "db_write"
            result["proposed_fix"] = "DB write failed - extraction succeeded but invoice row not found. Check upsert_invoice() function."
        elif result["ocr_text_length"] > 0 and result["ocr_text_length"] < 100:
            result["first_failure_stage"] = "ocr"
            result["proposed_fix"] = f"OCR produced insufficient text ({result['ocr_text_length']} chars, minimum 100 required). Check OCR engine configuration."
        else:
            result["first_failure_stage"] = "none"
            result["proposed_fix"] = "Pipeline completed successfully"
    
    conn.close()
    return result

def get_recent_doc_ids(hours: int = 24) -> List[str]:
    """Get doc_ids from recent documents."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
    cur.execute("""
        SELECT id
        FROM documents
        WHERE created_at >= ?
        ORDER BY created_at DESC
        LIMIT 100
    """, (cutoff,))
    
    doc_ids = [row[0] for row in cur.fetchall()]
    conn.close()
    return doc_ids

def generate_truth_table(doc_ids: List[str]) -> List[Dict[str, Any]]:
    """Generate truth table for given doc_ids."""
    results = []
    for doc_id in doc_ids:
        result = get_document_data(doc_id)
        results.append(result)
    return results

def print_truth_table(results: List[Dict[str, Any]], output_format: str = "table"):
    """Print truth table in specified format."""
    if output_format == "json":
        print(json.dumps(results, indent=2))
        return
    
    # Print as table
    print("\n" + "="*120)
    print("PIPELINE TRUTH TABLE")
    print("="*120)
    print(f"{'doc_id':<40} {'upload':<8} {'OCR len':<10} {'extract':<8} {'supplier':<25} {'total':<12} {'items':<8} {'DB':<4} {'stage':<15} {'fix':<30}")
    print("-"*120)
    
    for r in results:
        doc_id_short = r["doc_id"][:38] + ".." if len(r["doc_id"]) > 40 else r["doc_id"]
        upload = "Y" if r["upload_ok"] else "N"
        ocr_len = str(r["ocr_text_length"]) if r["ocr_text_length"] > 0 else "?"
        extract = "Y" if r["extraction_ok"] else "N"
        supplier = (r["supplier_extracted"][:23] + "..") if len(r["supplier_extracted"]) > 25 else r["supplier_extracted"]
        total = f"£{r['totals_extracted']:.2f}" if r["totals_extracted"] > 0 else "£0.00"
        items = str(r["line_items_count"])
        db = "Y" if r["db_invoice_row_exists"] else "N"
        stage = r["first_failure_stage"] or "ok"
        fix = (r["proposed_fix"][:28] + "..") if r["proposed_fix"] and len(r["proposed_fix"]) > 30 else (r["proposed_fix"] or "")
        
        print(f"{doc_id_short:<40} {upload:<8} {ocr_len:<10} {extract:<8} {supplier:<25} {total:<12} {items:<8} {db:<4} {stage:<15} {fix:<30}")
    
    print("="*120)
    print(f"Total documents analyzed: {len(results)}")
    
    # Summary statistics
    upload_ok = sum(1 for r in results if r["upload_ok"])
    extraction_ok = sum(1 for r in results if r["extraction_ok"])
    db_ok = sum(1 for r in results if r["db_invoice_row_exists"])
    
    print(f"\nSummary:")
    print(f"  Upload OK: {upload_ok}/{len(results)}")
    print(f"  Extraction OK: {extraction_ok}/{len(results)}")
    print(f"  DB Write OK: {db_ok}/{len(results)}")
    
    # Failure stages
    failure_stages = {}
    for r in results:
        stage = r["first_failure_stage"] or "none"
        failure_stages[stage] = failure_stages.get(stage, 0) + 1
    
    print(f"\nFailure stages:")
    for stage, count in sorted(failure_stages.items(), key=lambda x: -x[1]):
        print(f"  {stage}: {count}")

def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        doc_ids = sys.argv[1:]
    else:
        print("No doc_ids provided. Analyzing recent documents (last 24 hours)...")
        doc_ids = get_recent_doc_ids(24)
        if not doc_ids:
            print("No recent documents found.")
            return
        print(f"Found {len(doc_ids)} recent documents.")
    
    results = generate_truth_table(doc_ids)
    
    # Determine output format
    output_format = "table"
    if "--json" in sys.argv:
        output_format = "json"
    
    print_truth_table(results, output_format)
    
    # Save to file
    output_file = Path("data/pipeline_truth_table.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nTruth table saved to: {output_file}")

if __name__ == "__main__":
    main()

