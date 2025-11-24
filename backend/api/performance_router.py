#!/usr/bin/env python3
"""
Performance API Router

Provides endpoints for accessing performance benchmark results
and system performance metrics.
"""

import os
import json
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pathlib import Path
from backend.performance.timing import BenchmarkLogger
from backend.performance.regression import PerformanceRegressionDetector

router = APIRouter(prefix="/api/system", tags=["performance"])


@router.get("/perf_summary")
def get_performance_summary() -> Dict[str, Any]:
    """
    Get performance summary from the latest benchmark run.
    
    Returns:
        Dict containing performance metrics and summary statistics
    """
    try:
        # Initialize benchmark logger
        benchmark_logger = BenchmarkLogger()
        
        # Get latest benchmark results
        latest_benchmark = benchmark_logger.get_latest_benchmark()
        
        if not latest_benchmark:
            return {
                "timestamp": None,
                "documents": 0,
                "avg_total_time": 0.0,
                "avg_ocr_time": 0.0,
                "avg_llm_time": 0.0,
                "avg_memory_mb": None,
                "status": "no_benchmarks_found"
            }
        
        # Extract summary data
        summary = latest_benchmark.get("summary", {})
        
        # Build response
        response = {
            "timestamp": latest_benchmark.get("timestamp"),
            "documents": summary.get("documents", 0),
            "success_rate": summary.get("success_rate", 0.0),
            "avg_total_time": summary.get("avg_total_time", 0.0),
            "avg_ocr_time": summary.get("avg_ocr_time", 0.0),
            "avg_llm_time": summary.get("avg_llm_time", 0.0),
            "avg_memory_mb": summary.get("avg_memory_mb"),
            "max_total_time": summary.get("max_total_time", 0.0),
            "min_total_time": summary.get("min_total_time", 0.0),
            "total_benchmark_time": summary.get("total_benchmark_time", 0.0),
            "feature_flags": latest_benchmark.get("feature_flags", {}),
            "status": "success"
        }
        
        # Add stage-specific metrics
        stage_metrics = {}
        for stage in ["layout_segmentation", "paddle_ocr", "table_extraction", 
                     "htr_processing", "donut_fallback", "llm_processing", 
                     "template_matching", "db_write"]:
            key = f"avg_{stage}_time"
            if key in summary:
                stage_metrics[stage] = summary[key]
        
        response["stage_metrics"] = stage_metrics
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to get performance summary: {str(e)}"
        )


@router.get("/perf_history")
def get_performance_history(limit: int = 10) -> Dict[str, Any]:
    """
    Get performance benchmark history.
    
    Args:
        limit: Maximum number of benchmark runs to return
        
    Returns:
        Dict containing benchmark history
    """
    try:
        benchmark_logger = BenchmarkLogger()
        benchmark_dir = benchmark_logger.benchmark_dir
        
        # Get all benchmark files
        benchmark_files = []
        if os.path.exists(benchmark_dir):
            for filename in os.listdir(benchmark_dir):
                if filename.startswith("benchmark_run_") and filename.endswith(".json"):
                    filepath = os.path.join(benchmark_dir, filename)
                    try:
                        with open(filepath, 'r') as f:
                            data = json.load(f)
                        benchmark_files.append({
                            "filename": filename,
                            "timestamp": data.get("timestamp"),
                            "documents": data.get("summary", {}).get("documents", 0),
                            "avg_total_time": data.get("summary", {}).get("avg_total_time", 0.0),
                            "success_rate": data.get("summary", {}).get("success_rate", 0.0)
                        })
                    except (json.JSONDecodeError, OSError):
                        continue
        
        # Sort by timestamp (newest first)
        benchmark_files.sort(key=lambda x: x["timestamp"] or "", reverse=True)
        
        # Limit results
        benchmark_files = benchmark_files[:limit]
        
        return {
            "benchmarks": benchmark_files,
            "total_benchmarks": len(benchmark_files),
            "status": "success"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get performance history: {str(e)}"
        )


