#!/usr/bin/env python3
"""
Engine Performance Benchmark

Benchmarks the normalization, solver, and verdicts pipeline.
"""

import sys
import os
import time
import json
import logging
from pathlib import Path
from typing import Dict, Any, List
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.normalization.units import canonical_quantities
from backend.engine.discount_solver import get_discount_solver
from backend.engine.verdicts import get_verdict_engine, VerdictContext
from backend.engine.line_fingerprint import get_line_fingerprint

logger = logging.getLogger(__name__)

def generate_test_invoice(lines: int = 300) -> Dict[str, Any]:
    """Generate test invoice with specified number of lines"""
    invoice = {
        "id": 1,
        "supplier_id": "TEST_SUPPLIER",
        "invoice_date": "2024-01-15",
        "total_amount": 0.0,
        "lines": []
    }
    
    # Generate line items
    for i in range(lines):
        qty = (i % 10) + 1
        unit_price = 1.0 + (i % 50) * 0.1
        line_total = qty * unit_price
        invoice["total_amount"] += line_total
        
        line = {
            "id": i + 1,
            "sku_id": f"SKU_{i:03d}",
            "description": f"Product {i} - {qty}x330ml cans",
            "quantity": qty,
            "unit_price": unit_price,
            "line_total": line_total,
            "uom_key": "volume_ml",
            "date": "2024-01-15",
            "supplier_id": "TEST_SUPPLIER",
            "ruleset_id": 1
        }
        invoice["lines"].append(line)
    
    return invoice

def benchmark_normalization(invoice: Dict[str, Any]) -> float:
    """Benchmark normalization step"""
    start_time = time.time()
    
    try:
        for line in invoice["lines"]:
            # Normalize quantities
            canonical = canonical_quantities(line["quantity"], line["description"])
            
            # Update line with canonical data
            line.update(canonical)
        
        end_time = time.time()
        return end_time - start_time
        
    except Exception as e:
        logger.error(f"❌ Normalization benchmark failed: {e}")
        return float('inf')

def benchmark_discount_solver(invoice: Dict[str, Any]) -> float:
    """Benchmark discount solver step"""
    start_time = time.time()
    
    try:
        solver = get_discount_solver()
        
        for line in invoice["lines"]:
            # Solve for discount
            result = solver.solve_discount(
                qty=line["quantity"],
                unit_price=line["unit_price"],
                nett_value=line["line_total"],
                canonical_quantities=line
            )
            
            # Store result
            line["discount_result"] = result
        
        end_time = time.time()
        return end_time - start_time
        
    except Exception as e:
        logger.error(f"❌ Discount solver benchmark failed: {e}")
        return float('inf')

def benchmark_verdicts(invoice: Dict[str, Any]) -> float:
    """Benchmark verdict assignment step"""
    start_time = time.time()
    
    try:
        verdict_engine = get_verdict_engine()
        
        for line in invoice["lines"]:
            # Create context
            context = VerdictContext(
                price_incoherent=False,
                vat_mismatch=False,
                pack_mismatch=False,
                ocr_low_conf=False,
                off_contract_discount=line.get("discount_result") is not None
            )
            
            # Assign verdict
            verdict = verdict_engine.assign_verdict(context)
            line["verdict"] = verdict.value
        
        end_time = time.time()
        return end_time - start_time
        
    except Exception as e:
        logger.error(f"❌ Verdicts benchmark failed: {e}")
        return float('inf')

def benchmark_line_fingerprints(invoice: Dict[str, Any]) -> float:
    """Benchmark line fingerprint computation"""
    start_time = time.time()
    
    try:
        fingerprint_engine = get_line_fingerprint()
        
        for line in invoice["lines"]:
            # Compute fingerprint
            fingerprint = fingerprint_engine.compute_fingerprint(line)
            line["fingerprint"] = fingerprint
        
        end_time = time.time()
        return end_time - start_time
        
    except Exception as e:
        logger.error(f"❌ Line fingerprint benchmark failed: {e}")
        return float('inf')

