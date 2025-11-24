"""
Chat Metrics

Tracks quality metrics for chat responses including generic response rate,
code reference rate, and model performance.
"""

import logging
import json
import time
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("owlin.services.chat_metrics")


class ChatMetrics:
    """Tracks and aggregates chat service quality metrics."""
    
    def __init__(self, metrics_file: str = "data/chat_metrics.jsonl"):
        """
        Initialize metrics tracker.
        
        Args:
            metrics_file: Path to metrics log file (JSONL format)
        """
        self.metrics_file = Path(metrics_file)
        self.metrics_file.parent.mkdir(parents=True, exist_ok=True)
        
        # In-memory stats for quick access
        self.session_stats = {
            "total_requests": 0,
            "generic_responses": 0,
            "forced_retries": 0,
            "model_failures": 0,
            "successful_responses": 0,
            "avg_response_time": 0.0,
            "total_files_read": 0,
            "total_code_references": 0,
            # Exploration metrics
            "exploration_requests": 0,
            "exploration_successes": 0,
            "total_findings": 0,
            "total_searches": 0,
            "total_traces": 0,
            "avg_exploration_time": 0.0,
            "exploration_timeouts": 0
        }
    
    def log_request(
        self,
        request_id: str,
        message: str,
        question_type: str,
        context_size: int,
        files_count: int,
        model_selected: str,
        response_time: float,
        success: bool,
        generic_detected: bool,
        forced_retry: bool,
        code_references_count: int
    ) -> None:
        """
        Log a chat request with all metrics.
        
        Args:
            request_id: Unique request identifier
            message: User's message
            question_type: Type of question (debugging, code_flow, general)
            context_size: Context window size used
            files_count: Number of files included
            model_selected: Model used for response
            response_time: Time taken in seconds
            success: Whether request succeeded
            generic_detected: Whether generic response was detected
            forced_retry: Whether forced retry was triggered
            code_references_count: Number of code references in response
        """
        # Update session stats
        self.session_stats["total_requests"] += 1
        if generic_detected:
            self.session_stats["generic_responses"] += 1
        if forced_retry:
            self.session_stats["forced_retries"] += 1
        if not success:
            self.session_stats["model_failures"] += 1
        if success and not generic_detected:
            self.session_stats["successful_responses"] += 1
        
        # Update running averages
        total = self.session_stats["total_requests"]
        current_avg = self.session_stats["avg_response_time"]
        self.session_stats["avg_response_time"] = (
            (current_avg * (total - 1) + response_time) / total
        )
        
        self.session_stats["total_files_read"] += files_count
        self.session_stats["total_code_references"] += code_references_count
        
        # Log to file
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "request_id": request_id,
            "message_preview": message[:100],
            "question_type": question_type,
            "context_size": context_size,
            "files_count": files_count,
            "model_selected": model_selected,
            "response_time": round(response_time, 3),
            "success": success,
            "generic_detected": generic_detected,
            "forced_retry": forced_retry,
            "code_references_count": code_references_count
        }
        
        try:
            with open(self.metrics_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            logger.error(f"Failed to write metrics: {e}")
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get current session statistics."""
        stats = self.session_stats.copy()
        
        # Calculate rates
        total = stats["total_requests"]
        if total > 0:
            stats["generic_response_rate"] = round(
                (stats["generic_responses"] / total) * 100, 2
            )
            stats["success_rate"] = round(
                (stats["successful_responses"] / total) * 100, 2
            )
            stats["forced_retry_rate"] = round(
                (stats["forced_retries"] / total) * 100, 2
            )
            stats["avg_files_per_request"] = round(
                stats["total_files_read"] / total, 1
            )
            stats["avg_code_refs_per_request"] = round(
                stats["total_code_references"] / total, 1
            )
        else:
            stats["generic_response_rate"] = 0.0
            stats["success_rate"] = 0.0
            stats["forced_retry_rate"] = 0.0
            stats["avg_files_per_request"] = 0.0
            stats["avg_code_refs_per_request"] = 0.0
        
        return stats
    
    def get_quality_report(self) -> Dict[str, Any]:
        """Generate quality report with pass/fail indicators."""
        stats = self.get_session_stats()
        
        # Quality thresholds (from plan)
        quality_checks = {
            "generic_response_rate": {
                "value": stats.get("generic_response_rate", 0),
                "threshold": 5.0,
                "target": "< 5%",
                "passing": stats.get("generic_response_rate", 0) < 5.0
            },
            "code_reference_rate": {
                "value": stats.get("avg_code_refs_per_request", 0),
                "threshold": 2.0,
                "target": "> 2 refs/request",
                "passing": stats.get("avg_code_refs_per_request", 0) > 2.0
            },
            "files_per_debugging_question": {
                "value": stats.get("avg_files_per_request", 0),
                "threshold": 3.0,
                "target": "> 3 files",
                "passing": stats.get("avg_files_per_request", 0) > 3.0
            },
            "success_rate": {
                "value": stats.get("success_rate", 0),
                "threshold": 90.0,
                "target": "> 90%",
                "passing": stats.get("success_rate", 0) > 90.0
            }
        }
        
        # Overall health
        passing_checks = sum(1 for check in quality_checks.values() if check["passing"])
        total_checks = len(quality_checks)
        overall_health = "EXCELLENT" if passing_checks == total_checks else \
                        "GOOD" if passing_checks >= total_checks * 0.75 else \
                        "NEEDS IMPROVEMENT"
        
        return {
            "overall_health": overall_health,
            "passing_checks": passing_checks,
            "total_checks": total_checks,
            "quality_checks": quality_checks,
            "session_stats": stats
        }
    
    def log_exploration(
        self,
        request_id: str,
        message: str,
        findings_count: int,
        searches_executed: int,
        files_read: int,
        traces_executed: int,
        exploration_time: float,
        success: bool,
        timeout: bool = False
    ) -> None:
        """
        Log exploration metrics.
        
        Args:
            request_id: Unique request identifier
            message: User's message that triggered exploration
            findings_count: Number of findings discovered
            searches_executed: Number of searches performed
            files_read: Number of files read
            traces_executed: Number of traces executed
            exploration_time: Time taken for exploration in seconds
            success: Whether exploration succeeded
            timeout: Whether exploration timed out
        """
        # Update session stats
        self.session_stats["exploration_requests"] += 1
        if success:
            self.session_stats["exploration_successes"] += 1
        if timeout:
            self.session_stats["exploration_timeouts"] += 1
        
        self.session_stats["total_findings"] += findings_count
        self.session_stats["total_searches"] += searches_executed
        self.session_stats["total_traces"] += traces_executed
        self.session_stats["total_files_read"] += files_read
        
        # Update running average
        total = self.session_stats["exploration_requests"]
        current_avg = self.session_stats["avg_exploration_time"]
        self.session_stats["avg_exploration_time"] = (
            (current_avg * (total - 1) + exploration_time) / total
        )
        
        # Log to file
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "request_id": request_id,
            "type": "exploration",
            "message_preview": message[:100],
            "findings_count": findings_count,
            "searches_executed": searches_executed,
            "files_read": files_read,
            "traces_executed": traces_executed,
            "exploration_time": round(exploration_time, 3),
            "success": success,
            "timeout": timeout
        }
        
        try:
            with open(self.metrics_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            logger.error(f"Failed to write exploration metrics: {e}")


# Global metrics instance
_metrics: Optional[ChatMetrics] = None


def get_metrics() -> ChatMetrics:
    """Get or create global metrics tracker."""
    global _metrics
    if _metrics is None:
        _metrics = ChatMetrics()
    return _metrics

