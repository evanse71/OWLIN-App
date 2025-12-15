#!/usr/bin/env python3
"""
Result Checker - Verify LLM Extraction Results

This script fetches the processed invoice data from the API and checks
if LLM extraction worked by looking for real product names vs "Unknown Item".

Usage:
    python check_result.py [doc_id]
    python check_result.py  # Searches for latest _Fresh_ invoice
"""

import sys
import requests
import json
from pathlib import Path
from datetime import datetime

def find_latest_fresh_doc_id():
    """Find the doc_id from the most recent upload by checking data/uploads."""
    uploads_dir = Path("data") / "uploads"
    
    if not uploads_dir.exists():
        return None
    
    # Find files with _Fresh_ in the name, sort by modification time
    fresh_files = list(uploads_dir.glob("*_Fresh_*.pdf"))
    if fresh_files:
        fresh_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        # Extract doc_id from filename (format: {doc_id}__{filename})
        latest_file = fresh_files[0]
        if '__' in latest_file.name:
            doc_id = latest_file.name.split('__')[0]
            return doc_id
    
    return None

def check_invoice_result(doc_id: str = None, api_url: str = "http://127.0.0.1:5176"):
    """
    Check the invoice processing result from the API.
    
    Args:
        doc_id: Document ID to check (if None, searches for latest _Fresh_ invoice)
        api_url: Base URL of the backend API
    """
    print("=" * 80)
    print("🔍 CHECKING LLM EXTRACTION RESULTS")
    print("=" * 80)
    print()
    
    # Determine doc_id
    if not doc_id:
        print("🔍 Searching for latest _Fresh_ invoice...")
        doc_id = find_latest_fresh_doc_id()
        
        if not doc_id:
            print("❌ No _Fresh_ invoice found in data/uploads/")
            print()
            print("Usage:")
            print("  python check_result.py [doc_id]")
            print()
            print("Or provide the doc_id from the upload response.")
            sys.exit(1)
        
        print(f"✓ Found doc_id: {doc_id}")
        print()
    
    # First check document status
    status_url = f"{api_url}/api/upload/status?doc_id={doc_id}"
    print(f"📡 Checking document status: {status_url}")
    print()
    
    try:
        status_response = requests.get(status_url, timeout=10)
        status_response.raise_for_status()
        status_data = status_response.json()
        
        print(f"✓ Document status: {status_data.get('status', 'unknown')}")
        if status_data.get('parsed'):
            print(f"✓ Invoice data available")
        if status_data.get('items'):
            print(f"✓ Found {len(status_data.get('items', []))} line item(s)")
        print()
        
        # If we have data from status endpoint, use it
        if status_data.get('parsed') or status_data.get('items'):
            print("=" * 80)
            print("📋 INVOICE DATA (from status endpoint)")
            print("=" * 80)
            print()
            
            parsed = status_data.get('parsed', {})
            if parsed:
                print(f"Supplier:   {parsed.get('supplier', 'N/A')}")
                print(f"Date:       {parsed.get('invoice_date', 'N/A')}")
                print(f"Total:      {parsed.get('total_value', 'N/A')}")
                print(f"Status:     {parsed.get('status', 'N/A')}")
                print()
            
            line_items = status_data.get('items', [])
            if line_items:
                print(f"✓ Found {len(line_items)} line item(s)")
                print()
                
                # Check line items for LLM success indicators
                print("=" * 80)
                print("📦 LINE ITEMS")
                print("=" * 80)
                print()
                
                has_real_items = False
                has_unknown_items = False
                
                for idx, item in enumerate(line_items, 1):
                    description = item.get("description", item.get("desc", ""))
                    qty = item.get("qty", item.get("quantity", 0))
                    price = item.get("unit_price", item.get("price", 0))
                    total = item.get("total", item.get("line_total", 0))
                    
                    print(f"{idx}. {description}")
                    print(f"   Qty: {qty}, Price: {price}, Total: {total}")
                    print()
                    
                    # Check for real items vs unknown
                    desc_lower = description.lower()
                    if "unknown" in desc_lower or desc_lower.strip() == "":
                        has_unknown_items = True
                    else:
                        has_real_items = True
                
                # Final verdict
                print("=" * 80)
                print("🏆 VERDICT")
                print("=" * 80)
                print()
                
                if has_real_items and not has_unknown_items:
                    print("✅ SUCCESS: LLM WORKED!")
                    print()
                    print("The pipeline extracted real product names.")
                    print("Examples found:")
                    for item in line_items[:3]:
                        desc = item.get("description", item.get("desc", ""))
                        if desc and "unknown" not in desc.lower():
                            print(f"  - {desc}")
                    print()
                    print("🎉 The AI Invoice Engine is working!")
                elif has_unknown_items:
                    print("❌ FAILURE: Still using Geometric/Regex extraction")
                    print()
                    print("The pipeline is still returning 'Unknown Item' data.")
                    print("This means LLM extraction did not trigger or failed.")
                else:
                    print("⚠️  UNCLEAR: No clear indicators found")
                
                print()
                print("=" * 80)
                return
        
        # If status endpoint doesn't have data, try invoices endpoint
        print("Status endpoint has no data yet, checking invoices endpoint...")
        print()
    
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print("⚠️  Document not found in status endpoint (may still be processing)")
            print()
        else:
            print(f"⚠️  Status endpoint error: {e.response.status_code}")
            print()
    
    # Fetch invoices from API
    invoices_url = f"{api_url}/api/invoices"
    print(f"📡 Fetching invoices from: {invoices_url}")
    print()
    
    try:
        response = requests.get(invoices_url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Handle different response formats
        if isinstance(data, dict):
            invoices = data.get("invoices", data.get("data", []))
        elif isinstance(data, list):
            invoices = data
        else:
            print(f"❌ Unexpected response format: {type(data)}")
            print(f"Response: {json.dumps(data, indent=2)}")
            sys.exit(1)
        
        print(f"✓ Found {len(invoices)} invoice(s) in database")
        print()
        
        # Find our invoice
        target_invoice = None
        for inv in invoices:
            # Check by doc_id or id
            if inv.get("doc_id") == doc_id or inv.get("id") == doc_id:
                target_invoice = inv
                break
            # Also check filename for _Fresh_
            filename = inv.get("filename", inv.get("sourceFilename", ""))
            if "_Fresh_" in filename:
                target_invoice = inv
                doc_id = inv.get("doc_id") or inv.get("id")
                break
        
        if not target_invoice:
            print(f"❌ Invoice with doc_id '{doc_id}' not found in results")
            print()
            print("Available invoices:")
            for inv in invoices[:5]:  # Show first 5
                inv_id = inv.get("doc_id") or inv.get("id", "N/A")
                filename = inv.get("filename", inv.get("sourceFilename", "N/A"))
                print(f"  - {inv_id}: {filename}")
            if len(invoices) > 5:
                print(f"  ... and {len(invoices) - 5} more")
            sys.exit(1)
        
        print("=" * 80)
        print("📋 INVOICE FOUND")
        print("=" * 80)
        print()
        print(f"Doc ID:     {target_invoice.get('doc_id') or target_invoice.get('id', 'N/A')}")
        print(f"Supplier:   {target_invoice.get('supplier', 'N/A')}")
        print(f"Date:       {target_invoice.get('date', 'N/A')}")
        print(f"Total:      {target_invoice.get('value', target_invoice.get('total', 'N/A'))}")
        print(f"Status:     {target_invoice.get('status', 'N/A')}")
        print()
        
        # Fetch line items
        invoice_id = target_invoice.get("id") or target_invoice.get("doc_id")
        line_items_url = f"{api_url}/api/invoices/{invoice_id}/line-items"
        
        print(f"📦 Fetching line items from: {line_items_url}")
        print()
        
        try:
            items_response = requests.get(line_items_url, timeout=10)
            items_response.raise_for_status()
            items_data = items_response.json()
            
            # Handle different response formats
            if isinstance(items_data, dict):
                line_items = items_data.get("line_items", items_data.get("items", items_data.get("data", [])))
            elif isinstance(items_data, list):
                line_items = items_data
            else:
                line_items = []
            
            print(f"✓ Found {len(line_items)} line item(s)")
            print()
            
            if not line_items:
                print("=" * 80)
                print("⚠️  NO LINE ITEMS FOUND")
                print("=" * 80)
                print()
                print("This could mean:")
                print("  1. Processing is still in progress")
                print("  2. No line items were extracted")
                print("  3. Line items endpoint returned empty")
                print()
                print("Check the invoice status and try again in a few seconds.")
                return
            
            # Check line items for LLM success indicators
            print("=" * 80)
            print("📦 LINE ITEMS")
            print("=" * 80)
            print()
            
            has_real_items = False
            has_unknown_items = False
            
            for idx, item in enumerate(line_items, 1):
                description = item.get("description", item.get("desc", ""))
                qty = item.get("qty", item.get("quantity", 0))
                price = item.get("unit_price", item.get("price", 0))
                total = item.get("total", item.get("line_total", 0))
                
                print(f"{idx}. {description}")
                print(f"   Qty: {qty}, Price: {price}, Total: {total}")
                print()
                
                # Check for real items vs unknown
                desc_lower = description.lower()
                if "unknown" in desc_lower or desc_lower.strip() == "":
                    has_unknown_items = True
                else:
                    has_real_items = True
            
            # Final verdict
            print("=" * 80)
            print("🏆 VERDICT")
            print("=" * 80)
            print()
            
            if has_real_items and not has_unknown_items:
                print("✅ SUCCESS: LLM WORKED!")
                print()
                print("The pipeline extracted real product names.")
                print("Examples found:")
                for item in line_items[:3]:
                    desc = item.get("description", item.get("desc", ""))
                    if desc and "unknown" not in desc.lower():
                        print(f"  - {desc}")
                print()
                print("🎉 The AI Invoice Engine is working!")
            elif has_unknown_items:
                print("❌ FAILURE: Still using Geometric/Regex extraction")
                print()
                print("The pipeline is still returning 'Unknown Item' data.")
                print("This means LLM extraction did not trigger or failed.")
                print()
                print("Next steps:")
                print("  1. Check backend logs for LLM errors")
                print("  2. Verify FEATURE_LLM_EXTRACTION is enabled")
                print("  3. Check Ollama is running and accessible")
            else:
                print("⚠️  UNCLEAR: No clear indicators found")
                print()
                print("Line items exist but don't show clear LLM vs geometric patterns.")
                print("Check the descriptions manually to verify.")
            
            print()
            print("=" * 80)
            
        except requests.exceptions.HTTPError as e:
            print(f"❌ HTTP Error fetching line items: {e.response.status_code}")
            print(f"Response: {e.response.text}")
            print()
            print("Trying alternative endpoint...")
            
            # Try getting full invoice details
            detail_url = f"{api_url}/api/invoices/{invoice_id}"
            try:
                detail_response = requests.get(detail_url, timeout=10)
                detail_response.raise_for_status()
                detail_data = detail_response.json()
                
                # Check if line items are in the detail response
                if "line_items" in detail_data or "lineItems" in detail_data:
                    line_items = detail_data.get("line_items") or detail_data.get("lineItems", [])
                    print(f"✓ Found {len(line_items)} line item(s) in detail response")
                    # Re-run the check logic
                    # (This is a simplified version - you could refactor to avoid duplication)
            except:
                pass
        
    except requests.exceptions.ConnectionError:
        print("❌ CONNECTION ERROR")
        print()
        print(f"Could not connect to: {api_url}")
        print()
        print("Make sure the backend is running:")
        print(f"  - Check: {api_url}/api/health")
        sys.exit(1)
        
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP ERROR: {e.response.status_code}")
        print(f"Response: {e.response.text}")
        sys.exit(1)
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def main():
    """Main entry point."""
    doc_id = None
    if len(sys.argv) > 1:
        doc_id = sys.argv[1]
    
    check_invoice_result(doc_id)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled by user")
        sys.exit(1)

