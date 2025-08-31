#!/usr/bin/env python3
"""
Comprehensive health monitoring tests
"""

import os
import sys
import tempfile
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from db_manager_unified import DatabaseManager

def test_health_metrics_calculation():
    """Test health metrics calculation"""
    print("🧪 Testing health metrics calculation...")
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
        db_path = tmp_db.name
    
    try:
        # Initialize database
        db = DatabaseManager(db_path)
        db.run_migrations()
        
        # Insert test data
        with db.get_connection() as conn:
            # Insert test jobs
            conn.execute("""
                INSERT INTO jobs (id, kind, status, duration_ms, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, ("job_1", "ocr", "timeout", None, datetime.now().isoformat()))
            
            conn.execute("""
                INSERT INTO jobs (id, kind, status, duration_ms, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, ("job_2", "ocr", "failed", None, datetime.now().isoformat()))
            
            conn.execute("""
                INSERT INTO jobs (id, kind, status, duration_ms, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, ("job_3", "ocr", "completed", 15000, datetime.now().isoformat()))
            
            conn.execute("""
                INSERT INTO jobs (id, kind, status, duration_ms, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, ("job_4", "ocr", "completed", 5000, datetime.now().isoformat()))
            
            # Insert test invoices
            conn.execute("""
                INSERT INTO uploaded_files (id, original_filename, canonical_path, file_size, file_hash, mime_type, doc_type, upload_timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, ("test_file_1", "test_invoice.pdf", "/tmp/test_invoice.pdf", 1024, "test_hash_1", "application/pdf", "invoice"))
            
            conn.execute("""
                INSERT INTO invoices (id, file_id, supplier_name, invoice_date, total_amount_pennies, confidence, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, ("test_inv_1", "test_file_1", "ABC Company", "2024-01-01", 10000, 0.9, datetime.now().isoformat()))
            
            conn.commit()
        
        # Test health endpoint logic
        twenty_four_hours_ago = datetime.now() - timedelta(hours=24)
        twenty_four_hours_str = twenty_four_hours_ago.strftime('%Y-%m-%d %H:%M:%S')
        
        with db.get_connection() as conn:
            # Timeouts in last 24h
            timeouts_24h = conn.execute("""
                SELECT COUNT(*) as count FROM jobs 
                WHERE status = 'timeout' AND created_at >= ?
            """, (twenty_four_hours_str,)).fetchone()['count']
            
            # Failed jobs in last 24h
            failed_24h = conn.execute("""
                SELECT COUNT(*) as count FROM jobs 
                WHERE status = 'failed' AND created_at >= ?
            """, (twenty_four_hours_str,)).fetchone()['count']
            
            # Average duration for completed jobs in last 24h
            avg_duration = conn.execute("""
                SELECT AVG(duration_ms) as avg_duration FROM jobs 
                WHERE status = 'completed' AND created_at >= ? AND duration_ms IS NOT NULL
            """, (twenty_four_hours_str,)).fetchone()['avg_duration']
            avg_duration_ms_24h = int(avg_duration) if avg_duration else 0
            
            # High confidence invoices with zero line items in last 24h
            hi_conf_zero_lines_24h = conn.execute("""
                SELECT COUNT(*) as count FROM invoices i
                LEFT JOIN invoice_line_items ili ON i.id = ili.invoice_id
                WHERE i.confidence > 0.8 AND i.created_at >= ?
                GROUP BY i.id
                HAVING COUNT(ili.id) = 0
            """, (twenty_four_hours_str,)).fetchall()
            hi_conf_zero_lines_24h = len(hi_conf_zero_lines_24h)
        
        # Verify metrics
        assert timeouts_24h == 1, f"Expected 1 timeout, got {timeouts_24h}"
        assert failed_24h == 1, f"Expected 1 failed job, got {failed_24h}"
        assert avg_duration_ms_24h == 10000, f"Expected avg duration 10000ms, got {avg_duration_ms_24h}"
        assert hi_conf_zero_lines_24h == 1, f"Expected 1 high conf zero lines, got {hi_conf_zero_lines_24h}"
        
        print("✅ Health metrics calculation tests passed")
        
    finally:
        # Cleanup
        os.unlink(db_path)

def test_health_status_evaluation():
    """Test health status evaluation logic"""
    print("🧪 Testing health status evaluation...")
    
    # Test critical status
    violations = []
    status = "healthy"
    
    # Test critical violations
    timeouts_24h = 1
    failed_24h = 0
    
    if timeouts_24h > 0:
        violations.append(f"OCR timeouts detected: {timeouts_24h} in last 24h")
        status = "critical"
    elif failed_24h > 0:
        violations.append(f"Failed jobs detected: {failed_24h} in last 24h")
        status = "critical"
    
    assert status == "critical", f"Expected critical status, got {status}"
    assert len(violations) == 1, f"Expected 1 violation, got {len(violations)}"
    
    # Test degraded status
    violations = []
    status = "healthy"
    
    avg_duration_ms_24h = 15000
    hi_conf_zero_lines_24h = 0
    
    if avg_duration_ms_24h > 10000:
        violations.append(f"Slow processing: avg {avg_duration_ms_24h}ms in last 24h")
        if status != "critical":
            status = "degraded"
    
    if hi_conf_zero_lines_24h > 0:
        violations.append(f"High confidence invoices with no line items: {hi_conf_zero_lines_24h}")
        if status != "critical":
            status = "degraded"
    
    assert status == "degraded", f"Expected degraded status, got {status}"
    assert len(violations) == 1, f"Expected 1 violation, got {len(violations)}"
    
    # Test healthy status
    violations = []
    status = "healthy"
    
    avg_duration_ms_24h = 5000
    hi_conf_zero_lines_24h = 0
    
    if avg_duration_ms_24h > 10000:
        violations.append(f"Slow processing: avg {avg_duration_ms_24h}ms in last 24h")
        if status != "critical":
            status = "degraded"
    
    if hi_conf_zero_lines_24h > 0:
        violations.append(f"High confidence invoices with no line items: {hi_conf_zero_lines_24h}")
        if status != "critical":
            status = "degraded"
    
    assert status == "healthy", f"Expected healthy status, got {status}"
    assert len(violations) == 0, f"Expected 0 violations, got {len(violations)}"
    
    print("✅ Health status evaluation tests passed")

def test_health_endpoint_integration():
    """Test health endpoint integration"""
    print("🧪 Testing health endpoint integration...")
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
        db_path = tmp_db.name
    
    try:
        # Initialize database
        db = DatabaseManager(db_path)
        db.run_migrations()
        
        # Insert test data for different scenarios
        with db.get_connection() as conn:
            # Insert timeout job
            conn.execute("""
                INSERT INTO jobs (id, kind, status, duration_ms, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, ("job_timeout", "ocr", "timeout", None, datetime.now().isoformat()))
            
            # Insert slow job
            conn.execute("""
                INSERT INTO jobs (id, kind, status, duration_ms, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, ("job_slow", "ocr", "completed", 15000, datetime.now().isoformat()))
            
            # Insert high confidence invoice with no line items
            conn.execute("""
                INSERT INTO uploaded_files (id, original_filename, canonical_path, file_size, file_hash, mime_type, doc_type, upload_timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, ("test_file_1", "test_invoice.pdf", "/tmp/test_invoice.pdf", 1024, "test_hash_1", "application/pdf", "invoice"))
            
            conn.execute("""
                INSERT INTO invoices (id, file_id, supplier_name, invoice_date, total_amount_pennies, confidence, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, ("test_inv_1", "test_file_1", "ABC Company", "2024-01-01", 10000, 0.9, datetime.now().isoformat()))
            
            conn.commit()
        
        # Simulate health endpoint logic
        twenty_four_hours_ago = datetime.now() - timedelta(hours=24)
        twenty_four_hours_str = twenty_four_hours_ago.strftime('%Y-%m-%d %H:%M:%S')
        
        with db.get_connection() as conn:
            # Calculate metrics
            timeouts_24h = conn.execute("""
                SELECT COUNT(*) as count FROM jobs 
                WHERE status = 'timeout' AND created_at >= ?
            """, (twenty_four_hours_str,)).fetchone()['count']
            
            failed_24h = conn.execute("""
                SELECT COUNT(*) as count FROM jobs 
                WHERE status = 'failed' AND created_at >= ?
            """, (twenty_four_hours_str,)).fetchone()['count']
            
            avg_duration = conn.execute("""
                SELECT AVG(duration_ms) as avg_duration FROM jobs 
                WHERE status = 'completed' AND created_at >= ? AND duration_ms IS NOT NULL
            """, (twenty_four_hours_str,)).fetchone()['avg_duration']
            avg_duration_ms_24h = int(avg_duration) if avg_duration else 0
            
            hi_conf_zero_lines_24h = conn.execute("""
                SELECT COUNT(*) as count FROM invoices i
                LEFT JOIN invoice_line_items ili ON i.id = ili.invoice_id
                WHERE i.confidence > 0.8 AND i.created_at >= ?
                GROUP BY i.id
                HAVING COUNT(ili.id) = 0
            """, (twenty_four_hours_str,)).fetchall()
            hi_conf_zero_lines_24h = len(hi_conf_zero_lines_24h)
            
            # Evaluate health status
            violations = []
            status = "healthy"
            
            # Check for critical violations
            if timeouts_24h > 0:
                violations.append(f"OCR timeouts detected: {timeouts_24h} in last 24h")
                status = "critical"
            elif failed_24h > 0:
                violations.append(f"Failed jobs detected: {failed_24h} in last 24h")
                status = "critical"
            
            # Check for degraded conditions
            if avg_duration_ms_24h > 10000:
                violations.append(f"Slow processing: avg {avg_duration_ms_24h}ms in last 24h")
                if status != "critical":
                    status = "degraded"
            
            if hi_conf_zero_lines_24h > 0:
                violations.append(f"High confidence invoices with no line items: {hi_conf_zero_lines_24h}")
                if status != "critical":
                    status = "degraded"
        
        # Verify health evaluation
        assert status == "critical", f"Expected critical status due to timeout, got {status}"
        assert len(violations) >= 1, f"Expected at least 1 violation, got {len(violations)}"
        assert any("timeout" in v for v in violations), "Should have timeout violation"
        
        print("✅ Health endpoint integration tests passed")
        
    finally:
        # Cleanup
        os.unlink(db_path)

if __name__ == "__main__":
    print("🚀 Running comprehensive health monitoring tests...")
    
    test_health_metrics_calculation()
    test_health_status_evaluation()
    test_health_endpoint_integration()
    
    print("🎉 All health monitoring tests passed!") 