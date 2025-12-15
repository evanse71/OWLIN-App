#!/usr/bin/env python3
"""Batch OCR Testing Script - Tests multiple invoice files using /api/dev/ocr-test endpoint."""

import argparse
import sys
import time
from pathlib import Path
from typing import List, Dict, Any
import csv

try:
    import requests
except ImportError:
    print("ERROR: requests library not installed. Run: pip install requests")
    sys.exit(1)

BASE_URL = "http://localhost:8000"
UPLOADS_DIR = Path("data/uploads")


def get_available_files() -> List[str]:
    """Get list of available image files in uploads directory."""
    if not UPLOADS_DIR.exists():
        return []
    image_extensions = {".jpg", ".jpeg", ".png", ".jpe"}
    files = []
    for ext in image_extensions:
        files.extend([f.name for f in UPLOADS_DIR.glob(f"*{ext}") if f.is_file()])
    return sorted(files)


def test_file(filename: str, timeout: int = 30, base_url: str = None) -> Dict[str, Any]:
    """Test a single file using /api/dev/ocr-test endpoint."""
    if base_url is None:
        base_url = BASE_URL
    url = f"{base_url}/api/dev/ocr-test"
    params = {"filename": filename}
    result = {
        "filename": filename,
        "status": "error",
        "error": None,
        "items_count": 0,
        "confidence": 0.0,
        "processing_time": 0.0,
        "method_chosen": "unknown",
        "table_score": 0.0,
        "fallback_score": 0.0,
        "has_pack_size": False,
        "has_prices": False,
        "parity_rating": "unknown",
        "total_mismatch_pct": None,
        "price_coverage": None,
        "parity_detail": "unknown",
    }
    try:
        start = time.time()
        response = requests.get(url, params=params, timeout=timeout)
        elapsed = time.time() - start
        if response.status_code != 200:
            result["error"] = f"HTTP {response.status_code}: {response.text[:200]}"
            return result
        data = response.json()
        if data.get("status") == "ok":
            result["status"] = "ok"
            result["items_count"] = data.get("line_items_count", 0)
            result["confidence"] = data.get("confidence", 0.0)
            result["processing_time"] = data.get("processing_time", elapsed)
            debug_info = data.get("line_items_debug", [])
            if debug_info and len(debug_info) > 0:
                debug = debug_info[0]
                result["method_chosen"] = debug.get("method_chosen", "unknown")
                result["table_score"] = debug.get("table_score", 0.0)
                result["fallback_score"] = debug.get("fallback_score", 0.0)
            line_items = data.get("line_items", [])
            for item in line_items:
                if item.get("pack_size"):
                    result["has_pack_size"] = True
                if item.get("unit_price") or item.get("total_price"):
                    result["has_prices"] = True
            
            # Extract parity information
            result["parity_rating"] = data.get("parity_rating", "unknown")
            result["total_mismatch_pct"] = data.get("total_mismatch_pct")
            result["price_coverage"] = data.get("price_coverage")
            result["parity_detail"] = data.get("parity_detail", "unknown")
        else:
            result["error"] = data.get("error", "Unknown error")
    except requests.exceptions.Timeout:
        result["error"] = f"Timeout after {timeout}s"
    except requests.exceptions.ConnectionError:
        result["error"] = "Cannot connect to backend. Is it running?"
    except Exception as e:
        result["error"] = f"{type(e).__name__}: {str(e)}"
    return result