def run_full_pipeline_benchmark(lines: int = 300) -> Dict[str, Any]:
    """Run full pipeline benchmark"""
    print(f"🚀 Starting benchmark with {lines} lines...")
    
    # Generate test invoice
    invoice = generate_test_invoice(lines)
    
    # Run benchmarks
    results = {
        "lines": lines,
        "timestamp": time.time(),
        "stages": {}
    }
    
    # Stage 1: Normalization
    print("📊 Benchmarking normalization...")
    norm_time = benchmark_normalization(invoice)
    results["stages"]["normalization"] = {
        "time_seconds": norm_time,
        "lines_per_second": lines / norm_time if norm_time > 0 else 0
    }
    
    # Stage 2: Discount Solver
    print("💰 Benchmarking discount solver...")
    solver_time = benchmark_discount_solver(invoice)
    results["stages"]["discount_solver"] = {
        "time_seconds": solver_time,
        "lines_per_second": lines / solver_time if solver_time > 0 else 0
    }
    
    # Stage 3: Verdicts
    print("⚖️ Benchmarking verdicts...")
    verdict_time = benchmark_verdicts(invoice)
    results["stages"]["verdicts"] = {
        "time_seconds": verdict_time,
        "lines_per_second": lines / verdict_time if verdict_time > 0 else 0
    }
    
    # Stage 4: Line Fingerprints
    print("🔍 Benchmarking line fingerprints...")
    fingerprint_time = benchmark_line_fingerprints(invoice)
    results["stages"]["line_fingerprints"] = {
        "time_seconds": fingerprint_time,
        "lines_per_second": lines / fingerprint_time if fingerprint_time > 0 else 0
    }
    
    # Calculate totals
    total_time = norm_time + solver_time + verdict_time + fingerprint_time
    results["total"] = {
        "time_seconds": total_time,
        "lines_per_second": lines / total_time if total_time > 0 else 0
    }
    
    # Performance assessment
    results["performance"] = {
        "meets_target": total_time <= 2.0,
        "target_seconds": 2.0,
        "actual_seconds": total_time,
        "performance_ratio": total_time / 2.0
    }
    
    return results

def print_benchmark_results(results: Dict[str, Any]):
    """Print formatted benchmark results"""
    print("\n" + "="*60)
    print("📈 BENCHMARK RESULTS")
    print("="*60)
    
    print(f"Lines processed: {results['lines']}")
    print(f"Total time: {results['total']['time_seconds']:.3f}s")
    print(f"Lines per second: {results['total']['lines_per_second']:.1f}")
    
    print("\nStage breakdown:")
    for stage, data in results["stages"].items():
        print(f"  {stage:20} {data['time_seconds']:6.3f}s ({data['lines_per_second']:6.1f} l/s)")
    
    print("\nPerformance assessment:")
    perf = results["performance"]
    status = "✅ PASS" if perf["meets_target"] else "❌ FAIL"
    print(f"  Target: {perf['target_seconds']}s")
    print(f"  Actual: {perf['actual_seconds']:.3f}s")
    print(f"  Status: {status}")
    print(f"  Ratio: {perf['performance_ratio']:.2f}x target")
    
    print("="*60)

def save_benchmark_results(results: Dict[str, Any], output_file: str = "benchmark_results.json"):
    """Save benchmark results to file"""
    try:
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"💾 Results saved to {output_file}")
    except Exception as e:
        logger.error(f"❌ Failed to save results: {e}")

def main():
    """Main benchmark function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Engine Performance Benchmark")
    parser.add_argument("--lines", type=int, default=300, 
                       help="Number of lines to process (default: 300)")
    parser.add_argument("--output", type=str, default="benchmark_results.json",
                       help="Output file for results (default: benchmark_results.json)")
    parser.add_argument("--iterations", type=int, default=1,
                       help="Number of iterations to run (default: 1)")
    
    args = parser.parse_args()
    
    print(f"🔧 Engine Performance Benchmark")
    print(f"📊 Lines: {args.lines}")
    print(f"🔄 Iterations: {args.iterations}")
    print(f"💾 Output: {args.output}")
    
    all_results = []
    
    for i in range(args.iterations):
        print(f"\n🔄 Iteration {i+1}/{args.iterations}")
        results = run_full_pipeline_benchmark(args.lines)
        all_results.append(results)
        print_benchmark_results(results)
    
    # Aggregate results if multiple iterations
    if args.iterations > 1:
        avg_total_time = sum(r["total"]["time_seconds"] for r in all_results) / args.iterations
        avg_lines_per_sec = sum(r["total"]["lines_per_second"] for r in all_results) / args.iterations
        
        print(f"\n📊 AVERAGE RESULTS ({args.iterations} iterations):")
        print(f"  Average time: {avg_total_time:.3f}s")
        print(f"  Average lines/sec: {avg_lines_per_sec:.1f}")
        print(f"  Meets target: {avg_total_time <= 2.0}")
    
    # Save results
    save_benchmark_results(all_results[0] if args.iterations == 1 else {
        "iterations": all_results,
        "summary": {
            "avg_total_time": avg_total_time,
            "avg_lines_per_second": avg_lines_per_sec,
            "meets_target": avg_total_time <= 2.0
        }
    }, args.output)
    
    # Exit with appropriate code
    final_time = all_results[-1]["total"]["time_seconds"]
    if final_time <= 2.0:
        print("✅ Benchmark PASSED - meets performance target")
        sys.exit(0)
    else:
        print("❌ Benchmark FAILED - exceeds performance target")
        sys.exit(1)

if __name__ == "__main__":
    main() 