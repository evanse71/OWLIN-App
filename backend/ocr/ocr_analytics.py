#!/usr/bin/env python3
"""
OCR Analytics and Monitoring System

Tracks performance, accuracy, and usage patterns of the unified OCR engine.
"""

import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

@dataclass
class OCRMetrics:
    """OCR processing metrics"""
    timestamp: str
    file_path: str
    engine_used: str
    processing_time: float
    confidence: float
    word_count: int
    success: bool
    document_type: str
    error_message: Optional[str] = None

class OCRAnalytics:
    """
    Analytics system for OCR performance monitoring
    """
    
    def __init__(self, metrics_file: str = "data/ocr_metrics.json"):
        self.metrics_file = Path(metrics_file)
        self.metrics_file.parent.mkdir(exist_ok=True)
        self.metrics: List[OCRMetrics] = []
        self._load_metrics()
    
    def _load_metrics(self):
        """Load existing metrics from file"""
        try:
            if self.metrics_file.exists():
                with open(self.metrics_file, 'r') as f:
                    data = json.load(f)
                    self.metrics = [OCRMetrics(**item) for item in data]
                    logger.info(f"📊 Loaded {len(self.metrics)} existing metrics")
        except Exception as e:
            logger.warning(f"⚠️ Could not load metrics: {e}")
            self.metrics = []
    
    def _save_metrics(self):
        """Save metrics to file"""
        try:
            with open(self.metrics_file, 'w') as f:
                data = [asdict(metric) for metric in self.metrics]
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"❌ Could not save metrics: {e}")
    
    def record_processing(self, result, file_path: str):
        """Record OCR processing metrics"""
        try:
            metric = OCRMetrics(
                timestamp=datetime.now().isoformat(),
                file_path=file_path,
                engine_used=result.engine_used,
                processing_time=result.processing_time,
                confidence=result.overall_confidence,
                word_count=result.word_count,
                success=result.success,
                document_type=result.document_type,
                error_message=result.error_message
            )
            
            self.metrics.append(metric)
            
            # Keep only last 1000 metrics to prevent file bloat
            if len(self.metrics) > 1000:
                self.metrics = self.metrics[-1000:]
            
            self._save_metrics()
            
        except Exception as e:
            logger.error(f"❌ Could not record metrics: {e}")
    
    def get_performance_summary(self, days: int = 7) -> Dict[str, Any]:
        """Get performance summary for the last N days"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            recent_metrics = [
                m for m in self.metrics 
                if datetime.fromisoformat(m.timestamp) > cutoff_date
            ]
            
            if not recent_metrics:
                return {"message": "No recent metrics available"}
            
            total_processed = len(recent_metrics)
            successful = sum(1 for m in recent_metrics if m.success)
            success_rate = (successful / total_processed) * 100 if total_processed > 0 else 0
            
            # Engine usage statistics
            engine_usage = {}
            for metric in recent_metrics:
                engine_usage[metric.engine_used] = engine_usage.get(metric.engine_used, 0) + 1
            
            # Average processing time by engine
            engine_times = {}
            for engine in engine_usage.keys():
                engine_metrics = [m for m in recent_metrics if m.engine_used == engine]
                avg_time = sum(m.processing_time for m in engine_metrics) / len(engine_metrics)
                engine_times[engine] = round(avg_time, 2)
            
            # Confidence distribution
            confidences = [m.confidence for m in recent_metrics if m.success]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            # Document type distribution
            doc_types = {}
            for metric in recent_metrics:
                doc_types[metric.document_type] = doc_types.get(metric.document_type, 0) + 1
            
            return {
                "period_days": days,
                "total_processed": total_processed,
                "success_rate": round(success_rate, 2),
                "average_confidence": round(avg_confidence, 2),
                "engine_usage": engine_usage,
                "average_processing_time": engine_times,
                "document_types": doc_types,
                "total_processing_time": round(sum(m.processing_time for m in recent_metrics), 2)
            }
            
        except Exception as e:
            logger.error(f"❌ Could not generate performance summary: {e}")
            return {"error": str(e)}
    
    def get_engine_performance(self) -> Dict[str, Any]:
        """Get detailed engine performance comparison"""
        try:
            engines = {}
            
            for metric in self.metrics:
                engine = metric.engine_used
                if engine not in engines:
                    engines[engine] = {
                        "total_usage": 0,
                        "success_count": 0,
                        "total_time": 0,
                        "total_confidence": 0,
                        "confidence_count": 0
                    }
                
                engines[engine]["total_usage"] += 1
                engines[engine]["total_time"] += metric.processing_time
                
                if metric.success:
                    engines[engine]["success_count"] += 1
                    engines[engine]["total_confidence"] += metric.confidence
                    engines[engine]["confidence_count"] += 1
            
            # Calculate averages
            for engine, stats in engines.items():
                stats["success_rate"] = (stats["success_count"] / stats["total_usage"]) * 100
                stats["avg_processing_time"] = stats["total_time"] / stats["total_usage"]
                stats["avg_confidence"] = (
                    stats["total_confidence"] / stats["confidence_count"] 
                    if stats["confidence_count"] > 0 else 0
                )
                
                # Round values
                stats["success_rate"] = round(stats["success_rate"], 2)
                stats["avg_processing_time"] = round(stats["avg_processing_time"], 2)
                stats["avg_confidence"] = round(stats["avg_confidence"], 2)
            
            return engines
            
        except Exception as e:
            logger.error(f"❌ Could not generate engine performance: {e}")
            return {"error": str(e)}
    
    def get_error_analysis(self) -> Dict[str, Any]:
        """Analyze common errors and failure patterns"""
        try:
            failed_metrics = [m for m in self.metrics if not m.success]
            
            if not failed_metrics:
                return {"message": "No failures recorded"}
            
            # Error message frequency
            error_frequency = {}
            for metric in failed_metrics:
                error = metric.error_message or "Unknown error"
                error_frequency[error] = error_frequency.get(error, 0) + 1
            
            # Failure rate by engine
            engine_failures = {}
            for metric in self.metrics:
                engine = metric.engine_used
                if engine not in engine_failures:
                    engine_failures[engine] = {"total": 0, "failed": 0}
                
                engine_failures[engine]["total"] += 1
                if not metric.success:
                    engine_failures[engine]["failed"] += 1
            
            # Calculate failure rates
            for engine, stats in engine_failures.items():
                stats["failure_rate"] = round((stats["failed"] / stats["total"]) * 100, 2)
            
            return {
                "total_failures": len(failed_metrics),
                "error_frequency": error_frequency,
                "failure_by_engine": engine_failures
            }
            
        except Exception as e:
            logger.error(f"❌ Could not generate error analysis: {e}")
            return {"error": str(e)}

# Global analytics instance
ocr_analytics = OCRAnalytics() 