def print_summary(results: List[Dict[str, Any]]):
    """Print a summary table of results."""
    print("\n" + "=" * 100)
    print("BATCH OCR TEST SUMMARY")
    print("=" * 100)
    total = len(results)
    successful = sum(1 for r in results if r["status"] == "ok")
    failed = total - successful
    print(f"\nTotal files tested: {total}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    
    # Count by parity rating (do this early so we can display it prominently)
    parity_counts = {"excellent": 0, "good": 0, "ok": 0, "poor": 0, "unknown": 0}
    for r in results:
        if r["status"] == "ok":
            rating = r.get("parity_rating", "unknown")
            # Handle missing or None parity_rating gracefully
            if rating is None:
                rating = "unknown"
            parity_counts[rating] = parity_counts.get(rating, 0) + 1
    
    # Display parity breakdown prominently at the top
    if successful > 0:
        print(f"\nParity Quality Breakdown:")
        print(f"  Excellent (<1% mismatch): {parity_counts['excellent']}")
        print(f"  Good (<3% mismatch):      {parity_counts['good']}")
        print(f"  Ok (<8% mismatch):        {parity_counts['ok']}")
        print(f"  Poor (>=8% mismatch):     {parity_counts['poor']}")
        print(f"  Unknown:                  {parity_counts['unknown']}")
        
        # Extended breakdown: count by parity + coverage
        excellent_high_coverage = 0
        poor_low_coverage = 0
        poor_adequate_coverage = 0
        for r in results:
            if r["status"] == "ok":
                rating = r.get("parity_rating", "unknown")
                coverage = r.get("price_coverage")
                if rating == "excellent" and coverage is not None and coverage >= 0.7:
                    excellent_high_coverage += 1
                elif rating == "poor":
                    if coverage is not None and coverage < 0.3:
                        poor_low_coverage += 1
                    elif coverage is not None and coverage >= 0.3:
                        poor_adequate_coverage += 1
        
        print(f"\nExtended Parity Breakdown:")
        print(f"  Excellent parity + high coverage (>=70%): {excellent_high_coverage}")
        print(f"  Poor parity + low coverage (<30%):        {poor_low_coverage}")
        print(f"  Poor parity + adequate coverage (>=30%):  {poor_adequate_coverage}")
    
    if successful > 0:
        avg_items = sum(r["items_count"] for r in results if r["status"] == "ok") / successful
        avg_confidence = sum(r["confidence"] for r in results if r["status"] == "ok") / successful
        avg_time = sum(r["processing_time"] for r in results if r["status"] == "ok") / successful
        print(f"\nAverage items per file: {avg_items:.1f}")
        print(f"Average confidence: {avg_confidence:.3f}")
        print(f"Average processing time: {avg_time:.2f}s")
    
    print("\n" + "-" * 150)
    print(f"{'Filename':<40} {'Status':<8} {'Items':<7} {'Conf':<7} {'Method':<10} {'Parity':<10} {'Coverage':<10} {'Reason':<25} {'Mismatch%':<10} {'Time':<8}")
    print("-" * 150)
    for r in results:
        status_icon = "✅" if r["status"] == "ok" else "❌"
        filename = r["filename"][:38]
        status = r["status"]
        items = r["items_count"]
        conf = f"{r['confidence']:.3f}" if r["confidence"] > 0 else "N/A"
        method = r["method_chosen"][:8]
        parity = r.get("parity_rating") or "unknown"  # Handle None gracefully
        coverage = r.get("price_coverage")
        if coverage is not None:
            coverage_str = f"{coverage*100:.0f}%"
        else:
            coverage_str = "-"
        parity_detail = r.get("parity_detail", "unknown")
        reason_str = parity_detail[:23] if parity_detail else "-"
        mismatch_pct = r.get("total_mismatch_pct")
        if mismatch_pct is not None:
            mismatch_str = f"{mismatch_pct*100:.1f}%"
        else:
            mismatch_str = "-"
        time_str = f"{r['processing_time']:.2f}s"
        print(f"{filename:<40} {status_icon} {status:<7} {items:<7} {conf:<7} {method:<10} {parity:<10} {coverage_str:<10} {reason_str:<25} {mismatch_str:<10} {time_str:<8}")
    errors = [r for r in results if r["status"] != "ok"]
    if errors:
        print("\n" + "-" * 100)
        print("ERRORS:")
        print("-" * 100)
        for r in errors:
            print(f"  {r['filename']}: {r.get('error', 'Unknown error')}")
    print("\n" + "=" * 100)


def save_csv(results: List[Dict[str, Any]], output_file: str):
    """Save results to CSV file."""
    if not results:
        print("No results to save.")
        return
    fieldnames = [
        "filename", "status", "items_count", "confidence", "processing_time",
        "method_chosen", "table_score", "fallback_score", "has_pack_size", "has_prices",
        "parity_rating", "parity_detail", "price_coverage", "total_mismatch_pct", "error"
    ]
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow({k: r.get(k, "") for k in fieldnames})
    print(f"\nResults saved to: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Batch test OCR extraction on invoice files")
    parser.add_argument("--files", nargs="+", help="Specific files to test")
    parser.add_argument("--all", action="store_true", help="Test all image files in uploads/")
    parser.add_argument("--list", action="store_true", help="List available files and exit")
    parser.add_argument("--output", "-o", help="Save results to CSV file")
    parser.add_argument("--timeout", type=int, default=30, help="Request timeout in seconds")
    parser.add_argument("--url", default=BASE_URL, help=f"Backend URL (default: {BASE_URL})")
    args = parser.parse_args()
    test_url = args.url
    if args.list:
        files = get_available_files()
        print(f"\nAvailable files in {UPLOADS_DIR}:")
        print("-" * 60)
        for f in files:
            print(f"  {f}")
        print(f"\nTotal: {len(files)} files")
        return
    if args.all:
        files = get_available_files()
        if not files:
            print(f"ERROR: No image files found in {UPLOADS_DIR}")
            sys.exit(1)
        print(f"Testing all {len(files)} files...")
    elif args.files:
        files = args.files
    else:
        print("ERROR: Must specify --files, --all, or --list")
        parser.print_help()
        sys.exit(1)
    print(f"\nTesting {len(files)} file(s) against {test_url}...")
    print("=" * 100)
    results = []
    for i, filename in enumerate(files, 1):
        print(f"[{i}/{len(files)}] Testing: {filename}...", end=" ", flush=True)
        result = test_file(filename, timeout=args.timeout, base_url=test_url)
        results.append(result)
        if result["status"] == "ok":
            print(f"✅ {result['items_count']} items, conf={result['confidence']:.3f}, method={result['method_chosen']}")
        else:
            print(f"❌ {result.get('error', 'Unknown error')}")
    print_summary(results)
    if args.output:
        save_csv(results, args.output)


if __name__ == "__main__":
    main()
