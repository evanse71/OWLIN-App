#!/usr/bin/env python3
"""
Local Telemetry System

Logs OCR processing metrics for operational visibility
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from os import PathLike

# --- TYPE SAFETY GUARD: paths are Path-like, not plain strings ---
StrPath = Union[str, PathLike[str], Path]

def _ensure_path(p: Optional[StrPath]) -> Optional[Path]:
    if p is None:
        return None
    return Path(p)
# -----------------------------------------------------------------

logger = logging.getLogger(__name__)

class TelemetryLogger:
    """Local telemetry logger for OCR metrics"""
    
    def __init__(self, log_path: Optional[StrPath] = None):
        if log_path is None:
            log_path = Path(__file__).parent.parent.parent / "data" / "ocr_metrics.log"
        
        p = _ensure_path(log_path)
        if p is None:
            raise ValueError("log_path cannot be None")
        
        self.log_path = p
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Maximum log file size (20MB)
        self.max_log_size = 20 * 1024 * 1024
    
    def log_processing(self, 
                      doc_id: str,
                      doc_type: str,
                      policy_action: str,
                      confidence: float,
                      duration_ms: int,
                      reasons: List[str],
                      template_hint_used: bool = False,
                      auto_retry_used: bool = False,
                      llm_used: bool = False,
                      llm_ms: int = 0) -> bool:
        """
        Log OCR processing metrics
        
        Args:
            doc_id: Document identifier
            doc_type: Document type
            policy_action: Policy decision
            confidence: Processing confidence
            duration_ms: Processing time in milliseconds
            reasons: Top reasons for decision
            template_hint_used: Whether template hint was used
            auto_retry_used: Whether auto-retry was used
            
        Returns:
            True if logged successfully
        """
        try:
            # Check if log file needs rotation
            self._rotate_log_if_needed()
            
            # Prepare log entry
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'doc_id': doc_id,
                'doc_type': doc_type,
                'policy_action': policy_action,
                'confidence': round(confidence, 3),
                'duration_ms': duration_ms,
                'reasons_top3': reasons[:3],
                'template_hint_used': template_hint_used,
                'auto_retry_used': auto_retry_used,
                'llm_used': llm_used,
                'llm_ms': llm_ms
            }
            
            # Write to log file
            with open(self.log_path, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to log telemetry: {e}")
            return False
    
    def _rotate_log_if_needed(self):
        """Rotate log file if it exceeds maximum size"""
        if not self.log_path.exists():
            return
        
        if self.log_path.stat().st_size > self.max_log_size:
            # Create backup with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.log_path.with_suffix(f'.{timestamp}.log')
            
            try:
                # Move current log to backup
                self.log_path.rename(backup_path)
                logger.info(f"📁 Rotated telemetry log: {backup_path}")
            except Exception as e:
                logger.error(f"❌ Failed to rotate log: {e}")
    
    def get_metrics_summary(self, days: int = 7) -> Dict[str, Any]:
        """
        Get metrics summary for the last N days
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dictionary with metrics summary
        """
        try:
            if not self.log_path.exists():
                return self._empty_summary()
            
            # Calculate cutoff date
            cutoff_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            cutoff_date = cutoff_date.replace(day=cutoff_date.day - days)
            
            # Read and parse log entries
            entries = []
            with open(self.log_path, 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        entry_date = datetime.fromisoformat(entry['timestamp'])
                        if entry_date >= cutoff_date:
                            entries.append(entry)
                    except json.JSONDecodeError:
                        continue
            
            if not entries:
                return self._empty_summary()
            
            # Calculate metrics
            total_docs = len(entries)
            
            # Policy action counts
            policy_counts = {}
            for entry in entries:
                action = entry['policy_action']
                policy_counts[action] = policy_counts.get(action, 0) + 1
            
            # Confidence statistics
            confidences = [entry['confidence'] for entry in entries]
            mean_confidence = sum(confidences) / len(confidences)
            
            # Processing time statistics
            durations = [entry['duration_ms'] for entry in entries]
            mean_duration = sum(durations) / len(durations)
            
            # Top reasons
            all_reasons = []
            for entry in entries:
                all_reasons.extend(entry.get('reasons_top3', []))
            
            reason_counts = {}
            for reason in all_reasons:
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
            
            top_reasons = sorted(reason_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            
            # Template and retry usage
            template_usage = sum(1 for entry in entries if entry.get('template_hint_used', False))
            retry_usage = sum(1 for entry in entries if entry.get('auto_retry_used', False))
            
            # Calculate rates
            quarantine_rate = (policy_counts.get('QUARANTINE', 0) / total_docs) * 100
            reject_rate = (policy_counts.get('REJECT', 0) / total_docs) * 100
            
            return {
                'period_days': days,
                'total_docs': total_docs,
                'policy_actions': policy_counts,
                'mean_confidence': round(mean_confidence, 3),
                'mean_duration_ms': round(mean_duration, 1),
                'top_reasons': top_reasons,
                'template_usage': template_usage,
                'retry_usage': retry_usage,
                'quarantine_rate': round(quarantine_rate, 1),
                'reject_rate': round(reject_rate, 1),
                'summary': {
                    'quarantine_rate_ok': quarantine_rate <= 8.0,
                    'reject_rate_ok': reject_rate <= 2.0,
                    'confidence_ok': mean_confidence >= 0.7
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get metrics summary: {e}")
            return self._empty_summary()
    
    def _empty_summary(self) -> Dict[str, Any]:
        """Return empty summary structure"""
        return {
            'period_days': 7,
            'total_docs': 0,
            'policy_actions': {},
            'mean_confidence': 0.0,
            'mean_duration_ms': 0.0,
            'top_reasons': [],
            'template_usage': 0,
            'retry_usage': 0,
            'quarantine_rate': 0.0,
            'reject_rate': 0.0,
            'summary': {
                'quarantine_rate_ok': True,
                'reject_rate_ok': True,
                'confidence_ok': True
            }
        }
    
    def export_metrics(self, output_path: Optional[StrPath] = None) -> str:
        """
        Export telemetry metrics to a file
        
        Args:
            output_path: Output file path (optional)
            
        Returns:
            Path to exported file
        """
        try:
            if output_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = Path(__file__).parent.parent.parent / "data" / f"ocr_metrics_export_{timestamp}.json"
            
            p = _ensure_path(output_path)
            if p is None:
                raise ValueError("output_path cannot be None")
            
            p.parent.mkdir(parents=True, exist_ok=True)
            
            # Get summary
            summary = self.get_metrics_summary()
            
            # Add raw data if log exists
            if self.log_path.exists():
                raw_entries = []
                with open(self.log_path, 'r') as f:
                    for line in f:
                        try:
                            raw_entries.append(json.loads(line.strip()))
                        except json.JSONDecodeError:
                            continue
                
                summary['raw_entries'] = raw_entries
            
            # Write to file
            with open(p, 'w') as f:
                json.dump(summary, f, indent=2)
            
            logger.info(f"📄 Exported telemetry metrics to: {p}")
            return str(p)
            
        except Exception as e:
            logger.error(f"❌ Failed to export metrics: {e}")
            raise

# Global telemetry logger instance
_telemetry_logger: Optional[TelemetryLogger] = None

def get_telemetry_logger() -> TelemetryLogger:
    """Get global telemetry logger instance"""
    global _telemetry_logger
    if _telemetry_logger is None:
        _telemetry_logger = TelemetryLogger()
    return _telemetry_logger 