#!/usr/bin/env python3
"""
Performance Timing Utilities for Owlin AI Pipeline

Provides decorators and context managers for measuring execution time
and memory usage across different pipeline stages.
"""

import time
import functools
import psutil
import os
from typing import Dict, Any, Optional, Callable
from contextlib import contextmanager
import json
from datetime import datetime


class PerformanceTimer:
    """Context manager for timing operations with memory tracking."""
    
    def __init__(self, stage_name: str, metrics: Dict[str, Any]):
        self.stage_name = stage_name
        self.metrics = metrics
        self.start_time = None
        self.start_memory = None
        
    def __enter__(self):
        self.start_time = time.perf_counter()
        try:
            process = psutil.Process(os.getpid())
            self.start_memory = process.memory_info().rss / 1024 / 1024  # MB
        except (ImportError, AttributeError, OSError):
            self.start_memory = None
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        end_time = time.perf_counter()
        duration = round(end_time - self.start_time, 3)
        
        # Record timing
        self.metrics[f"{self.stage_name}_time"] = duration
        
        # Record memory if available
        if self.start_memory is not None:
            try:
                process = psutil.Process(os.getpid())
                end_memory = process.memory_info().rss / 1024 / 1024  # MB
                memory_delta = round(end_memory - self.start_memory, 2)
                self.metrics[f"{self.stage_name}_memory_mb"] = memory_delta
            except (ImportError, AttributeError, OSError):
                self.metrics[f"{self.stage_name}_memory_mb"] = None


def time_stage(stage_name: str):
    """Decorator for timing function execution."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Try to get metrics from first argument if it's a dict
            metrics = {}
            if args and isinstance(args[0], dict):
                metrics = args[0]
            elif 'metrics' in kwargs:
                metrics = kwargs['metrics']
            
            with PerformanceTimer(stage_name, metrics):
                return func(*args, **kwargs)
        return wrapper
    return decorator


@contextmanager
def time_operation(stage_name: str, metrics: Dict[str, Any]):
    """Context manager for timing operations."""
    with PerformanceTimer(stage_name, metrics):
        yield


class BenchmarkLogger:
    """Handles benchmark result logging and storage."""
    
    def __init__(self, benchmark_dir: str = "data/benchmarks"):
        self.benchmark_dir = benchmark_dir
        self.ensure_benchmark_dir()
        
    def ensure_benchmark_dir(self):
        """Create benchmark directory if it doesn't exist."""
        os.makedirs(self.benchmark_dir, exist_ok=True)
        
    def log_benchmark_run(self, results: Dict[str, Any]) -> str:
        """Log benchmark results to JSON file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"benchmark_run_{timestamp}.json"
        filepath = os.path.join(self.benchmark_dir, filename)
        
        # Add metadata
        results["timestamp"] = datetime.now().isoformat() + "Z"
        results["benchmark_version"] = "1.0"
        
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2)
            
        return filepath
        
    def get_latest_benchmark(self) -> Optional[Dict[str, Any]]:
        """Get the most recent benchmark results."""
        try:
            benchmark_files = [
                f for f in os.listdir(self.benchmark_dir) 
                if f.startswith("benchmark_run_") and f.endswith(".json")
            ]
            
            if not benchmark_files:
                return None
                
            # Sort by filename (timestamp)
            latest_file = sorted(benchmark_files)[-1]
            filepath = os.path.join(self.benchmark_dir, latest_file)
            
            with open(filepath, 'r') as f:
                return json.load(f)
                
        except (OSError, json.JSONDecodeError):
            return None


def get_safe_memory_usage() -> Optional[float]:
    """Get current memory usage in MB, with safe fallback."""
    try:
        process = psutil.Process(os.getpid())
        return round(process.memory_info().rss / 1024 / 1024, 2)
    except (ImportError, AttributeError, OSError):
        return None


def format_duration(seconds: float) -> str:
    """Format duration for human readability."""
    if seconds < 1:
        return f"{seconds*1000:.1f}ms"
    elif seconds < 60:
        return f"{seconds:.2f}s"
    else:
        minutes = int(seconds // 60)
        remaining = seconds % 60
        return f"{minutes}m {remaining:.1f}s"
