#!/usr/bin/env python3
"""
Threshold Alerts Script - Fail Fast on Critical Metrics

Checks critical metrics and exits non-zero if any thresholds are exceeded:
- timeouts_24h > 0: Job timeouts indicate system overload or OCR issues
- failed_24h > 0: Failed jobs indicate system failures
- hi_conf_zero_lines_24h > 0: High confidence invoices with no line items indicate OCR/parsing issues

Usage:
    python3 backend/scripts/threshold_alerts.py
    
Exit codes:
    0: All metrics within acceptable thresholds
    1: One or more thresholds exceeded
    2: Error accessing metrics
"""

import sys
import os
import requests
import json
from pathlib import Path

# Add backend to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

def check_thresholds(api_url="http://localhost:8001"):
    """
    Check critical thresholds via API
    
    Args:
        api_url: Base URL for the API
        
    Returns:
        tuple: (success: bool, metrics: dict, violations: list)
    """
    try:
        # Get health metrics
        response = requests.get(f"{api_url}/api/health/post_ocr", timeout=10)
        
        if response.status_code != 200:
            print(f"❌ Failed to get health metrics: HTTP {response.status_code}")
            return False, {}, ["API_ERROR"]
        
        data = response.json()
        metrics = data.get("metrics", {})
        
        print("📊 Current Metrics:")
        print(f"   Timeouts (24h): {metrics.get('timeouts_24h', 'N/A')}")
        print(f"   Failed jobs (24h): {metrics.get('failed_24h', 'N/A')}")
        print(f"   Avg duration (24h): {metrics.get('avg_duration_ms_24h', 'N/A')}ms")
        print(f"   Hi-conf zero lines (24h): {metrics.get('hi_conf_zero_lines_24h', 'N/A')}")
        print(f"   Multi uploads (24h): {metrics.get('multi_invoice_uploads_24h', 'N/A')}")
        
        # Check thresholds
        violations = []
        
        # Critical thresholds (cause immediate failure)
        if metrics.get('timeouts_24h', 0) > 0:
            violations.append(f"TIMEOUT_THRESHOLD: {metrics['timeouts_24h']} timeouts in last 24h (threshold: 0)")
        
        if metrics.get('failed_24h', 0) > 0:
            violations.append(f"FAILURE_THRESHOLD: {metrics['failed_24h']} failed jobs in last 24h (threshold: 0)")
        
        if metrics.get('hi_conf_zero_lines_24h', 0) > 0:
            violations.append(f"PARSING_THRESHOLD: {metrics['hi_conf_zero_lines_24h']} high-confidence invoices with zero line items in last 24h (threshold: 0)")
        
        # Warning thresholds (log but don't fail)
        if metrics.get('avg_duration_ms_24h', 0) > 30000:  # 30 seconds
            print(f"⚠️ WARNING: Average processing time is high: {metrics['avg_duration_ms_24h']}ms")
        
        if metrics.get('multi_invoice_uploads_24h', 0) > 5:
            print(f"⚠️ WARNING: High number of duplicate uploads: {metrics['multi_invoice_uploads_24h']}")
        
        return True, metrics, violations
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        return False, {}, ["NETWORK_ERROR"]
    except json.JSONDecodeError as e:
        print(f"❌ JSON decode error: {e}")
        return False, {}, ["JSON_ERROR"]
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False, {}, ["UNEXPECTED_ERROR"]

def main():
    """Main function"""
    print("🚨 THRESHOLD ALERTS - CHECKING CRITICAL METRICS")
    print("=" * 50)
    
    # Check if API is available
    api_url = os.environ.get("OWLIN_API_URL", "http://localhost:8001")
    
    success, metrics, violations = check_thresholds(api_url)
    
    if not success:
        print("❌ CRITICAL: Failed to retrieve metrics")
        print("🚫 THRESHOLD CHECK FAILED")
        return 2
    
    if violations:
        print("\n🚨 CRITICAL THRESHOLD VIOLATIONS:")
        for violation in violations:
            print(f"   ❌ {violation}")
        
        print(f"\n🚫 THRESHOLD CHECK FAILED ({len(violations)} violations)")
        print("💡 REMEDIATION:")
        print("   - Check system logs for errors")
        print("   - Monitor resource usage (CPU, memory, disk)")
        print("   - Verify OCR service health")
        print("   - Check database connectivity")
        print("   - Review recent deployments")
        
        return 1
    else:
        print("\n✅ ALL THRESHOLDS WITHIN ACCEPTABLE LIMITS")
        print("🎉 THRESHOLD CHECK PASSED")
        return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 