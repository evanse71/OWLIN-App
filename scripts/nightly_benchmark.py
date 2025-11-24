#!/usr/bin/env python3
"""
Nightly Benchmark Automation

Runs performance benchmarks and updates rolling history.
Designed for automated execution without manual intervention.
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.performance_benchmark import PerformanceBenchmark
from backend.performance.regression import PerformanceRegressionDetector


class NightlyBenchmarkRunner:
    """Handles nightly benchmark execution and history management."""
    
    def __init__(self, benchmark_dir: str = "data/benchmarks"):
        self.benchmark_dir = benchmark_dir
        self.history_file = os.path.join(benchmark_dir, "history.jsonl")
        self.update_baseline = os.getenv("OWLIN_PERF_UPDATE_BASELINE", "false").lower() == "true"
        
        # Ensure benchmark directory exists
        os.makedirs(benchmark_dir, exist_ok=True)
    
    def append_to_history(self, benchmark_result: dict):
        """Append benchmark result to rolling history."""
        try:
            # Create history entry
            history_entry = {
                "timestamp": datetime.now().isoformat() + "Z",
                "documents": benchmark_result.get("summary", {}).get("documents", 0),
                "avg_total_time": benchmark_result.get("summary", {}).get("avg_total_time", 0.0),
                "avg_ocr_time": benchmark_result.get("summary", {}).get("avg_ocr_time", 0.0),
                "avg_llm_time": benchmark_result.get("summary", {}).get("avg_llm_time", 0.0),
                "avg_memory_mb": benchmark_result.get("summary", {}).get("avg_memory_mb", 0.0),
                "success_rate": benchmark_result.get("summary", {}).get("success_rate", 0.0),
                "total_benchmark_time": benchmark_result.get("summary", {}).get("total_benchmark_time", 0.0),
                "feature_flags": benchmark_result.get("feature_flags", {}),
                "benchmark_file": benchmark_result.get("benchmark_file", "")
            }
            
            # Append to history file
            with open(self.history_file, 'a') as f:
                f.write(json.dumps(history_entry) + '\n')
            
            return True
            
        except Exception as e:
            print(f"Failed to append to history: {e}")
            return False
    
    def run_nightly_benchmark(self, n: int = 10) -> dict:
        """Run nightly benchmark and update history."""
        print(f"Running nightly benchmark with {n} documents...")
        
        try:
            # Run benchmark
            benchmark = PerformanceBenchmark(benchmark_dir=self.benchmark_dir)
            benchmark_file = benchmark.run_benchmark(n)
            
            if not benchmark_file:
                return {
                    "success": False,
                    "error": "Benchmark failed to complete",
                    "benchmark_file": None
                }
            
            # Load benchmark results
            with open(benchmark_file, 'r') as f:
                benchmark_result = json.load(f)
            
            # Add benchmark file path to result
            benchmark_result["benchmark_file"] = benchmark_file
            
            # Append to history
            history_success = self.append_to_history(benchmark_result)
            
            # Update baseline if requested
            baseline_updated = False
            if self.update_baseline:
                detector = PerformanceRegressionDetector(self.benchmark_dir)
                baseline_updated = detector.create_baseline_from_latest()
                if baseline_updated:
                    print("Baseline updated from latest benchmark")
            
            # Run regression check
            detector = PerformanceRegressionDetector(self.benchmark_dir)
            regression_result = detector.run_regression_check()
            
            return {
                "success": True,
                "benchmark_file": benchmark_file,
                "history_updated": history_success,
                "baseline_updated": baseline_updated,
                "regression_check": regression_result,
                "summary": benchmark_result.get("summary", {})
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "benchmark_file": None
            }
    
    def get_history_summary(self, limit: int = 20) -> dict:
        """Get summary of recent benchmark history."""
        try:
            if not os.path.exists(self.history_file):
                return {
                    "entries": [],
                    "total_entries": 0,
                    "latest_timestamp": None
                }
            
            # Read recent entries
            entries = []
            with open(self.history_file, 'r') as f:
                lines = f.readlines()
            
            # Get last N entries
            recent_lines = lines[-limit:] if len(lines) > limit else lines
            
            for line in recent_lines:
                try:
                    entry = json.loads(line.strip())
                    entries.append(entry)
                except json.JSONDecodeError:
                    continue
            
            return {
                "entries": entries,
                "total_entries": len(lines),
                "latest_timestamp": entries[-1]["timestamp"] if entries else None
            }
            
        except Exception as e:
            return {
                "entries": [],
                "total_entries": 0,
                "latest_timestamp": None,
                "error": str(e)
            }


def main():
    """Main nightly benchmark function."""
    parser = argparse.ArgumentParser(description="Nightly Performance Benchmark")
    parser.add_argument("--n", type=int, default=10, help="Number of documents to benchmark")
    parser.add_argument("--benchmark-dir", type=str, default="data/benchmarks", help="Benchmark directory")
    parser.add_argument("--update-baseline", action="store_true", help="Update baseline from latest benchmark")
    parser.add_argument("--history-only", action="store_true", help="Only show history summary")
    
    args = parser.parse_args()
    
    # Set environment variable if requested
    if args.update_baseline:
        os.environ["OWLIN_PERF_UPDATE_BASELINE"] = "true"
    
    runner = NightlyBenchmarkRunner(args.benchmark_dir)
    
    if args.history_only:
        # Show history summary
        summary = runner.get_history_summary()
        print(f"History entries: {summary['total_entries']}")
        if summary['latest_timestamp']:
            print(f"Latest run: {summary['latest_timestamp']}")
        return 0
    
    # Run nightly benchmark
    result = runner.run_nightly_benchmark(args.n)
    
    if result["success"]:
        print("Nightly benchmark completed successfully")
        print(f"Benchmark file: {result['benchmark_file']}")
        print(f"History updated: {result['history_updated']}")
        print(f"Baseline updated: {result['baseline_updated']}")
        
        # Show regression check results
        regression = result.get("regression_check", {})
        if regression.get("alerts"):
            print(f"Performance alerts: {len(regression['alerts'])}")
            for alert in regression["alerts"]:
                print(f"  - {alert['message']}")
        else:
            print("No performance regressions detected")
        
        return 0
    else:
        print(f"Nightly benchmark failed: {result['error']}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
