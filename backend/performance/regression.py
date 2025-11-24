#!/usr/bin/env python3
"""
Performance Regression Detection

Detects performance regressions by comparing current benchmarks
against established baselines.
"""

import json
import os
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
from backend.performance.timing import BenchmarkLogger


class PerformanceRegressionDetector:
    """Detects performance regressions against baseline metrics."""
    
    def __init__(self, benchmark_dir: str = "data/benchmarks"):
        self.benchmark_dir = benchmark_dir
        self.baseline_file = os.path.join(benchmark_dir, "baseline.json")
        self.regression_threshold = float(os.getenv("OWLIN_PERF_REGRESSION_PCT", "0.20"))
        self.soft_fail = os.getenv("OWLIN_PERF_SOFT_FAIL", "false").lower() == "true"
        
    def get_baseline(self) -> Optional[Dict[str, Any]]:
        """Load baseline performance metrics."""
        try:
            if os.path.exists(self.baseline_file):
                with open(self.baseline_file, 'r') as f:
                    return json.load(f)
        except (OSError, json.JSONDecodeError):
            pass
        return None
    
    def create_baseline_from_latest(self) -> bool:
        """Create baseline from the latest benchmark run."""
        try:
            logger = BenchmarkLogger(self.benchmark_dir)
            latest_benchmark = logger.get_latest_benchmark()
            
            if not latest_benchmark or not latest_benchmark.get("summary"):
                return False
            
            summary = latest_benchmark["summary"]
            baseline = {
                "avg_total_time": summary.get("avg_total_time", 0.0),
                "avg_ocr_time": summary.get("avg_ocr_time", 0.0),
                "avg_llm_time": summary.get("avg_llm_time", 0.0),
                "avg_memory_mb": summary.get("avg_memory_mb", 0.0),
                "success_rate": summary.get("success_rate", 0.0),
                "created_at": datetime.now().isoformat() + "Z",
                "source_benchmark": latest_benchmark.get("timestamp", ""),
                "documents": summary.get("documents", 0)
            }
            
            # Ensure directory exists
            os.makedirs(self.benchmark_dir, exist_ok=True)
            
            with open(self.baseline_file, 'w') as f:
                json.dump(baseline, f, indent=2)
            
            return True
            
        except Exception:
            return False
    
    def check_regression(self, current_benchmark: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for performance regressions against baseline."""
        baseline = self.get_baseline()
        if not baseline:
            return []
        
        summary = current_benchmark.get("summary", {})
        alerts = []
        
        # Check key metrics
        metrics_to_check = [
            ("avg_total_time", "Total Processing Time"),
            ("avg_ocr_time", "OCR Processing Time"),
            ("avg_llm_time", "LLM Processing Time"),
            ("avg_memory_mb", "Memory Usage")
        ]
        
        for metric_key, metric_name in metrics_to_check:
            baseline_value = baseline.get(metric_key, 0.0)
            current_value = summary.get(metric_key, 0.0)
            
            if baseline_value > 0 and current_value > 0:
                # Calculate percentage change
                change_pct = (current_value - baseline_value) / baseline_value
                
                if change_pct > self.regression_threshold:
                    alerts.append({
                        "metric": metric_key,
                        "metric_name": metric_name,
                        "baseline_value": baseline_value,
                        "current_value": current_value,
                        "change_pct": round(change_pct * 100, 1),
                        "severity": "high" if change_pct > 0.5 else "medium",
                        "message": f"{metric_name} up {change_pct*100:.1f}% vs baseline ({baseline_value:.3f}s â†’ {current_value:.3f}s)"
                    })
        
        # Check success rate regression
        baseline_success = baseline.get("success_rate", 1.0)
        current_success = summary.get("success_rate", 1.0)
        
        if current_success < baseline_success - 0.1:  # 10% success rate drop
            alerts.append({
                "metric": "success_rate",
                "metric_name": "Success Rate",
                "baseline_value": baseline_success,
                "current_value": current_success,
                "change_pct": round((current_success - baseline_success) * 100, 1),
                "severity": "high",
                "message": f"Success rate down {abs(current_success - baseline_success)*100:.1f}% vs baseline ({baseline_success:.1%} â†’ {current_success:.1%})"
            })
        
        return alerts
    
    def run_regression_check(self) -> Dict[str, Any]:
        """Run full regression check and return results."""
        try:
            logger = BenchmarkLogger(self.benchmark_dir)
            latest_benchmark = logger.get_latest_benchmark()
            
            if not latest_benchmark:
                return {
                    "status": "no_benchmarks",
                    "message": "No benchmark data found",
                    "alerts": [],
                    "baseline_exists": False
                }
            
            baseline = self.get_baseline()
            if not baseline:
                # Create baseline from latest benchmark
                if self.create_baseline_from_latest():
                    return {
                        "status": "baseline_created",
                        "message": "Baseline created from latest benchmark",
                        "alerts": [],
                        "baseline_exists": True
                    }
                else:
                    return {
                        "status": "baseline_creation_failed",
                        "message": "Failed to create baseline",
                        "alerts": [],
                        "baseline_exists": False
                    }
            
            # Check for regressions
            alerts = self.check_regression(latest_benchmark)
            
            if alerts:
                return {
                    "status": "regressions_detected",
                    "message": f"Found {len(alerts)} performance regression(s)",
                    "alerts": alerts,
                    "baseline_exists": True,
                    "regression_count": len(alerts)
                }
            else:
                return {
                    "status": "no_regressions",
                    "message": "No performance regressions detected",
                    "alerts": [],
                    "baseline_exists": True,
                    "regression_count": 0
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"Regression check failed: {str(e)}",
                "alerts": [],
                "baseline_exists": False,
                "error": str(e)
            }


def test_performance_regression():
    """Pytest-compatible regression test function."""
    detector = PerformanceRegressionDetector()
    result = detector.run_regression_check()
    
    # Handle different statuses
    if result["status"] == "no_benchmarks":
        if detector.soft_fail:
            print(f"WARNING: {result['message']}")
            return
        else:
            raise AssertionError(f"Performance regression check failed: {result['message']}")
    
    elif result["status"] == "baseline_created":
        print(f"INFO: {result['message']}")
        return
    
    elif result["status"] == "baseline_creation_failed":
        if detector.soft_fail:
            print(f"WARNING: {result['message']}")
            return
        else:
            raise AssertionError(f"Performance regression check failed: {result['message']}")
    
    elif result["status"] == "regressions_detected":
        # Format regression messages
        messages = [alert["message"] for alert in result["alerts"]]
        error_msg = f"Performance regressions detected: {'; '.join(messages)}"
        
        if detector.soft_fail:
            print(f"WARNING: {error_msg}")
            return
        else:
            raise AssertionError(error_msg)
    
    elif result["status"] == "no_regressions":
        print(f"INFO: {result['message']}")
        return
    
    elif result["status"] == "error":
        if detector.soft_fail:
            print(f"WARNING: {result['message']}")
            return
        else:
            raise AssertionError(f"Performance regression check failed: {result['message']}")


if __name__ == "__main__":
    # Command-line interface for regression checking
    import sys
    
    detector = PerformanceRegressionDetector()
    result = detector.run_regression_check()
    
    print(f"Status: {result['status']}")
    print(f"Message: {result['message']}")
    
    if result["alerts"]:
        print("\nAlerts:")
        for alert in result["alerts"]:
            print(f"  - {alert['message']}")
    
    # Exit with appropriate code
    if result["status"] in ["regressions_detected", "error"] and not detector.soft_fail:
        sys.exit(1)
    else:
        sys.exit(0)


