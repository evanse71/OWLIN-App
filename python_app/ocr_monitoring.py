"""
OCR Monitoring and Maintenance System for Owlin App
Provides comprehensive monitoring, analytics, and maintenance for OCR processing.
"""
import sqlite3
import logging
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import numpy as np
import streamlit as st
from dataclasses import dataclass, asdict
import os

logger = logging.getLogger(__name__)

@dataclass
class OCRMetrics:
    """Data class for OCR processing metrics."""
    timestamp: str
    file_id: str
    file_type: str
    original_confidence: float
    processed_confidence: float
    confidence_improvement: float
    preprocessing_time: float
    ocr_time: float
    total_time: float
    text_length: int
    quality_score: float
    preprocessing_stats: Dict
    success: bool
    error_message: Optional[str] = None

class OCRMonitor:
    """Comprehensive monitoring system for OCR processing."""
    
    def __init__(self, db_path: str = "data/owlin.db"):
        """Initialize the OCR monitor."""
        self.db_path = db_path
        self.metrics_table = "ocr_processing_metrics"
        self.alerts_table = "ocr_alerts"
        self.create_monitoring_tables()
        logger.info("OCR Monitor initialized")
    
    def create_monitoring_tables(self):
        """Create monitoring tables if they don't exist."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # OCR Processing Metrics Table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ocr_processing_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    file_id TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    original_confidence REAL,
                    processed_confidence REAL,
                    confidence_improvement REAL,
                    preprocessing_time REAL,
                    ocr_time REAL,
                    total_time REAL,
                    text_length INTEGER,
                    quality_score REAL,
                    preprocessing_stats TEXT,
                    success BOOLEAN,
                    error_message TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # OCR Alerts Table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ocr_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    alert_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    message TEXT NOT NULL,
                    file_id TEXT,
                    metrics TEXT,
                    resolved BOOLEAN DEFAULT FALSE,
                    resolved_at TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Performance Trends Table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ocr_performance_trends (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    total_files INTEGER,
                    successful_files INTEGER,
                    failed_files INTEGER,
                    avg_confidence REAL,
                    avg_processing_time REAL,
                    avg_confidence_improvement REAL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Monitoring tables created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create monitoring tables: {e}")
    
    def record_metrics(self, metrics: OCRMetrics):
        """Record OCR processing metrics."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO ocr_processing_metrics 
                (timestamp, file_id, file_type, original_confidence, processed_confidence,
                 confidence_improvement, preprocessing_time, ocr_time, total_time,
                 text_length, quality_score, preprocessing_stats, success, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                metrics.timestamp, metrics.file_id, metrics.file_type,
                metrics.original_confidence, metrics.processed_confidence,
                metrics.confidence_improvement, metrics.preprocessing_time,
                metrics.ocr_time, metrics.total_time, metrics.text_length,
                metrics.quality_score, json.dumps(metrics.preprocessing_stats),
                metrics.success, metrics.error_message
            ))
            
            conn.commit()
            conn.close()
            logger.debug(f"Recorded metrics for file {metrics.file_id}")
            
            # Check for alerts
            self.check_alerts(metrics)
            
        except Exception as e:
            logger.error(f"Failed to record metrics: {e}")
    
    def check_alerts(self, metrics: OCRMetrics):
        """Check for potential alerts based on metrics."""
        alerts = []
        
        # Low confidence alert
        if metrics.processed_confidence < 0.5:
            alerts.append({
                'type': 'low_confidence',
                'severity': 'warning',
                'message': f"Low OCR confidence ({metrics.processed_confidence:.2f}) for file {metrics.file_id}",
                'file_id': metrics.file_id
            })
        
        # No confidence improvement alert
        if metrics.confidence_improvement < 0:
            alerts.append({
                'type': 'confidence_degradation',
                'severity': 'warning',
                'message': f"OCR confidence degraded by {abs(metrics.confidence_improvement):.2f} for file {metrics.file_id}",
                'file_id': metrics.file_id
            })
        
        # Long processing time alert
        if metrics.total_time > 30.0:  # 30 seconds
            alerts.append({
                'type': 'slow_processing',
                'severity': 'info',
                'message': f"Slow processing time ({metrics.total_time:.1f}s) for file {metrics.file_id}",
                'file_id': metrics.file_id
            })
        
        # Failed processing alert
        if not metrics.success:
            alerts.append({
                'type': 'processing_failure',
                'severity': 'error',
                'message': f"OCR processing failed for file {metrics.file_id}: {metrics.error_message}",
                'file_id': metrics.file_id
            })
        
        # Record alerts
        for alert in alerts:
            self.record_alert(alert)
    
    def record_alert(self, alert: Dict):
        """Record an alert."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO ocr_alerts 
                (timestamp, alert_type, severity, message, file_id, metrics)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(),
                alert['type'],
                alert['severity'],
                alert['message'],
                alert.get('file_id'),
                json.dumps(alert.get('metrics', {}))
            ))
            
            conn.commit()
            conn.close()
            logger.info(f"Recorded alert: {alert['type']} - {alert['message']}")
            
        except Exception as e:
            logger.error(f"Failed to record alert: {e}")
    
    def get_performance_summary(self, days: int = 7) -> Dict:
        """Get performance summary for the last N days."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_files,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_files,
                    SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed_files,
                    AVG(processed_confidence) as avg_confidence,
                    AVG(total_time) as avg_processing_time,
                    AVG(confidence_improvement) as avg_confidence_improvement,
                    AVG(quality_score) as avg_quality_score
                FROM ocr_processing_metrics 
                WHERE timestamp >= ? AND timestamp <= ?
            ''', (start_date.isoformat(), end_date.isoformat()))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {
                    'total_files': result[0] or 0,
                    'successful_files': result[1] or 0,
                    'failed_files': result[2] or 0,
                    'success_rate': (result[1] or 0) / max(result[0] or 1, 1) * 100,
                    'avg_confidence': result[3] or 0.0,
                    'avg_processing_time': result[4] or 0.0,
                    'avg_confidence_improvement': result[5] or 0.0,
                    'avg_quality_score': result[6] or 0.0,
                    'period_days': days
                }
            
            return {}
            
        except Exception as e:
            logger.error(f"Failed to get performance summary: {e}")
            return {}
    
    def get_recent_alerts(self, limit: int = 10) -> List[Dict]:
        """Get recent alerts."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT timestamp, alert_type, severity, message, file_id, resolved
                FROM ocr_alerts 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (limit,))
            
            alerts = []
            for row in cursor.fetchall():
                alerts.append({
                    'timestamp': row[0],
                    'type': row[1],
                    'severity': row[2],
                    'message': row[3],
                    'file_id': row[4],
                    'resolved': bool(row[5])
                })
            
            conn.close()
            return alerts
            
        except Exception as e:
            logger.error(f"Failed to get recent alerts: {e}")
            return []
    
    def get_confidence_trends(self, days: int = 7) -> List[Dict]:
        """Get confidence trends over time."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            cursor.execute('''
                SELECT 
                    DATE(timestamp) as date,
                    AVG(processed_confidence) as avg_confidence,
                    AVG(confidence_improvement) as avg_improvement,
                    COUNT(*) as file_count
                FROM ocr_processing_metrics 
                WHERE timestamp >= ? AND timestamp <= ?
                GROUP BY DATE(timestamp)
                ORDER BY date
            ''', (start_date.isoformat(), end_date.isoformat()))
            
            trends = []
            for row in cursor.fetchall():
                trends.append({
                    'date': row[0],
                    'avg_confidence': row[1] or 0.0,
                    'avg_improvement': row[2] or 0.0,
                    'file_count': row[3] or 0
                })
            
            conn.close()
            return trends
            
        except Exception as e:
            logger.error(f"Failed to get confidence trends: {e}")
            return []
    
    def cleanup_old_metrics(self, days_to_keep: int = 90):
        """Clean up old metrics data."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).isoformat()
            
            # Delete old metrics
            cursor.execute('''
                DELETE FROM ocr_processing_metrics 
                WHERE timestamp < ?
            ''', (cutoff_date,))
            
            metrics_deleted = cursor.rowcount
            
            # Delete old alerts
            cursor.execute('''
                DELETE FROM ocr_alerts 
                WHERE timestamp < ? AND resolved = 1
            ''', (cutoff_date,))
            
            alerts_deleted = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            logger.info(f"Cleanup completed: {metrics_deleted} metrics, {alerts_deleted} alerts deleted")
            return {'metrics_deleted': metrics_deleted, 'alerts_deleted': alerts_deleted}
            
        except Exception as e:
            logger.error(f"Failed to cleanup old metrics: {e}")
            return {'metrics_deleted': 0, 'alerts_deleted': 0}
    
    def generate_health_report(self) -> Dict:
        """Generate a comprehensive health report."""
        try:
            # Get performance summary
            summary = self.get_performance_summary(days=7)
            
            # Get recent alerts
            alerts = self.get_recent_alerts(limit=20)
            
            # Get confidence trends
            trends = self.get_confidence_trends(days=7)
            
            # Calculate health score
            health_score = 100.0
            
            # Deduct points for failures
            if summary.get('total_files', 0) > 0:
                failure_rate = summary.get('failed_files', 0) / summary.get('total_files', 1)
                health_score -= failure_rate * 50  # Up to 50 points for failures
            
            # Deduct points for low confidence
            avg_confidence = summary.get('avg_confidence', 0.0)
            if avg_confidence < 0.7:
                health_score -= (0.7 - avg_confidence) * 30  # Up to 30 points for low confidence
            
            # Deduct points for recent alerts
            error_alerts = sum(1 for alert in alerts if alert['severity'] == 'error' and not alert['resolved'])
            health_score -= error_alerts * 5  # 5 points per error alert
            
            health_score = max(0.0, health_score)
            
            return {
                'health_score': health_score,
                'status': 'healthy' if health_score >= 80 else 'warning' if health_score >= 60 else 'critical',
                'summary': summary,
                'recent_alerts': alerts,
                'confidence_trends': trends,
                'recommendations': self.generate_recommendations(summary, alerts)
            }
            
        except Exception as e:
            logger.error(f"Failed to generate health report: {e}")
            return {'error': str(e)}

    def generate_recommendations(self, summary: Dict, alerts: List[Dict]) -> List[str]:
        """Generate recommendations based on performance data."""
        recommendations = []
        
        # Check success rate
        success_rate = summary.get('success_rate', 0)
        if success_rate < 90:
            recommendations.append(f"Low success rate ({success_rate:.1f}%). Review failed processing logs.")
        
        # Check average confidence
        avg_confidence = summary.get('avg_confidence', 0)
        if avg_confidence < 0.7:
            recommendations.append(f"Low average confidence ({avg_confidence:.2f}). Consider improving image quality or preprocessing.")
        
        # Check processing time
        avg_time = summary.get('avg_processing_time', 0)
        if avg_time > 15:
            recommendations.append(f"Slow average processing time ({avg_time:.1f}s). Consider optimizing preprocessing pipeline.")
        
        # Check for unresolved alerts
        unresolved_alerts = [a for a in alerts if not a['resolved']]
        if unresolved_alerts:
            recommendations.append(f"{len(unresolved_alerts)} unresolved alerts. Review and address issues.")
        
        if not recommendations:
            recommendations.append("System is performing well. Continue monitoring.")
        
        return recommendations

def create_monitoring_dashboard():
    """Create a Streamlit dashboard for OCR monitoring."""
    st.title("🔍 OCR Processing Monitor")
    
    # Initialize monitor
    monitor = OCRMonitor()
    
    # Get health report
    health_report = monitor.generate_health_report()
    
    if 'error' in health_report:
        st.error(f"Failed to generate health report: {health_report['error']}")
        return
    
    # Health Score
    col1, col2, col3 = st.columns(3)
    
    with col1:
        health_score = health_report['health_score']
        status = health_report['status']
        
        if status == 'healthy':
            st.metric("System Health", f"{health_score:.1f}%", delta="Good", delta_color="normal")
        elif status == 'warning':
            st.metric("System Health", f"{health_score:.1f}%", delta="Warning", delta_color="off")
        else:
            st.metric("System Health", f"{health_score:.1f}%", delta="Critical", delta_color="inverse")
    
    with col2:
        summary = health_report['summary']
        st.metric("Success Rate", f"{summary.get('success_rate', 0):.1f}%")
    
    with col3:
        st.metric("Avg Confidence", f"{summary.get('avg_confidence', 0):.2f}")
    
    # Performance Summary
    st.subheader("📊 Performance Summary (Last 7 Days)")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Files", summary.get('total_files', 0))
    
    with col2:
        st.metric("Successful", summary.get('successful_files', 0))
    
    with col3:
        st.metric("Failed", summary.get('failed_files', 0))
    
    with col4:
        st.metric("Avg Processing Time", f"{summary.get('avg_processing_time', 0):.1f}s")
    
    # Recent Alerts
    st.subheader("🚨 Recent Alerts")
    
    alerts = health_report['recent_alerts']
    if alerts:
        for alert in alerts[:5]:  # Show last 5 alerts
            severity_color = {
                'error': '🔴',
                'warning': '🟡',
                'info': '🔵'
            }.get(alert['severity'], '⚪')
            
            st.write(f"{severity_color} **{alert['severity'].upper()}**: {alert['message']}")
            st.caption(f"Time: {alert['timestamp']} | File: {alert.get('file_id', 'N/A')}")
    else:
        st.success("No recent alerts")
    
    # Recommendations
    st.subheader("💡 Recommendations")
    
    recommendations = health_report['recommendations']
    for rec in recommendations:
        st.write(f"• {rec}")
    
    # Actions
    st.subheader("🔧 Actions")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Refresh Data"):
            st.rerun()
    
    with col2:
        if st.button("🧹 Cleanup Old Data"):
            with st.spinner("Cleaning up old data..."):
                result = monitor.cleanup_old_metrics(days_to_keep=30)
                st.success(f"Cleanup completed: {result['metrics_deleted']} metrics, {result['alerts_deleted']} alerts deleted")

if __name__ == "__main__":
    # Test the monitoring system
    monitor = OCRMonitor()
    
    # Create test metrics
    test_metrics = OCRMetrics(
        timestamp=datetime.now().isoformat(),
        file_id="test-123",
        file_type="invoice",
        original_confidence=0.65,
        processed_confidence=0.85,
        confidence_improvement=0.20,
        preprocessing_time=2.5,
        ocr_time=1.8,
        total_time=4.3,
        text_length=1500,
        quality_score=0.75,
        preprocessing_stats={'contrast_improvement': 12.5, 'noise_reduction': 8.2},
        success=True
    )
    
    # Record test metrics
    monitor.record_metrics(test_metrics)
    
    # Generate health report
    health_report = monitor.generate_health_report()
    print("Health Report:", json.dumps(health_report, indent=2)) 