#!/usr/bin/env python3
"""
Data Health API Routes

Provides endpoints for OCR metrics and system health monitoring
"""

import json
import subprocess
import sys
import logging
from pathlib import Path
from flask import Blueprint, jsonify, request, send_file
from io import BytesIO

from ..ocr.telemetry import get_telemetry_logger

logger = logging.getLogger(__name__)

data_health_bp = Blueprint('data_health', __name__)

@data_health_bp.route('/api/data-health/ocr-metrics', methods=['GET'])
def get_ocr_metrics():
    """Get OCR metrics summary"""
    try:
        days = request.args.get('days', 7, type=int)
        
        telemetry_logger = get_telemetry_logger()
        metrics = telemetry_logger.get_metrics_summary(days)
        
        return jsonify(metrics)
        
    except Exception as e:
        logger.error(f"❌ Failed to get OCR metrics: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@data_health_bp.route('/api/data-health/export-metrics', methods=['POST'])
def export_metrics():
    """Export OCR metrics to JSON file"""
    try:
        telemetry_logger = get_telemetry_logger()
        export_path = telemetry_logger.export_metrics()
        
        # Read the exported file
        with open(export_path, 'r') as f:
            content = f.read()
        
        # Create file-like object for download
        file_obj = BytesIO(content.encode('utf-8'))
        file_obj.seek(0)
        
        return send_file(
            file_obj,
            mimetype='application/json',
            as_attachment=True,
            download_name=f'ocr_metrics_{Path(export_path).name}'
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to export metrics: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@data_health_bp.route('/api/data-health/run-smoke-test', methods=['POST'])
def run_smoke_test():
    """Run smoke test and return results"""
    try:
        # Get the path to the smoke test script
        script_path = Path(__file__).parent.parent.parent / "scripts" / "smoke_test.py"
        
        if not script_path.exists():
            return jsonify({'error': 'Smoke test script not found'}), 404
        
        # Run the smoke test
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        if result.returncode == 0:
            # Parse the output to extract results
            # The smoke test prints results to stdout, so we need to parse them
            output_lines = result.stdout.split('\n')
            
            # Look for the summary section
            summary_start = None
            for i, line in enumerate(output_lines):
                if 'SMOKE TEST SUMMARY' in line:
                    summary_start = i
                    break
            
            if summary_start:
                # Extract key metrics from the output
                smoke_result = {
                    'total_tests': 8,  # Fixed for our smoke test
                    'passed': 8,  # Will be updated based on output
                    'failed': 0,
                    'pass_rate': 100.0,
                    'total_time': 0.0,
                    'all_passed': True,
                    'output': result.stdout
                }
                
                # Parse the output to get actual results
                for line in output_lines[summary_start:]:
                    if 'Total Tests:' in line:
                        smoke_result['total_tests'] = int(line.split(':')[1].strip())
                    elif 'Passed:' in line:
                        smoke_result['passed'] = int(line.split(':')[1].strip())
                    elif 'Failed:' in line:
                        smoke_result['failed'] = int(line.split(':')[1].strip())
                    elif 'Pass Rate:' in line:
                        smoke_result['pass_rate'] = float(line.split(':')[1].replace('%', '').strip())
                    elif 'Total Time:' in line:
                        smoke_result['total_time'] = float(line.split(':')[1].replace('s', '').strip())
                    elif 'SMOKE: PASS' in line:
                        smoke_result['all_passed'] = True
                    elif 'SMOKE: FAIL' in line:
                        smoke_result['all_passed'] = False
                
                return jsonify(smoke_result)
            else:
                return jsonify({'error': 'Could not parse smoke test output'}), 500
        else:
            return jsonify({
                'error': 'Smoke test failed',
                'stderr': result.stderr
            }), 500
        
    except Exception as e:
        logger.error(f"❌ Failed to run smoke test: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# Add route to Flask app
def init_app(app):
    """Initialize the data health blueprint"""
    app.register_blueprint(data_health_bp) 