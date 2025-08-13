#!/usr/bin/env python3
"""
Performance Monitoring System for Multi-Invoice Detection

This module provides comprehensive performance monitoring, metrics collection,
and optimization insights for the multi-invoice detection system.
"""

import time
import threading
import statistics
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """Performance metrics for multi-invoice detection"""
    operation_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    success: bool = True
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SystemMetrics:
    """System-wide performance metrics"""
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    average_duration_ms: float = 0.0
    median_duration_ms: float = 0.0
    min_duration_ms: float = float('inf')
    max_duration_ms: float = 0.0
    throughput_ops_per_second: float = 0.0
    error_rate: float = 0.0
    last_updated: datetime = field(default_factory=datetime.now)

class PerformanceMonitor:
    """Comprehensive performance monitoring system"""
    
    def __init__(self, metrics_dir: str = "metrics", max_metrics: int = 10000):
        self.metrics_dir = Path(metrics_dir)
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        self.max_metrics = max_metrics
        self.metrics: List[PerformanceMetrics] = []
        self.system_metrics = SystemMetrics()
        self._lock = threading.Lock()
        self._start_time = datetime.now()
        
        # Performance thresholds
        self.thresholds = {
            "slow_operation_ms": 5000,  # 5 seconds
            "error_rate_threshold": 0.1,  # 10%
            "throughput_threshold": 10,  # 10 ops/second
        }
    
    def start_operation(self, operation_name: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Start timing an operation"""
        operation_id = f"{operation_name}_{int(time.time() * 1000)}"
        
        metric = PerformanceMetrics(
            operation_name=operation_name,
            start_time=datetime.now(),
            metadata=metadata or {}
        )
        
        with self._lock:
            self.metrics.append(metric)
            if len(self.metrics) > self.max_metrics:
                self.metrics.pop(0)  # Remove oldest metric
        
        return operation_id
    
    def end_operation(self, operation_id: str, success: bool = True, 
                     error_message: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> None:
        """End timing an operation"""
        with self._lock:
            # Find the metric by operation_id (simplified - in real implementation, you'd store the ID)
            for metric in reversed(self.metrics):
                if metric.operation_name in operation_id and metric.end_time is None:
                    metric.end_time = datetime.now()
                    metric.duration_ms = (metric.end_time - metric.start_time).total_seconds() * 1000
                    metric.success = success
                    metric.error_message = error_message
                    if metadata:
                        metric.metadata.update(metadata)
                    break
        
        # Update system metrics
        self._update_system_metrics()
    
    def _update_system_metrics(self) -> None:
        """Update system-wide metrics"""
        with self._lock:
            completed_metrics = [m for m in self.metrics if m.end_time is not None]
            
            if not completed_metrics:
                return
            
            self.system_metrics.total_operations = len(completed_metrics)
            self.system_metrics.successful_operations = len([m for m in completed_metrics if m.success])
            self.system_metrics.failed_operations = len([m for m in completed_metrics if not m.success])
            
            durations = [m.duration_ms for m in completed_metrics if m.duration_ms is not None]
            if durations:
                self.system_metrics.average_duration_ms = statistics.mean(durations)
                self.system_metrics.median_duration_ms = statistics.median(durations)
                self.system_metrics.min_duration_ms = min(durations)
                self.system_metrics.max_duration_ms = max(durations)
            
            # Calculate throughput (operations per second)
            if completed_metrics:
                total_time = (datetime.now() - self._start_time).total_seconds()
                if total_time > 0:
                    self.system_metrics.throughput_ops_per_second = len(completed_metrics) / total_time
            
            # Calculate error rate
            if self.system_metrics.total_operations > 0:
                self.system_metrics.error_rate = self.system_metrics.failed_operations / self.system_metrics.total_operations
            
            self.system_metrics.last_updated = datetime.now()
    
    def get_operation_metrics(self, operation_name: Optional[str] = None, 
                            time_window: Optional[timedelta] = None) -> List[PerformanceMetrics]:
        """Get metrics for specific operations"""
        with self._lock:
            metrics = self.metrics.copy()
        
        if operation_name:
            metrics = [m for m in metrics if m.operation_name == operation_name]
        
        if time_window:
            cutoff_time = datetime.now() - time_window
            metrics = [m for m in metrics if m.start_time >= cutoff_time]
        
        return metrics
    
    def get_system_metrics(self) -> SystemMetrics:
        """Get current system metrics"""
        with self._lock:
            return self.system_metrics
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        system_metrics = self.get_system_metrics()
        
        # Get recent metrics (last hour)
        recent_metrics = self.get_operation_metrics(time_window=timedelta(hours=1))
        
        # Calculate recent performance
        recent_durations = [m.duration_ms for m in recent_metrics if m.duration_ms is not None]
        recent_avg_duration = statistics.mean(recent_durations) if recent_durations else 0.0
        
        # Performance insights
        insights = []
        
        if system_metrics.error_rate > self.thresholds["error_rate_threshold"]:
            insights.append(f"High error rate detected: {system_metrics.error_rate:.2%}")
        
        if recent_avg_duration > self.thresholds["slow_operation_ms"]:
            insights.append(f"Slow operations detected: {recent_avg_duration:.0f}ms average")
        
        if system_metrics.throughput_ops_per_second < self.thresholds["throughput_threshold"]:
            insights.append(f"Low throughput detected: {system_metrics.throughput_ops_per_second:.1f} ops/sec")
        
        return {
            "system_metrics": {
                "total_operations": system_metrics.total_operations,
                "successful_operations": system_metrics.successful_operations,
                "failed_operations": system_metrics.failed_operations,
                "average_duration_ms": system_metrics.average_duration_ms,
                "median_duration_ms": system_metrics.median_duration_ms,
                "min_duration_ms": system_metrics.min_duration_ms,
                "max_duration_ms": system_metrics.max_duration_ms,
                "throughput_ops_per_second": system_metrics.throughput_ops_per_second,
                "error_rate": system_metrics.error_rate,
                "last_updated": system_metrics.last_updated.isoformat()
            },
            "recent_performance": {
                "recent_operations": len(recent_metrics),
                "recent_average_duration_ms": recent_avg_duration,
                "time_window_hours": 1
            },
            "insights": insights,
            "thresholds": self.thresholds
        }
    
    def save_metrics(self, filename: Optional[str] = None) -> None:
        """Save metrics to file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"performance_metrics_{timestamp}.json"
        
        filepath = self.metrics_dir / filename
        
        try:
            with self._lock:
                metrics_data = []
                for metric in self.metrics:
                    metrics_data.append({
                        "operation_name": metric.operation_name,
                        "start_time": metric.start_time.isoformat(),
                        "end_time": metric.end_time.isoformat() if metric.end_time else None,
                        "duration_ms": metric.duration_ms,
                        "success": metric.success,
                        "error_message": metric.error_message,
                        "metadata": metric.metadata
                    })
            
            with open(filepath, 'w') as f:
                json.dump({
                    "metrics": metrics_data,
                    "system_metrics": self.get_performance_report(),
                    "exported_at": datetime.now().isoformat()
                }, f, indent=2)
            
            logger.info(f"✅ Performance metrics saved to {filepath}")
        except Exception as e:
            logger.error(f"❌ Failed to save metrics: {e}")
    
    def clear_metrics(self) -> None:
        """Clear all stored metrics"""
        with self._lock:
            self.metrics.clear()
            self.system_metrics = SystemMetrics()
            self._start_time = datetime.now()
        
        logger.info("✅ Performance metrics cleared")

# Global performance monitor instance
_performance_monitor = None
_performance_monitor_lock = threading.Lock()

def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance"""
    global _performance_monitor
    
    with _performance_monitor_lock:
        if _performance_monitor is None:
            _performance_monitor = PerformanceMonitor()
    
    return _performance_monitor

def monitor_operation(operation_name: str):
    """Decorator for monitoring operations"""
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            monitor = get_performance_monitor()
            operation_id = monitor.start_operation(operation_name)
            
            try:
                result = func(*args, **kwargs)
                monitor.end_operation(operation_id, success=True)
                return result
            except Exception as e:
                monitor.end_operation(operation_id, success=False, error_message=str(e))
                raise
        
        return wrapper
    return decorator 