@router.get("/perf_benchmark/{benchmark_id}")
def get_benchmark_details(benchmark_id: str) -> Dict[str, Any]:
    """
    Get detailed results for a specific benchmark run.
    
    Args:
        benchmark_id: Benchmark filename (without .json extension)
        
    Returns:
        Dict containing detailed benchmark results
    """
    try:
        benchmark_logger = BenchmarkLogger()
        benchmark_dir = benchmark_logger.benchmark_dir
        
        # Construct filepath
        filename = f"{benchmark_id}.json"
        filepath = os.path.join(benchmark_dir, filename)
        
        if not os.path.exists(filepath):
            raise HTTPException(
                status_code=404,
                detail=f"Benchmark {benchmark_id} not found"
            )
        
        # Load benchmark data
        with open(filepath, 'r') as f:
            benchmark_data = json.load(f)
        
        return {
            "benchmark_id": benchmark_id,
            "data": benchmark_data,
            "status": "success"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get benchmark details: {str(e)}"
        )


@router.get("/perf_status")
def get_performance_status() -> Dict[str, Any]:
    """
    Get current performance system status.
    
    Returns:
        Dict containing system status information
    """
    try:
        benchmark_logger = BenchmarkLogger()
        
        # Check if benchmark directory exists and is writable
        benchmark_dir = benchmark_logger.benchmark_dir
        dir_exists = os.path.exists(benchmark_dir)
        dir_writable = os.access(benchmark_dir, os.W_OK) if dir_exists else False
        
        # Get latest benchmark info
        latest_benchmark = benchmark_logger.get_latest_benchmark()
        
        # Count total benchmarks
        total_benchmarks = 0
        if dir_exists:
            benchmark_files = [
                f for f in os.listdir(benchmark_dir)
                if f.startswith("benchmark_run_") and f.endswith(".json")
            ]
            total_benchmarks = len(benchmark_files)
        
        return {
            "benchmark_directory": benchmark_dir,
            "directory_exists": dir_exists,
            "directory_writable": dir_writable,
            "total_benchmarks": total_benchmarks,
            "latest_benchmark": latest_benchmark.get("timestamp") if latest_benchmark else None,
            "status": "operational" if dir_exists and dir_writable else "error"
        }
        
    except Exception as e:
        return {
            "benchmark_directory": "data/benchmarks",
            "directory_exists": False,
            "directory_writable": False,
            "total_benchmarks": 0,
            "latest_benchmark": None,
            "status": "error",
            "error": str(e)
        }


@router.get("/perf_history")
def get_performance_history(limit: int = 50) -> Dict[str, Any]:
    """
    Get performance benchmark history from rolling history file.
    
    Args:
        limit: Maximum number of history entries to return
        
    Returns:
        Dict containing benchmark history
    """
    try:
        benchmark_logger = BenchmarkLogger()
        benchmark_dir = benchmark_logger.benchmark_dir
        history_file = os.path.join(benchmark_dir, "history.jsonl")
        
        if not os.path.exists(history_file):
            return {
                "entries": [],
                "total_entries": 0,
                "status": "no_history",
                "message": "No benchmark history found"
            }
        
        # Read history entries
        entries = []
        with open(history_file, 'r') as f:
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
            "limit": limit,
            "status": "success"
        }
        
    except Exception as e:
        return {
            "entries": [],
            "total_entries": 0,
            "status": "error",
            "error": str(e)
        }


@router.get("/perf_alerts")
def get_performance_alerts() -> Dict[str, Any]:
    """
    Get performance alerts by comparing latest benchmark to baseline.
    
    Returns:
        Dict containing performance alerts and regression information
    """
    try:
        detector = PerformanceRegressionDetector()
        result = detector.run_regression_check()
        
        # Format alerts for API response
        alerts = []
        for alert in result.get("alerts", []):
            alerts.append({
                "metric": alert["metric"],
                "metric_name": alert["metric_name"],
                "message": alert["message"],
                "severity": alert["severity"],
                "change_pct": alert["change_pct"],
                "baseline_value": alert["baseline_value"],
                "current_value": alert["current_value"]
            })
        
        return {
            "alerts": alerts,
            "status": result["status"],
            "message": result["message"],
            "baseline_exists": result.get("baseline_exists", False),
            "regression_count": len(alerts)
        }
        
    except Exception as e:
        return {
            "alerts": [],
            "status": "error",
            "message": f"Failed to check performance alerts: {str(e)}",
            "baseline_exists": False,
            "regression_count": 0
        }


